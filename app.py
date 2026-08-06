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

    app.register_blueprint(auth_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(paquetes_bp)
    app.register_blueprint(facturas_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rastreo_bp)
    app.register_blueprint(usuarios_bp)

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
        
        crear_usuario_admin()

    from flask import session
    from datetime import timedelta
    
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

    @app.before_request
    def make_session_permanent():
        session.permanent = True
        session.modified = True

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
