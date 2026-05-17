# EtnoSIG — Plataforma de Análisis Automatizado de Estudios Etnológicos
## Visión General del Sistema

**Proveedor:** Simonky S.A.S — CTO Eduwin Andrés Flórez Orejuela  
**Cliente:** Universidad de Cartagena / Ministerio del Interior (usuario final)  
**Versión:** 1.0  
**Fecha:** Mayo 2026  

---

## 1. Propósito del Sistema

EtnoSIG es una plataforma web que **asiste la generación de la resolución de reconocimiento** de resguardos y cabildos indígenas ante el Ministerio del Interior de Colombia. Automatiza el análisis del corpus documental y geoespacial de cada estudio etnológico para producir el informe técnico que sustenta el acto administrativo de reconocimiento.

El software no reemplaza el criterio metodológico del responsable técnico: lo asiste. El profesional SIG dispara la generación, revisa el borrador, ajusta lo necesario y exporta la versión final.

---

## 2. Problema que Resuelve

El proceso actual para estudiar y reconocer una comunidad indígena es manual:

| Problema actual | Solución EtnoSIG |
|---|---|
| Semanas de trabajo manual por informe | Generación completa en < 15 minutos |
| Inconsistencias entre informes de distintos profesionales | Motor estandarizado con misma metodología SIG |
| Cruce manual de fuentes poblacionales | Validación automática con alertas de discrepancias |
| Sin enriquecimiento con datos DANE | Cruce automático con datos abiertos DANE |
| Mapas hechos uno a uno en QGIS | Mapas temáticos generados programáticamente |
| Sin trazabilidad de versiones | Historial completo por estudio |

---

## 3. Contexto del Dominio

### 3.1 El Proceso Etnológico

Cada comunidad que busca reconocimiento ante el Estado colombiano requiere un **estudio etnológico** que sigue tres fases:

```
FASE 1 — Pre-campo
  Recolección de acervo documental del cabildo
  (actas, censos, reglamentos, mapas, solicitudes)
  
FASE 2 — Campo
  Visita al territorio: grupos focales, entrevistas,
  cartografía social, levantamiento GPS de capas SIG
  
FASE 3 — Post-campo
  Síntesis: concepto etnológico + borrador de resolución
  → Registro en DAIRM / Ministerio del Interior
```

### 3.2 El Corpus de Datos

Cada estudio produce un corpus heterogéneo almacenado en Google Drive:

| Tipo | Formatos | Ejemplos |
|---|---|---|
| Documentos formales | PDF, DOCX | Actas, censos, resoluciones, reglamentos |
| Datos tabulares | XLSX | Autocenso, matrices SIG, metadatos capas |
| Proyectos geoespaciales | .qgz, GeoPackage, .shp | Proyecto QGIS con capas levantadas en campo |
| Evidencia fotográfica | JPG, HEIC | Fotos clasificadas por práctica cultural |
| Registros audiovisuales | MP4, MP3 | Entrevistas, notas de voz |

### 3.3 Las Cuatro Capas SIG Principales

El análisis geoespacial se basa siempre en cuatro capas puntuales levantadas en campo:

| Capa | Código | Contenido |
|---|---|---|
| Prácticas Culturales | PUNT_PC | Pesca, medicina, caza, cocina, agricultura, artesanía, rituales |
| Expresiones Simbólicas | PUNT_ES | Lugares sagrados, sitios de memoria, cementerios ancestrales |
| Entornos Territoriales | PUNT_ET | Zonas de uso tradicional, cultivos, protección, zonas de riesgo |
| Procesos Organizativos | PUNT_PO | Asambleas, gobierno propio, control territorial, guardia indígena |

### 3.4 El Producto Final

El informe Word que produce el sistema es la **base técnica de la resolución administrativa** que reconoce a la comunidad. Tiene estructura institucional fija definida por el Ministerio del Interior.

---

## 4. Actores del Sistema

| Rol | Descripción | Acceso |
|---|---|---|
| **Administrador** | Gestiona usuarios, estudios y configuraciones | CRUD completo |
| **Responsable Técnico** | Profesional SIG. Dispara, revisa y aprueba informes | Todo excepto admin de usuarios |
| **Equipo de Campo** | Consultores que levantaron la información | Solo lectura del estado |
| **Supervisor** | Coordinador del proyecto (ej. PhD) | Solo lectura y aprobación final |

---

## 5. Stack Tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Rendimiento, tipado, ecosistema SIG |
| Motor SIG | GeoPandas, Shapely, Matplotlib, Contextily | Análisis vectorial + cartografía |
| Procesamiento documental | pdfplumber, python-docx, pandas | Extracción multi-formato |
| NLP / Entidades | spaCy (es_core_news_lg) | Extracción de nombres, fechas, lugares |
| Generación Word | python-docx | Plantillado institucional |
| Base de datos | PostgreSQL 15 | Metadatos, usuarios, versiones, auditoría |
| Integración nube | Google Drive API v3 | Corpus almacenado por el cliente |
| Frontend | HTML/CSS/JS (sin framework pesado) | Interfaz ligera, sin dep. complejas |
| Hosting | Servidores Simonky S.A.S | Incluido en contrato |
| Seguridad | TLS + JWT + bcrypt | Estándar industria |

---

## 6. Flujo Operativo Completo

```
[Corpus en Google Drive — FASE 1, 2, 3]
           │
           ▼
   1. SINCRONIZACIÓN
      └─ Google Drive API conecta el estudio
      └─ Sistema reconoce estructura por fases
      └─ Clasifica archivos por tipo y rol
           │
           ▼
   2. PROCESAMIENTO PARALELO
      ┌─────────────────────┬──────────────────────┐
      │    MOTOR SIG        │   MOTOR DOCUMENTAL   │
      │  GeoPandas+Shapely  │   pdfplumber+spaCy   │
      │  Lee proyecto QGIS  │   Extrae cifras,     │
      │  Genera buffers,    │   nombres, fechas,   │
      │  matrices, cruces,  │   ubicaciones de     │
      │  mapas temáticos    │   PDFs/DOCX/XLSX     │
      └─────────────────────┴──────────────────────┘
           │
           ▼
   3. MÓDULOS ANALÍTICOS DE VALOR AGREGADO
      └─ Validación discrepancias poblacionales
      └─ Cruce con datos abiertos DANE
      └─ Red de actores clave (diagrama)
      └─ Línea de tiempo eventos organizativos
           │
           ▼
   4. ENSAMBLADO DEL INFORME
      └─ python-docx ensambla plantilla Word
      └─ Inserta mapas, tablas, textos, gráficos
           │
           ▼
   5. REVISIÓN HUMANA
      └─ Responsable técnico revisa en interfaz web
      └─ Ajusta parámetros si necesario
      └─ Aprueba versión final
           │
           ▼
   6. EXPORTACIÓN
      └─ Documento Word (.docx) listo para entregar
      └─ Archivos SIG resultantes
      └─ Registro de trazabilidad / auditoría
```

---

## 7. Pantallas del Sistema (basado en mockup)

| Pantalla | Descripción |
|---|---|
| **Login** | Autenticación con email/contraseña |
| **Dashboard** | Resumen de estudios activos, métricas, actividad reciente |
| **Lista de Estudios** | Todos los estudios con estado y búsqueda |
| **Nuevo Estudio** | Formulario de creación de estudio etnológico |
| **Detalle de Estudio** | Vista completa con corpus, análisis y generación |
| **Sincronización Drive** | Panel de conexión y revisión del corpus |
| **Motor SIG** | Configuración y resultados del análisis geoespacial |
| **Vista de Mapa** | Mapa interactivo con capas georreferenciadas |
| **Generación de Informe** | Disparador + seguimiento del proceso |
| **Revisión de Informe** | Preview Word + ajustes antes de exportar |
| **Usuarios** | Gestión de cuentas y roles (solo admin) |
| **Configuración** | Parámetros del sistema |

---

## 8. Entregables del Proyecto

| Entregable | Descripción |
|---|---|
| Plataforma web en producción | Aplicación completa desplegada |
| Código fuente en Git | Repositorio privado con historial |
| Manual de arquitectura | Componentes, interfaces, decisiones técnicas |
| Manual de administración | Despliegue, monitoreo, resolución de incidencias |
| Manual de usuario | Paso a paso para profesionales del cliente |
| Documentación motor SIG | Algoritmos de buffer, matrices, superposiciones |
| Sesiones de capacitación | Grabadas, con material de referencia |

---

## 9. Inversión y Cronograma

| Fase | Duración | Descripción |
|---|---|---|
| Implementación | 4 semanas | Diseño, desarrollo, pruebas, despliegue |
| Operación estable | 11 meses | Soporte, mantenimiento, mejoras menores |
| **Total** | **12 meses** | Incluye hosting |

**Inversión total:** 40.000.000 COP (IVA incluido)

---

*Documento raíz del proyecto EtnoSIG. Ver archivos relacionados en la carpeta DOCUMENTACION/ para especificaciones detalladas.*
