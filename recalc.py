from app import create_app
from models import db, Paquete

app = create_app()

with app.app_context():
    paquetes = Paquete.query.filter_by(factura_id=None).all()
    count = 0
    for p in paquetes:
        nuevo_costo = p.calcular_costo()
        if p.costo != nuevo_costo:
            print(f"Paquete {p.id}: {p.costo} -> {nuevo_costo}")
            p.costo = nuevo_costo
            count += 1
            
    db.session.commit()
    print(f"Total paquetes actualizados: {count}")
