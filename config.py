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

class ProductionConfig(BaseConfig):
    DEBUG = False
    # En producción suele usarse Postgres vía URL en env var
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql+pg8000://postgres:2209@localhost/agencia_paqueteria'
    )
