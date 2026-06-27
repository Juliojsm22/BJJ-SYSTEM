import os
from datetime import datetime, timedelta

def run():
    from app import create_app
    app = create_app()
    from extensions import db
    from models import Factura, Pago, Paquete

    with app.app_context():
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Marcar como pagadas las facturas viejas
        facturas_pendientes = Factura.query.filter(
            Factura.fecha_emision < start_of_week,
            Factura.estado != 'pagada'
        ).all()
        
        count = 0
        for f in facturas_pendientes:
            f.estado = 'pagada'
            
            pago = Pago(
                factura_id=f.id,
                monto=f.total,
                metodo_pago='Ajuste (Limpieza)',
                referencia='Limpieza',
                registrado_por=1
            )
            db.session.add(pago)
            count += 1
            
        # 2. Facturar y pagar paquetes viejos que no tengan factura
        old_packages = Paquete.query.filter(
            Paquete.registrado_en < start_of_week,
            Paquete.factura_id == None
        ).all()
        
        packages_by_client = {}
        for p in old_packages:
            packages_by_client.setdefault(p.cliente_id, []).append(p)
            
        for client_id, packages in packages_by_client.items():
            from models import Factura # re-import for generar_numero
            factura = Factura(
                numero=Factura.generar_numero(),
                cliente_id=client_id,
                notas='Facturación automática (Limpieza paquetes viejos)',
                estado='pagada',
                creado_por=1
            )
            db.session.add(factura)
            db.session.flush()
            
            for p in packages:
                p.factura_id = factura.id
                
            factura.total = factura.calcular_total()
            
            pago = Pago(
                factura_id=factura.id,
                monto=factura.total,
                metodo_pago='Ajuste (Limpieza)',
                referencia='Limpieza',
                registrado_por=1
            )
            db.session.add(pago)
            count += 1
            
        db.session.commit()
        print(f"Exito: Se marcaron/crearon {count} facturas como pagadas en la base de datos.")

if __name__ == '__main__':
    run()
