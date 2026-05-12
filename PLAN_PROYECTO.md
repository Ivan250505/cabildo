# Plan de Desarrollo — Plataforma Automatizada de Análisis Etnográfico
**Cliente:** Cabildo Indígena Murui Muina  
**Proveedor:** Simonky S.A.S — CTO Eduwin Andrés Flórez Orejuela  
**Fecha:** Mayo 2026

---

## Resumen de fases

| Fase | Nombre | Estado |
|------|--------|--------|
| **Fase 1** | Lectura y comprensión del negocio | En curso |
| **Fase 2** | Mockups — Interfaz web (HTML/CSS) | Pendiente |
| **Fase 3** | Arquitectura y diseño técnico | Pendiente |
| **Fase 4** | Motor SIG — Procesamiento geoespacial | Pendiente |
| **Fase 5** | Procesamiento documental y extracción de datos | Pendiente |
| **Fase 6** | Módulos analíticos de valor agregado | Pendiente |
| **Fase 7** | Motor de generación del informe Word | Pendiente |
| **Fase 8** | Integración Google Drive + Backend FastAPI | Pendiente |
| **Fase 9** | Pruebas integrales y validación con corpus real | Pendiente |
| **Fase 10** | Despliegue, capacitación y go-live | Pendiente |

---

## Fase 1 — Lectura y comprensión del negocio

### 1.1 Contexto del negocio

El cliente final ejecuta **estudios etnológicos** para sustentar el reconocimiento estatal de comunidades indígenas ante el Ministerio del Interior de Colombia. Cada estudio produce un corpus heterogéneo de información (documentos, datos tabulares, evidencia geoespacial y audiovisual) que debe ser procesado y traducido en un **informe final** — base técnica de la resolución de reconocimiento del resguardo o cabildo.

El proceso actual es manual o semi-manual. La plataforma busca **industrializarlo**: el responsable técnico dispara la generación del informe, lo revisa, ajusta y exporta. El software no reemplaza el criterio metodológico; lo asiste.

> **Hallazgo clave (nota de voz):** El producto final del software es asistir en la generación de la **resolución de reconocimiento** del resguardo. Todo el corpus alimenta ese objetivo. El usuario ingresa la información inicial, indica dónde está cada dato en Google Drive, y el sistema emite el informe que soporta esa resolución.

---

### 1.2 Actores / Roles del sistema

| Rol | Descripción | Permisos esperados |
|-----|-------------|-------------------|
| **Responsable técnico** | Profesional SIG del cliente. Revisa, ajusta y aprueba cada informe antes de exportarlo. | Disparar generación, revisar, ajustar parámetros, exportar, aprobar |
| **Equipo de campo** | Consultores que levantaron la información en territorio. | Consultar estado del estudio |
| **Administrador** | Gestiona usuarios, estudios y configuraciones del sistema. | CRUD completo de usuarios y estudios |

---

### 1.3 Estructura del corpus — Inventario de datos

El corpus de cada comunidad se organiza en tres fases que coinciden con las carpetas existentes:

#### FASE 1 — Pre-campo
| Subcarpeta | Archivos clave | Uso en el informe |
|------------|---------------|-------------------|
| `SOLICITUD/` | Solicitud Formal.pdf, Reglamento interno.pdf, Acta de elección.pdf, Acta de posesión.pdf, Mapa.pdf, Reseña histórica.docx, Autocenso_Murui Muina.xlsx, Autocenso depurado.xlsx | Datos poblacionales, estructura organizativa, antecedentes históricos |
| `ACERVO_CABILDO MUINA/` | Actas de asamblea (PDF), Acta de Posesión, Censo comunidad (PDF), bd-caqueta.pdf, CC Gobernadora, RUT comunidad, ENLACES CABILDO, Lista de asistencia elecciones | Validación de discrepancias poblacionales, línea de tiempo, red de actores |
| `FICHA DE PRE-CAMPO/` | Ficha de Pre-campo_MURUI (docx/xlsx) | Datos iniciales del cabildo, actores clave, estructura organizativa |
| `MODELO CARTAS A TERCEROS/` | Cartas a universidades, instituciones | Evidencia de relacionamiento institucional |
| `NOTIFICACIÓN DE VISITA/` | Imágenes WhatsApp de notificaciones | Evidencia de proceso previo |

#### FASE 2 — Campo
| Subcarpeta | Archivos clave | Uso en el informe |
|------------|---------------|-------------------|
| `ACTA DE INICIO/` | Acta de inicio (PDF/DOCX), Cronograma | Evidencia de inicio del estudio |
| `DIARIO DE CAMPO/` | Diario de campo (PDF/DOCX) | Evidencia etnográfica narrativa |
| `EVIDENCIA/` | Apuntes reuniones, Cartografía social, Registro de asistencia, Árbol de riesgo, Evidencia fotográfica (HEIC/JPG clasificada por categoría) | Evidencia documental y fotográfica por categorías culturales |
| `EVIDENCIA/EVIDENCIA FOTOGRÁFICA/` | Artesanías, Cartografía social, Danza tradicional, Ficha abundancia, Gastronomía, Indumentaria, Maloka Murui, Objetos culturales, Preparación, Reunión comunidad, Vivienda tradicional | Fotografías clasificadas por práctica cultural |
| `FICHA DE COMISIÓN/` | Ficha de comisión (PDF/DOCX) | Registro de actividades en campo |
| `INFORMACIÓN SIG/ETNIA 1/` | Proyecto QGIS (.qgz), GeoPackage, Fichas de campo (XLSX), Meta datos (XLSX), Análisis (XLSX), Coordenadas (XLSX), Mapa Final - Grupos SIG (imágenes por capa) | **Núcleo del análisis geoespacial** |

#### FASE 3 — Post-campo
| Subcarpeta | Archivos clave | Uso en el informe |
|------------|---------------|-------------------|
| `CONCEPTO/` | Informe_Comunidad Murui Muina.pdf | **Plantilla/referencia del informe final** — documento que el sistema debe replicar |
| `ACTO ADMINISTRATIVO/` | Borrador Acto administrativo | Resolución de reconocimiento — documento destino |

---

### 1.4 Metodología SIG — Capas y análisis espaciales

#### Cuatro capas principales (levantadas en campo)
1. **Prácticas Culturales** — actividades culturales georeferenciadas
2. **Expresiones Simbólicas** — sitios y elementos simbólicos del territorio
3. **Entornos Territoriales** — espacios físicos de uso comunitario
4. **Procesos Organizativos** — lugares de reunión, gobierno y organización

#### Capas de soporte topográfico
- Infraestructura, hidrografía, vías, caminos tradicionales, linderos, zonas ambientales, actividades extractivas

#### Análisis espaciales requeridos (automatizables)
| Análisis | Parámetro | Descripción |
|----------|-----------|-------------|
| Buffers de influencia | 50 metros | Sobre cada una de las 4 capas principales |
| Matrices de distancia | 6 matrices | Entre pares de capas (C1↔C2, C1↔C3, C1↔C4, C2↔C3, C2↔C4, C3↔C4) |
| Superposiciones territoriales | 6 superposiciones | Intersecciones entre pares de capas |
| Mapas temáticos | Por capa | Con simbología consistente + capas de soporte como referencia |

---

### 1.5 Estructura del informe final (output)

El documento Word a generar tiene la siguiente estructura institucional:

```
1. Portada institucional
   - Datos del contrato
   - Datos del equipo técnico
   - Nombre de la comunidad

2. Vista general de la comunidad
   - Datos básicos (nombre, ubicación, municipio, departamento)
   - Número de familias y personas (fuentes cruzadas)
   - Estructura organizativa del cabildo

3. Contexto territorial y demográfico
   - Mapa de ubicación general
   - Cruce con datos DANE (Censo Nacional, proyecciones, autorreconocimiento étnico)

4. Análisis SIG por capa
   Para cada una de las 4 capas principales:
   - Mapa temático con simbología
   - Descripción de los puntos levantados
   - Justificación teórica y referencias académicas

5. Análisis espacial integrado
   - Buffers de influencia (resultados y mapas)
   - Matrices de distancia entre capas
   - Superposiciones territoriales
   - Tabla consolidada de resultados

6. Módulos de valor agregado
   6.1 Validación de discrepancias poblacionales
       (Ministerio vs. Derecho de petición vs. Autocenso vs. Registros cabildo)
   6.2 Cruce con datos abiertos DANE
   6.3 Red de actores clave (organigrama + red de co-ocurrencias)
   6.4 Línea de tiempo de eventos organizativos

7. Evidencia documental
   - Fotografías clasificadas por categoría cultural
   - Cartografía social
   - Registros de asistencia

8. Anexos cartográficos
   - Mapas finales por capa (alta resolución)
   - Archivos resultantes de los análisis SIG

9. Referencias académicas y normativas
```

---

### 1.6 Flujo operativo de la plataforma

```
[Corpus en Google Drive]
         │
         ▼
[1. Sincronización y normalización]
    • Conexión Google Drive API
    • Reconocimiento automático de estructura por fases
    • Clasificación de archivos por tipo y rol

         │
         ▼
[2. Procesamiento paralelo]
    ┌────────────────────┬─────────────────────┐
    │   Motor SIG        │  Motor Documental   │
    │  (GeoPandas,       │  (pdfplumber,       │
    │   Shapely,         │   python-docx,      │
    │   Matplotlib)      │   pandas, spaCy)    │
    └────────────────────┴─────────────────────┘
         │
         ▼
[3. Módulos analíticos de valor agregado]
    • Validación discrepancias poblacionales
    • Cruce DANE
    • Red de actores
    • Línea de tiempo

         │
         ▼
[4. Ensamblado del informe]
    • Plantillador Word (python-docx)
    • Inserción de mapas, tablas, textos, gráficos

         │
         ▼
[5. Revisión humana]
    • Responsable técnico revisa en la interfaz web
    • Ajusta parámetros si es necesario
    • Aprueba la versión final

         │
         ▼
[6. Exportación]
    • Documento Word final
    • Archivos SIG resultantes
    • Registro de trazabilidad
```

---

### 1.7 Fuentes de datos poblacionales (a cruzar y validar)

| Fuente | Archivo origen | Dato esperado |
|--------|---------------|---------------|
| Censo del Ministerio | Censo.pdf / bd-caqueta.pdf | Familias y personas según registro oficial |
| Derecho de petición | Solicitud Formal.pdf | Cifras declaradas por la comunidad en la solicitud |
| Autocenso comunitario | Autocenso_Murui Muina.xlsx / Autocenso depurado.xlsx | Conteo interno de la comunidad |
| Registros del cabildo | LISTA DE ASISTENCIA / ENLACES CABILDO MUINA.docx | Miembros activos registrados |
| DANE | API datos abiertos | Censo Nacional, proyecciones, autorreconocimiento étnico del municipio |

---

### 1.8 Preguntas abiertas a resolver antes de Fase 3

Estos puntos deben aclararse con el responsable técnico del cliente antes de proceder al diseño técnico:

1. **Plantilla del informe**: ¿Se entrega el documento `Informe_Comunidad Murui Muina.pdf` como plantilla de referencia completa para replicar la estructura exacta?
2. **Conexión Google Drive**: ¿El corpus de cada nueva comunidad seguirá exactamente la misma estructura de carpetas FASE 1 / FASE 2 / FASE 3?
3. **Proyecto QGIS**: ¿El archivo `.qgz` contiene siempre las mismas 4 capas principales con los mismos nombres? ¿O varían por estudio?
4. **Número de estudios simultáneos**: ¿Cuántos estudios activos se esperan manejar al mismo tiempo en la plataforma?
5. **Parámetros ajustables**: ¿El buffer de 50m es fijo o puede variar por estudio?
6. **Aprobación del informe**: ¿El responsable técnico edita directamente en la interfaz o descarga el Word y edita en Office?
7. **Idioma de los documentos**: ¿Todos los documentos del corpus están en español?
8. **Evidencia fotográfica**: ¿Las fotos siempre vienen clasificadas en subcarpetas por categoría, o se clasifican manualmente antes de ingresar al sistema?

---

### 1.9 Requerimientos identificados en esta fase

#### Funcionales
- RF-01: El sistema debe conectarse a Google Drive y sincronizar el corpus de cada estudio por fases.
- RF-02: El sistema debe reconocer automáticamente el tipo de cada archivo (PDF, DOCX, XLSX, QGIS, GeoPackage, JPG/HEIC).
- RF-03: El sistema debe leer proyectos QGIS y extraer las 4 capas principales y las capas de soporte.
- RF-04: El sistema debe generar buffers de 50m, 6 matrices de distancia y 6 superposiciones territoriales sobre las capas principales.
- RF-05: El sistema debe generar mapas temáticos por capa con simbología consistente.
- RF-06: El sistema debe extraer datos estructurados de los documentos del corpus (cifras poblacionales, nombres de actores, fechas, cargos).
- RF-07: El sistema debe cruzar fuentes poblacionales y detectar discrepancias automáticamente.
- RF-08: El sistema debe consultar datos abiertos del DANE para enriquecer el contexto territorial.
- RF-09: El sistema debe generar un diagrama de actores clave a partir de la ficha pre-campo y las actas.
- RF-10: El sistema debe construir una línea de tiempo de eventos organizativos extraída de los documentos.
- RF-11: El sistema debe ensamblar todos los componentes en un documento Word siguiendo la plantilla institucional.
- RF-12: El responsable técnico debe poder disparar la generación, revisar el resultado y exportar la versión final desde la interfaz web.
- RF-13: El sistema debe mantener un historial de versiones y trazabilidad completa por cada informe generado.
- RF-14: El sistema debe generar el informe completo en menos de 15 minutos.
- RF-15: El sistema debe permitir gestión de usuarios con roles diferenciados.

#### No funcionales
- RNF-01: Disponibilidad mínima del 99% mensual.
- RNF-02: Autenticación individual por usuario con control de roles.
- RNF-03: Cifrado TLS en tránsito y cifrado en reposo en base de datos.
- RNF-04: Respaldos automatizados diarios con retención mínima de 30 días.
- RNF-05: Interfaz usable sin conocimientos de programación ni SIG.
- RNF-06: Manejo de información conforme a la normativa colombiana de protección de datos (Ley 1581 de 2012) y consideraciones éticas sobre información etnográfica indígena.

---

### 1.10 Stack tecnológico definido (según propuesta)

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+ + FastAPI |
| Procesamiento SIG | GeoPandas, Shapely, Matplotlib, Contextily |
| Procesamiento documental | pdfplumber, python-docx, pandas |
| NLP / Extracción de entidades | spaCy (modelos es_core_news_lg) |
| Motor de plantillas Word | python-docx |
| Base de datos | PostgreSQL |
| Integración nube | Google Drive API v3 |
| Frontend | Aplicación web ligera (por definir en Fase 2) |
| Hosting | Servidores administrados Simonky S.A.S. |
| Formatos de entrada | GeoPackage, .shp, .qgz, PDF, DOCX, XLSX, JPG, HEIC |
| Formato de salida | DOCX (Word), mapas PNG/SVG |

---

### 1.11 Entregables de la Fase 1

- [x] Mapa del negocio y flujo operativo documentado
- [x] Inventario completo del corpus (estructura de carpetas y archivos)
- [x] Estructura del informe final identificada
- [x] Metodología SIG documentada (capas, buffers, matrices, superposiciones)
- [x] Fuentes de datos poblacionales identificadas y cruzadas
- [x] Requerimientos funcionales y no funcionales levantados
- [x] Stack tecnológico confirmado
- [ ] Validación de la plantilla del informe con el responsable técnico *(pendiente reunión)*
- [ ] Aclaración de preguntas abiertas (sección 1.8) *(pendiente)*

---

*Siguiente fase → **Fase 2: Mockups** — Diseño visual de la interfaz web en HTML/CSS*
