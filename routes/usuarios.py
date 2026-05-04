from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Usuario, db
from werkzeug.security import generate_password_hash

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

@usuarios_bp.route('/')
@login_required
def index():
    if current_user.rol != 'admin':
        flash('No tienes permisos para ver esta página.', 'error')
        return redirect(url_for('dashboard.index'))
    usuarios = Usuario.query.order_by(Usuario.id).all()
    return render_template('usuarios/index.html', usuarios=usuarios)

@usuarios_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if current_user.rol != 'admin':
        flash('No tienes permisos.', 'error')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username').strip()
        if Usuario.query.filter_by(username=username).first():
            flash('Ese nombre de usuario ya existe.', 'error')
            return redirect(request.url)
            
        usuario = Usuario(
            username=username,
            email=request.form.get('email').strip(),
            password=generate_password_hash(request.form.get('password')),
            nombre_completo=request.form.get('nombre_completo').strip(),
            rol=request.form.get('rol'),
            activo=True
        )
        db.session.add(usuario)
        db.session.commit()
        flash('Usuario creado exitosamente.', 'success')
        return redirect(url_for('usuarios.index'))
        
    return render_template('usuarios/form.html', usuario=None)

@usuarios_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    if current_user.rol != 'admin':
        flash('No tienes permisos.', 'error')
        return redirect(url_for('dashboard.index'))
        
    usuario = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        username = request.form.get('username').strip()
        existente = Usuario.query.filter_by(username=username).first()
        if existente and existente.id != id:
            flash('Ese nombre de usuario ya está en uso.', 'error')
            return redirect(request.url)
            
        usuario.username = username
        usuario.email = request.form.get('email').strip()
        usuario.nombre_completo = request.form.get('nombre_completo').strip()
        usuario.rol = request.form.get('rol')
        usuario.activo = request.form.get('activo') == 'on'
        
        nueva_pass = request.form.get('password')
        if nueva_pass:
            usuario.password = generate_password_hash(nueva_pass)
            
        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('usuarios.index'))
        
    return render_template('usuarios/form.html', usuario=usuario)
