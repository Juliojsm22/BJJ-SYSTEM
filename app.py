import os
import sys

# Asegurar que el directorio actual esté en el path para poder importar config y extensions en Render
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db, login_manager, migrate, csrf, limiter
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno desde .env

def create_app():
    app = Flask(__name__)
    
    # Seleccionar configuración según FLASK_ENV
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder.'

    from routes.auth import auth_bp
    from routes.clientes import clientes_bp
    from routes.paquetes import paquetes_bp
    from routes.facturas import facturas_bp
    from routes.dashboard import dashboard_bp
    from routes.rastreo import rastreo_bp
    from routes.usuarios import usuarios_bp
    from routes.caja import caja_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(paquetes_bp)
    app.register_blueprint(facturas_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rastreo_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(caja_bp)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Aviso db.create_all: {e}")
            db.session.rollback()

        for query in [
            "ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(20)",
            "ALTER TABLE paquetes ADD COLUMN numero_seguimiento VARCHAR(100)",
            "ALTER TABLE paquetes ADD COLUMN notificado_whatsapp BOOLEAN DEFAULT FALSE",
            "ALTER TABLE paquetes ADD COLUMN fecha_notificacion TIMESTAMP"
        ]:
            try:
                db.session.execute(db.text(query))
                db.session.commit()
            except Exception:
                db.session.rollback()

        # Marcar paquetes anteriores a hoy como notificados automáticamente (desarrollo y producción)
        try:
            from models import get_local_now, Paquete
            hoy_inicio = datetime.combine(get_local_now().date(), datetime.min.time())
            Paquete.query.filter(
                Paquete.registrado_en < hoy_inicio,
                (Paquete.notificado_whatsapp == False) | (Paquete.notificado_whatsapp == None)
            ).update(
                {Paquete.notificado_whatsapp: True, Paquete.fecha_notificacion: Paquete.registrado_en},
                synchronize_session=False
            )
            db.session.commit()
        except Exception as e:
            print(f"Aviso actualizacion paquetes anteriores: {e}")
            db.session.rollback()
        
        crear_usuario_admin()

    from flask import session
    from datetime import timedelta
    import time
    
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

    @app.before_request
    def make_session_permanent():
        session.permanent = True
        session.modified = True

    last_checked = {'time': 0}

    @app.before_request
    def actualizar_estados_paquetes():
        current_time = time.time()
        # Ejecutar la verificación como máximo una vez por hora (3600 segundos)
        if current_time - last_checked['time'] > 3600:
            last_checked['time'] = current_time
            try:
                from models import Paquete, HistorialRastreo, get_local_now
                now = get_local_now()
                limite_aduana = now - timedelta(days=12)
                limite_transito = now - timedelta(days=2)

                # 1. Paquetes que llevan más de 12 días -> En aduana
                paquetes_aduana = Paquete.query.filter(
                    Paquete.registrado_en <= limite_aduana,
                    Paquete.estado_rastreo.in_(['bodega_miami', 'en_transito'])
                ).all()

                for p in paquetes_aduana:
                    p.estado_rastreo = 'en_aduana'
                    db.session.add(HistorialRastreo(
                        paquete_id=p.id,
                        estado='en_aduana',
                        ubicacion='Aduana',
                        comentarios='Actualización automática: 12 días después del registro'
                    ))

                # 2. Paquetes que llevan entre 2 y 12 días -> En tránsito
                paquetes_transito = Paquete.query.filter(
                    Paquete.registrado_en <= limite_transito,
                    Paquete.registrado_en > limite_aduana,
                    Paquete.estado_rastreo == 'bodega_miami'
                ).all()

                for p in paquetes_transito:
                    p.estado_rastreo = 'en_transito'
                    db.session.add(HistorialRastreo(
                        paquete_id=p.id,
                        estado='en_transito',
                        ubicacion='En Tránsito',
                        comentarios='Actualización automática: 2 días después del registro'
                    ))

                if paquetes_aduana or paquetes_transito:
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error actualizando estados automáticamente: {e}")

    return app

def crear_usuario_admin():
    from models import Usuario
    from werkzeug.security import generate_password_hash
    try:
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                email='admin@agencia.com',
                password=generate_password_hash('admin123'),
                rol='admin',
                nombre_completo='Administrador'
            )
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Aviso: No se pudo verificar el usuario admin (probablemente falte correr migraciones). Detalles: {e}")
