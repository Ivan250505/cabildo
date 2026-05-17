# EtnoSIG — Arquitectura del Sistema

---

## 1. Diagrama de Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE (Browser)                        │
│           HTML/CSS/JS — Interfaz institucional                   │
│    [Leaflet.js para mapas]  [Fetch API para comunicación]        │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS / TLS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND — FastAPI (Python 3.11)             │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Auth Router │  │ Studies      │  │ Reports Router         │  │
│  │ /api/auth/  │  │ Router       │  │ /api/reports/          │  │
│  └─────────────┘  │ /api/studies/│  └────────────────────────┘  │
│                   └──────────────┘                               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Users Router│  │ Drive Router │  │ Map Router             │  │
│  │ /api/users/ │  │ /api/drive/  │  │ /api/map/              │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   SERVICE LAYER                           │  │
│  │  AuthService  StudyService  DriveService  ReportService  │  │
│  │  UserService  GISService   DocService    MapService      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────┐    ┌──────────────────────────────┐    │
│  │   TASK QUEUE        │    │  PROCESSING ENGINES          │    │
│  │   (asyncio/celery)  │    │  ┌──────────┐ ┌──────────┐  │    │
│  │   - gis_task        │───▶│  │ Motor    │ │ Motor    │  │    │
│  │   - doc_task        │    │  │ SIG      │ │ Documen- │  │    │
│  │   - report_task     │    │  │ GeoPandas│ │ tal      │  │    │
│  └─────────────────────┘    │  │ Shapely  │ │ pdfplum- │  │    │
│                             │  │ Matplotl.│ │ ber+spaCy│  │    │
│                             │  └──────────┘ └──────────┘  │    │
│                             │  ┌──────────────────────┐   │    │
│                             │  │ Plantillador Word     │   │    │
│                             │  │ python-docx           │   │    │
│                             │  └──────────────────────┘   │    │
│                             └──────────────────────────────┘    │
└───────────┬───────────────────────────────┬─────────────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────┐      ┌──────────────────────────────────┐
│   PostgreSQL 15     │      │   Google Drive API v3            │
│   Base de datos     │      │   Corpus de cada estudio         │
│   - usuarios        │      │   FASE1/ FASE2/ FASE3/           │
│   - estudios        │      │   PDFs, QGIS, XLSX, fotos        │
│   - informes        │      └──────────────────────────────────┘
│   - auditoría       │
└─────────────────────┘      ┌──────────────────────────────────┐
                             │   datos.gov.co API (DANE)        │
                             │   Datos demográficos municipios  │
                             └──────────────────────────────────┘
```

---

## 2. Estructura de Carpetas del Proyecto

```
etnosig/
├── backend/
│   ├── app/
│   │   ├── main.py                   # Entry point FastAPI
│   │   ├── config.py                 # Settings (env vars)
│   │   ├── database.py               # SQLAlchemy + PostgreSQL
│   │   ├── auth/
│   │   │   ├── router.py             # /api/auth/*
│   │   │   ├── service.py            # AuthService
│   │   │   ├── models.py             # User ORM model
│   │   │   └── schemas.py            # Pydantic schemas
│   │   ├── users/
│   │   │   ├── router.py             # /api/users/*
│   │   │   ├── service.py            # UserService
│   │   │   ├── models.py
│   │   │   └── schemas.py
│   │   ├── studies/
│   │   │   ├── router.py             # /api/studies/*
│   │   │   ├── service.py            # StudyService
│   │   │   ├── models.py             # Study, StudyCorpus ORM
│   │   │   └── schemas.py
│   │   ├── drive/
│   │   │   ├── router.py             # /api/drive/*
│   │   │   ├── service.py            # DriveService (OAuth2)
│   │   │   └── schemas.py
│   │   ├── gis/
│   │   │   ├── router.py             # /api/gis/*
│   │   │   ├── service.py            # GISService
│   │   │   ├── engine.py             # Motor SIG principal
│   │   │   ├── buffers.py            # Generación de buffers
│   │   │   ├── matrices.py           # Matrices de distancia
│   │   │   ├── overlaps.py           # Superposiciones
│   │   │   └── mapper.py             # Generación de mapas PNG
│   │   ├── documents/
│   │   │   ├── router.py             # /api/documents/*
│   │   │   ├── service.py            # DocService
│   │   │   ├── extractor_pdf.py      # pdfplumber
│   │   │   ├── extractor_docx.py     # python-docx
│   │   │   ├── extractor_xlsx.py     # pandas
│   │   │   └── nlp_extractor.py      # spaCy NLP
│   │   ├── analytics/
│   │   │   ├── population.py         # RF-009: discrepancias
│   │   │   ├── dane.py               # RF-010: cruce DANE
│   │   │   ├── actors.py             # RF-011: red de actores
│   │   │   └── timeline.py           # RF-012: línea de tiempo
│   │   ├── reports/
│   │   │   ├── router.py             # /api/reports/*
│   │   │   ├── service.py            # ReportService
│   │   │   ├── generator.py          # Ensamblador Word
│   │   │   ├── template_engine.py    # python-docx plantilla
│   │   │   └── templates/
│   │   │       └── informe_base.docx # Plantilla institucional
│   │   ├── map/
│   │   │   ├── router.py             # /api/map/*
│   │   │   └── service.py            # MapService (geojson para Leaflet)
│   │   ├── notifications/
│   │   │   └── service.py            # Email (SMTP)
│   │   └── audit/
│   │       ├── models.py             # AuditLog ORM
│   │       └── service.py            # AuditService
│   ├── tasks/
│   │   ├── gis_task.py               # Tarea async: procesamiento SIG
│   │   ├── doc_task.py               # Tarea async: extracción docs
│   │   └── report_task.py            # Tarea async: generación informe
│   ├── migrations/                   # Alembic migrations
│   ├── tests/
│   │   ├── test_gis.py
│   │   ├── test_documents.py
│   │   └── test_reports.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                    # App shell SPA
│   ├── css/
│   │   └── styles.css                # Sistema de diseño institucional
│   ├── js/
│   │   ├── app.js                    # Router SPA
│   │   ├── auth.js                   # Auth logic + JWT
│   │   ├── api.js                    # Fetch wrapper
│   │   ├── pages/
│   │   │   ├── login.js
│   │   │   ├── dashboard.js
│   │   │   ├── studies.js
│   │   │   ├── study_detail.js
│   │   │   ├── study_form.js
│   │   │   ├── drive_sync.js
│   │   │   ├── report_review.js
│   │   │   ├── map_view.js
│   │   │   └── users.js
│   │   └── components/
│   │       ├── sidebar.js
│   │       ├── topbar.js
│   │       ├── study_card.js
│   │       └── map_widget.js
│   └── assets/
│       ├── logo.svg
│       └── indigenous_divider.svg
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 3. Modelos de Base de Datos

### 3.1 Tabla `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_completo VARCHAR(200) NOT NULL,
    email           VARCHAR(254) UNIQUE NOT NULL,
    password_hash   VARCHAR(128) NOT NULL,
    rol             VARCHAR(20) NOT NULL CHECK (rol IN ('admin','tecnico','campo','supervisor')),
    estado          VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','suspendido')),
    google_token    TEXT,                   -- OAuth2 token cifrado
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
    ultimo_acceso   TIMESTAMP WITH TIME ZONE
);
```

### 3.2 Tabla `studies`

```sql
CREATE TABLE studies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_comunidad    VARCHAR(300) NOT NULL,
    pueblo_indigena     VARCHAR(200),
    municipio           VARCHAR(200) NOT NULL,
    departamento        VARCHAR(200) NOT NULL,
    nit_comunidad       VARCHAR(20),
    contrato_referencia VARCHAR(100),
    lat                 DECIMAL(10,8),
    lng                 DECIMAL(11,8),
    estado              VARCHAR(30) NOT NULL DEFAULT 'borrador',
    -- estados: borrador|sincronizando|corpus_ok|procesando|listo_revision|
    --           en_revision|aprobado|exportado|error
    url_drive_fase1     TEXT,
    url_drive_fase2     TEXT,
    url_drive_fase3     TEXT,
    drive_folder_id     VARCHAR(200),
    buffer_metros       INTEGER DEFAULT 50,
    responsable_id      UUID REFERENCES users(id),
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 3.3 Tabla `study_corpus`

```sql
CREATE TABLE study_corpus (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id        UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    fase            VARCHAR(10) NOT NULL CHECK (fase IN ('FASE1','FASE2','FASE3')),
    nombre_archivo  VARCHAR(500) NOT NULL,
    drive_file_id   VARCHAR(200) NOT NULL,
    tipo_archivo    VARCHAR(50) NOT NULL,
    -- tipos: pdf|docx|xlsx|qgz|gpkg|shp|jpg|heic|mp4|mp3
    rol_en_corpus   VARCHAR(100),
    -- roles: acta_eleccion|acta_posesion|censo|autocenso|reglamento|
    --         ficha_precampo|proyecto_qgis|geopackage|evidencia_foto|
    --         diario_campo|ficha_comision|informe_final
    tamanio_bytes   BIGINT,
    estado          VARCHAR(20) DEFAULT 'pendiente',
    -- pendiente|descargado|procesado|error
    error_msg       TEXT,
    descargado_en   TIMESTAMP WITH TIME ZONE,
    procesado_en    TIMESTAMP WITH TIME ZONE,
    sync_at         TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 3.4 Tabla `corpus_extractions`

```sql
CREATE TABLE corpus_extractions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id        UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    tipo_dato       VARCHAR(100) NOT NULL,
    -- familias_censo_ministerio|personas_censo_ministerio|
    -- familias_autocenso|personas_autocenso|gobernador_nombre|
    -- cacique_nombre|fecha_fundacion|etc.
    valor           TEXT,
    fuente_archivo  VARCHAR(500),
    confianza       DECIMAL(4,3),   -- 0.000 a 1.000
    extraido_en     TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 3.5 Tabla `gis_results`

```sql
CREATE TABLE gis_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id        UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    tipo_resultado  VARCHAR(100) NOT NULL,
    -- buffer_pc|buffer_es|buffer_et|buffer_po|
    -- matriz_pc_es|matriz_pc_et|...|
    -- superposicion_pc_es|...|
    -- mapa_pc|mapa_es|mapa_et|mapa_po|mapa_integrado
    parametros      JSONB,
    resultado_json  JSONB,
    archivo_path    TEXT,           -- PNG o GeoPackage en disco
    generado_en     TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### 3.6 Tabla `reports`

```sql
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id        UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 1,
    estado          VARCHAR(30) NOT NULL DEFAULT 'generando',
    -- generando|listo_revision|en_revision|aprobado|exportado|error
    archivo_docx    TEXT,           -- path en disco
    archivo_zip     TEXT,
    hash_docx       VARCHAR(64),    -- SHA-256
    generado_por    UUID REFERENCES users(id),
    aprobado_por    UUID REFERENCES users(id),
    generado_en     TIMESTAMP WITH TIME ZONE DEFAULT now(),
    aprobado_en     TIMESTAMP WITH TIME ZONE,
    exportado_en    TIMESTAMP WITH TIME ZONE,
    parametros      JSONB,
    error_msg       TEXT,
    UNIQUE (study_id, version)
);
```

### 3.7 Tabla `audit_log`

```sql
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    study_id    UUID REFERENCES studies(id),
    accion      VARCHAR(200) NOT NULL,
    detalle     JSONB,
    ip_address  INET,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_audit_study ON audit_log(study_id, created_at DESC);
CREATE INDEX idx_audit_user  ON audit_log(user_id, created_at DESC);
```

### 3.8 Tabla `study_team`

```sql
CREATE TABLE study_team (
    study_id    UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rol_en_estudio VARCHAR(50) DEFAULT 'campo',
    PRIMARY KEY (study_id, user_id)
);
```

---

## 4. Flujo de Estados de un Estudio

```
[borrador]
    │ Usuario completa formulario + conecta Drive
    ▼
[sincronizando]
    │ DriveService cataloga corpus
    ▼
[corpus_ok]  ←── advertencias si faltan archivos clave
    │ Responsable técnico dispara generación
    ▼
[procesando]
    │ Cola de tareas: GIS + Doc + Analytics
    ▼
[listo_revision]
    │ Responsable abre revisión
    ▼
[en_revision]
    │ Responsable aprueba
    ▼
[aprobado]
    │ Cualquier usuario autorizado descarga
    ▼
[exportado]

En cualquier estado:  → [error] con mensaje descriptivo
```

---

## 5. Estrategia de Procesamiento Asíncrono

El procesamiento es pesado y puede tardar varios minutos. Se usa una cola de tareas:

```python
# Secuencia de tareas para generar un informe:

1. sync_drive_task(study_id)
   └─ Descarga archivos del Drive al servidor temporal
   
2. [paralelo]
   ├─ gis_task(study_id)
   │   └─ Lee QGIS → buffers → matrices → superposiciones → mapas PNG
   └─ doc_task(study_id)
       └─ Extrae datos de PDFs/DOCX/XLSX → corpus_extractions
   
3. [secuencial tras 1 y 2]
   analytics_task(study_id)
   └─ discrepancias + DANE + actores + línea de tiempo
   
4. report_task(study_id)
   └─ Ensambla Word con todos los componentes
   └─ Guarda en disco + actualiza DB
   └─ Notifica por email al responsable
```

**Implementación:** FastAPI + `asyncio.create_task()` para estudios pequeños. Para corpus grandes (> 500 MB), usar Celery + Redis como broker.

---

## 6. Configuración de Variables de Entorno

```bash
# .env.example

# Base de datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/etnosig

# Seguridad
SECRET_KEY=<32 bytes aleatorios en hex>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Drive OAuth2
GOOGLE_CLIENT_ID=<desde Google Cloud Console>
GOOGLE_CLIENT_SECRET=<desde Google Cloud Console>
GOOGLE_REDIRECT_URI=https://etnosig.simonky.com/api/drive/callback

# DANE API
DANE_API_BASE_URL=https://www.datos.gov.co/resource/

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@simonky.com
SMTP_PASSWORD=<app password>

# Almacenamiento de archivos
FILES_BASE_PATH=/var/etnosig/files
TEMP_PATH=/tmp/etnosig

# NLP
SPACY_MODEL=es_core_news_lg

# Celery (opcional para producción)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## 7. Seguridad — Middleware y Guards

```python
# Middleware stack FastAPI

app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_URL])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[...])
app.add_middleware(HTTPSRedirectMiddleware)

# Guard de autenticación (dependency injection)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    ...

# Guard de roles
def require_role(*roles: str):
    async def guard(user = Depends(get_current_user)):
        if user.rol not in roles:
            raise HTTPException(403, "Permisos insuficientes")
    return guard

# Uso:
@router.get("/users", dependencies=[Depends(require_role("admin"))])
```
