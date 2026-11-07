# 🛍️ ClickModa

Plataforma web de comercio electrónico y gestión de moda desarrollada con una arquitectura desacoplada: **Django REST Framework** en el backend, **Angular** en el frontend y **PostgreSQL** como motor de base de datos, todo completamente containerizado y orquestado mediante **Docker Compose**.

---

## 🚀 Tecnologías Principales

- **Frontend:**
  - [Angular](https://angular.dev/) (v20+)
  - [Tailwind CSS](https://tailwindcss.com/) (v4+)
  - TypeScript & HTML5
- **Backend:**
  - [Django](https://www.djangoproject.com/) (v6+) & [Django REST Framework (DRF)](https://www.django-rest-framework.org/)
  - [drf-spectacular](https://drf-spectacular.readthedocs.io/) (Documentación OpenAPI / Swagger)
  - `psycopg2-binary` (Conexión a PostgreSQL)
- **Base de Datos:**
  - [PostgreSQL 15](https://www.postgresql.org/)
- **Infraestructura & Contenedores:**
  - [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)

---

## 📁 Estructura del Proyecto

```text
clickmoda/
├── backend/                  # Proyecto Django API
│   ├── config/               # Configuración central (settings, urls, wsgi)
│   ├── manage.py             # CLI de Django
│   ├── requirements.txt      # Dependencias de Python
│   └── Dockerfile            # Imagen Docker para el backend
├── frontend/                 # Aplicación SPA Angular
│   ├── src/                  # Código fuente (componentes, estilos, etc.)
│   ├── package.json          # Dependencias y scripts de Node.js
│   ├── angular.json          # Configuración del workspace de Angular
│   └── Dockerfile            # Imagen Docker para el frontend
├── docker-compose.yml        # Orquestación de servicios (db, backend, frontend)
├── .env.example              # Plantilla de variables de entorno
├── .env                      # Variables de entorno locales (ignorado en git)
├── .gitignore
└── README.md
```

---

## ⚙️ Requisitos Previos

Asegúrate de tener instalado en tu máquina local:

- [Git](https://git-scm.com/)
- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/) (o Docker Desktop)
- *(Opcional para desarrollo local sin Docker)*: Python 3.12+, Node.js 20+ y PostgreSQL.

---

## 🛠️ Instalación y Puesta en Marcha con Docker

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/clickmoda.git
cd clickmoda
```

### 2. Configurar variables de entorno

Copia el archivo de ejemplo `.env.example` para crear tu `.env`:

```bash
# En Windows (PowerShell):
Copy-Item .env.example .env

# En Linux / macOS / Git Bash:
cp .env.example .env
```

Abre `.env` y ajusta los valores necesarios (especialmente contraseñas y claves secretas para entornos reales):

```ini
POSTGRES_DB=clickmoda_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=tu_password_aqui
DB_HOST=db
DB_PORT=5432
SECRET_KEY=cambiar_en_produccion
DEBUG=True
FRONTEND_URL=http://localhost:4200
```

### 3. Levantar los contenedores

Construye las imágenes y ejecuta los servicios en segundo plano:

```bash
docker compose up --build -d
```

### 4. Ejecutar migraciones de la base de datos

Una vez que los contenedores estén en ejecución:

```bash
docker compose exec backend python manage.py migrate
```

*(Opcional)* Crea un superusuario para acceder al panel de administración de Django:

```bash
docker compose exec backend python manage.py createsuperuser
```

---

## 🌐 Servicios Disponibles

| Servicio | URL / Puerto | Descripción |
| :--- | :--- | :--- |
| **Frontend (Angular)** | [http://localhost:4200](http://localhost:4200) | Aplicación web cliente |
| **Backend (Django API)** | [http://localhost:8001](http://localhost:8001) | API REST del backend |
| **Django Admin** | [http://localhost:8001/admin/](http://localhost:8001/admin/) | Panel de administración |
| **PostgreSQL** | `localhost:5432` | Base de datos relacional |

---

## 💻 Comandos Útiles

### Gestión de Contenedores

```bash
# Ver el estado de los contenedores
docker compose ps

# Ver logs en tiempo real
docker compose logs -f

# Ver logs solo del backend o frontend
docker compose logs -f backend
docker compose logs -f frontend

# Detener los servicios
docker compose down

# Detener y eliminar volúmenes (elimina datos de la base de datos)
docker compose down -v
```

### Comandos de Backend (Django)

```bash
# Crear nuevas migraciones tras modificar modelos
docker compose exec backend python manage.py makemigrations

# Aplicar migraciones
docker compose exec backend python manage.py migrate

# Entrar a la consola interactiva de Django
docker compose exec backend python manage.py shell
```

---

## 🎨 Paleta de Colores Corporativa (Tailwind CSS)

El tema de Tailwind incluye variables de color predefinidas para la identidad de ClickModa:

| Token | Hex | Muestra |
| :--- | :--- | :--- |
| `cm-blue` | `#2563EB` | Azul principal |
| `cm-amber` | `#F59E0B` | Acento / Destacados |
| `cm-dark-gray`| `#1F2937` | Fondos oscuros / Texto secundario |
| `cm-black` | `#111827` | Texto principal / Alto contraste |
| `cm-light-gray`| `#F9FAFB` | Fondo de interfaz / Superficies claras |

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.
