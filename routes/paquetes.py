from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from models import Paquete, Cliente, db, HistorialRastreo, Tarifa
import io
import openpyxl

paquetes_bp = Blueprint('paquetes', __name__, url_prefix='/paquetes')

@paquetes_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')

    query = Paquete.query.options(joinedload(Paquete.cliente), joinedload(Paquete.factura)).join(Cliente).filter(Cliente.activo == True)
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
        cliente_id_form = int(request.form.get('cliente_id'))
        cliente = Cliente.query.get(cliente_id_form)
        
        nombres = request.form.getlist('nombre[]')
        descripciones = request.form.getlist('descripcion[]')
        pesos = request.form.getlist('peso[]')
        tipos_envio = request.form.getlist('tipo_envio[]')
        numeros_seguimiento = request.form.getlist('numero_seguimiento[]')
        estados_rastreo = request.form.getlist('estado_rastreo[]')
        
        # Validar números de seguimiento duplicados antes de guardar
        for num in numeros_seguimiento:
            if num.strip():
                existente = Paquete.query.filter_by(numero_seguimiento=num.strip()).first()
                if existente:
                    flash(f'El número de seguimiento "{num.strip()}" ya está registrado en el paquete {existente.tracking_number}.', 'error')
                    return redirect(request.url)
                    
        paquetes_creados = []
        costo_total = 0
        
        for i in range(len(nombres)):
            peso = float(pesos[i] if pesos[i] else 0)
            tipo_envio = tipos_envio[i]
            numero_seg = numeros_seguimiento[i].strip()
            
            tarifa = None
            if cliente and cliente.tarifa_especial:
                if tipo_envio == 'aereo' and cliente.tarifa_especial.aereo is not None:
                    tarifa = cliente.tarifa_especial.aereo
                elif tipo_envio == 'maritimo' and cliente.tarifa_especial.maritimo is not None:
                    tarifa = cliente.tarifa_especial.maritimo
                    
            if tarifa is None:
                tarifa_db = Tarifa.query.filter_by(nombre=tipo_envio).first()
                tarifa = tarifa_db.precio_por_libra if tarifa_db else (6.50 if tipo_envio == 'aereo' else 2.50)
                
            paquete = Paquete(
                nombre=nombres[i].strip(),
                descripcion=descripciones[i].strip() if i < len(descripciones) else '',
                peso=peso,
                tipo_envio=tipo_envio,
                cliente_id=cliente_id_form,
                numero_seguimiento=numero_seg,
                estado_rastreo=estados_rastreo[i] if i < len(estados_rastreo) else 'bodega_miami',
                registrado_por=current_user.id
            )
            paquete.save()
            costo_total += paquete.costo
            paquetes_creados.append(paquete)
            
            historial_inicial = HistorialRastreo(
                paquete_id=paquete.id,
                estado=paquete.estado_rastreo,
                ubicacion='Miami',
                comentarios='Paquete registrado en el sistema',
                creado_por=current_user.id
            )
            db.session.add(historial_inicial)
            
        db.session.commit()
        
        if paquetes_creados:
            from models import registrar_actividad
            registrar_actividad(current_user.id, 'Registró Paquetes', f'Registró {len(paquetes_creados)} paquete(s) para {cliente.nombre_completo}')
            
            accion = request.form.get('accion')
            if accion == 'facturar':
                from models import Factura
                factura = Factura(
                    numero=Factura.generar_numero(),
                    cliente_id=cliente.id,
                    notas='',
                    creado_por=current_user.id,
                    estado='borrador'
                )
                db.session.add(factura)
                db.session.flush()

                for p in paquetes_creados:
                    p.factura_id = factura.id
                
                factura.actualizar_total()
                db.session.commit()
                
                registrar_actividad(current_user.id, 'Creó Factura', f'Factura {factura.numero} generada automáticamente')
                flash(f'Paquetes registrados y factura {factura.numero} creada con éxito.', 'success')
                return redirect(url_for('facturas.detalle', id=factura.id))
            
            flash(f'Se registraron {len(paquetes_creados)} paquete(s) con éxito. Costo total estimado: ${costo_total:.2f}', 'success')
            
        return redirect(url_for('paquetes.index'))

    return render_template('paquetes/nuevo.html', clientes=clientes, cliente_id=cliente_id)

@paquetes_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    paquete = Paquete.query.get_or_404(id)
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre_completo).all()

    if paquete.factura_id and current_user.rol != 'admin':
        flash('Solo los administradores pueden editar un paquete ya facturado.', 'warning')
        return redirect(url_for('paquetes.index'))

    if request.method == 'POST':
        peso = float(request.form.get('peso', 0))
        tipo_envio = request.form.get('tipo_envio')
        cliente_id = int(request.form.get('cliente_id'))
        
        cliente = Cliente.query.get(cliente_id)
        tarifa = None
        if cliente and cliente.tarifa_especial:
            if tipo_envio == 'aereo' and cliente.tarifa_especial.aereo is not None:
                tarifa = cliente.tarifa_especial.aereo
            elif tipo_envio == 'maritimo' and cliente.tarifa_especial.maritimo is not None:
                tarifa = cliente.tarifa_especial.maritimo
                
        if tarifa is None:
            tarifa_db = Tarifa.query.filter_by(nombre=tipo_envio).first()
            tarifa = tarifa_db.precio_por_libra if tarifa_db else (6.50 if tipo_envio == 'aereo' else 2.50)

        numero_seguimiento = request.form.get('numero_seguimiento', '').strip()
        if numero_seguimiento and numero_seguimiento != paquete.numero_seguimiento:
            existente = Paquete.query.filter_by(numero_seguimiento=numero_seguimiento).first()
            if existente:
                flash(f'El número de seguimiento "{numero_seguimiento}" ya está registrado en el paquete {existente.tracking_number}.', 'error')
                return redirect(request.url)

        paquete.nombre = request.form.get('nombre').strip()
        paquete.descripcion = request.form.get('descripcion', '').strip()
        paquete.peso = peso
        paquete.tipo_envio = tipo_envio
        paquete.numero_seguimiento = numero_seguimiento
        paquete.estado_rastreo = request.form.get('estado_rastreo', paquete.estado_rastreo)
        paquete.costo = round(peso * tarifa, 2)
        paquete.cliente_id = int(request.form.get('cliente_id'))
        
        if paquete.factura:
            paquete.factura.actualizar_total()
            
        db.session.commit()
        
        from models import registrar_actividad
        registrar_actividad(current_user.id, 'Editó Paquete', f'Actualizó paquete {paquete.tracking_number}')
        
        flash('Paquete actualizado.', 'success')
        return redirect(url_for('paquetes.index'))

    return render_template('paquetes/form.html', clientes=clientes, paquete=paquete, cliente_id=paquete.cliente_id)

@paquetes_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    if current_user.rol != 'admin':
        flash('Solo los administradores pueden eliminar paquetes.', 'error')
        return redirect(url_for('paquetes.index'))
        
    paquete = Paquete.query.get_or_404(id)
    if paquete.factura_id:
        flash('No se puede eliminar un paquete facturado.', 'error')
        return redirect(url_for('paquetes.index'))
    db.session.delete(paquete)
    db.session.commit()
    
    from models import registrar_actividad
    registrar_actividad(current_user.id, 'Eliminó Paquete', f'Eliminó paquete {paquete.tracking_number}')
    
    flash('Paquete eliminado.', 'success')
    return redirect(url_for('paquetes.index'))

@paquetes_bp.route('/calcular-costo')
@login_required
def calcular_costo():
    peso = float(request.args.get('peso', 0))
    tipo = request.args.get('tipo', 'aereo')
    cliente_id = request.args.get('cliente_id')
    
    tarifa = None
    if cliente_id:
        cliente = Cliente.query.get(int(cliente_id))
        if cliente and cliente.tarifa_especial:
            if tipo == 'aereo' and cliente.tarifa_especial.aereo is not None:
                tarifa = cliente.tarifa_especial.aereo
            elif tipo == 'maritimo' and cliente.tarifa_especial.maritimo is not None:
                tarifa = cliente.tarifa_especial.maritimo
                
    if tarifa is None:
        tarifa_db = Tarifa.query.filter_by(nombre=tipo).first()
        tarifa = tarifa_db.precio_por_libra if tarifa_db else (6.50 if tipo == 'aereo' else 2.50)
        
    costo = round(peso * tarifa, 2)
    return jsonify({'costo': costo, 'tarifa': tarifa})

@paquetes_bp.route('/tarifas-cliente')
@login_required
def tarifas_cliente():
    cliente_id = request.args.get('cliente_id')
    
    t_aereo = Tarifa.query.filter_by(nombre='aereo').first()
    t_maritimo = Tarifa.query.filter_by(nombre='maritimo').first()
    
    precio_aereo = t_aereo.precio_por_libra if t_aereo else 6.50
    precio_maritimo = t_maritimo.precio_por_libra if t_maritimo else 2.50
    
    if cliente_id:
        cliente = Cliente.query.get(int(cliente_id))
        if cliente and cliente.tarifa_especial:
            if cliente.tarifa_especial.aereo is not None:
                precio_aereo = cliente.tarifa_especial.aereo
            if cliente.tarifa_especial.maritimo is not None:
                precio_maritimo = cliente.tarifa_especial.maritimo
                
    return jsonify({
        'aereo': precio_aereo,
        'maritimo': precio_maritimo
    })

@paquetes_bp.route('/<int:id>/historial', methods=['GET', 'POST'])
@login_required
def historial(id):
    paquete = Paquete.query.get_or_404(id)
    if request.method == 'POST':
        estado = request.form.get('estado').strip()
        ubicacion = request.form.get('ubicacion', '').strip()
        comentarios = request.form.get('comentarios', '').strip()

        if estado:
            nuevo_historial = HistorialRastreo(
                paquete_id=paquete.id,
                estado=estado,
                ubicacion=ubicacion,
                comentarios=comentarios,
                creado_por=current_user.id
            )
            paquete.estado_rastreo = estado
            db.session.add(nuevo_historial)
            db.session.commit()
            
            from models import registrar_actividad
            registrar_actividad(current_user.id, 'Actualizó Rastreo', f'Paquete {paquete.tracking_number} a estado "{estado}"')
            
            flash('Historial actualizado correctamente.', 'success')
            return redirect(url_for('paquetes.historial', id=paquete.id))

    return render_template('paquetes/historial.html', paquete=paquete)

@paquetes_bp.route('/exportar')
@login_required
def exportar():
    q = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')
    filtro_fecha = request.args.get('filtro_fecha', '')
    mes = request.args.get('mes', '')
    semana = request.args.get('semana', '')

    query = Paquete.query.options(joinedload(Paquete.cliente), joinedload(Paquete.factura)).join(Cliente).filter(Cliente.activo == True)
    if q:
        query = query.filter(
            (Paquete.nombre.ilike(f'%{q}%')) |
            (Cliente.nombre_completo.ilike(f'%{q}%')) |
            (Paquete.numero_seguimiento.ilike(f'%{q}%'))
        )
    if tipo:
        query = query.filter(Paquete.tipo_envio == tipo)
    if estado == 'sin_facturar':
        query = query.filter(Paquete.factura_id == None)
    elif estado == 'facturado':
        query = query.filter(Paquete.factura_id != None)

    if filtro_fecha == 'mes' and mes:
        year, month = map(int, mes.split('-'))
        import calendar
        from datetime import datetime
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        query = query.filter(Paquete.registrado_en >= start_date, Paquete.registrado_en <= end_date)
    elif filtro_fecha == 'semana' and semana:
        from datetime import datetime, timedelta
        year_str, week_str = semana.split('-W')
        start_date = datetime.strptime(semana + '-1', '%G-W%V-%u')
        end_date = start_date + timedelta(days=7)
        query = query.filter(Paquete.registrado_en >= start_date, Paquete.registrado_en < end_date)

    paquetes = query.order_by(Paquete.registrado_en.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Paquetes"

    headers = ['ID', 'Tracking (Sistema)', 'Guía Rastreo', 'Cliente', 'Contenido', 'Peso (lb)', 'Tipo', 'Costo', 'Estado Actual', 'Facturado', 'Fecha Registro']
    ws.append(headers)

    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True, color='FFFFFF')
        cell.fill = openpyxl.styles.PatternFill(start_color='3D5BA0', end_color='3D5BA0', fill_type='solid')

    import re
    def clean_text(val):
        if isinstance(val, str):
            return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', val)
        return val

    for p in paquetes:
        row = [
            p.id,
            p.tracking_number,
            p.numero_seguimiento or '',
            p.cliente.nombre_completo,
            p.nombre,
            p.peso,
            p.tipo_envio.upper() if p.tipo_envio else '',
            p.costo,
            p.estado_rastreo.replace('_', ' ').title() if p.estado_rastreo else '',
            'SÍ' if p.factura_id else 'NO',
            p.registrado_en.strftime('%Y-%m-%d %H:%M') if p.registrado_en else ''
        ]
        ws.append([clean_text(v) for v in row])

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        ws.column_dimensions[column].width = (max_length + 2)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    from datetime import datetime
    filename = f"Paquetes_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
