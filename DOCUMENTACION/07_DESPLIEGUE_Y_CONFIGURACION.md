# EtnoSIG — Guía de Despliegue y Configuración
## Instrucciones para Construcción e Instalación del Sistema

---

## 1. Prerrequisitos del Servidor

| Componente | Versión mínima | Notas |
|---|---|---|
| Ubuntu Server | 22.04 LTS | Recomendado |
| Python | 3.11+ | Con venv |
| PostgreSQL | 15+ | Con extensión PostGIS opcional |
| Redis | 7+ | Para caché y cola de tareas |
| Nginx | 1.22+ | Reverse proxy |
| Certbot | Último | Certificados TLS |
| Node.js | 18+ | Solo para build del frontend si aplica |

---

## 2. Instalación Paso a Paso

### 2.1 Clonar Repositorio

```bash
git clone git@github.com:simonky/etnosig.git /opt/etnosig
cd /opt/etnosig
```

### 2.2 Configurar Variables de Entorno

```bash
cp .env.example .env
nano .env
# Completar todas las variables (ver sección 6 de 02_ARQUITECTURA.md)
```

### 2.3 Base de Datos

```bash
# Crear usuario y base de datos
sudo -u postgres psql
CREATE USER etnosig WITH PASSWORD 'tu_password_seguro';
CREATE DATABASE etnosig OWNER etnosig;
\q

# Ejecutar migraciones
cd /opt/etnosig/backend
python -m alembic upgrade head
```

### 2.4 Backend

```bash
cd /opt/etnosig/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download es_core_news_lg

# Verificar instalación
python -c "import geopandas, spacy, fastapi; print('OK')"
```

### 2.5 Servicio systemd — Backend

```ini
# /etc/systemd/system/etnosig-backend.service

[Unit]
Description=EtnoSIG Backend — FastAPI
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/etnosig/backend
Environment=PATH=/opt/etnosig/backend/venv/bin
EnvironmentFile=/opt/etnosig/.env
ExecStart=/opt/etnosig/backend/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --log-level info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable etnosig-backend
sudo systemctl start etnosig-backend
sudo systemctl status etnosig-backend
```

### 2.6 Configuración Nginx

```nginx
# /etc/nginx/sites-available/etnosig

server {
    listen 80;
    server_name etnosig.simonky.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name etnosig.simonky.com;

    ssl_certificate     /etc/letsencrypt/live/etnosig.simonky.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/etnosig.simonky.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Frontend estático
    root /opt/etnosig/frontend;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 900s;  # 15 min para generación de informes
    }

    # WebSocket
    location /ws/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
    }

    # Archivos generados (mapas, informes)
    location /files/ {
        alias /var/etnosig/files/;
        internal;  # Solo accesible via X-Accel-Redirect del backend
    }

    # Rate limiting para auth
    location /api/auth/login {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }

    # Tamaño máximo de upload
    client_max_body_size 10M;
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/etnosig /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Certificado TLS
sudo certbot --nginx -d etnosig.simonky.com
```

---

## 3. Docker Compose (Alternativa)

```yaml
# docker-compose.yml

version: "3.9"

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: etnosig
      POSTGRES_USER: etnosig
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "etnosig"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - /var/etnosig/files:/var/etnosig/files
      - /tmp/etnosig:/tmp/etnosig
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

```bash
# Levantar con Docker
docker compose up -d
docker compose exec backend alembic upgrade head
```

---

## 4. Dockerfile del Backend

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

# Dependencias del sistema para GeoPandas / GDAL
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download es_core_news_lg

COPY . .

RUN mkdir -p /var/etnosig/files /tmp/etnosig

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 5. requirements.txt

```txt
# Framework
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
pydantic-settings==2.2.1

# Base de datos
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.1
psycopg2-binary==2.9.9

# Autenticación
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# Motor SIG
geopandas==0.14.4
shapely==2.0.4
fiona==1.9.6
pyproj==3.6.1
matplotlib==3.9.0
contextily==1.6.0
matplotlib-scalebar==0.8.1

# Procesamiento documental
pdfplumber==0.11.0
python-docx==1.1.2
pandas==2.2.2
openpyxl==3.1.3
Pillow==10.3.0

# NLP
spacy==3.7.4

# Google Drive
google-api-python-client==2.130.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0

# Cifrado de tokens
cryptography==42.0.8

# HTTP cliente (DANE API)
httpx==0.27.0

# Redis / caché
redis==5.0.4

# Email
aiosmtplib==3.0.1

# Utilidades
python-dateutil==2.9.0
python-dotenv==1.0.1

# Tests
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0  # Para TestClient
```

---

## 6. Migraciones de Base de Datos (Alembic)

```bash
# Inicializar Alembic (solo primera vez)
alembic init migrations

# Crear migración automática
alembic revision --autogenerate -m "initial_tables"

# Aplicar migraciones
alembic upgrade head

# Ver historial
alembic history

# Rollback una migración
alembic downgrade -1
```

---

## 7. Variables de Entorno Completas

```bash
# .env (completar antes de desplegar)

# ─── Base de datos ──────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://etnosig:PASSWORD@localhost:5432/etnosig

# ─── Seguridad ──────────────────────────────────────────
SECRET_KEY=genera_con: python -c "import secrets; print(secrets.token_hex(32))"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=7
FERNET_KEY=genera_con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ─── CORS ───────────────────────────────────────────────
ALLOWED_ORIGINS=https://etnosig.simonky.com

# ─── Google Drive OAuth2 ────────────────────────────────
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxx
GOOGLE_REDIRECT_URI=https://etnosig.simonky.com/api/drive/callback

# ─── DANE API ───────────────────────────────────────────
DANE_API_BASE_URL=https://www.datos.gov.co/resource/

# ─── Email SMTP ─────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@simonky.com
SMTP_PASSWORD=app_password_aqui
FROM_EMAIL=EtnoSIG <noreply@simonky.com>

# ─── Almacenamiento ────────────────────────────────────
FILES_BASE_PATH=/var/etnosig/files
TEMP_PATH=/tmp/etnosig

# ─── NLP ────────────────────────────────────────────────
SPACY_MODEL=es_core_news_lg

# ─── Redis ──────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ─── Motor SIG ──────────────────────────────────────────
DEFAULT_BUFFER_METROS=50
CRS_COLOMBIA=EPSG:3116
CRS_WGS84=EPSG:4326
MAP_DPI=300

# ─── Entorno ────────────────────────────────────────────
ENVIRONMENT=production
LOG_LEVEL=info
```

---

## 8. Respaldos Automatizados

```bash
# /etc/cron.d/etnosig-backup

# Respaldo diario de la base de datos (2 AM)
0 2 * * * www-data pg_dump -U etnosig etnosig | gzip > /var/backups/etnosig/db_$(date +\%Y\%m\%d).sql.gz

# Respaldo de archivos generados (3 AM)
0 3 * * * www-data tar czf /var/backups/etnosig/files_$(date +\%Y\%m\%d).tar.gz /var/etnosig/files/

# Limpiar backups con más de 30 días
0 4 * * * www-data find /var/backups/etnosig/ -mtime +30 -delete
```

---

## 9. Monitoreo

```bash
# Ver logs del backend
journalctl -u etnosig-backend -f

# Estado del sistema
systemctl status etnosig-backend nginx postgresql redis

# Espacio en disco
df -h /var/etnosig/files

# Conexiones a la base de datos
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='etnosig';"
```

---

## 10. Checklist de Puesta en Marcha

### Semana 1 — Configuración
- [ ] Servidor aprovisionado y actualizado
- [ ] Python 3.11, PostgreSQL 15, Redis, Nginx instalados
- [ ] Variables de entorno configuradas
- [ ] Base de datos creada y migraciones aplicadas
- [ ] Certificados TLS configurados
- [ ] Servicio backend iniciado y funcionando

### Semana 2 — Motor SIG
- [ ] GeoPandas y dependencias SIG instaladas correctamente
- [ ] Modelo spaCy `es_core_news_lg` descargado
- [ ] Test de buffer con GeoPackage de referencia (Murui Muina) pasa
- [ ] Mapas temáticos se generan correctamente (300 DPI)
- [ ] Matrices de distancia producen resultados correctos

### Semana 3 — Integraciones
- [ ] OAuth2 Google Drive configurado y funcional
- [ ] Sincronización de corpus completa sin errores
- [ ] API DANE retorna datos para municipio La Montañita
- [ ] Notificaciones por email llegando correctamente

### Semana 4 — Validación Final
- [ ] Informe completo generado de extremo a extremo con corpus Murui Muina
- [ ] Resultados SIG coinciden con análisis manual de referencia (±5%)
- [ ] Usuarios de prueba creados y flujo completo validado
- [ ] Respaldos automatizados configurados y verificados
- [ ] Sesión de capacitación con el equipo del cliente completada
- [ ] **Go-live**
