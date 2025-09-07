# Project Manager API

API REST para la gestión de proyectos y tareas desarrollada con Django REST Framework.

## 📋 Características

- **Autenticación JWT**: Sistema completo de autenticación con tokens de acceso y renovación
- **Gestión de Proyectos**: CRUD completo de proyectos con asignaciones de usuarios
- **Gestión de Tareas**: Administración de tareas con estados, asignaciones y comentarios
- **Sistema de Notificaciones**: Notificaciones automáticas para eventos del sistema
- **Documentación Interactiva**: API documentada con Swagger/OpenAPI
- **Permisos Granulares**: Sistema de permisos basado en roles y ownership

## 🛠️ Tecnologías

- **Backend**: Django 5.1.3, Django REST Framework 3.15.2
- **Base de Datos**: SQLite (desarrollo), PostgreSQL (producción)
- **Autenticación**: JWT con djangorestframework-simplejwt
- **Documentación**: drf-spectacular (OpenAPI/Swagger)
- **Validación**: Django Validators + DRF Serializers

## 📦 Requisitos Previos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)
- Git

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd project_manager_back
```

### 2. Crear y activar entorno virtual

```powershell
# Crear entorno virtual
python -m venv .\venv

# Activar entorno virtual (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activar entorno virtual (Windows CMD)
venv\Scripts\activate.bat

# Activar entorno virtual (Linux/Mac)
source venv/bin/activate
```

### 3. Instalar dependencias

```powershell
# Instalar dependencias de producción
pip install -r requirements.txt

# Instalar dependencias de desarrollo (opcional)
pip install -r requirements-dev.txt
```

### 4. Configurar variables de entorno

```powershell
# Copiar archivo de ejemplo
copy .env.example .env
```

Editar el archivo `.env` con tus configuraciones:

```env
# Configuración básica
DEBUG=True
SECRET_KEY=tu-clave-secreta-muy-segura-aqui
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos (SQLite por defecto)
DATABASE_URL=sqlite:///db.sqlite3

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=60  # minutos
JWT_REFRESH_TOKEN_LIFETIME=1440  # minutos (24 horas)
JWT_ALGORITHM=HS256

# Email (opcional, para reset de contraseñas)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-password-de-app

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text
```

### 5. Configurar base de datos

```powershell
# Aplicar migraciones
python manage.py migrate

# Crear usuarios de prueba (recomendado para desarrollo)
python manage.py seed_users

# Crear superusuario adicional (opcional)
python manage.py createsuperuser
```

#### 🧑‍💻 Usuarios de Prueba

El comando `seed_users` crea automáticamente usuarios con diferentes roles para facilitar las pruebas:

| Email | Contraseña | Rol | Permisos |
|-------|------------|-----|----------|
| `admin@example.com` | `12345678` | Administrador | Acceso completo al sistema |
| `collaborator@example.com` | `12345678` | Colaborador | Gestión de proyectos y tareas |
| `viewer@example.com` | `12345678` | Visor | Solo lectura |

```powershell
# Forzar actualización de usuarios existentes
python manage.py seed_users --force
```

### 6. Ejecutar el servidor

```powershell
# Modo desarrollo
python manage.py runserver

# El servidor estará disponible en: http://127.0.0.1:8000/
```

## 📚 Documentación de la API

Una vez que el servidor esté ejecutándose, puedes acceder a:

- **Documentación Swagger**: http://127.0.0.1:8000/api/docs/
- **Documentación ReDoc**: http://127.0.0.1:8000/api/redoc/
- **Schema OpenAPI**: http://127.0.0.1:8000/api/schema/

## 🔐 Autenticación

La API utiliza autenticación JWT. Para obtener tokens:

### Registro de usuario
```http
POST /api/auth/register/
Content-Type: application/json

{
    "email": "usuario@ejemplo.com",
    "password": "contraseña123",
    "first_name": "Nombre",
    "last_name": "Apellido"
}
```

### Iniciar sesión
```http
POST /api/auth/login/
Content-Type: application/json

{
    "email": "admin@example.com",
    "password": "12345678"
}
```

### Usar el token
```http
Authorization: Bearer <tu-access-token>
```

## 🏗️ Estructura del Proyecto

```
project_manager_back/
├── apps/                          # Aplicaciones Django
│   ├── authentication/           # Autenticación y usuarios
│   ├── projects/                  # Gestión de proyectos
│   ├── tasks/                     # Gestión de tareas
│   ├── notifications/             # Sistema de notificaciones
│   └── shared/                    # Utilidades compartidas
├── project_manager/               # Configuración principal
│   ├── settings.py               # Configuración Django
│   ├── urls.py                   # URLs principales
│   └── wsgi.py                   # WSGI config
├── logs/                         # Archivos de log
├── requirements.txt              # Dependencias de producción
├── requirements-dev.txt          # Dependencias de desarrollo
├── .env.example                  # Ejemplo de variables de entorno
└── manage.py                     # Script de gestión Django
```

## 🧪 Ejecutar Tests

```powershell
# Ejecutar todos los tests
python manage.py test

# Ejecutar tests de una app específica
python manage.py test apps.authentication

# Ejecutar con coverage (si está instalado)
coverage run --source='.' manage.py test
coverage report
```

## 📊 Endpoints Principales

### Autenticación y Usuarios
- `POST /api/auth/register/` - Registro de usuario
- `POST /api/auth/login/` - Iniciar sesión
- `POST /api/auth/refresh/` - Renovar token
- `POST /api/auth/logout/` - Cerrar sesión
- `GET /api/auth/profile/` - Obtener perfil
- `PUT /api/auth/profile/` - Actualizar perfil

### Gestión de Proyectos
- `GET /api/projects/` - Listar proyectos
- `POST /api/projects/` - Crear proyecto
- `GET /api/projects/{id}/` - Obtener proyecto
- `PUT /api/projects/{id}/` - Actualizar proyecto
- `DELETE /api/projects/{id}/` - Eliminar proyecto
- `POST /api/projects/{id}/assign_user/` - Asignar usuario

### Gestión de Tareas
- `GET /api/tasks/` - Listar tareas
- `POST /api/tasks/` - Crear tarea
- `GET /api/tasks/{id}/` - Obtener tarea
- `PUT /api/tasks/{id}/` - Actualizar tarea
- `PATCH /api/tasks/{id}/update_status/` - Cambiar estado
- `POST /api/tasks/{id}/add_comment/` - Agregar comentario

### Sistema de Notificaciones
- `GET /api/notifications/` - Listar notificaciones
- `PATCH /api/notifications/{id}/mark_as_read/` - Marcar como leída
- `PATCH /api/notifications/mark_all_as_read/` - Marcar todas como leídas
- `GET /api/notifications/unread_count/` - Contador de no leídas

## 🔧 Configuración para Producción

### Variables de entorno para producción
```env
DEBUG=False
SECRET_KEY=clave-super-secreta-para-produccion
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
DATABASE_URL=postgresql://usuario:password@localhost:5432/project_manager
LOG_LEVEL=WARNING
```

### Configurar PostgreSQL
```bash
# Instalar dependencias de PostgreSQL
pip install psycopg2-binary

# Configurar DATABASE_URL en .env
DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db
```

### Recolectar archivos estáticos
```bash
python manage.py collectstatic --noinput
```

## 🐛 Solución de Problemas

### Error de migraciones
```bash
# Resetear migraciones (solo desarrollo)
python manage.py migrate --fake-initial
```

### Error de permisos
```bash
# Verificar permisos de archivos
# En Windows, ejecutar PowerShell como administrador
```

### Error de dependencias
```bash
# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

## 📝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🤝 Soporte

Si tienes problemas o preguntas:

1. Revisa la documentación de la API en `/api/docs/`
2. Verifica los logs en `logs/django.log`
3. Abre un issue en el repositorio

---

**Desarrollado con ❤️ usando Django REST Framework**