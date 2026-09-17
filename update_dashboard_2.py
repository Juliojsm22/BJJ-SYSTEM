import re

with open('routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# For pdf-reporte
pdf_old = '''@dashboard_bp.route('/pdf-reporte')
@login_required
def pdf_reporte():
    if current_user.rol != 'admin':
        flash('No tienes permisos.', 'error')
        return redirect(url_for('paquetes.index'))
        
    from flask import make_response
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    import os

    periodo = request.args.get('periodo', 'mes')
    hoy = get_local_now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)'''

pdf_new = '''@dashboard_bp.route('/pdf-reporte')
@login_required
def pdf_reporte():
    if current_user.rol != 'admin':
        flash('No tienes permisos.', 'error')
        return redirect(url_for('paquetes.index'))
        
    from flask import make_response
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    import os

    periodo = request.args.get('periodo', 'mes')
    mes_historico = request.args.get('mes_historico')
    hoy = get_local_now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if periodo == 'historico' and mes_historico:
        year, month = map(int, mes_historico.split('-'))
        inicio_periodo = hoy.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        inicio_periodo = hoy
'''
if pdf_old in content:
    content = content.replace(pdf_old, pdf_new)


# For exportar_excel
excel_old = '''    periodo = request.args.get('periodo', 'mes')
    hoy = get_local_now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if periodo == 'dia':
        inicio_periodo = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        titulo_periodo = 'Diario'
    elif periodo == 'semana':
        inicio_periodo = inicio_semana
        titulo_periodo = 'Semanal'
    else:  # mes
        inicio_periodo = inicio_mes
        titulo_periodo = 'Mensual'

    # 1. KPIs Globales
    ganancia_periodo = calcular_ganancia_facturas(inicio_periodo)
    total_clientes = Cliente.query.filter_by(activo=True).count()
    total_paquetes = Paquete.query.count()
    aereos = Paquete.query.join(Factura).filter(
        Paquete.tipo_envio == 'aereo',
        Factura.estado.in_(['finalizada', 'pagada']),
        Factura.fecha_emision >= inicio_periodo
    ).count()
    maritimos = Paquete.query.join(Factura).filter(
        Paquete.tipo_envio == 'maritimo',
        Factura.estado.in_(['finalizada', 'pagada']),
        Factura.fecha_emision >= inicio_periodo
    ).count()'''

excel_new = '''    periodo = request.args.get('periodo', 'mes')
    mes_historico = request.args.get('mes_historico')
    hoy = get_local_now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    fin_periodo = None

    if periodo == 'historico' and mes_historico:
        year, month = map(int, mes_historico.split('-'))
        inicio_periodo = hoy.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        if month == 12:
            fin_periodo = hoy.replace(year=year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            fin_periodo = hoy.replace(year=year, month=month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
        titulo_periodo = f'Histórico ({mes_historico})'
    elif periodo == 'dia':
        inicio_periodo = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        titulo_periodo = 'Diario'
    elif periodo == 'semana':
        inicio_periodo = inicio_semana
        titulo_periodo = 'Semanal'
    else:  # mes
        inicio_periodo = inicio_mes
        titulo_periodo = 'Mensual'
        
    filtros_fecha = [Factura.fecha_emision >= inicio_periodo]
    if fin_periodo:
        filtros_fecha.append(Factura.fecha_emision < fin_periodo)

    # 1. KPIs Globales
    ganancia_periodo = calcular_ganancia_facturas(inicio_periodo, fin_periodo)
    total_clientes = Cliente.query.filter_by(activo=True).count()
    total_paquetes = Paquete.query.count()
    
    aereos = Paquete.query.join(Factura).filter(
        Paquete.tipo_envio == 'aereo',
        Factura.estado.in_(['finalizada', 'pagada']),
        *filtros_fecha
    ).count()
    maritimos = Paquete.query.join(Factura).filter(
        Paquete.tipo_envio == 'maritimo',
        Factura.estado.in_(['finalizada', 'pagada']),
        *filtros_fecha
    ).count()'''
if excel_old in content:
    content = content.replace(excel_old, excel_new)

excel_loop_old = '''    if periodo == 'dia':
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=1)
            total = calcular_ganancia_facturas(inicio, fin)
            lbl = inicio.strftime('%d %b')
            ws2.append([lbl if i != 0 else "Hoy", total])
    elif periodo == 'semana':
        for i in range(3, -1, -1):
            inicio = inicio_semana - timedelta(days=7 * i)
            fin = inicio + timedelta(days=7)
            total = calcular_ganancia_facturas(inicio, fin)
            lbl = f"{inicio.strftime('%d %b')} - {(fin - timedelta(days=1)).strftime('%d %b')}"
            ws2.append([lbl if i != 0 else "Esta Semana", total])
    else:
        for i in range(5, -1, -1):
            target_month = hoy.month - i
            target_year = hoy.year
            while target_month <= 0:
                target_month += 12; target_year -= 1
            inicio = hoy.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if target_month == 12: fin = hoy.replace(year=target_year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else: fin = hoy.replace(year=target_year, month=target_month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
            total = calcular_ganancia_facturas(inicio, fin)
            ws2.append([inicio.strftime('%b %Y'), total])'''

excel_loop_new = '''    if periodo == 'dia':
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=1)
            total = calcular_ganancia_facturas(inicio, fin)
            lbl = inicio.strftime('%d %b')
            ws2.append([lbl if i != 0 else "Hoy", total])
    elif periodo == 'semana':
        for i in range(3, -1, -1):
            inicio = inicio_semana - timedelta(days=7 * i)
            fin = inicio + timedelta(days=7)
            total = calcular_ganancia_facturas(inicio, fin)
            lbl = f"{inicio.strftime('%d %b')} - {(fin - timedelta(days=1)).strftime('%d %b')}"
            ws2.append([lbl if i != 0 else "Esta Semana", total])
    else:
        base_date = inicio_periodo if periodo == 'historico' else hoy
        for i in range(5, -1, -1):
            target_month = base_date.month - i
            target_year = base_date.year
            while target_month <= 0:
                target_month += 12; target_year -= 1
            inicio = base_date.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if target_month == 12: fin = base_date.replace(year=target_year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else: fin = base_date.replace(year=target_year, month=target_month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
            total = calcular_ganancia_facturas(inicio, fin)
            ws2.append([inicio.strftime('%b %Y'), total])'''
if excel_loop_old in content:
    content = content.replace(excel_loop_old, excel_loop_new)
    
excel_q_old = '''    top_clientes = db.session.query(
        Cliente.nombre_completo,
        func.sum(Paquete.peso).label('total_libras'),
        func.count(Paquete.id).label('total_paquetes')
    ).join(Factura, Cliente.id == Factura.cliente_id).join(Paquete, Factura.id == Paquete.factura_id).filter(
        Cliente.activo == True, Factura.estado.in_(['finalizada', 'pagada']), Factura.fecha_emision >= inicio_periodo
    ).group_by(Cliente.id).order_by(func.sum(Paquete.peso).desc()).limit(10).all()'''

excel_q_new = '''    top_clientes = db.session.query(
        Cliente.nombre_completo,
        func.sum(Paquete.peso).label('total_libras'),
        func.count(Paquete.id).label('total_paquetes')
    ).join(Factura, Cliente.id == Factura.cliente_id).join(Paquete, Factura.id == Paquete.factura_id).filter(
        Cliente.activo == True, Factura.estado.in_(['finalizada', 'pagada']), *filtros_fecha
    ).group_by(Cliente.id).order_by(func.sum(Paquete.peso).desc()).limit(10).all()'''
if excel_q_old in content:
    content = content.replace(excel_q_old, excel_q_new)

excel_f_old = '''    facturas = Factura.query.options(joinedload(Factura.paquetes)).filter(
        Factura.estado.in_(['finalizada', 'pagada']),
        Factura.fecha_emision >= inicio_periodo
    ).order_by(Factura.fecha_emision.desc()).all()'''
excel_f_new = '''    facturas = Factura.query.options(joinedload(Factura.paquetes)).filter(
        Factura.estado.in_(['finalizada', 'pagada']),
        *filtros_fecha
    ).order_by(Factura.fecha_emision.desc()).all()'''
if excel_f_old in content:
    content = content.replace(excel_f_old, excel_f_new)
    
with open('routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
