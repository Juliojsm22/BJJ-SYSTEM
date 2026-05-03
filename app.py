from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-agencia-2024')
    db_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:2209@localhost/agencia_paqueteria')
    if db_url.startswith('postgres'):
        # Extraer el resto de la URL después del '://'
        resto_url = db_url.split('://', 1)[1]
        db_url = f"postgresql+pg8000://{resto_url}"
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder.'

    from routes.auth import auth_bp
    from routes.clientes import clientes_bp
    from routes.paquetes import paquetes_bp
    from routes.facturas import facturas_bp
    from routes.dashboard import dashboard_bp
    from routes.rastreo import rastreo_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(paquetes_bp)
    app.register_blueprint(facturas_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rastreo_bp)

    with app.app_context():
        db.create_all()
        crear_usuario_admin()

    return app

def crear_usuario_admin():
    from models import Usuario
    from werkzeug.security import generate_password_hash
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
