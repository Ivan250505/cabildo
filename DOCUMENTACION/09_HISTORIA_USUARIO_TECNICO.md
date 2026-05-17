# Historia de Usuario — Técnico de Campo (Rol: `tecnico`)
## Plataforma EtnIA · Simonky S.A.S.

> **Actor principal:** Profesional SIG / Técnico encuestador asignado a un estudio etnológico.  
> **Objetivo:** Registrar un nuevo estudio, conectar el corpus en Google Drive, procesarlo y obtener el informe Word listo para el Ministerio del Interior.  
> **Rol en el sistema:** `tecnico` — puede crear estudios, sincronizar Drive, disparar análisis, revisar y exportar informes. No gestiona usuarios ni configura el sistema.

---

## Resumen del Flujo

```
[INICIO]
    │
    ▼
 1. LOGIN ──────────────────► Dashboard
    │
    ▼
 2. CREAR ESTUDIO ──────────► Formulario: nombre comunidad, municipio,
    │                          departamento, pueblo indígena, Drive URLs
    │                          Estado inicial: BORRADOR
    ▼
 3. CONECTAR GOOGLE DRIVE ──► OAuth2 Google → autorizar acceso
    │                          Sistema navega carpetas FASE 1/2/3
    │                          Reporte de corpus: archivos OK / ⚠ faltantes
    │                          Estado: SINCRONIZANDO → CORPUS_OK
    ▼
 4. ANÁLISIS SIG ───────────► Sistema lee proyecto QGIS (.qgz / .gpkg)
    │                          Genera: buffers 50m · matrices distancia
    │                          superposiciones · mapas temáticos PNG
    │                          Estado: PROCESANDO
    ▼
 5. GENERACIÓN INFORME ─────► Motor documental extrae datos del corpus
    │                          Módulos: discrepancias · DANE · actores · timeline
    │                          python-docx ensambla Word institucional
    │                          Estado: LISTO_REVISION
    ▼
 6. REVISIÓN ───────────────► Técnico revisa cada sección en la plataforma
    │                          Ajusta parámetros si es necesario
    │                          Estado: EN_REVISION → APROBADO
    ▼
 7. EXPORTAR ───────────────► Descarga ZIP: Word + mapas PNG + GeoPackage
    │                          Registro de auditoría automático
    │                          Estado: EXPORTADO
    │
   [FIN]
```

---

## Paso a Paso Detallado

### PASO 1 — Iniciar Sesión

**Pantalla:** Login

1. El técnico abre la plataforma en el navegador (Chrome / Firefox).
2. Ingresa su **correo electrónico** institucional (ej. `tecnico@universidad.edu.co`).
3. Ingresa su **contraseña** (asignada por el administrador).
4. Hace clic en **"Ingresar →"**.
5. El sistema valida las credenciales contra la base de datos (bcrypt + JWT).
6. Si son correctas → redirige al **Dashboard**.
7. Si son incorrectas → muestra mensaje genérico: _"Correo o contraseña incorrectos"_ (no revela si el email existe).

**Resultado:** Sesión activa por 8 horas. Token almacenado en el navegador.

> **Nota:** Si el administrador suspendió la cuenta (`estado: suspendido`), el sistema rechaza el acceso aunque la contraseña sea correcta.

---

### PASO 2 — Ver el Dashboard

**Pantalla:** Dashboard

Al ingresar, el técnico ve:

| Sección | Contenido |
|---------|-----------|
| **Tarjetas de resumen** | Total estudios · En proceso · Pendientes de revisión · Aprobados |
| **Lista de estudios activos** | Nombre comunidad · Municipio · Estado (badge de color) · Última actividad |
| **Actividad reciente** | Últimas acciones registradas en el sistema |

El técnico identifica si tiene estudios asignados o si necesita crear uno nuevo.

---

### PASO 3 — Crear un Nuevo Estudio

**Pantalla:** Lista de Estudios → Modal "Nuevo Estudio"

1. En la barra lateral, el técnico hace clic en **"Estudios"** (ícono 📂).
2. En la lista de estudios, hace clic en el botón **"+ Nuevo estudio"** (esquina superior derecha).
3. Se abre un **modal de creación** con el formulario F-01:

**Formulario — Sección 1: Identificación de la Comunidad**

| Campo | Ejemplo | Obligatorio |
|-------|---------|:-----------:|
| Nombre de la comunidad | `Cabildo Indígena Murui Muina` | ✓ |
| Pueblo indígena | `Murui Muina` | — |
| Municipio | `La Montañita` | ✓ |
| Departamento | `Caquetá` | ✓ |
| Contrato de referencia | `UC-CPS-MINTERIOR-023-2026` | — |

4. El técnico completa los campos requeridos mínimos: **nombre, municipio y departamento**.
5. Hace clic en **"Crear estudio"**.
6. El sistema crea el registro en la base de datos con estado **`borrador`**.
7. El modal se cierra y el nuevo estudio aparece en la lista con badge **BORRADOR**.

> **Regla de negocio RN-001:** El estudio permanece en borrador hasta que tenga corpus sincronizado con el proyecto QGIS de FASE 2.

---

### PASO 4 — Acceder al Detalle del Estudio

**Pantalla:** Detalle del Estudio

1. El técnico hace clic en el nombre del estudio recién creado (o en cualquier estudio asignado).
2. Se carga la **vista de detalle** con pestañas:

| Pestaña | Contenido |
|---------|-----------|
| **Corpus** | Árbol de archivos sincronizados desde Google Drive por fase |
| **Mapa** | Mapa interactivo Leaflet con la ubicación del estudio |
| **Análisis** | Resultados del motor SIG (buffers, matrices, mapas) |
| **Informe** | Estado del informe y opciones de generación/revisión |

El técnico verifica que el estudio tiene los datos correctos antes de continuar.

---

### PASO 5 — Conectar Google Drive y Sincronizar el Corpus

**Pantalla:** Detalle del Estudio → pestaña Corpus / Panel Drive

> Esta es la acción más importante: conecta el corpus documental real al estudio.

1. En la vista de detalle, el técnico localiza el panel **"Google Drive"** o botón **"Conectar Drive"**.
2. Hace clic en **"Conectar Google Drive"**.
3. El sistema genera una URL de autorización OAuth2 con el scope `drive.readonly`.
4. El navegador **redirige a Google** → el técnico ve la pantalla de autorización de Google.
5. El técnico selecciona su cuenta de Google institucional y hace clic en **"Permitir"**.
6. Google redirige de vuelta a la plataforma (`/api/drive/callback?code=...`).
7. El backend intercambia el código por tokens (access + refresh), los **cifra y almacena** (nunca en logs).

**Ahora el técnico ingresa las URLs de las carpetas del corpus:**

| Campo | URL de ejemplo |
|-------|---------------|
| URL carpeta FASE 1 | `https://drive.google.com/drive/folders/1ABC...XYZ` |
| URL carpeta FASE 2 | `https://drive.google.com/drive/folders/2DEF...UVW` |
| URL carpeta FASE 3 | `https://drive.google.com/drive/folders/3GHI...RST` |

8. El técnico pega las URLs de las carpetas y hace clic en **"Sincronizar corpus"**.
9. El sistema cambia el estado del estudio a **`sincronizando`**.

**Lo que hace el sistema automáticamente:**

```
Sistema navega FASE 1/FASE 2/FASE 3 en Drive
  ├── Clasifica cada archivo por tipo:
  │   • PDF/DOCX → documentos formales
  │   • XLSX → datos tabulares (autocenso, matrices)
  │   • .qgz / .gpkg → proyecto QGIS / GeoPackage  ← CRÍTICO
  │   • JPG/HEIC → evidencia fotográfica
  │   └── MP4/MP3 → registros audiovisuales
  │
  └── Genera reporte de corpus:
      • ✓ Verde: archivo encontrado y reconocido
      • ⚠ Amarillo: archivo presente pero formato inesperado
      • ✗ Rojo: archivo esperado no encontrado
```

10. El técnico ve el **árbol de archivos** organizado por fases con íconos de estado.
11. Revisa que todos los archivos críticos estén presentes (especialmente el `.qgz`/`.gpkg`).
12. Si hay archivos faltantes → los sube a la carpeta correcta en Drive y hace clic en **"Re-sincronizar"**.
13. Cuando el corpus está completo → el sistema cambia el estado a **`corpus_ok`**.

> **Resultado esperado:** El técnico debe ver al menos estos archivos marcados en ✓:
> - `Solicitud Formal.pdf` (FASE 1)
> - `Acta de posesión.pdf` (FASE 1)
> - `Autocenso depurado.xlsx` (FASE 1)
> - `Proyecto QGIS.qgz` o `datos.gpkg` (FASE 2)
> - `Diario de campo.docx` (FASE 2)
> - `Concepto/Informe.docx` (FASE 3)

---

### PASO 6 — Disparar el Análisis SIG

**Pantalla:** Detalle del Estudio → pestaña Análisis / Motor SIG

> Solo disponible si el estudio está en estado `corpus_ok`.

1. El técnico accede a la pestaña **"Análisis"** o hace clic en **"Generar informe"**.
2. Antes de disparar, puede ajustar el parámetro **Radio de buffer** (default: 50 metros, rango 10–500 m).
3. Selecciona qué módulos incluir:
   - ✓ Validación de discrepancias poblacionales
   - ✓ Cruce con datos DANE
   - ✓ Red de actores clave
   - ✓ Línea de tiempo de eventos
4. Hace clic en **"Iniciar procesamiento"**.
5. El estado cambia a **`procesando`**.

**Lo que ejecuta el motor SIG (automático, < 15 minutos):**

| Análisis | Descripción | Output |
|----------|-------------|--------|
| **Buffers 50m** | Área de influencia de cada punto levantado | 4 capas GeoPackage |
| **Matrices de distancia** | Distancia entre las 6 combinaciones de capas | 6 tablas CSV |
| **Superposiciones** | Porcentaje de solapamiento entre capas | 6 resultados numéricos |
| **Mapas temáticos** | Un mapa PNG por capa + mapa integrado | 5 imágenes PNG 300 DPI |

**Módulos analíticos de valor agregado:**

| Módulo | Fuente | Output |
|--------|--------|--------|
| **Discrepancias poblacionales** | Censo Ministerio · Autocenso · Derecho de petición · Registros cabildo | Tabla comparativa con alertas rojas si diferencia > 10% |
| **Cruce DANE** | API datos.gov.co (CNPV 2018) | Párrafo contextual + tabla municipio vs. departamento |
| **Red de actores** | Ficha pre-campo + actas posesión | Organigrama PNG (gobernadora → junta directiva → cargos) |
| **Línea de tiempo** | Todas las fechas extraídas del corpus | Cronología horizontal PNG (desde fundación hasta estudio actual) |

6. El técnico puede ver el progreso en tiempo real con íconos animados por módulo.
7. Al terminar → estado cambia a **`listo_revision`** y el técnico recibe notificación por email.

---

### PASO 7 — Revisar el Informe Generado

**Pantalla:** Detalle del Estudio → pestaña Informe / Revisión

1. El técnico recibe el email de notificación: _"Informe listo para revisión: Cabildo Indígena Murui Muina"_.
2. Ingresa a la plataforma y abre el estudio.
3. El estado muestra **`listo_revision`** (badge naranja).
4. Hace clic en **"Revisar informe"**.
5. El estado cambia a **`en_revision`**.

**En la pantalla de revisión, el técnico puede:**

| Función | Descripción |
|---------|-------------|
| **Table of contents** | Navegar sección por sección del Word generado |
| **Marcadores de advertencia** | Ver secciones con datos que necesitan validación (ej. discrepancias poblacionales) |
| **Preview del documento** | Vista previa del Word antes de descargar |
| **Re-generar sección** | Volver a procesar una sección específica sin regenerar todo |
| **Ajustar parámetros** | Cambiar radio de buffer y re-procesar solo el motor SIG |

6. El técnico revisa sistemáticamente cada sección:
   - **Datos básicos:** nombre oficial, NIT, municipio, departamento — confirma que se extrajeron bien del corpus.
   - **Cifras poblacionales:** valida la tabla de discrepancias. Si hay alertas rojas, decide qué fuente usar como oficial y anota en el campo "notas".
   - **Mapas temáticos:** verifica que los 4 mapas de capas SIG estén correctos (simbología, norte, escala, leyenda).
   - **Red de actores:** confirma que el organigrama muestra los cargos vigentes del cabildo.
   - **Línea de tiempo:** verifica que los hitos históricos clave estén incluidos.
   - **Concepto etnológico:** revisa el texto de conclusión (puede editarlo antes de aprobar).

7. Si necesita correcciones mayores → puede devolver a `listo_revision` y regenerar.
8. Cuando está conforme → hace clic en **"Aprobar informe"**.
9. Estado cambia a **`aprobado`**.

> **Regla de negocio RN-002:** Solo el responsable técnico asignado al estudio puede aprobarlo.  
> **Regla de negocio RN-003:** Una vez aprobado, el informe no puede modificarse. Si se requieren cambios, se crea una nueva versión.

---

### PASO 8 — Exportar el Informe Final

**Pantalla:** Detalle del Estudio → estado `aprobado`

1. El técnico hace clic en **"Exportar"**.
2. El sistema prepara un archivo **ZIP** con todos los entregables:

```
informe_murui_muina_v1.zip
├── informe_Cabildo_Indigena_Murui_Muina_v1.docx   ← Informe Word completo
├── mapas/
│   ├── mapa_practicas_culturales.png              ← 300 DPI
│   ├── mapa_expresiones_simbolicas.png
│   ├── mapa_entornos_territoriales.png
│   ├── mapa_procesos_organizativos.png
│   └── mapa_integrado.png
├── gis/
│   └── capas_procesadas.gpkg                      ← GeoPackage con buffers y análisis
└── metadatos/
    └── trazabilidad_informe_v1.json               ← Usuario, fecha, hash del archivo
```

3. El navegador descarga el ZIP (< 30 segundos).
4. El estado del estudio cambia a **`exportado`**.
5. El sistema registra en la bitácora de auditoría: usuario, fecha/hora, versión, hash SHA-256 del archivo.
6. El resguardo aparece ahora en el **mapa interactivo** de la plataforma (regla RN-007: solo estudios `aprobado`/`exportado` se muestran en el mapa público).

---

## Estados del Estudio — Ciclo Completo

```
BORRADOR ──► SINCRONIZANDO ──► CORPUS_OK ──► PROCESANDO ──► LISTO_REVISION
                                                                    │
                                                              ┌─────┘
                                                              ▼
                                                         EN_REVISION
                                                         │         │
                                                    (ajustes)    (aprueba)
                                                         │         │
                                                         └──► APROBADO ──► EXPORTADO
                                                         
Además: ERROR (en cualquier punto si el motor falla → técnico notificado por email)
```

| Estado | Color Badge | Quién lo activa |
|--------|-------------|-----------------|
| `borrador` | Gris | Sistema (al crear) |
| `sincronizando` | Azul claro | Técnico (al conectar Drive) |
| `corpus_ok` | Verde claro | Sistema (al completar sincronización) |
| `procesando` | Azul | Sistema (al disparar análisis) |
| `listo_revision` | Naranja | Sistema (al completar generación) |
| `en_revision` | Naranja oscuro | Técnico (al abrir revisión) |
| `aprobado` | Verde | Técnico (al aprobar) |
| `exportado` | Verde oscuro | Técnico (al descargar) |
| `error` | Rojo | Sistema (si falla el procesamiento) |

---

## Permisos del Rol `tecnico`

| Acción | ¿Puede? |
|--------|:-------:|
| Ver dashboard | ✓ |
| Ver todos los estudios | ✓ |
| Crear estudio | ✓ |
| Editar estudio | ✓ |
| Conectar y sincronizar Google Drive | ✓ |
| Disparar análisis SIG | ✓ |
| Revisar y aprobar informe | ✓ |
| Exportar informe | ✓ |
| Ver mapa interactivo | ✓ |
| Gestionar usuarios | — |
| Configurar el sistema | — |
| Ver bitácora de auditoría | — |

---

## Historia de Usuario Breve (formato estándar)

> **Como** técnico SIG asignado a un estudio etnológico,  
> **quiero** registrar la comunidad, conectar el corpus en Drive, obtener el análisis automático y descargar el informe Word institucional,  
> **para** entregarle al Ministerio del Interior el concepto técnico que sustenta el reconocimiento del cabildo, en horas en lugar de semanas.

### Criterios de Aceptación

- [ ] El técnico puede crear un estudio con nombre, municipio y departamento sin necesidad de un administrador.
- [ ] El flujo OAuth2 con Google Drive funciona sin que el técnico necesite conocimientos de programación.
- [ ] El sistema muestra con claridad qué archivos del corpus están presentes y cuáles faltan.
- [ ] El motor SIG genera los 4 mapas temáticos y las 6 matrices de distancia sin intervención manual.
- [ ] El Word generado tiene la misma estructura que el informe de referencia (Murui Muina).
- [ ] El técnico puede aprobar y descargar el informe en ≤ 3 clics desde el estado `listo_revision`.
- [ ] Todo el flujo completo (desde corpus sincronizado hasta informe exportado) toma < 15 minutos de procesamiento automático.

---

## Flujo de Notificaciones por Email

| Evento | Destinatario | Asunto |
|--------|-------------|--------|
| Sincronización Drive completada | Técnico asignado | ✓ Corpus listo: [nombre comunidad] |
| Informe listo para revisión | Técnico + Supervisor | ✓ Informe listo para revisión |
| Error en procesamiento | Técnico asignado | ✗ Error en procesamiento: [nombre comunidad] |
| Informe aprobado | Técnico + Admin | ✓ Informe aprobado: [nombre comunidad] |

---

*Documento: `09_HISTORIA_USUARIO_TECNICO.md` — EtnIA v1.0 — Simonky S.A.S. — Mayo 2026*
