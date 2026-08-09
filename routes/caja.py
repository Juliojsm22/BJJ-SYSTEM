from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from models import Cliente, Factura, Pago, HistorialRastreo, db, registrar_actividad
from datetime import datetime

caja_bp = Blueprint('caja', __name__, url_prefix='/caja')

@caja_bp.before_request
def check_admin():
    if current_user.is_authenticated and current_user.rol != 'admin':
        flash('Acceso denegado. Solo los administradores pueden acceder a la Caja.', 'error')
        return redirect(url_for('paquetes.index'))

@caja_bp.route('/')
@login_required
def index():
    # Obtener todos los clientes activos para el buscador
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()
    return render_template('caja/index.html', clientes=clientes)

@caja_bp.route('/facturas-pendientes')
@login_required
def facturas_pendientes():
    cliente_id = request.args.get('cliente_id')
    busqueda = request.args.get('busqueda')
    
    query = Factura.query.options(joinedload(Factura.paquetes)).filter(
        Factura.estado.in_(['borrador', 'finalizada'])
    )
    
    if cliente_id:
        try:
            cliente_id = int(cliente_id)
            query = query.filter(Factura.cliente_id == cliente_id)
        except ValueError:
            return jsonify([])
    elif busqueda:
        # Búsqueda por número de factura o nombre de cliente
        busqueda_format = f"%{busqueda}%"
        query = query.join(Cliente).filter(
            db.or_(
                Factura.numero.ilike(busqueda_format),
                Cliente.nombre_completo.ilike(busqueda_format),
                Cliente.cedula.ilike(busqueda_format)
            )
        )
    else:
        return jsonify([])
        
    facturas = query.order_by(Factura.fecha_emision.desc()).all()
    
    resultados = []
    for f in facturas:
        total_val = float(f.total) if f.total is not None else 0.0
        resultados.append({
            'id': f.id,
            'numero': f.numero,
            'cliente_nombre': f.cliente.nombre_completo if f.cliente else 'Desconocido',
            'fecha_emision': f.fecha_emision.strftime('%d/%m/%Y %H:%M') if f.fecha_emision else '',
            'estado': f.estado,
            'total': total_val,
            'cantidad_paquetes': len(f.paquetes)
        })
        
    return jsonify(resultados)

@caja_bp.route('/procesar-pago', methods=['POST'])
@login_required
def procesar_pago():
    factura_id = request.form.get('factura_id')
    metodo_pago = request.form.get('metodo_pago', 'Efectivo')
    referencia = request.form.get('referencia', '')
    
    if not factura_id:
        return jsonify({'success': False, 'error': 'No se proporcionó la factura.'})
        
    factura = Factura.query.get(factura_id)
    if not factura:
        return jsonify({'success': False, 'error': 'Factura no encontrada.'})
        
    if factura.estado == 'pagada':
        return jsonify({'success': False, 'error': 'La factura ya se encuentra pagada.'})
        
    try:
        # Registrar el pago
        pago = Pago(
            factura_id=factura.id,
            monto=factura.total,
            metodo_pago=metodo_pago,
            referencia=referencia,
            registrado_por=current_user.id
        )
        db.session.add(pago)
        
        # Actualizar estado de la factura
        factura.estado = 'pagada'
        
        # Actualizar paquetes a 'entregado'
        for paquete in factura.paquetes:
            paquete.estado_rastreo = 'entregado'
            nuevo_historial = HistorialRastreo(
                paquete_id=paquete.id,
                estado='entregado',
                ubicacion='Caja',
                comentarios=f'Entregado tras pago en caja de factura {factura.numero}',
                creado_por=current_user.id
            )
            db.session.add(nuevo_historial)
            
        # Registrar actividad
        registrar_actividad(
            current_user.id, 
            'Cobro en Caja', 
            f'Pago de ${factura.total:.2f} con {metodo_pago} en factura {factura.numero}'
        )
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Factura {factura.numero} cobrada exitosamente con {metodo_pago}.',
            'factura_id': factura.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
