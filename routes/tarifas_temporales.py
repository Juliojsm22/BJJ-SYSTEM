from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, TarifaTemporal, Cliente
from datetime import datetime

tarifas_temporales_bp = Blueprint('tarifas_temporales', __name__, url_prefix='/tarifas-temporales')

@tarifas_temporales_bp.route('/')
@login_required
def index():
    if current_user.rol != 'admin':
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard.index'))
    
    tarifas = TarifaTemporal.query.order_by(TarifaTemporal.fecha_inicio.desc()).all()
    
    # Calcular estado dinámico (Vigente, Expirada, Futura)
    from models import get_local_now
    hoy = get_local_now().date()
    
    for t in tarifas:
        if hoy < t.fecha_inicio:
            t.estado_texto = "Programada"
            t.estado_clase = "badge-info"
        elif hoy > t.fecha_fin:
            t.estado_texto = "Expirada"
            t.estado_clase = "badge-secondary"
        else:
            t.estado_texto = "Vigente"
            t.estado_clase = "badge-success"
            
    return render_template('tarifas_temporales/index.html', tarifas=tarifas)

@tarifas_temporales_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    if current_user.rol != 'admin':
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('dashboard.index'))
        
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre').strip()
        cliente_id = request.form.get('cliente_id')
        aereo = request.form.get('aereo')
        maritimo = request.form.get('maritimo')
        fecha_inicio_str = request.form.get('fecha_inicio')
        fecha_fin_str = request.form.get('fecha_fin')
        
        if not nombre or not fecha_inicio_str or not fecha_fin_str:
            flash('Por favor completa todos los campos requeridos.', 'error')
            return redirect(url_for('tarifas_temporales.nueva'))
            
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            
            if fecha_inicio > fecha_fin:
                flash('La fecha de inicio no puede ser mayor a la fecha de fin.', 'error')
                return redirect(url_for('tarifas_temporales.nueva'))
                
            tarifa = TarifaTemporal(
                nombre=nombre,
                cliente_id=int(cliente_id) if cliente_id else None,
                aereo=float(aereo) if aereo else None,
                maritimo=float(maritimo) if maritimo else None,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                creado_por=current_user.id
            )
            
            db.session.add(tarifa)
            db.session.commit()
            
            # Recalcular paquetes pendientes dentro del rango de fechas
            from models import Paquete
            paquetes_pendientes = Paquete.query.filter(
                Paquete.factura_id == None,
                Paquete.registrado_en >= fecha_inicio,
                # Convertir fecha_fin a datetime hasta el final del día para comparar
                db.func.date(Paquete.registrado_en) <= fecha_fin
            ).all()
            
            if tarifa.cliente_id:
                paquetes_pendientes = [p for p in paquetes_pendientes if p.cliente_id == tarifa.cliente_id]
                
            actualizados = 0
            for p in paquetes_pendientes:
                nuevo_costo = p.calcular_costo()
                if p.costo != nuevo_costo:
                    p.costo = nuevo_costo
                    actualizados += 1
            
            if actualizados > 0:
                db.session.commit()
                flash(f'Tarifa temporal creada. Se recalcularon {actualizados} paquetes pendientes.', 'success')
            else:
                flash('Tarifa temporal creada exitosamente.', 'success')
                
            return redirect(url_for('tarifas_temporales.index'))
        except Exception as e:
            flash(f'Error al crear tarifa: {str(e)}', 'error')
            return redirect(url_for('tarifas_temporales.nueva'))
            
    return render_template('tarifas_temporales/form.html', tarifa=None, clientes=clientes)

@tarifas_temporales_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    if current_user.rol != 'admin':
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('dashboard.index'))
        
    tarifa = TarifaTemporal.query.get_or_404(id)
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()
    
    if request.method == 'POST':
        tarifa.nombre = request.form.get('nombre').strip()
        cliente_id = request.form.get('cliente_id')
        aereo = request.form.get('aereo')
        maritimo = request.form.get('maritimo')
        fecha_inicio_str = request.form.get('fecha_inicio')
        fecha_fin_str = request.form.get('fecha_fin')
        
        try:
            tarifa.cliente_id = int(cliente_id) if cliente_id else None
            tarifa.aereo = float(aereo) if aereo else None
            tarifa.maritimo = float(maritimo) if maritimo else None
            tarifa.fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            tarifa.fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            
            if tarifa.fecha_inicio > tarifa.fecha_fin:
                flash('La fecha de inicio no puede ser mayor a la fecha de fin.', 'error')
                return redirect(url_for('tarifas_temporales.editar', id=id))
                
            db.session.commit()
            
            # Recalcular paquetes pendientes dentro del rango de fechas
            from models import Paquete
            paquetes_pendientes = Paquete.query.filter(
                Paquete.factura_id == None,
                Paquete.registrado_en >= tarifa.fecha_inicio,
                db.func.date(Paquete.registrado_en) <= tarifa.fecha_fin
            ).all()
            
            if tarifa.cliente_id:
                paquetes_pendientes = [p for p in paquetes_pendientes if p.cliente_id == tarifa.cliente_id]
                
            actualizados = 0
            for p in paquetes_pendientes:
                nuevo_costo = p.calcular_costo()
                if p.costo != nuevo_costo:
                    p.costo = nuevo_costo
                    actualizados += 1
                    
            # También debemos recalcular paquetes cuyo costo deba volver a la normalidad si la tarifa se acortó
            # Para esto, podemos recalcular todos los paquetes pendientes que no tienen factura, es más seguro.
            todos_pendientes = Paquete.query.filter_by(factura_id=None).all()
            for p in todos_pendientes:
                if p not in paquetes_pendientes:
                    nuevo_costo = p.calcular_costo()
                    if p.costo != nuevo_costo:
                        p.costo = nuevo_costo
                        actualizados += 1
            
            if actualizados > 0:
                db.session.commit()
                flash(f'Tarifa actualizada. Se recalcularon {actualizados} paquetes pendientes.', 'success')
            else:
                flash('Tarifa temporal actualizada correctamente.', 'success')
                
            return redirect(url_for('tarifas_temporales.index'))
        except Exception as e:
            flash(f'Error al actualizar tarifa: {str(e)}', 'error')
            return redirect(url_for('tarifas_temporales.editar', id=id))
            
    return render_template('tarifas_temporales/form.html', tarifa=tarifa, clientes=clientes)

@tarifas_temporales_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    if current_user.rol != 'admin':
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('dashboard.index'))
        
    tarifa = TarifaTemporal.query.get_or_404(id)
    db.session.delete(tarifa)
    db.session.commit()
    flash('Tarifa temporal eliminada.', 'success')
    return redirect(url_for('tarifas_temporales.index'))
