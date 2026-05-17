# EtnoSIG — Índice de Documentación del Sistema
## Versión 1.0 — Mayo 2026

---

## ¿Cómo usar esta documentación?

Esta carpeta contiene **toda la especificación** necesaria para construir el sistema EtnoSIG desde cero. Los archivos están ordenados por prioridad de lectura.

---

## Archivos de Documentación

| # | Archivo | Contenido | Leer primero si... |
|---|---|---|---|
| 1 | `00_VISION_GENERAL.md` | Propósito, actores, stack, flujo completo | Eres nuevo en el proyecto |
| 2 | `01_REQUERIMIENTOS.md` | RF y RNF completos, tabla de permisos, reglas de negocio | Defines el alcance |
| 3 | `02_ARQUITECTURA.md` | Diagramas, estructura de carpetas, modelos de BD, variables de entorno | Diseñas la arquitectura |
| 4 | `03_API_SPEC.md` | Todos los endpoints REST + WebSocket con ejemplos | Desarrollas el backend o frontend |
| 5 | `04_MODULOS.md` | Especificación detallada de cada módulo con código de referencia | Implementas un módulo específico |
| 6 | `05_MOTOR_SIG_Y_MAPA.md` | Algoritmos SIG, capas, mapas Leaflet, código Python | Implementas el motor SIG |
| 7 | `06_GOOGLE_DRIVE_E_IA.md` | OAuth2 Drive, extracción NLP, analytics, organizagrama, timeline | Implementas Drive o NLP |
| 8 | `07_DESPLIEGUE_Y_CONFIGURACION.md` | Instalación, Docker, Nginx, systemd, checklist go-live | Despliega el sistema |
| 9 | `08_CONTEXTO_ETNOLOGICO.md` | Dominio del negocio, caso Murui Muina, sensibilidades éticas | Entiendes qué procesa el sistema |

---

## Resumen de lo que hace el Sistema

```
ENTRADA:  Corpus en Google Drive (PDFs, XLSX, proyecto QGIS, fotos)
          organizado en 3 fases por comunidad indígena

PROCESO:  1. Sincroniza corpus desde Drive
          2. Motor SIG: buffers 50m + 6 matrices distancia + 6 superposiciones + mapas
          3. Motor documental: extrae cifras, nombres, fechas con NLP
          4. Módulos analíticos: discrepancias + DANE + actores + timeline
          5. Plantillador: ensambla todo en documento Word institucional

SALIDA:   Informe Word completo que sustenta la resolución de reconocimiento
          ante el Ministerio del Interior + mapa interactivo de resguardos
```

---

## Stack Tecnológico (Resumen)

```
Backend:       Python 3.11 + FastAPI
BD:            PostgreSQL 15
SIG:           GeoPandas + Shapely + Matplotlib + Contextily
Documentos:    pdfplumber + python-docx + pandas
NLP:           spaCy (es_core_news_lg)
Drive:         Google Drive API v3 (OAuth2)
DANE:          datos.gov.co API
Mapa web:      Leaflet.js + OpenStreetMap
Frontend:      HTML/CSS/JS (diseño institucional gov.co)
Hosting:       Simonky S.A.S (Ubuntu 22.04 + Nginx)
```

---

## Módulos del Sistema (Resumen)

| Módulo | Descripción |
|---|---|
| M1 — Autenticación | JWT, roles, sesiones |
| M2 — Usuarios | CRUD, roles (admin/tecnico/campo/supervisor) |
| M3 — Estudios | CRUD de estudios etnológicos, gestión de estados |
| M4 — Formularios | F-01 Creación estudio, F-02 Datos resguardo, F-03 Config informe |
| M5 — Google Drive | OAuth2, sincronización, clasificación de corpus |
| M6 — Motor SIG | Buffers, matrices, superposiciones, mapas temáticos |
| M7 — Motor Documental | Extracción PDF/DOCX/XLSX + NLP spaCy |
| M8 — Analytics | Discrepancias + DANE + Actores + Timeline |
| M9 — Generación Word | Plantillador python-docx con estructura institucional |
| M10 — Mapa | Leaflet.js con resguardos georreferenciados |
| M11 — Auditoría | Log inmutable de todas las acciones |

---

## Roles y Permisos (Resumen)

| Rol | Puede |
|---|---|
| `admin` | Todo — CRUD usuarios, configuración, auditoría |
| `tecnico` | Crear/editar estudios, sincronizar Drive, generar/aprobar/exportar informes |
| `campo` | Ver estado de estudios asignados, ver mapa |
| `supervisor` | Ver estudios, revisar y aprobar informes, ver mapa |

---

## Requerimientos Funcionales (Lista)

| ID | Descripción |
|---|---|
| RF-001 | Autenticación JWT |
| RF-002 | Gestión de usuarios (CRUD + roles) |
| RF-003 | Crear estudio etnológico |
| RF-004 | Sincronización Google Drive |
| RF-005 | Procesamiento geoespacial (Motor SIG) |
| RF-006 | Generación de mapas temáticos |
| RF-007 | Vista de mapa interactivo (Leaflet) |
| RF-008 | Procesamiento documental (NLP) |
| RF-009 | Validación discrepancias poblacionales |
| RF-010 | Cruce con datos DANE |
| RF-011 | Red de actores clave (organigrama) |
| RF-012 | Línea de tiempo de eventos |
| RF-013 | Generación informe Word |
| RF-014 | Revisión y aprobación del informe |
| RF-015 | Exportación (.docx + ZIP) |
| RF-016 | Historial y trazabilidad |
| RF-017 | Dashboard de métricas |
| RF-018 | Formulario de información del resguardo |
| RF-019 | Gestión de roles y permisos |
| RF-020 | Notificaciones por email |

---

## Requerimientos No Funcionales (Lista)

| ID | Criterio clave |
|---|---|
| RNF-001 | Rendimiento: informe < 15 min, dashboard < 2s |
| RNF-002 | Disponibilidad: 99% mensual, backups diarios |
| RNF-003 | Seguridad: TLS, JWT, bcrypt, rate limiting |
| RNF-004 | Protección datos: Ley 1581/2012, datos étnicos cifrados |
| RNF-005 | Usabilidad: sin formación técnica, español Colombia |
| RNF-006 | Escalabilidad: 20 estudios simultáneos |
| RNF-007 | Mantenibilidad: ≥80% cobertura tests motor SIG |
| RNF-008 | Compatibilidad: Chrome/Firefox/Edge/Safari |

---

*Documentación generada a partir del análisis de: nota_voz.txt, PLAN_PROYECTO.md, propuesta.txt, RESUMEN_ANALISIS_FASE1.md, RESUMEN_ANALISIS_FASE2.md, RESUMEN_ANALISIS_FASE3.md y mockups/index.html*
