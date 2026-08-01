from flask import Blueprint, render_template, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Cliente, Paquete, Factura, db, get_local_now
from datetime import datetime, timedelta
from sqlalchemy import func, case

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

from flask import request

@dashboard_bp.route('/')
@login_required
def index():
    if current_user.rol != 'admin':
        return redirect(url_for('paquetes.index'))
        
    periodo = request.args.get('periodo', 'mes')
    hoy = get_local_now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if periodo == 'dia':
        inicio_periodo = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'semana':
        inicio_periodo = inicio_semana
    else:  # mes
        inicio_periodo = inicio_mes

    ganancia_expr = case(
        (Paquete.tipo_envio == 'aereo', Paquete.costo - (Paquete.peso * 5.0)),
        (Paquete.tipo_envio == 'maritimo', Paquete.costo - (Paquete.peso * 1.6)),
        else_=0
    )

    ganancias_semana = db.session.query(func.sum(ganancia_expr)).filter(
        Paquete.registrado_en >= inicio_semana
    ).scalar() or 0

    ganancias_mes = db.session.query(func.sum(ganancia_expr)).filter(
        Paquete.registrado_en >= inicio_mes
    ).scalar() or 0

    total_clientes = Cliente.query.filter_by(activo=True).count()
    total_paquetes = Paquete.query.count()
    paquetes_sin_facturar = Paquete.query.filter_by(factura_id=None).count()
    facturas_pendientes = Factura.query.filter_by(estado='borrador').count()

    top_clientes = db.session.query(
        Cliente.nombre_completo,
        func.sum(Paquete.peso).label('total_libras'),
        func.count(Paquete.id).label('total_paquetes')
    ).join(Paquete, Cliente.id == Paquete.cliente_id)\
     .filter(Cliente.activo == True, Paquete.registrado_en >= inicio_periodo)\
     .group_by(Cliente.id)\
     .order_by(func.sum(Paquete.peso).desc())\
     .limit(5).all()

    tendencia_labels = []
    tendencia_valores = []

    if periodo == 'dia':
        # Últimos 7 días
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=1)
            total = db.session.query(func.sum(ganancia_expr)).filter(
                Paquete.registrado_en >= inicio,
                Paquete.registrado_en < fin
            ).scalar() or 0
            
            lbl = inicio.strftime('%d %b')
            if i == 0: lbl = "Hoy"
            tendencia_labels.append(lbl)
            tendencia_valores.append(float(total))

    elif periodo == 'semana':
        # Últimas 4 semanas
        for i in range(3, -1, -1):
            inicio = inicio_semana - timedelta(days=7 * i)
            fin = inicio + timedelta(days=7)
            total = db.session.query(func.sum(ganancia_expr)).filter(
                Paquete.registrado_en >= inicio,
                Paquete.registrado_en < fin
            ).scalar() or 0
            
            lbl = f"{inicio.strftime('%d %b')}"
            if i == 0: lbl = "Esta Sem"
            tendencia_labels.append(lbl)
            tendencia_valores.append(float(total))

    else:
        # Últimos 6 meses
        for i in range(5, -1, -1):
            target_month = hoy.month - i
            target_year = hoy.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
                
            inicio = hoy.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if target_month == 12:
                fin = hoy.replace(year=target_year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                fin = hoy.replace(year=target_year, month=target_month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
                
            total = db.session.query(func.sum(ganancia_expr)).filter(
                Paquete.registrado_en >= inicio,
                Paquete.registrado_en < fin
            ).scalar() or 0
            tendencia_labels.append(inicio.strftime('%b %Y'))
            tendencia_valores.append(float(total))

    aereos = Paquete.query.filter(Paquete.tipo_envio == 'aereo', Paquete.registrado_en >= inicio_periodo).count()
    maritimos = Paquete.query.filter(Paquete.tipo_envio == 'maritimo', Paquete.registrado_en >= inicio_periodo).count()

    # Legacy variables for tables
    meses_data = []
    semanas_data = []
    for i in range(len(tendencia_labels)):
        item = {'total': tendencia_valores[i]}
        if periodo == 'mes':
            item['mes'] = tendencia_labels[i]
            meses_data.append(item)
        elif periodo == 'semana':
            item['semana'] = tendencia_labels[i]
            semanas_data.append(item)
        else:
            item['dia'] = tendencia_labels[i]
            # Usar semanas_data para no romper la tabla de abajo, adaptándola en el HTML
            item['semana'] = tendencia_labels[i] 
            semanas_data.append(item)

    return render_template('dashboard/index.html',
        periodo=periodo,
        ganancias_semana=ganancias_semana,
        ganancias_mes=ganancias_mes,
        total_clientes=total_clientes,
        total_paquetes=total_paquetes,
        paquetes_sin_facturar=paquetes_sin_facturar,
        facturas_pendientes=facturas_pendientes,
        top_clientes=top_clientes,
        meses_data=meses_data,
        semanas_data=semanas_data,
        tendencia_labels=tendencia_labels,
        tendencia_valores=tendencia_valores,
        aereos=aereos,
        maritimos=maritimos
    )

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    hoy = get_local_now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ganancia_expr = case(
        (Paquete.tipo_envio == 'aereo', Paquete.costo - (Paquete.peso * 5.0)),
        (Paquete.tipo_envio == 'maritimo', Paquete.costo - (Paquete.peso * 1.6)),
        else_=0
    )
    ganancias_mes = db.session.query(func.sum(ganancia_expr)).filter(
        Paquete.registrado_en >= inicio_mes
    ).scalar() or 0
    return jsonify({'ganancias_mes': float(ganancias_mes)})

@dashboard_bp.route('/pdf-reporte')
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
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    ganancia_expr = case(
        (Paquete.tipo_envio == 'aereo', Paquete.costo - (Paquete.peso * 5.0)),
        (Paquete.tipo_envio == 'maritimo', Paquete.costo - (Paquete.peso * 1.6)),
        else_=0
    )

    tendencia_data = []
    titulo_tabla = ""
    encabezado_columna = ""

    if periodo == 'dia':
        titulo_tabla = 'Resumen Diario (Últimos 7 Días)'
        encabezado_columna = 'Día'
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=1)
            total = db.session.query(func.sum(ganancia_expr)).filter(
                Paquete.registrado_en >= inicio,
                Paquete.registrado_en < fin
            ).scalar() or 0
            
            lbl = inicio.strftime('%d %b')
            if i == 0: lbl = "Hoy"
            tendencia_data.append([lbl, f'${total:.2f}'])

    elif periodo == 'semana':
        titulo_tabla = 'Resumen Semanal (Últimas 4 Semanas)'
        encabezado_columna = 'Semana'
        for i in range(3, -1, -1):
            inicio = inicio_semana - timedelta(days=7 * i)
            fin = inicio + timedelta(days=7)
            total = db.session.query(func.sum(ganancia_expr)).filter(
                Paquete.registrado_en >= inicio,
                Paquete.registrado_en < fin
            ).scalar() or 0
            
            lbl = f"{inicio.strftime('%d %b')} - {(fin - timedelta(days=1)).strftime('%d %b')}"
            if i == 0: lbl = "Esta Semana"
            tendencia_data.append([lbl, f'${total:.2f}'])

    else:
        titulo_tabla = 'Resumen Mensual (Últimos 6 Meses)'
        encabezado_columna = 'Mes'
        for i in range(5, -1, -1):
            target_month = hoy.month - i
            target_year = hoy.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
                
            inicio = hoy.replace(year=target_year, month=target_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if target_month == 12:
                fin = hoy.replace(year=target_year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                fin = hoy.replace(year=target_year, month=target_month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
                
            total = db.session.query(func.sum(ganancia_expr)).filter(
                Paquete.registrado_en >= inicio,
                Paquete.registrado_en < fin
            ).scalar() or 0
            tendencia_data.append([inicio.strftime('%b %Y'), f'${total:.2f}'])

    # Reverse data so most recent is at top, like in HTML
    tendencia_data.reverse()

    buffer = io.BytesIO()
    numero_reporte = f"REP-{hoy.strftime('%Y%m%d%H%M')}"
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch, title=f"Reporte Financiero {numero_reporte}", author="BJJ SYSTEM")
    styles = getSampleStyleSheet()
    story = []

    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'logoazul.PNG')
    if os.path.exists(logo_path):
        header_left = Image(logo_path, width=3.0*inch, height=1.0*inch, kind='proportional')
        header_left.hAlign = 'CENTER'
        story.append(header_left)
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f'<font size=18 color="#3d5ba0"><b>REPORTE FINANCIERO ({periodo.upper()})</b></font>', styles['Title']))
    story.append(Paragraph(f'<font size=10 color="#666666">Generado el: {hoy.strftime("%d/%m/%Y %H:%M")}</font>', styles['Title']))
    story.append(Spacer(1, 0.5*inch))

    story.append(Paragraph(f'<b>{titulo_tabla}</b>', styles['Heading3']))
    story.append(Spacer(1, 0.1*inch))
    t_data = Table([[encabezado_columna, 'Ganancia Neta']] + tendencia_data, colWidths=[4*inch, 2*inch])
    t_data.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3d5ba0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_data)

    doc.build(story)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=reporte-financiero-{hoy.strftime("%Y%m%d")}.pdf'
    return response

@dashboard_bp.route('/fix-timezones')
@login_required
def fix_timezones():
    if current_user.rol != 'admin':
        flash('No tienes permisos.', 'error')
        return redirect(url_for('dashboard.index'))
        
    from models import Pago, HistorialRastreo, RegistroActividad
    
    # Bandera para saber si ya se corrigió
    ya_corregido = Factura.query.filter(Factura.fecha_emision < datetime(2025, 1, 1)).first()
    if ya_corregido:
        flash('Las fechas ya fueron corregidas anteriormente.', 'info')
        return redirect(url_for('dashboard.index'))
    
    # Restar 6 horas a todos los registros
    for c in Cliente.query.all():
        if c.creado_en: c.creado_en -= timedelta(hours=6)
    
    for p in Paquete.query.all():
        if p.registrado_en: p.registrado_en -= timedelta(hours=6)
        
    for f in Factura.query.all():
        if f.fecha_emision: f.fecha_emision -= timedelta(hours=6)
        
    for p in Pago.query.all():
        if p.fecha_pago: p.fecha_pago -= timedelta(hours=6)
        
    for h in HistorialRastreo.query.all():
        if h.creado_en: h.creado_en -= timedelta(hours=6)
        
    for r in RegistroActividad.query.all():
        if r.fecha: r.fecha -= timedelta(hours=6)
        
    # Crear un registro viejo falso para marcar que ya se corrigió y evitar doble resta
    falso = Factura(numero='FIX-TZ', cliente_id=1, fecha_emision=datetime(2020, 1, 1))
    db.session.add(falso)
    
    db.session.commit()
    flash('Se han corregido las horas de todos los registros antiguos exitosamente.', 'success')
    return redirect(url_for('facturas.index'))

