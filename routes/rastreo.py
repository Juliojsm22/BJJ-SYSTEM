from flask import Blueprint, render_template, request
from models import Paquete

rastreo_bp = Blueprint('rastreo', __name__, url_prefix='/rastreo')

@rastreo_bp.route('/', methods=['GET'])
def index():
    codigo_original = request.args.get('codigo', '').strip()
    codigo_upper = codigo_original.upper()
    paquete = None
    error = None
    if codigo_original:
        paquete = Paquete.query.filter(
            (Paquete.tracking_number == codigo_upper) | 
            (Paquete.numero_seguimiento == codigo_original) |
            (Paquete.numero_seguimiento == codigo_upper)
        ).first()
        if not paquete:
            error = "No se encontró ningún paquete con ese número de guía o seguimiento."
    return render_template('rastreo/index.html', codigo=codigo_original, paquete=paquete, error=error)
