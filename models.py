from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(150))
    rol = db.Column(db.String(20), default='empleado')  # admin, empleado
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(150), nullable=False)
    cedula = db.Column(db.String(30), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

    paquetes = db.relationship('Paquete', backref='cliente', lazy=True)
    facturas = db.relationship('Factura', backref='cliente', lazy=True)

    @property
    def total_libras(self):
        return sum(p.peso for p in self.paquetes)

    @property
    def paquetes_sin_facturar(self):
        return [p for p in self.paquetes if not p.factura_id]

class Paquete(db.Model):
    __tablename__ = 'paquetes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    peso = db.Column(db.Float, nullable=False)
    tipo_envio = db.Column(db.String(10), nullable=False)  # aereo, maritimo
    costo = db.Column(db.Float)
    tracking_number = db.Column(db.String(50), unique=True)
    numero_seguimiento = db.Column(db.String(100))
    estado_rastreo = db.Column(db.String(50), default='bodega_miami')
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    factura_id = db.Column(db.Integer, db.ForeignKey('facturas.id'), nullable=True)
    registrado_en = db.Column(db.DateTime, default=datetime.utcnow)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    historial = db.relationship('HistorialRastreo', backref='paquete', lazy=True, cascade='all, delete-orphan')

    TARIFA_AEREO = 6.50
    TARIFA_MARITIMO = 2.50

    def calcular_costo(self):
        tarifa_db = Tarifa.query.filter_by(nombre=self.tipo_envio).first()
        if tarifa_db:
            tarifa = tarifa_db.precio_por_libra
        else:
            tarifa = self.TARIFA_AEREO if self.tipo_envio == 'aereo' else self.TARIFA_MARITIMO
        return round(self.peso * tarifa, 2)

    def save(self):
        self.costo = self.calcular_costo()
        if not self.tracking_number:
            ultimo = Paquete.query.order_by(Paquete.id.desc()).first()
            num = (ultimo.id + 1) if ultimo else 1
            prefijo = 'A' if self.tipo_envio == 'aereo' else 'M'
            self.tracking_number = f'BJJ-{prefijo}-{datetime.utcnow().year}-{num:05d}'
        db.session.add(self)
        db.session.commit()

class Factura(db.Model):
    __tablename__ = 'facturas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='borrador')  # borrador, finalizada, pagada
    total = db.Column(db.Float, default=0.0)
    notas = db.Column(db.Text)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    paquetes = db.relationship('Paquete', backref='factura', lazy=True,
                               foreign_keys='Paquete.factura_id')
    pagos = db.relationship('Pago', backref='factura', lazy=True, cascade='all, delete-orphan')

    def calcular_total(self):
        return round(sum(p.costo or 0 for p in self.paquetes), 2)

    def actualizar_total(self):
        self.total = self.calcular_total()
        db.session.commit()

    @staticmethod
    def generar_numero():
        ultimo = Factura.query.order_by(Factura.id.desc()).first()
        num = (ultimo.id + 1) if ultimo else 1
        return f'FAC-{datetime.utcnow().year}-{num:05d}'

class HistorialRastreo(db.Model):
    __tablename__ = 'historial_rastreo'
    id = db.Column(db.Integer, primary_key=True)
    paquete_id = db.Column(db.Integer, db.ForeignKey('paquetes.id'), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    ubicacion = db.Column(db.String(100))
    comentarios = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    usuario = db.relationship('Usuario', backref='actualizaciones_rastreo', lazy=True)

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, db.ForeignKey('facturas.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False) # Efectivo, Transferencia, Tarjeta, etc.
    referencia = db.Column(db.String(100))
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    usuario = db.relationship('Usuario', backref='pagos_registrados', lazy=True)

class Tarifa(db.Model):
    __tablename__ = 'tarifas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False) # aereo, maritimo
    precio_por_libra = db.Column(db.Float, nullable=False)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

