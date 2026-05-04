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
        db.session.flush() # Para obtener el ID del cliente
        
        tarifa_aereo = request.form.get('tarifa_aereo')
        tarifa_maritimo = request.form.get('tarifa_maritimo')
        
        if tarifa_aereo or tarifa_maritimo:
            from models import TarifaEspecialCliente
            tarifa_esp = TarifaEspecialCliente(
                cliente_id=cliente.id,
                aereo=float(tarifa_aereo) if tarifa_aereo else None,
                maritimo=float(tarifa_maritimo) if tarifa_maritimo else None
            )
            db.session.add(tarifa_esp)
            
        db.session.commit()
        
        from models import registrar_actividad
        registrar_actividad(current_user.id, 'Registró Cliente', f'Cliente {cliente.nombre_completo} (Cédula: {cliente.cedula})')
        
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
        
        tarifa_aereo = request.form.get('tarifa_aereo')
        tarifa_maritimo = request.form.get('tarifa_maritimo')
        
        from models import TarifaEspecialCliente, Paquete, Tarifa
        if tarifa_aereo or tarifa_maritimo:
            if not cliente.tarifa_especial:
                cliente.tarifa_especial = TarifaEspecialCliente(cliente_id=cliente.id)
            cliente.tarifa_especial.aereo = float(tarifa_aereo) if tarifa_aereo else None
            cliente.tarifa_especial.maritimo = float(tarifa_maritimo) if tarifa_maritimo else None
        else:
            if cliente.tarifa_especial:
                db.session.delete(cliente.tarifa_especial)
                
        # Recalcular costos de paquetes pendientes
        t_aereo = Tarifa.query.filter_by(nombre='aereo').first()
        t_maritimo = Tarifa.query.filter_by(nombre='maritimo').first()
        precio_aereo_base = t_aereo.precio_por_libra if t_aereo else 6.50
        precio_maritimo_base = t_maritimo.precio_por_libra if t_maritimo else 2.50
        
        paquetes_pendientes = Paquete.query.filter_by(cliente_id=cliente.id, factura_id=None).all()
        for p in paquetes_pendientes:
            tarifa_p = None
            if cliente.tarifa_especial:
                if p.tipo_envio == 'aereo' and cliente.tarifa_especial.aereo is not None:
                    tarifa_p = cliente.tarifa_especial.aereo
                elif p.tipo_envio == 'maritimo' and cliente.tarifa_especial.maritimo is not None:
                    tarifa_p = cliente.tarifa_especial.maritimo
            
            if tarifa_p is None:
                tarifa_p = precio_aereo_base if p.tipo_envio == 'aereo' else precio_maritimo_base
                
            p.costo = round(p.peso * tarifa_p, 2)

        db.session.commit()
        
        from models import registrar_actividad
        registrar_actividad(current_user.id, 'Editó Cliente', f'Actualizó perfil de {cliente.nombre_completo}')
        
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
    
    from models import registrar_actividad
    registrar_actividad(current_user.id, 'Eliminó Cliente', f'Desactivó a {cliente.nombre_completo}')
    
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
