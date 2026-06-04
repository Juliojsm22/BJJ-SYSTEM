import os

class BaseConfig:
    """Configuración base compartida por todos los entornos"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-secreta-agencia-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Puedes añadir más configuraciones comunes aquí

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # Base de datos local (puedes sobreescribir con DATABASE_URL)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///dev.db'  # fallback para desarrollo rápido
    )

def get_prod_db_url():
    url = os.getenv('DATABASE_URL', 'postgresql+pg8000://postgres:2209@localhost/agencia_paqueteria')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+pg8000://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+pg8000://', 1)
    return url

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_prod_db_url()
