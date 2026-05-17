# EtnoSIG — Requerimientos Funcionales y No Funcionales
## Especificación Completa

---

## REQUERIMIENTOS FUNCIONALES

### RF-001 — Autenticación y Sesión

| Campo | Detalle |
|---|---|
| **ID** | RF-001 |
| **Módulo** | Autenticación |
| **Descripción** | El sistema debe autenticar usuarios mediante email y contraseña. |
| **Precondición** | El usuario tiene cuenta activa en el sistema. |
| **Flujo principal** | 1. Usuario ingresa email y contraseña. 2. Sistema valida credenciales. 3. Sistema emite JWT (access token 8h + refresh token 7d). 4. Usuario accede al dashboard. |
| **Flujo alternativo** | Credenciales incorrectas: mensaje de error genérico (no revelar si el email existe). |
| **Criterio de aceptación** | Login exitoso redirige al dashboard. Sesión expira tras 8h de inactividad. |

---

### RF-002 — Gestión de Usuarios

| Campo | Detalle |
|---|---|
| **ID** | RF-002 |
| **Módulo** | Administración de Usuarios |
| **Descripción** | El administrador puede crear, editar, suspender y eliminar usuarios. |
| **Roles disponibles** | `admin`, `tecnico`, `campo`, `supervisor` |
| **Campos del usuario** | nombre_completo, email (único), rol, estado (activo/suspendido), estudios_asignados[], fecha_creacion, ultimo_acceso |
| **Permisos por rol** | Ver tabla de permisos en sección 4 |
| **Criterio de aceptación** | Solo usuarios con rol `admin` acceden al módulo de usuarios. |

---

### RF-003 — Crear Estudio Etnológico

| Campo | Detalle |
|---|---|
| **ID** | RF-003 |
| **Módulo** | Estudios |
| **Descripción** | El sistema permite crear un nuevo estudio para una comunidad indígena. |
| **Formulario** | Ver `06_FORMULARIOS.md` — Formulario F-01 |
| **Campos requeridos** | nombre_comunidad, pueblo_indigena, municipio, departamento, url_drive_fase1, url_drive_fase2, url_drive_fase3, contrato_referencia, equipo_tecnico[] |
| **Campos opcionales** | coordenadas_aproximadas, nit_comunidad, gobernador_nombre, notas_adicionales |
| **Estado inicial** | `borrador` |
| **Criterio de aceptación** | Estudio creado aparece en lista con estado `borrador`. |

---

### RF-004 — Sincronización con Google Drive

| Campo | Detalle |
|---|---|
| **ID** | RF-004 |
| **Módulo** | Ingesta / Google Drive |
| **Descripción** | El sistema se conecta a Google Drive y sincroniza el corpus del estudio por fases. |
| **Método de conexión** | OAuth2 con Google Drive API v3, token almacenado por usuario. |
| **Proceso** | 1. Usuario autoriza acceso a Drive. 2. Sistema navega carpetas FASE 1, FASE 2, FASE 3. 3. Sistema cataloga todos los archivos por tipo y rol. 4. Genera reporte de corpus: archivos encontrados, ausentes, advertencias. |
| **Reconocimiento automático** | PDF → documento formal; XLSX → datos tabulares; .qgz → proyecto QGIS; .gpkg → GeoPackage; JPG/HEIC → evidencia fotográfica; MP4/MP3 → audiovisual |
| **Criterio de aceptación** | Reporte de corpus muestra árbol de archivos con estado OK/WARN por cada archivo esperado. |

---

### RF-005 — Procesamiento Geoespacial (Motor SIG)

| Campo | Detalle |
|---|---|
| **ID** | RF-005 |
| **Módulo** | Motor SIG |
| **Descripción** | El sistema ejecuta análisis espaciales sobre las capas del proyecto QGIS. |
| **Inputs** | Proyecto .qgz o GeoPackage con las 4 capas principales + capas de soporte |
| **Outputs obligatorios** | Buffers de 50m (4 capas), 6 matrices de distancia, 6 superposiciones, 4 mapas temáticos PNG |
| **Capas de entrada** | PUNT_PracticasCulturales, PUNT_ExpresionesSimbólicas, PUNT_EntornosTerritoriales, PUNT_ProcesosOrganizativos |
| **Parámetro configurable** | Radio de buffer (default: 50m, ajustable por estudio) |
| **Criterio de aceptación** | Resultados deben coincidir con los producidos por QGIS manualmente (validado en semana 4). |

---

### RF-006 — Generación de Mapas Temáticos

| Campo | Detalle |
|---|---|
| **ID** | RF-006 |
| **Módulo** | Motor SIG |
| **Descripción** | El sistema genera un mapa PNG por cada capa principal más el mapa integrado. |
| **Simbología** | Consistente entre estudios (definida en plantilla de configuración) |
| **Capas de referencia** | Hidrografía, vías, infraestructura comunitaria como fondo |
| **Formato salida** | PNG 300 DPI para inserción en Word, SVG para visualización web |
| **Herramientas** | GeoPandas + Matplotlib + Contextily (tiles de fondo) |
| **Criterio de aceptación** | Cada mapa incluye: norte, escala, leyenda, título de capa, fuente. |

---

### RF-007 — Vista de Mapa Interactivo

| Campo | Detalle |
|---|---|
| **ID** | RF-007 |
| **Módulo** | Mapa / Georreferenciación |
| **Descripción** | Interfaz web con mapa interactivo donde se visualizan los resguardos reconocidos y en proceso. |
| **Funcionalidades** | Zoom, pan, clic en punto para ver info, filtro por estado (reconocido/en proceso), capas activables/desactivables |
| **Datos mostrados** | Punto por resguardo: nombre, municipio, estado, fecha reconocimiento |
| **Tecnología** | Leaflet.js + tiles OpenStreetMap |
| **Criterio de aceptación** | Mapa carga en < 3s. Cada punto muestra popup con datos básicos del resguardo. |

---

### RF-008 — Procesamiento Documental

| Campo | Detalle |
|---|---|
| **ID** | RF-008 |
| **Módulo** | Motor Documental |
| **Descripción** | El sistema extrae datos estructurados de los documentos del corpus. |
| **Documentos procesados** | Actas de elección, censos, derechos de petición, autocenso, reglamento, ficha de pre-campo |
| **Datos extraídos** | Cifras poblacionales (familias, personas), nombres y cargos de actores, fechas de eventos, ubicaciones territoriales, referencias normativas |
| **Tecnología** | pdfplumber (PDF), python-docx (DOCX), pandas (XLSX), spaCy es_core_news_lg (NLP) |
| **Criterio de aceptación** | Sistema extrae correctamente ≥ 80% de los datos estructurados de un corpus de referencia. |

---

### RF-009 — Validación de Discrepancias Poblacionales

| Campo | Detalle |
|---|---|
| **ID** | RF-009 |
| **Módulo** | Módulo Analítico 1 |
| **Descripción** | Sistema cruza automáticamente fuentes de datos poblacionales y alerta sobre inconsistencias. |
| **Fuentes a cruzar** | Censo Ministerio, Derecho de Petición, Autocenso comunitario, Registros del Cabildo |
| **Métricas** | Número de familias y número de personas por cada fuente |
| **Output** | Tabla comparativa con columnas resaltadas en rojo donde hay discrepancia (> 10% de diferencia) |
| **Criterio de aceptación** | Para el corpus Murui Muina: detecta discrepancia entre autocenso 2023 (102 personas) y autocenso depurado 2026 (31 personas). |

---

### RF-010 — Cruce con Datos DANE

| Campo | Detalle |
|---|---|
| **ID** | RF-010 |
| **Módulo** | Módulo Analítico 2 |
| **Descripción** | Sistema consulta API datos abiertos DANE para enriquecer el contexto demográfico del municipio. |
| **Datos consultados** | Población total municipal, porcentaje población indígena, proyecciones, autorreconocimiento étnico |
| **API** | datos.gov.co — Censo Nacional de Población y Vivienda 2018 |
| **Output** | Párrafo contextual + tabla comparativa cabildo vs. municipio vs. departamento |
| **Caché** | Resultados cacheados 30 días por municipio |
| **Criterio de aceptación** | Para municipio La Montañita, Caquetá: muestra 14.714 habitantes, 1.2% población indígena. |

---

### RF-011 — Red de Actores Clave

| Campo | Detalle |
|---|---|
| **ID** | RF-011 |
| **Módulo** | Módulo Analítico 3 |
| **Descripción** | Sistema genera diagrama de la estructura organizativa del cabildo. |
| **Fuente** | Ficha de pre-campo + actas de elección/posesión |
| **Cargos identificados** | Gobernador/a, Cacique, Vicegobernador, Secretaria, Tesorera, Fiscal, Médico Tradicional, Consejero/a Mayor, Abuela Consejera |
| **Output primario** | Organigrama jerárquico (imagen PNG) para insertar en Word |
| **Output secundario** | Red de co-ocurrencias: nodos = actores, aristas = co-mención en documentos (opcional) |
| **Criterio de aceptación** | Organigrama muestra correctamente la jerarquía: Asamblea → Junta Directiva → roles individuales. |

---

### RF-012 — Línea de Tiempo de Eventos

| Campo | Detalle |
|---|---|
| **ID** | RF-012 |
| **Módulo** | Módulo Analítico 4 |
| **Descripción** | Sistema extrae fechas y eventos relevantes y construye cronología visual. |
| **Eventos extraídos** | Asambleas, elecciones, posesiones, derechos de petición, hitos institucionales, fechas de despojo/reconstitución |
| **Output** | Línea de tiempo horizontal (imagen PNG) para inserción en Word |
| **Criterio de aceptación** | Para corpus Murui Muina: incluye hitos desde 1909 (llegada cauchero) hasta 2026 (estudio). |

---

### RF-013 — Generación del Informe Word

| Campo | Detalle |
|---|---|
| **ID** | RF-013 |
| **Módulo** | Plantillador / Generador |
| **Descripción** | Sistema ensambla todos los componentes en un documento Word siguiendo la plantilla institucional. |
| **Estructura del Word** | Ver `10_GENERACION_INFORME.md` — Estructura completa |
| **Componentes insertados** | Mapas PNG, tablas de análisis, textos contextualizados, organigrama, línea de tiempo, referencias académicas |
| **Tiempo máximo** | < 15 minutos para corpus de hasta 2 GB |
| **Versiones** | Cada generación crea una versión numerada. El responsable puede volver a versiones anteriores. |
| **Criterio de aceptación** | El Word generado tiene la misma estructura que `Informe_Comunidad Murui Muina.pdf` de referencia. |

---

### RF-014 — Revisión y Aprobación del Informe

| Campo | Detalle |
|---|---|
| **ID** | RF-014 |
| **Módulo** | Revisión |
| **Descripción** | Interfaz de revisión donde el responsable técnico valida el informe antes de exportar. |
| **Funcionalidades** | Preview del documento, tabla de contenido navegable, secciones con marcadores de advertencia, ajuste de parámetros, re-generación de secciones específicas |
| **Estados del informe** | `generando` → `listo_revision` → `en_revision` → `aprobado` → `exportado` |
| **Criterio de aceptación** | Responsable puede aprobar y descargar el Word en ≤ 3 clics desde el estado `listo_revision`. |

---

### RF-015 — Exportación

| Campo | Detalle |
|---|---|
| **ID** | RF-015 |
| **Módulo** | Exportación |
| **Descripción** | Sistema permite descargar el informe final y los archivos SIG resultantes. |
| **Formatos exportados** | Word (.docx), mapas PNG, GeoPackage con capas procesadas, ZIP con todo |
| **Trazabilidad** | Cada exportación queda registrada con: usuario, fecha/hora, versión del informe, hash del archivo |
| **Criterio de aceptación** | Descarga exitosa del ZIP con todos los entregables en < 30s. |

---

### RF-016 — Historial y Trazabilidad

| Campo | Detalle |
|---|---|
| **ID** | RF-016 |
| **Módulo** | Auditoría |
| **Descripción** | Sistema mantiene registro completo de todas las acciones sobre cada estudio. |
| **Registro incluye** | Usuario, acción, timestamp, parámetros utilizados, resultado |
| **Retención** | Mínimo 2 años |
| **Criterio de aceptación** | Administrador puede ver bitácora completa de un estudio ordenada por fecha. |

---

### RF-017 — Dashboard de Métricas

| Campo | Detalle |
|---|---|
| **ID** | RF-017 |
| **Módulo** | Dashboard |
| **Descripción** | Pantalla principal con resumen del estado de todos los estudios activos. |
| **Métricas mostradas** | Total estudios, estudios en proceso, informes generados, informes aprobados, tiempo promedio de generación |
| **Tarjetas de estudio** | Nombre comunidad, municipio, estado, progreso (barra), última actividad |
| **Criterio de aceptación** | Dashboard carga en < 2s. Métricas en tiempo real. |

---

### RF-018 — Formulario de Información del Resguardo

| Campo | Detalle |
|---|---|
| **ID** | RF-018 |
| **Módulo** | Formularios |
| **Descripción** | Formulario web donde el usuario ingresa o confirma la información del resguardo/cabildo. |
| **Secciones** | Identificación, Territorio, Población, Organización, Documentos, Drive |
| **Detalle completo** | Ver `06_FORMULARIOS.md` — Formulario F-02 |
| **Criterio de aceptación** | Datos del formulario se auto-llenan cuando el motor documental los extrae del corpus. El usuario valida o corrige. |

---

### RF-019 — Gestión de Roles y Permisos

| Campo | Detalle |
|---|---|
| **ID** | RF-019 |
| **Módulo** | Seguridad |
| **Descripción** | Control granular de acceso basado en roles. |
| **Permisos** | Ver tabla en `05_GESTION_USUARIOS.md` |
| **Criterio de aceptación** | Usuario con rol `campo` no puede acceder a gestión de usuarios ni exportar informes. |

---

### RF-020 — Notificaciones

| Campo | Detalle |
|---|---|
| **ID** | RF-020 |
| **Módulo** | Notificaciones |
| **Descripción** | Sistema notifica por email eventos clave del proceso. |
| **Eventos notificados** | Sincronización Drive completada, informe listo para revisión, informe aprobado, error en procesamiento |
| **Configuración** | Cada usuario configura qué notificaciones recibir |
| **Criterio de aceptación** | Email llega en < 5 minutos tras el evento. |

---

## REQUERIMIENTOS NO FUNCIONALES

### RNF-001 — Rendimiento

| ID | Criterio | Valor |
|---|---|---|
| RNF-001a | Generación de informe completo | < 15 minutos para corpus hasta 2 GB |
| RNF-001b | Carga del dashboard | < 2 segundos |
| RNF-001c | Sincronización Drive (listado) | < 30 segundos para hasta 500 archivos |
| RNF-001d | Carga del mapa interactivo | < 3 segundos |
| RNF-001e | Tiempo de respuesta API (endpoints regulares) | < 500ms p95 |

---

### RNF-002 — Disponibilidad

| ID | Criterio | Valor |
|---|---|---|
| RNF-002a | Uptime mensual objetivo | 99% |
| RNF-002b | Ventanas de mantenimiento | Anunciadas con 48h de anticipación |
| RNF-002c | Respaldos automatizados | Diarios, retención 30 días mínimo |
| RNF-002d | Tiempo de recuperación (RTO) | < 4 horas para incidentes críticos |

---

### RNF-003 — Seguridad

| ID | Criterio | Detalle |
|---|---|---|
| RNF-003a | Cifrado en tránsito | TLS 1.2+ en todos los endpoints |
| RNF-003b | Cifrado en reposo | Contraseñas con bcrypt (cost≥12), datos sensibles con AES-256 |
| RNF-003c | Autenticación | JWT con expiración 8h, refresh token 7d |
| RNF-003d | Protección CSRF | Tokens CSRF en formularios |
| RNF-003e | Rate limiting | 100 req/min por IP en endpoints de auth |
| RNF-003f | Auditoría | Log inmutable de todos los accesos y operaciones |
| RNF-003g | Tokens Google | Almacenados cifrados, nunca en logs |

---

### RNF-004 — Protección de Datos

| ID | Criterio | Detalle |
|---|---|---|
| RNF-004a | Marco legal | Ley 1581 de 2012 (Colombia) |
| RNF-004b | Consideraciones éticas | Información etnográfica de comunidades indígenas — acceso solo a personal autorizado |
| RNF-004c | Datos sensibles | Cédulas, datos de salud, información de seguridad (amenazas armadas) — cifrado adicional |
| RNF-004d | Retención | Datos de estudios conservados mínimo 5 años por requisito legal |
| RNF-004e | Portabilidad | Cliente puede exportar todo su corpus en formato abierto |

---

### RNF-005 — Usabilidad

| ID | Criterio | Detalle |
|---|---|---|
| RNF-005a | Audiencia objetivo | Profesionales SIG y antropólogos, sin formación en programación |
| RNF-005b | Curva de aprendizaje | Cubierta en una sesión de capacitación de 2 horas |
| RNF-005c | Idioma | Español (Colombia) en toda la interfaz |
| RNF-005d | Accesibilidad | Contraste AA mínimo (WCAG 2.1) |
| RNF-005e | Mensajes de error | En lenguaje claro, sin tecnicismos |
| RNF-005f | Diseño | Visual institucional colombiano (gov.co aesthetic) |

---

### RNF-006 — Escalabilidad

| ID | Criterio | Detalle |
|---|---|---|
| RNF-006a | Estudios simultáneos | Hasta 20 estudios activos en paralelo sin degradación |
| RNF-006b | Procesamiento concurrente | Cola de trabajos SIG (máx. 3 simultáneos por servidor) |
| RNF-006c | Almacenamiento | Diseñado para crecer sin rediseño de arquitectura |

---

### RNF-007 — Mantenibilidad

| ID | Criterio | Detalle |
|---|---|---|
| RNF-007a | Cobertura de tests | ≥ 80% en motor SIG y motor documental |
| RNF-007b | Documentación de código | Docstrings en funciones críticas |
| RNF-007c | Estilo de código | PEP8 + Black formatter |
| RNF-007d | Reproducibilidad | Los resultados del motor SIG son deterministas (mismo corpus → mismo resultado) |

---

### RNF-008 — Compatibilidad

| ID | Criterio | Detalle |
|---|---|---|
| RNF-008a | Navegadores | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+ |
| RNF-008b | Dispositivos | Desktop-first. Tablet funcional, móvil consulta básica |
| RNF-008c | Formatos de entrada | GeoPackage, shapefile, .qgz, PDF, DOCX, XLSX, JPG, HEIC |
| RNF-008d | Formato de salida | DOCX (Word 2016+), PNG 300 DPI, ZIP |

---

## TABLA DE PERMISOS POR ROL

| Funcionalidad | admin | tecnico | campo | supervisor |
|---|:---:|:---:|:---:|:---:|
| Ver dashboard | ✓ | ✓ | ✓ | ✓ |
| Ver lista estudios | ✓ | ✓ | ✓ (solo asignados) | ✓ |
| Crear estudio | ✓ | ✓ | — | — |
| Editar estudio | ✓ | ✓ | — | — |
| Sincronizar Drive | ✓ | ✓ | — | — |
| Disparar generación | ✓ | ✓ | — | — |
| Revisar informe | ✓ | ✓ | — | ✓ (solo leer) |
| Aprobar informe | ✓ | ✓ | — | ✓ |
| Exportar informe | ✓ | ✓ | — | ✓ |
| Ver mapa georreferenciación | ✓ | ✓ | ✓ | ✓ |
| Gestión de usuarios | ✓ | — | — | — |
| Configuración sistema | ✓ | — | — | — |
| Ver auditoría | ✓ | — | — | — |

---

## REGLAS DE NEGOCIO

| ID | Regla |
|---|---|
| RN-001 | Un estudio solo puede disparar generación si tiene corpus sincronizado (FASE 2 con proyecto QGIS obligatorio). |
| RN-002 | Solo el responsable técnico asignado puede aprobar el informe de su estudio. |
| RN-003 | Una vez aprobado, el informe no puede modificarse. Se debe crear una nueva versión. |
| RN-004 | El token de Google Drive se almacena por usuario, no por estudio. |
| RN-005 | Los buffers de 50m son el valor por defecto, pero el responsable técnico puede ajustarlos antes de generar. |
| RN-006 | Las discrepancias poblacionales > 10% se marcan automáticamente como advertencia en el informe. |
| RN-007 | El mapa georreferenciado solo muestra resguardos de estudios en estado `aprobado` o `exportado`. |
| RN-008 | Las credenciales de Google (OAuth tokens) nunca se registran en logs ni se exportan. |
