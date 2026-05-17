# EtnoSIG — Especificación de Módulos del Sistema

---

## MÓDULO 1 — AUTENTICACIÓN Y GESTIÓN DE SESIÓN

### Responsabilidad
Controlar el acceso al sistema. Emitir y validar tokens JWT. Gestionar sesiones.

### Componentes
- `backend/app/auth/router.py` — Endpoints de login, logout, refresh, me
- `backend/app/auth/service.py` — Lógica de autenticación
- `backend/app/auth/models.py` — Modelo User (SQLAlchemy)
- `frontend/js/auth.js` — Lógica de sesión en el cliente

### Comportamiento Clave

```python
# Flujo de autenticación
1. POST /api/auth/login
   ├── Validar email/password contra DB (bcrypt.checkpw)
   ├── Si falla: registrar intento en audit_log, retornar 401 genérico
   └── Si éxito:
       ├── Generar access_token (JWT, 8h, HS256)
       ├── Generar refresh_token (JWT, 7d)
       ├── Actualizar ultimo_acceso en DB
       └── Retornar tokens + perfil de usuario

# Guard de autenticación (FastAPI dependency)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user = await user_service.get_by_id(user_id)
        if not user or user.estado != "activo":
            raise HTTPException(401)
        return user
    except JWTError:
        raise HTTPException(401)
```

### Pantalla Asociada
**Login** — Mockup: pantalla de inicio de sesión con:
- Logo EtnoSIG centrado (Playfair Display, navy)
- Campo email + contraseña
- Botón "Ingresar" (rojo institucional)
- Footer con referencia al Ministerio del Interior

---

## MÓDULO 2 — GESTIÓN DE USUARIOS

### Responsabilidad
CRUD de usuarios, asignación de roles, reset de contraseñas.

### Solo accesible por: `admin`

### Comportamiento Clave

```python
# Crear usuario (admin)
async def create_user(data: UserCreate) -> User:
    # Verificar email único
    if await user_repo.exists_by_email(data.email):
        raise HTTPException(409, "Email ya registrado")
    # Hash de contraseña
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt(rounds=12))
    # Crear en DB
    user = await user_repo.create({...})
    # Enviar email de bienvenida con credenciales temporales
    await notification_service.send_welcome_email(user)
    return user

# Suspender usuario (no eliminar si tiene estudios)
async def suspend_user(user_id: UUID) -> None:
    user = await user_repo.get_or_404(user_id)
    if user.estudios_activos_count > 0:
        # Solo suspender, no eliminar
        await user_repo.update(user_id, {"estado": "suspendido"})
    else:
        # Sin estudios: eliminar físicamente
        await user_repo.delete(user_id)
```

### Pantalla Asociada
**Administración de Usuarios** — Tabla con:
- Columnas: Nombre, Email, Rol (badge), Estado (badge), Estudios asignados, Último acceso, Acciones
- Filtros por rol y estado
- Botón "Nuevo usuario" → modal con formulario
- Acciones por fila: Editar, Suspender/Activar, Resetear contraseña

---

## MÓDULO 3 — GESTIÓN DE ESTUDIOS

### Responsabilidad
CRUD de estudios etnológicos. Orquestación del flujo completo de un estudio.

### Comportamiento Clave

```python
# Crear estudio
async def create_study(data: StudyCreate, created_by: UUID) -> Study:
    study = await study_repo.create({
        **data.dict(),
        "estado": "borrador",
        "created_by": created_by
    })
    # Asignar equipo
    for user_id in data.equipo_ids:
        await study_team_repo.create({"study_id": study.id, "user_id": user_id})
    # Log
    await audit_service.log(created_by, study.id, "crear_estudio")
    return study

# Transición de estado
async def transition_state(study_id: UUID, nuevo_estado: str, user_id: UUID):
    TRANSICIONES_VALIDAS = {
        "borrador": ["sincronizando"],
        "corpus_ok": ["procesando"],
        "listo_revision": ["en_revision"],
        "en_revision": ["aprobado", "listo_revision"],  # puede devolver
        "aprobado": ["exportado"]
    }
    study = await study_repo.get_or_404(study_id)
    if nuevo_estado not in TRANSICIONES_VALIDAS.get(study.estado, []):
        raise HTTPException(409, f"No se puede pasar de '{study.estado}' a '{nuevo_estado}'")
    await study_repo.update(study_id, {"estado": nuevo_estado})
    await audit_service.log(user_id, study_id, f"cambio_estado_{nuevo_estado}")
```

### Pantallas Asociadas
1. **Dashboard** — Tarjetas de estudio con: nombre, municipio, estado (badge), barra de progreso, última actividad
2. **Lista de Estudios** — Tabla con filtros y búsqueda
3. **Formulario Nuevo Estudio** — Formulario multi-sección (ver Módulo 4)
4. **Detalle de Estudio** — Vista completa con tabs: Corpus, SIG, Informe, Historial

---

## MÓDULO 4 — FORMULARIOS

### Responsabilidad
Captura y validación de toda la información de un estudio etnológico.

### Formulario F-01: Datos del Estudio (Creación)

**Sección 1 — Identificación de la Comunidad**
| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| nombre_comunidad | text | Sí | min 5, max 300 chars |
| pueblo_indigena | text | No | — |
| nit_comunidad | text | No | Formato NIT colombiano |
| contrato_referencia | text | No | — |
| notas_adicionales | textarea | No | — |

**Sección 2 — Ubicación Territorial**
| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| departamento | select | Sí | Lista 33 departamentos Colombia |
| municipio | text + autocomplete | Sí | — |
| vereda | text | No | — |
| lat | number | No | -90 a 90 |
| lng | number | No | -180 a 180 |

**Sección 3 — Corpus en Google Drive**
| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| url_drive_fase1 | url | Sí | Must be drive.google.com URL |
| url_drive_fase2 | url | Sí | Must be drive.google.com URL |
| url_drive_fase3 | url | No | Must be drive.google.com URL |

**Sección 4 — Equipo**
| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| responsable_id | select (usuarios activos) | Sí | — |
| equipo_ids | multiselect | No | — |

**Sección 5 — Parámetros SIG**
| Campo | Tipo | Requerido | Default | Validación |
|---|---|---|---|---|
| buffer_metros | number | No | 50 | 10 a 500 |

---

### Formulario F-02: Datos del Resguardo/Cabildo (Detalle)

*Se muestra en la pestaña "Información" del detalle del estudio. Se auto-llena con los datos extraídos del corpus.*

**Sección 1 — Identificación**
| Campo | Tipo | Fuente Auto-llenado |
|---|---|---|
| nombre_oficial | text | Ficha de pre-campo |
| pueblo | text | Ficha de pre-campo |
| clan_principal | text | Reseña histórica |
| forma_organizacion | select (Cabildo/Resguardo/Asociación) | Reglamento interno |
| registro_legal | text | Solicitud formal |

**Sección 2 — Población**
| Campo | Tipo | Fuente Auto-llenado |
|---|---|---|
| familias_activas | number | Autocenso depurado |
| personas_activas | number | Autocenso depurado |
| familias_total | number | Autocenso 2023 |
| personas_total | number | Autocenso 2023 |
| fuente_poblacional_principal | select | — |

**Sección 3 — Autoridades Vigentes**
| Campo | Tipo | Fuente Auto-llenado |
|---|---|---|
| gobernador_nombre | text | Acta de posesión |
| gobernador_cedula | text | Acta de posesión |
| gobernador_contacto | text | RUT / pre-campo |
| cacique_nombre | text | Acta de inicio |
| secretaria_nombre | text | Acta de posesión |
| medico_tradicional | text | Ficha de comisión |

**Sección 4 — Territorio**
| Campo | Tipo | Fuente Auto-llenado |
|---|---|---|
| superficie_ha | number | Solicitud formal |
| tipo_tenencia | select (Comodato/Titulado/Resguardo/Otro) | — |
| nombre_predio | text | Solicitud formal |
| contexto_especial | textarea | — |

**Sección 5 — Documentación**
Lista de documentos requeridos con estado (✓ Presente / ⚠ Faltante):
- Reglamento interno
- Acta de constitución
- Acta de posesión vigente
- RUT DIAN
- Autocenso actualizado
- Reseña histórica
- Mapa territorial
- Solicitud formal ante Ministerio

---

### Formulario F-03: Configuración de Generación del Informe

**Parámetros ajustables antes de generar:**
| Campo | Tipo | Default |
|---|---|---|
| incluir_discrepancias | checkbox | ✓ |
| incluir_dane | checkbox | ✓ |
| incluir_red_actores | checkbox | ✓ |
| incluir_timeline | checkbox | ✓ |
| buffer_metros | number | 50 |
| notas_adicionales | textarea | — |
| seccion_seguridad | checkbox | ✓ (si hay datos de amenazas) |

---

## MÓDULO 5 — SINCRONIZACIÓN GOOGLE DRIVE

### Responsabilidad
Conectar con Google Drive API, catalogar el corpus, descargar archivos para procesamiento.

### Flujo de OAuth2

```
1. Usuario hace clic en "Conectar Google Drive"
2. Frontend llama GET /api/drive/auth-url
3. Backend genera URL de autorización OAuth2 con scopes:
   - https://www.googleapis.com/auth/drive.readonly
4. Frontend redirige a la URL de Google
5. Usuario autoriza en Google
6. Google redirige a GET /api/drive/callback?code=...
7. Backend intercambia code por access_token + refresh_token
8. Backend cifra y almacena tokens en users.google_token
9. Backend redirige frontend con ?drive_connected=true
```

### Estructura Esperada del Drive

```
[Carpeta raíz del estudio en Drive]
├── FASE 1/
│   ├── SOLICITUD/
│   │   ├── 1. Solicitud Formal.pdf
│   │   ├── 2. Reglamento interno.pdf
│   │   ├── 3. Acta de elección.pdf
│   │   ├── 4. Acta de posesión.pdf
│   │   ├── 6. Mapa.pdf
│   │   ├── 7. Reseña histórica.docx
│   │   ├── 8. Autocenso_Murui Muina.xlsx
│   │   └── 8. Autoncenso depurado.xlsx
│   ├── ACERVO_CABILDO/
│   ├── FICHA DE PRE-CAMPO/
│   ├── MODELO CARTAS A TERCEROS/
│   └── NOTIFICACIÓN DE VISITA/
├── FASE 2/
│   ├── ACTA DE INICIO/
│   ├── DIARIO DE CAMPO/
│   ├── EVIDENCIA/
│   │   └── EVIDENCIA FOTOGRÁFICA/
│   │       ├── Artesanías/
│   │       ├── Maloka Murui/
│   │       ├── Objetos culturales/
│   │       └── ...
│   ├── FICHA DE COMISIÓN/
│   └── INFORMACIÓN SIG/
│       └── ETNIA 1/
│           ├── *.qgz (proyecto QGIS)
│           ├── *.gpkg (GeoPackage)
│           └── BASE DE DATOS/
└── FASE 3/
    ├── CONCEPTO/
    └── ACTO ADMINISTRATIVO/
```

### Clasificación Automática de Archivos

```python
ROL_POR_NOMBRE = {
    r"solicitud.*formal": "solicitud_formal",
    r"reglamento.*interno": "reglamento",
    r"acta.*eleccion": "acta_eleccion",
    r"acta.*posesion": "acta_posesion",
    r"autocenso.*depurado": "autocenso_depurado",
    r"autocenso": "autocenso",
    r"pre.campo": "ficha_precampo",
    r"diario.*campo": "diario_campo",
    r"ficha.*comision": "ficha_comision",
    r"\.qgz$": "proyecto_qgis",
    r"\.gpkg$": "geopackage",
    r"\.(jpg|jpeg|heic)$": "evidencia_foto",
}
```

### Pantalla Asociada
**Sincronización Drive** — Árbol de archivos con:
- Ícono de estado por archivo (✓ verde / ⚠ amarillo / ✗ rojo)
- Carpetas expandibles por fase
- Botón "Re-sincronizar"
- Resumen: X archivos encontrados, Y archivos esperados no encontrados

---

## MÓDULO 6 — MOTOR SIG (Análisis Geoespacial)

### Responsabilidad
Leer proyectos QGIS/GeoPackage y ejecutar todos los análisis espaciales estandarizados.

### Librerías
- `geopandas` — manipulación de capas vectoriales
- `shapely` — operaciones geométricas
- `matplotlib` + `contextily` — generación de mapas
- `fiona` — lectura de formatos SIG

### Algoritmos

#### Buffer de Influencia (50m)
```python
def generar_buffer(capa: GeoDataFrame, radio_metros: int = 50) -> GeoDataFrame:
    # Reproyectar a CRS métrico (Colombia: EPSG:3116 — MAGNA-SIRGAS / Colombia Bogota)
    capa_m = capa.to_crs("EPSG:3116")
    buffer = capa_m.geometry.buffer(radio_metros)
    return gpd.GeoDataFrame(geometry=buffer, crs="EPSG:3116").to_crs("EPSG:4326")
```

#### Matriz de Distancia entre Capas
```python
def calcular_matriz_distancia(capa_a: GeoDataFrame, capa_b: GeoDataFrame) -> pd.DataFrame:
    capa_a_m = capa_a.to_crs("EPSG:3116")
    capa_b_m = capa_b.to_crs("EPSG:3116")
    resultados = []
    for _, punto_a in capa_a_m.iterrows():
        for _, punto_b in capa_b_m.iterrows():
            dist = punto_a.geometry.distance(punto_b.geometry)
            resultados.append({
                "origen": punto_a.get("nombre", "Punto A"),
                "destino": punto_b.get("nombre", "Punto B"),
                "distancia_m": round(dist, 2)
            })
    return pd.DataFrame(resultados).sort_values("distancia_m")
```

#### Superposición Territorial
```python
def calcular_superposicion(capa_a: GeoDataFrame, capa_b: GeoDataFrame) -> dict:
    buffer_a = capa_a.to_crs("EPSG:3116").buffer(50)
    buffer_b = capa_b.to_crs("EPSG:3116").buffer(50)
    union_a = buffer_a.union_all()
    union_b = buffer_b.union_all()
    interseccion = union_a.intersection(union_b)
    return {
        "interseccion_m2": round(interseccion.area, 2),
        "area_a_m2": round(union_a.area, 2),
        "area_b_m2": round(union_b.area, 2),
        "porcentaje_solapamiento": round(interseccion.area / min(union_a.area, union_b.area) * 100, 1)
    }
```

#### Generación de Mapa Temático
```python
def generar_mapa(
    capa_principal: GeoDataFrame,
    capas_soporte: dict,
    titulo: str,
    output_path: str,
    dpi: int = 300
) -> str:
    fig, ax = plt.subplots(figsize=(10, 10))
    # Fondo: tiles de OpenStreetMap
    capa_principal.to_crs("EPSG:3857").plot(ax=ax, color="#B22222", markersize=8, zorder=5)
    # Capas de soporte
    for nombre, capa in capas_soporte.items():
        capa.to_crs("EPSG:3857").plot(ax=ax, alpha=0.4, zorder=3)
    # Añadir tiles de fondo
    contextily.add_basemap(ax, source=contextily.providers.OpenStreetMap.Mapnik)
    # Decoraciones
    ax.set_title(titulo, fontsize=14, fontweight="bold", color="#1A3A5C")
    ax.set_axis_off()
    # Escala y norte
    _add_scalebar(ax)
    _add_north_arrow(ax)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output_path
```

### Las 6 Combinaciones de Matrices y Superposiciones
1. Prácticas Culturales ↔ Expresiones Simbólicas
2. Prácticas Culturales ↔ Entornos Territoriales
3. Prácticas Culturales ↔ Procesos Organizativos
4. Expresiones Simbólicas ↔ Entornos Territoriales
5. Expresiones Simbólicas ↔ Procesos Organizativos
6. Entornos Territoriales ↔ Procesos Organizativos

### Pantalla Asociada
**Motor SIG** — Muestra:
- Estado de cada paso (ícono animado en proceso)
- Miniaturas de mapas generados (clic para ver en grande)
- Tabla de resultados de matrices
- Botón "Re-procesar con nuevos parámetros"

---

## MÓDULO 7 — MOTOR DOCUMENTAL (Extracción de Datos)

### Responsabilidad
Leer todos los documentos del corpus y extraer datos estructurados.

### Extractores por Formato

#### PDF (pdfplumber)
```python
def extraer_pdf(ruta: str) -> dict:
    with pdfplumber.open(ruta) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)
        tablas = []
        for page in pdf.pages:
            for tabla in page.extract_tables():
                tablas.append(tabla)
    return {"texto": texto_completo, "tablas": tablas}
```

#### DOCX (python-docx)
```python
def extraer_docx(ruta: str) -> dict:
    doc = Document(ruta)
    texto = "\n".join(p.text for p in doc.paragraphs)
    tablas = [[cell.text for cell in row.cells] for t in doc.tables for row in t.rows]
    return {"texto": texto, "tablas": tablas}
```

#### XLSX (pandas)
```python
def extraer_xlsx(ruta: str) -> dict:
    hojas = {}
    xls = pd.ExcelFile(ruta)
    for nombre_hoja in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=nombre_hoja)
        hojas[nombre_hoja] = df.to_dict(orient="records")
    return {"hojas": hojas}
```

#### NLP — Extracción de Entidades (spaCy)
```python
def extraer_entidades(texto: str) -> dict:
    nlp = spacy.load("es_core_news_lg")
    doc = nlp(texto)
    return {
        "personas": [e.text for e in doc.ents if e.label_ == "PER"],
        "lugares": [e.text for e in doc.ents if e.label_ == "LOC"],
        "organizaciones": [e.text for e in doc.ents if e.label_ == "ORG"],
        "fechas": [e.text for e in doc.ents if e.label_ == "DATE"],
    }
```

#### Patrones Específicos por Documento
```python
# Extracción de cifras poblacionales
PATRONES_POBLACION = [
    r"(\d+)\s+familias",
    r"(\d+)\s+personas",
    r"(\d+)\s+hogares",
    r"conformada\s+por\s+(\d+)",
]

# Extracción de cargos y nombres
PATRONES_CARGOS = [
    r"gobernador[a]?\s+(.+?)(?:\n|,|\.|cedula)",
    r"cacique\s+(.+?)(?:\n|,|\.|cedula)",
    r"secretar[ia]+\s+(.+?)(?:\n|,|\.|cedula)",
]
```

---

## MÓDULO 8 — MÓDULOS ANALÍTICOS DE VALOR AGREGADO

### 8.1 Validación de Discrepancias Poblacionales
```python
# Compara familias y personas entre 4 fuentes
# Genera tabla comparativa con alertas
# Umbral de discrepancia: 10%
```

### 8.2 Cruce con Datos DANE
```python
# API: datos.gov.co
# Endpoint: /resource/3s7n-2acv.json (CNPV 2018 por municipio)
# Cachea respuesta 30 días en Redis/PostgreSQL
# Genera párrafo contextual + tabla comparativa
```

### 8.3 Red de Actores Clave
```python
# Input: extracciones de ficha_precampo + actas
# Output: organigrama jerárquico PNG (matplotlib)
# Jerarquía: Asamblea → Junta Directiva → roles individuales
# Opcional: red de co-ocurrencias (NetworkX)
```

### 8.4 Línea de Tiempo
```python
# Input: todas las fechas extraídas del corpus
# Output: línea de tiempo horizontal PNG (matplotlib)
# Categorías con colores: despojo/fundacion/institucional/campo/tramite
```

---

## MÓDULO 9 — GENERACIÓN DEL INFORME WORD

### Responsabilidad
Ensamblar todos los componentes en un documento Word siguiendo la plantilla institucional del Ministerio del Interior.

### Estructura del Informe Generado

```
informe_[nombre_comunidad]_v[N].docx
│
├─ [Portada]
│   • Logo Ministerio del Interior
│   • Logo Universidad de Cartagena
│   • Nombre de la comunidad (título principal)
│   • Datos del contrato (UC-CPS-MINTERIOR-023-2026)
│   • Equipo técnico
│   • Fecha
│
├─ [1. Vista General de la Comunidad]
│   • Tabla de datos básicos (nombre, NIT, municipio, departamento)
│   • Número de familias y personas (fuentes cruzadas)
│   • Estructura organizativa del cabildo
│
├─ [2. Contexto Territorial y Demográfico]
│   • Mapa de ubicación general
│   • Tabla datos DANE (municipio, departamento)
│   • Comparativa población indígena municipal
│
├─ [3. Dimensión Subjetiva — Identidad]
│   • Texto extraído del corpus
│   • Cosmovisión, autodenominación, elementos culturales
│
├─ [4. Dimensión Intra-Organizativa]
│   • Estructura de gobierno (organigrama PNG)
│   • Cargos y funciones
│   • Sistema normativo interno
│
├─ [5. Dimensión Inter-Relacional]
│   • Relaciones con instituciones (tabla)
│   • Relaciones con otras comunidades
│
├─ [6. Análisis SIG — Por Capa]
│   ├─ 6.1 Prácticas Culturales
│   │   • Mapa temático PNG (300 DPI)
│   │   • Tabla de puntos levantados
│   │   • Justificación teórica
│   ├─ 6.2 Expresiones Simbólicas
│   ├─ 6.3 Entornos Territoriales
│   └─ 6.4 Procesos Organizativos
│
├─ [7. Análisis Espacial Integrado]
│   • Tabla de buffers de influencia
│   • 6 matrices de distancia entre capas
│   • 6 superposiciones territoriales
│   • Mapa integrado PNG
│
├─ [8. Análisis de Discrepancias Poblacionales]
│   • Tabla comparativa (4 fuentes) con celdas resaltadas
│   • Explicación de diferencias
│   • Recomendación de cifra oficial
│
├─ [9. Red de Actores Clave]
│   • Organigrama PNG
│   • Tabla de actores con cargos y datos de contacto
│
├─ [10. Línea de Tiempo]
│   • Imagen PNG de la cronología
│
├─ [11. Evidencia Documental]
│   • Fotografías clasificadas por categoría cultural
│   • Cartografía social
│   • Registros de asistencia
│
├─ [12. Dimensión de Riesgo]
│   • Árbol de amenazas
│   • Vulnerabilidades por dimensión
│   • Estrategias de mitigación
│
├─ [13. Conclusión y Concepto Favorable]
│   • Texto de concepto etnológico
│   • Los 6 criterios de reconocimiento cumplidos
│   • Recomendaciones al Ministerio
│
├─ [14. Referencias Académicas y Normativas]
│   • Marco jurídico
│   • Referencias bibliográficas
│
└─ [Anexos Cartográficos]
    • Mapas finales por capa (alta resolución)
    • Lista de archivos SIG resultantes
```

### Implementación del Plantillador

```python
def ensamblar_informe(study_id: UUID, parametros: dict) -> str:
    doc = Document("templates/informe_base.docx")
    
    # 1. Portada
    _insertar_portada(doc, study_data)
    
    # 2. Sección por sección
    for seccion in SECCIONES_INFORME:
        datos = _obtener_datos_seccion(seccion, study_id)
        _escribir_seccion(doc, seccion, datos)
    
    # 3. Insertar mapas PNG
    for mapa in mapas_generados:
        _insertar_imagen(doc, mapa.path, ancho_cm=15)
    
    # 4. Guardar
    output_path = f"/var/etnosig/files/{study_id}/informe_v{version}.docx"
    doc.save(output_path)
    return output_path
```

---

## MÓDULO 10 — MAPA GEORREFERENCIADO

### Responsabilidad
Interfaz de mapa interactivo donde se visualizan los resguardos georreferenciados.

### Tecnología
- **Leaflet.js** — biblioteca de mapas interactivos
- **OpenStreetMap** — tiles de fondo
- **GeoJSON** — formato de datos desde la API

### Funcionalidades
1. Mapa base de Colombia con zoom libre
2. Puntos por cada resguardo/cabildo procesado (estados: `aprobado` o `exportado`)
3. Click en punto → popup con:
   - Nombre de la comunidad
   - Pueblo indígena
   - Municipio / Departamento
   - Estado del estudio
   - Fecha de aprobación
   - Enlace "Ver detalle"
4. Filtro por departamento (dropdown)
5. Filtro por estado (toggle)
6. Leyenda con colores por estado

### Colores de Puntos en el Mapa
- Azul navy (#1A3A5C) — En proceso
- Rojo institucional (#B22222) — Aprobado
- Oro (#C8922A) — Exportado / Finalizado

---

## MÓDULO 11 — AUDITORÍA Y TRAZABILIDAD

### Responsabilidad
Registrar todas las acciones del sistema para cumplimiento legal y depuración.

### Eventos Auditados
```python
EVENTOS_AUDITADOS = [
    "login", "logout", "login_fallido",
    "crear_estudio", "editar_estudio", "eliminar_estudio",
    "sincronizar_drive", "procesar_gis", "procesar_documentos",
    "generar_informe", "aprobar_informe", "exportar_informe",
    "crear_usuario", "suspender_usuario", "resetear_password",
    "cambiar_rol",
]
```

### Middleware de Auditoría
```python
# Decorator para auditar endpoints
@audit_action("generar_informe")
async def generate_report(study_id: UUID, user = Depends(get_current_user)):
    ...
# Registra automáticamente: user_id, study_id, accion, ip, timestamp, resultado
```
