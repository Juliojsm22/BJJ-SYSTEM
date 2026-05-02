from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Cliente, db

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

@clientes_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '')
    if q:
        clientes = Cliente.query.filter(
            (Cliente.nombre_completo.ilike(f'%{q}%')) |
            (Cliente.cedula.ilike(f'%{q}%')) |
            (Cliente.email.ilike(f'%{q}%'))
        ).filter_by(activo=True).order_by(Cliente.nombre_completo).all()
    else:
        clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()
    return render_template('clientes/index.html', clientes=clientes, q=q)

@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if request.method == 'POST':
        cedula = request.form.get('cedula').strip()
        if Cliente.query.filter_by(cedula=cedula).first():
            flash('Ya existe un cliente con esa cédula.', 'error')
            return render_template('clientes/form.html', cliente=None)
        
        cliente = Cliente(
            nombre_completo=request.form.get('nombre_completo').strip(),
            cedula=cedula,
            telefono=request.form.get('telefono').strip(),
            email=request.form.get('email').strip()
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente registrado exitosamente.', 'success')
        return redirect(url_for('clientes.index'))
    
    return render_template('clientes/form.html', cliente=None)

@clientes_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        cedula = request.form.get('cedula').strip()
        existente = Cliente.query.filter_by(cedula=cedula).first()
        if existente and existente.id != id:
            flash('Ya existe un cliente con esa cédula.', 'error')
            return render_template('clientes/form.html', cliente=cliente)
        
        cliente.nombre_completo = request.form.get('nombre_completo').strip()
        cliente.cedula = cedula
        cliente.telefono = request.form.get('telefono').strip()
        cliente.email = request.form.get('email').strip()
        db.session.commit()
        flash('Cliente actualizado correctamente.', 'success')
        return redirect(url_for('clientes.index'))
    
    return render_template('clientes/form.html', cliente=cliente)

@clientes_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    if current_user.rol != 'admin':
        flash('No tienes permisos para esto.', 'error')
        return redirect(url_for('clientes.index'))
    cliente = Cliente.query.get_or_404(id)
    cliente.activo = False
    db.session.commit()
    flash('Cliente eliminado.', 'success')
    return redirect(url_for('clientes.index'))

@clientes_bp.route('/buscar-json')
@login_required
def buscar_json():
    q = request.args.get('q', '')
    clientes = Cliente.query.filter(
        (Cliente.nombre_completo.ilike(f'%{q}%')) | (Cliente.cedula.ilike(f'%{q}%'))
    ).filter_by(activo=True).limit(10).all()
    return jsonify([{'id': c.id, 'nombre': c.nombre_completo, 'cedula': c.cedula} for c in clientes])

@clientes_bp.route('/detalle/<int:id>')
@login_required
def detalle(id):
    cliente = Cliente.query.get_or_404(id)
    return render_template('clientes/detalle.html', cliente=cliente)
