from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from markupsafe import Markup
from flask_login import login_user, logout_user, login_required, current_user
from models import Usuario
from werkzeug.security import generate_password_hash
from extensions import limiter, db
from itsdangerous import URLSafeTimedSerializer

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        usuario = Usuario.query.filter_by(username=username, activo=True).first()
        
        if usuario and usuario.check_password(password):
            login_user(usuario, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        telefono = request.form.get('telefono')
        usuario = Usuario.query.filter_by(username=username, activo=True).first()
        if usuario:
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(usuario.username, salt='recover-key')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            import urllib.parse
            telefono_limpio = ''.join(filter(str.isdigit, str(telefono)))
            if not telefono_limpio:
                flash('El número de teléfono proporcionado no es válido.', 'error')
                return redirect(url_for('auth.forgot_password'))
                
            mensaje = f"Hola {usuario.nombre_completo},\n\nAquí tienes tu enlace para restablecer tu contraseña:\n{reset_url}\n\nEste enlace expira en 1 hora."
            wa_url = f"https://api.whatsapp.com/send?phone={telefono_limpio}&text={urllib.parse.quote(mensaje)}"
            
            return redirect(wa_url)
        else:
            flash('Si el usuario existe en nuestro sistema y está activo, se generará el enlace.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        username = s.loads(token, salt='recover-key', max_age=3600)
    except:
        flash('El enlace de recuperación es inválido o ha expirado.', 'error')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('Por favor llena ambos campos de contraseña.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
            
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
            
        usuario = Usuario.query.filter_by(username=username, activo=True).first()
        if usuario:
            usuario.password = generate_password_hash(password)
            db.session.commit()
            flash('Tu contraseña ha sido actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Usuario no encontrado o inactivo.', 'error')
            return redirect(url_for('auth.login'))
            
    return render_template('reset_password.html', token=token)
