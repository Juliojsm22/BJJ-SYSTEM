# 📦 EnvíosPRO — Sistema de Gestión de Paquetería Internacional

Sistema web completo para administrar clientes, paquetes, facturación y reportes de una agencia de envíos.

---

## 🚀 Instalación rápida

### 1. Requisitos previos
- Python 3.9+
- MySQL 8.0+
- pip

### 2. Crear base de datos en MySQL
```sql
CREATE DATABASE agencia_paqueteria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Configurar entorno
```bash
cd agencia_paqueteria
cp .env.example .env
# Edita .env con tu usuario y contraseña de MySQL
```

### 4. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 5. Ejecutar el sistema
```bash
python run.py
```

Abre tu navegador en: **http://localhost:5000**

**Acceso inicial:**  
- Usuario: `admin`  
- Contraseña: `admin123`

---

## 📋 Módulos del sistema

### 🧑‍🤝‍🧑 Gestión de Clientes
- Registro con nombre, cédula, teléfono y email
- Edición y eliminación (soft delete)
- Búsqueda por nombre, cédula o email
- Vista de detalle con historial de paquetes y estadísticas

### 📦 Registro de Paquetería
- Asociación de paquetes a clientes
- Tipos: **Aéreo ($6.50/lb)** y **Marítimo ($2.50/lb)**
- Cálculo automático de costo en tiempo real
- Filtros por tipo y estado de facturación

### 🧾 Facturación
- Agrupación de múltiples paquetes en una sola factura
- Estados: Borrador → Finalizada → Pagada
- Edición antes de finalizar
- **Generación de PDF** con diseño profesional
- **Envío por WhatsApp** con enlace directo

### 📊 Dashboard
- Ganancias semanales y mensuales
- Gráfico de barras: ingresos por mes (últimos 6 meses)
- Gráfico de dona: distribución aéreo/marítimo
- Top 5 clientes por volumen de libras
- Estado general del sistema

---

## 🗄️ Estructura del proyecto

```
agencia_paqueteria/
├── run.py              # Punto de entrada
├── app.py              # Configuración de Flask y SQLAlchemy
├── models.py           # Modelos de base de datos
├── requirements.txt    # Dependencias
├── .env.example        # Ejemplo de configuración
├── routes/
│   ├── auth.py         # Login / Logout
│   ├── clientes.py     # CRUD de clientes
│   ├── paquetes.py     # CRUD de paquetes
│   ├── facturas.py     # Facturación + PDF
│   └── dashboard.py    # Estadísticas
└── templates/
    ├── base.html        # Layout principal con sidebar
    ├── login.html       # Pantalla de inicio de sesión
    ├── dashboard/
    ├── clientes/
    ├── paquetes/
    └── facturas/
```

---

## ⚙️ Tarifas configuradas

| Tipo    | Tarifa     |
|---------|-----------|
| Aéreo   | $6.50/lb  |
| Marítimo| $2.50/lb  |

Para cambiar tarifas, edita `models.py`:
```python
TARIFA_AEREO = 6.50
TARIFA_MARITIMO = 2.50
```

---

## 🔐 Roles de usuario

| Rol       | Permisos                              |
|-----------|---------------------------------------|
| Admin     | Todo + eliminar clientes              |
| Empleado  | Crear/editar clientes, paquetes, facturas |

Para crear un nuevo empleado, accede a MySQL:
```sql
INSERT INTO usuarios (username, email, password, nombre_completo, rol)
VALUES ('empleado1', 'emp@agencia.com', '<hash>', 'Nombre Apellido', 'empleado');
```

O puedes agregar un módulo de gestión de usuarios fácilmente.

---

## 📱 WhatsApp

El botón de WhatsApp genera automáticamente un mensaje con:
- Nombre del cliente
- Número de factura
- Total a pagar

Si el cliente tiene teléfono registrado, el enlace lo abre directamente.  
El prefijo de país está configurado para Nicaragua (`+505`). Cambia en `routes/facturas.py`.

---

## 🛠️ Próximas mejoras sugeridas

- [ ] Módulo de gestión de usuarios desde la web
- [ ] Importación de paquetes desde correo electrónico
- [ ] Notificaciones automáticas por WhatsApp API
- [ ] Exportación de reportes a Excel
- [ ] Módulo de pagos y cobros
- [ ] App móvil con QR por paquete
