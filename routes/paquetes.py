from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Paquete, Cliente, db
from datetime import datetime

paquetes_bp = Blueprint('paquetes', __name__, url_prefix='/paquetes')

@paquetes_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')

    query = Paquete.query.join(Cliente).filter(Cliente.activo == True)
    if q:
        query = query.filter(
            (Paquete.nombre.ilike(f'%{q}%')) |
            (Cliente.nombre_completo.ilike(f'%{q}%'))
        )
    if tipo:
        query = query.filter(Paquete.tipo_envio == tipo)
    if estado == 'sin_facturar':
        query = query.filter(Paquete.factura_id == None)
    elif estado == 'facturado':
        query = query.filter(Paquete.factura_id != None)

    paquetes = query.order_by(Paquete.registrado_en.desc()).all()
    return render_template('paquetes/index.html', paquetes=paquetes, q=q, tipo=tipo, estado=estado)

@paquetes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()
    cliente_id = request.args.get('cliente_id')

    if request.method == 'POST':
        peso = float(request.form.get('peso', 0))
        tipo_envio = request.form.get('tipo_envio')
        tarifa = 6.50 if tipo_envio == 'aereo' else 2.50
        costo = round(peso * tarifa, 2)

        paquete = Paquete(
            nombre=request.form.get('nombre').strip(),
            descripcion=request.form.get('descripcion', '').strip(),
            peso=peso,
            tipo_envio=tipo_envio,
            cliente_id=int(request.form.get('cliente_id')),
            estado_rastreo=request.form.get('estado_rastreo', 'bodega_miami'),
            registrado_por=current_user.id
        )
        paquete.save()
        flash(f'Paquete registrado. Costo: ${paquete.costo:.2f} | Guía: {paquete.tracking_number}', 'success')
        return redirect(url_for('paquetes.index'))

    return render_template('paquetes/form.html', clientes=clientes, cliente_id=cliente_id, paquete=None)

@paquetes_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    paquete = Paquete.query.get_or_404(id)
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()

    if paquete.factura_id:
        flash('No se puede editar un paquete ya facturado.', 'warning')
        return redirect(url_for('paquetes.index'))

    if request.method == 'POST':
        peso = float(request.form.get('peso', 0))
        tipo_envio = request.form.get('tipo_envio')
        tarifa = 6.50 if tipo_envio == 'aereo' else 2.50

        paquete.nombre = request.form.get('nombre').strip()
        paquete.descripcion = request.form.get('descripcion', '').strip()
        paquete.peso = peso
        paquete.tipo_envio = tipo_envio
        paquete.estado_rastreo = request.form.get('estado_rastreo', paquete.estado_rastreo)
        paquete.costo = round(peso * tarifa, 2)
        paquete.cliente_id = int(request.form.get('cliente_id'))
        db.session.commit()
        flash('Paquete actualizado.', 'success')
        return redirect(url_for('paquetes.index'))

    return render_template('paquetes/form.html', clientes=clientes, paquete=paquete, cliente_id=paquete.cliente_id)

@paquetes_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    paquete = Paquete.query.get_or_404(id)
    if paquete.factura_id:
        flash('No se puede eliminar un paquete facturado.', 'error')
        return redirect(url_for('paquetes.index'))
    db.session.delete(paquete)
    db.session.commit()
    flash('Paquete eliminado.', 'success')
    return redirect(url_for('paquetes.index'))

@paquetes_bp.route('/calcular-costo')
@login_required
def calcular_costo():
    peso = float(request.args.get('peso', 0))
    tipo = request.args.get('tipo', 'aereo')
    tarifa = 6.50 if tipo == 'aereo' else 2.50
    costo = round(peso * tarifa, 2)
    return jsonify({'costo': costo, 'tarifa': tarifa})
