from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from models import Cliente, Paquete, Factura, db
from datetime import datetime, timedelta
from sqlalchemy import func, case

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    hoy = datetime.utcnow()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    # Ganancias reales (precio venta - costo)
    # Aéreo: $6.5 - $5.0 = $1.5 ganancia por libra
    # Marítimo: $2.5 - $1.6 = $0.9 ganancia por libra
    ganancia_expr = case(
        (Paquete.tipo_envio == 'aereo', Paquete.peso * 1.5),
        (Paquete.tipo_envio == 'maritimo', Paquete.peso * 0.9),
        else_=0
    )

    ganancias_semana = db.session.query(func.sum(ganancia_expr)).join(
        Factura, Paquete.factura_id == Factura.id
    ).filter(
        Factura.fecha_emision >= inicio_semana,
        Factura.estado.in_(['finalizada', 'pagada'])
    ).scalar() or 0

    ganancias_mes = db.session.query(func.sum(ganancia_expr)).join(
        Factura, Paquete.factura_id == Factura.id
    ).filter(
        Factura.fecha_emision >= inicio_mes,
        Factura.estado.in_(['finalizada', 'pagada'])
    ).scalar() or 0

    total_clientes = Cliente.query.filter_by(activo=True).count()
    total_paquetes = Paquete.query.count()
    paquetes_sin_facturar = Paquete.query.filter_by(factura_id=None).count()
    facturas_pendientes = Factura.query.filter_by(estado='borrador').count()

    # Top clientes por libras
    top_clientes = db.session.query(
        Cliente.nombre_completo,
        func.sum(Paquete.peso).label('total_libras'),
        func.count(Paquete.id).label('total_paquetes')
    ).join(Paquete, Cliente.id == Paquete.cliente_id)\
     .filter(Cliente.activo == True)\
     .group_by(Cliente.id)\
     .order_by(func.sum(Paquete.peso).desc())\
     .limit(5).all()

    # Ganancias últimos 6 meses
    meses_data = []
    for i in range(5, -1, -1):
        mes = hoy - timedelta(days=30 * i)
        inicio = mes.replace(day=1)
        if mes.month == 12:
            fin = mes.replace(year=mes.year+1, month=1, day=1)
        else:
            fin = mes.replace(month=mes.month+1, day=1)
        total = db.session.query(func.sum(ganancia_expr)).join(
            Factura, Paquete.factura_id == Factura.id
        ).filter(
            Factura.fecha_emision >= inicio,
            Factura.fecha_emision < fin,
            Factura.estado.in_(['finalizada', 'pagada'])
        ).scalar() or 0
        meses_data.append({
            'mes': mes.strftime('%b %Y'),
            'total': float(total)
        })

    # Paquetes por tipo
    aereos = Paquete.query.filter_by(tipo_envio='aereo').count()
    maritimos = Paquete.query.filter_by(tipo_envio='maritimo').count()

    return render_template('dashboard/index.html',
        ganancias_semana=ganancias_semana,
        ganancias_mes=ganancias_mes,
        total_clientes=total_clientes,
        total_paquetes=total_paquetes,
        paquetes_sin_facturar=paquetes_sin_facturar,
        facturas_pendientes=facturas_pendientes,
        top_clientes=top_clientes,
        meses_data=meses_data,
        aereos=aereos,
        maritimos=maritimos
    )

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    hoy = datetime.utcnow()
    inicio_mes = hoy.replace(day=1)
    ganancia_expr = case(
        (Paquete.tipo_envio == 'aereo', Paquete.peso * 1.5),
        (Paquete.tipo_envio == 'maritimo', Paquete.peso * 0.9),
        else_=0
    )
    ganancias_mes = db.session.query(func.sum(ganancia_expr)).join(
        Factura, Paquete.factura_id == Factura.id
    ).filter(
        Factura.fecha_emision >= inicio_mes,
        Factura.estado.in_(['finalizada', 'pagada'])
    ).scalar() or 0
    return jsonify({'ganancias_mes': float(ganancias_mes)})
