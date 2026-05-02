from flask import Blueprint, render_template, request
from models import Paquete

rastreo_bp = Blueprint('rastreo', __name__, url_prefix='/rastreo')

@rastreo_bp.route('/', methods=['GET'])
def index():
    codigo = request.args.get('codigo', '').strip().upper()
    paquete = None
    error = None
    if codigo:
        paquete = Paquete.query.filter_by(tracking_number=codigo).first()
        if not paquete:
            error = "No se encontró ningún paquete con ese número de guía."
    return render_template('rastreo/index.html', codigo=codigo, paquete=paquete, error=error)
