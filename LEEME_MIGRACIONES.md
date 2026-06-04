# Guía de Flask-Migrate

¡Has integrado con éxito el sistema de control de versiones para tu base de datos!

## ¿Para qué sirve?
Cada vez que agregues una tabla, quites una columna o cambies el tipo de dato en `models.py`, ya no tendrás que tocar la base de datos a mano. Este sistema leerá los cambios y actualizará la base de datos de manera segura.

## Comandos que debes conocer (Ejecutar en la terminal)

### 1. Inicializar (Se hace UNA SOLA VEZ)
Si nunca has usado migraciones en este proyecto, ejecuta:
```bash
flask db init
```
Esto creará una carpeta llamada `migrations` en tu proyecto. **Esta carpeta debe subirse a GitHub/Render**.

### 2. Crear una migración (Cada vez que cambies models.py)
Modifica tu código en `models.py`. Luego ejecuta:
```bash
flask db migrate -m "Mensaje explicando el cambio, ej: Añadida columna peso"
```
Esto genera un archivo de historial dentro de `migrations/versions/`. Revisa ese archivo para asegurarte de que contiene lo que esperabas.

### 3. Aplicar los cambios a la Base de Datos
Para que tu base de datos local reciba esos cambios:
```bash
flask db upgrade
```

## ¿Y en Render?
1. Sube tu código (incluyendo la carpeta `migrations` y sus nuevos archivos) a GitHub.
2. Render descargará el nuevo código.
3. En la configuración de tu servicio web en Render, asegúrate de que el **Start Command** (Comando de inicio) diga:
   `flask db upgrade && gunicorn "app:create_app()"`
4. ¡Y listo! Render actualizará la estructura de su base de datos automáticamente antes de arrancar la aplicación.
