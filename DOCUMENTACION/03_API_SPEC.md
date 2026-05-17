# EtnoSIG — Especificación de API REST
## Versión 1.0 — FastAPI / OpenAPI

**Base URL:** `https://etnosig.simonky.com/api`  
**Autenticación:** Bearer JWT en header `Authorization: Bearer <token>`  
**Content-Type:** `application/json` (salvo uploads: `multipart/form-data`)

---

## MÓDULO: AUTENTICACIÓN `/api/auth`

### POST `/api/auth/login`
Autentica un usuario y emite tokens JWT.

**Request:**
```json
{
  "email": "tecnico@unicartagena.edu.co",
  "password": "MiContraseña123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 28800,
  "user": {
    "id": "uuid",
    "nombre_completo": "David Verdooren Flórez",
    "email": "tecnico@unicartagena.edu.co",
    "rol": "tecnico"
  }
}
```

**Response 401:** `{"detail": "Credenciales incorrectas"}`

---

### POST `/api/auth/refresh`
Renueva el access token usando el refresh token.

**Request:**
```json
{ "refresh_token": "eyJhbGc..." }
```

**Response 200:** Mismo esquema que `/login`

---

### POST `/api/auth/logout`
Invalida la sesión actual.

**Response 204:** Sin cuerpo

---

### GET `/api/auth/me`
Retorna el perfil del usuario autenticado.

**Response 200:**
```json
{
  "id": "uuid",
  "nombre_completo": "David Verdooren Flórez",
  "email": "tecnico@unicartagena.edu.co",
  "rol": "tecnico",
  "estado": "activo",
  "ultimo_acceso": "2026-05-16T10:30:00Z"
}
```

---

### PUT `/api/auth/change-password`
Cambia la contraseña del usuario autenticado.

**Request:**
```json
{
  "password_actual": "MiContraseña123",
  "password_nueva": "NuevaContraseña456",
  "password_nueva_confirmacion": "NuevaContraseña456"
}
```

**Response 204:** Sin cuerpo

---

## MÓDULO: USUARIOS `/api/users`
*Solo accesible con rol `admin`*

### GET `/api/users`
Lista todos los usuarios.

**Query params:** `?estado=activo&rol=tecnico&page=1&limit=20`

**Response 200:**
```json
{
  "total": 8,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "uuid",
      "nombre_completo": "Wisbell Yaleny Morales Gutierrez",
      "email": "sig@unicartagena.edu.co",
      "rol": "tecnico",
      "estado": "activo",
      "estudios_asignados": 3,
      "ultimo_acceso": "2026-05-15T14:00:00Z"
    }
  ]
}
```

---

### POST `/api/users`
Crea un nuevo usuario.

**Request:**
```json
{
  "nombre_completo": "Angie Xiomara Contreras Gutiérrez",
  "email": "campo@unicartagena.edu.co",
  "password": "TempPass123",
  "rol": "campo"
}
```

**Response 201:**
```json
{ "id": "uuid", "email": "campo@unicartagena.edu.co", "rol": "campo" }
```

---

### GET `/api/users/{user_id}`
Detalle de un usuario.

**Response 200:** Objeto usuario completo

---

### PUT `/api/users/{user_id}`
Edita un usuario.

**Request:** Campos opcionales: `nombre_completo`, `rol`, `estado`

**Response 200:** Usuario actualizado

---

### DELETE `/api/users/{user_id}`
Suspende (no elimina) un usuario. Elimina físicamente solo si no tiene estudios asociados.

**Response 204:** Sin cuerpo

---

### POST `/api/users/{user_id}/reset-password`
Genera una nueva contraseña temporal y la envía por email.

**Response 200:** `{"message": "Contraseña temporal enviada por email"}`

---

## MÓDULO: ESTUDIOS `/api/studies`

### GET `/api/studies`
Lista estudios según el rol del usuario autenticado.

**Query params:** `?estado=procesando&municipio=La+Montañita&q=Murui&page=1&limit=10`

**Response 200:**
```json
{
  "total": 12,
  "items": [
    {
      "id": "uuid",
      "nombre_comunidad": "Cabildo Indígena Murui Muina",
      "pueblo_indigena": "Huitoto",
      "municipio": "La Montañita",
      "departamento": "Caquetá",
      "estado": "listo_revision",
      "progreso_porcentaje": 85,
      "responsable": { "id": "uuid", "nombre": "David Verdooren Flórez" },
      "contrato_referencia": "UC-CPS-MINTERIOR-023-2026",
      "ultima_actividad": "2026-05-14T09:00:00Z",
      "created_at": "2026-04-01T00:00:00Z"
    }
  ]
}
```

---

### POST `/api/studies`
Crea un nuevo estudio etnológico.

**Request:**
```json
{
  "nombre_comunidad": "Cabildo Indígena Murui Muina",
  "pueblo_indigena": "Huitoto (Murui Muina)",
  "municipio": "La Montañita",
  "departamento": "Caquetá",
  "nit_comunidad": "901010837-9",
  "contrato_referencia": "UC-CPS-MINTERIOR-023-2026",
  "url_drive_fase1": "https://drive.google.com/drive/folders/...",
  "url_drive_fase2": "https://drive.google.com/drive/folders/...",
  "url_drive_fase3": "https://drive.google.com/drive/folders/...",
  "lat": 1.3744,
  "lng": -75.4000,
  "buffer_metros": 50,
  "responsable_id": "uuid-del-tecnico",
  "equipo_ids": ["uuid1", "uuid2"],
  "gobernador_nombre": "Luz Celida Perdomo Pakki",
  "notas_adicionales": "ETCR Agua Bonita — Vereda Semillas de Paz"
}
```

**Response 201:**
```json
{ "id": "uuid", "estado": "borrador", "nombre_comunidad": "Cabildo Indígena Murui Muina" }
```

---

### GET `/api/studies/{study_id}`
Detalle completo de un estudio.

**Response 200:**
```json
{
  "id": "uuid",
  "nombre_comunidad": "Cabildo Indígena Murui Muina",
  "pueblo_indigena": "Huitoto (Murui Muina)",
  "municipio": "La Montañita",
  "departamento": "Caquetá",
  "estado": "listo_revision",
  "corpus_resumen": {
    "total_archivos": 45,
    "archivos_ok": 42,
    "archivos_faltantes": 3,
    "fases": {
      "FASE1": { "archivos": 20, "ok": 20 },
      "FASE2": { "archivos": 22, "ok": 19 },
      "FASE3": { "archivos": 3, "ok": 3 }
    }
  },
  "gis_disponible": true,
  "ultimo_informe": {
    "id": "uuid",
    "version": 2,
    "estado": "listo_revision",
    "generado_en": "2026-05-14T08:45:00Z"
  },
  "responsable": { "id": "uuid", "nombre": "David Verdooren Flórez" },
  "equipo": [{ "id": "uuid", "nombre": "Angie Contreras", "rol_en_estudio": "campo" }],
  "extracciones_principales": {
    "familias_censo": 14,
    "personas_censo": 31,
    "familias_autocenso_2023": 37,
    "personas_autocenso_2023": 102,
    "gobernador": "Luz Celida Perdomo Pakki",
    "cacique": "Wualdo Orozco Ortiz",
    "fecha_fundacion": "2016-09-21"
  }
}
```

---

### PUT `/api/studies/{study_id}`
Edita un estudio (solo campos del formulario, no procesamiento).

**Request:** Campos opcionales del formulario de creación

**Response 200:** Estudio actualizado

---

### DELETE `/api/studies/{study_id}`
Elimina un estudio en estado `borrador`. Estudios en otros estados no se eliminan.

**Response 204:** Sin cuerpo  
**Response 409:** `{"detail": "No se puede eliminar un estudio en estado 'procesando'"}`

---

### GET `/api/studies/{study_id}/corpus`
Lista todos los archivos del corpus catalogados.

**Query params:** `?fase=FASE2&tipo=qgz&estado=procesado`

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "fase": "FASE2",
      "nombre_archivo": "ETNIA1_CABILDO_MURUI_MUINA_GRUPO3.qgz",
      "tipo_archivo": "qgz",
      "rol_en_corpus": "proyecto_qgis",
      "tamanio_bytes": 15728640,
      "estado": "procesado",
      "drive_file_id": "1xAbc..."
    }
  ]
}
```

---

### GET `/api/studies/{study_id}/extractions`
Lista todas las extracciones de datos del corpus.

**Response 200:**
```json
{
  "items": [
    {
      "tipo_dato": "familias_autocenso_2026",
      "valor": "14",
      "fuente_archivo": "8. Autoncenso depurado.xlsx",
      "confianza": 0.97
    }
  ]
}
```

---

## MÓDULO: GOOGLE DRIVE `/api/drive`

### GET `/api/drive/auth-url`
Genera la URL de autorización OAuth2 de Google.

**Response 200:**
```json
{ "auth_url": "https://accounts.google.com/o/oauth2/auth?..." }
```

---

### GET `/api/drive/callback`
Callback de Google OAuth2. Almacena el token cifrado.

**Query params:** `?code=...&state=...`

**Response 302:** Redirige al frontend con `?drive_connected=true`

---

### POST `/api/drive/sync/{study_id}`
Dispara la sincronización del corpus desde Google Drive.

**Response 202:**
```json
{
  "task_id": "task-uuid",
  "message": "Sincronización iniciada",
  "estimated_minutes": 3
}
```

---

### GET `/api/drive/sync/{study_id}/status`
Estado de la sincronización en curso.

**Response 200:**
```json
{
  "estado": "en_proceso",
  "archivos_procesados": 23,
  "total_archivos": 45,
  "porcentaje": 51,
  "errores": [],
  "iniciado_en": "2026-05-16T10:00:00Z"
}
```

---

### GET `/api/drive/validate/{study_id}`
Valida la estructura del corpus y reporta archivos esperados vs. encontrados.

**Response 200:**
```json
{
  "estado_general": "advertencia",
  "fases": {
    "FASE1": {
      "archivos_esperados": ["Solicitud Formal.pdf", "Reglamento interno.pdf", ...],
      "encontrados": ["Solicitud Formal.pdf", "Reglamento interno.pdf"],
      "faltantes": ["Acta de posesión.pdf"],
      "estado": "advertencia"
    },
    "FASE2": {
      "archivos_esperados": [...],
      "encontrados": [...],
      "faltantes": [],
      "estado": "ok"
    }
  }
}
```

---

## MÓDULO: MOTOR SIG `/api/gis`

### POST `/api/gis/process/{study_id}`
Dispara el procesamiento geoespacial completo.

**Request (opcional):**
```json
{
  "buffer_metros": 50,
  "capas": ["PUNT_PracticasCulturales", "PUNT_ExpresionesSimbólicas", "PUNT_EntornosTerritoriales", "PUNT_ProcesosOrganizativos"],
  "generar_mapas": true,
  "simbologia_config": null
}
```

**Response 202:**
```json
{ "task_id": "task-uuid", "message": "Procesamiento SIG iniciado" }
```

---

### GET `/api/gis/status/{study_id}`
Estado del procesamiento SIG.

**Response 200:**
```json
{
  "estado": "completado",
  "pasos_completados": ["buffers", "matrices", "superposiciones", "mapas"],
  "errores": [],
  "iniciado_en": "2026-05-16T10:05:00Z",
  "completado_en": "2026-05-16T10:08:30Z",
  "duracion_segundos": 210
}
```

---

### GET `/api/gis/results/{study_id}`
Resultados del análisis geoespacial.

**Response 200:**
```json
{
  "buffers": {
    "PUNT_PracticasCulturales": { "area_m2": 12450.3, "puntos_incluidos": 8 },
    "PUNT_ExpresionesSimbólicas": { "area_m2": 7820.1, "puntos_incluidos": 5 },
    "PUNT_EntornosTerritoriales": { "area_m2": 18900.7, "puntos_incluidos": 11 },
    "PUNT_ProcesosOrganizativos": { "area_m2": 3200.4, "puntos_incluidos": 3 }
  },
  "matrices_distancia": {
    "PC_ES": [{ "origen": "Rituales", "destino": "Asambleas_Gobierno", "distancia_m": 4.82 }],
    "PC_ET": [...],
    "PC_PO": [...],
    "ES_ET": [...],
    "ES_PO": [...],
    "ET_PO": [...]
  },
  "superposiciones": {
    "PC_ES": { "interseccion_m2": 2100.5, "interpretacion": "Paisajes culturales" },
    "PC_ET": {...},
    "PC_PO": {...},
    "ES_ET": {...},
    "ES_PO": {...},
    "ET_PO": {...}
  },
  "mapas": {
    "PUNT_PracticasCulturales": "/api/gis/maps/study-uuid/mapa_PC.png",
    "PUNT_ExpresionesSimbólicas": "/api/gis/maps/study-uuid/mapa_ES.png",
    "PUNT_EntornosTerritoriales": "/api/gis/maps/study-uuid/mapa_ET.png",
    "PUNT_ProcesosOrganizativos": "/api/gis/maps/study-uuid/mapa_PO.png",
    "integrado": "/api/gis/maps/study-uuid/mapa_integrado.png"
  }
}
```

---

### GET `/api/gis/maps/{study_id}/{filename}`
Sirve un mapa PNG generado.

**Response 200:** `Content-Type: image/png`

---

## MÓDULO: PROCESAMIENTO DOCUMENTAL `/api/documents`

### POST `/api/documents/process/{study_id}`
Dispara extracción de datos de todos los documentos del corpus.

**Response 202:** `{ "task_id": "..." }`

---

### GET `/api/documents/status/{study_id}`
Estado del procesamiento documental.

**Response 200:**
```json
{
  "estado": "completado",
  "documentos_procesados": 18,
  "documentos_totales": 20,
  "entidades_extraidas": 142
}
```

---

### GET `/api/documents/population/{study_id}`
Análisis de discrepancias poblacionales (RF-009).

**Response 200:**
```json
{
  "fuentes": [
    { "nombre": "Censo Ministerio Interior", "archivo": "Censo.pdf", "familias": 14, "personas": 31 },
    { "nombre": "Derecho de Petición", "archivo": "Solicitud Formal.pdf", "familias": 37, "personas": 102 },
    { "nombre": "Autocenso 2026 (depurado)", "archivo": "Autoncenso depurado.xlsx", "familias": 14, "personas": 31 },
    { "nombre": "Autocenso 2023", "archivo": "Autocenso_Murui Muina.xlsx", "familias": 37, "personas": 102 }
  ],
  "discrepancias": [
    {
      "campo": "personas",
      "diferencia_porcentual": 229.0,
      "min": 31,
      "max": 102,
      "nivel": "critica",
      "explicacion_sugerida": "El autocenso 2026 es una versión depurada del padrón 2023. La diferencia refleja familias dispersas fuera del territorio."
    }
  ],
  "recomendacion_informe": "Se recomienda usar 31 personas / 14 familias como cifra activa en territorio y 102 personas / 37 familias como cifra nominal total."
}
```

---

### GET `/api/documents/dane/{study_id}`
Datos DANE del municipio del estudio (RF-010).

**Response 200:**
```json
{
  "municipio": "La Montañita",
  "departamento": "Caquetá",
  "fuente": "CNPV 2018 — DANE",
  "datos": {
    "poblacion_total": 14714,
    "poblacion_indigena_total": 176,
    "porcentaje_indigena": 1.2,
    "hogares_total": 3891
  },
  "comparativa": {
    "cabildo_personas_activas": 31,
    "cabildo_porcentaje_del_municipio": 0.21
  },
  "cached_at": "2026-05-01T00:00:00Z"
}
```

---

### GET `/api/documents/actors/{study_id}`
Red de actores clave (RF-011).

**Response 200:**
```json
{
  "actores": [
    { "nombre": "Luz Celida Perdomo Pakki", "cargo": "Gobernadora", "cedula": "26636970", "nivel": "directivo" },
    { "nombre": "Wualdo Orozco Ortiz", "cargo": "Cacique", "pueblo": "Coreguaje", "nivel": "directivo" },
    { "nombre": "Ingri Natalia Perdomo Pakky", "cargo": "Secretaria", "cedula": "1117542436", "nivel": "directivo" }
  ],
  "imagen_organigrama": "/api/documents/actors/study-uuid/organigrama.png",
  "estructura": {
    "asamblea_general": {
      "hijos": ["junta_directiva"]
    },
    "junta_directiva": {
      "miembros": ["Gobernadora", "Cacique", "Vicegobernador", "Secretaria", "Tesorera"]
    }
  }
}
```

---

### GET `/api/documents/timeline/{study_id}`
Línea de tiempo de eventos (RF-012).

**Response 200:**
```json
{
  "eventos": [
    { "fecha": "1909", "tipo": "despojo", "descripcion": "Llegada cauchero Apolinar Cuéllar — inicio colonización" },
    { "fecha": "2016-09-21", "tipo": "fundacion", "descripcion": "Constitución jurídica del Cabildo" },
    { "fecha": "2024-08-09", "tipo": "institucional", "descripcion": "Afiliación a ACOTRI" },
    { "fecha": "2025-07-02", "tipo": "tramite", "descripcion": "Derecho de petición radicado ante DAIRM" },
    { "fecha": "2026-03-15", "tipo": "campo", "descripcion": "Inicio visita de campo — Universidad de Cartagena" }
  ],
  "imagen_timeline": "/api/documents/timeline/study-uuid/timeline.png"
}
```

---

## MÓDULO: INFORMES `/api/reports`

### POST `/api/reports/generate/{study_id}`
Dispara la generación completa del informe Word.

**Request (opcional):**
```json
{
  "incluir_modulos": ["poblacion", "dane", "actores", "timeline"],
  "notas_adicionales": "Incluir mención especial a la situación de seguridad"
}
```

**Response 202:**
```json
{
  "task_id": "task-uuid",
  "report_id": "report-uuid",
  "version": 3,
  "message": "Generación iniciada. Tiempo estimado: 8 minutos."
}
```

---

### GET `/api/reports/status/{report_id}`
Estado de la generación del informe.

**Response 200:**
```json
{
  "report_id": "uuid",
  "estado": "generando",
  "pasos": {
    "sincronizacion": "completado",
    "gis": "completado",
    "documentos": "completado",
    "analytics": "en_proceso",
    "ensamblado": "pendiente"
  },
  "porcentaje": 65,
  "iniciado_en": "2026-05-16T10:00:00Z"
}
```

---

### GET `/api/reports/{report_id}`
Detalle del informe y su estructura.

**Response 200:**
```json
{
  "id": "uuid",
  "study_id": "uuid",
  "version": 2,
  "estado": "listo_revision",
  "estructura_toc": [
    { "seccion": 1, "titulo": "Portada institucional", "estado": "ok" },
    { "seccion": 2, "titulo": "Vista general de la comunidad", "estado": "ok" },
    { "seccion": "2.1", "titulo": "Discrepancias poblacionales", "estado": "advertencia", "msg": "3 fuentes con diferencias > 10%" },
    { "seccion": 3, "titulo": "Contexto territorial y demográfico", "estado": "ok" }
  ],
  "advertencias": 2,
  "generado_en": "2026-05-14T08:45:00Z"
}
```

---

### GET `/api/reports/{report_id}/preview`
Retorna el contenido HTML del informe para previsualización web.

**Response 200:** `Content-Type: text/html`

---

### POST `/api/reports/{report_id}/approve`
Aprueba el informe (requiere rol `tecnico`, `admin` o `supervisor`).

**Response 200:**
```json
{ "estado": "aprobado", "aprobado_por": "David Verdooren Flórez", "aprobado_en": "2026-05-15T11:00:00Z" }
```

---

### GET `/api/reports/{report_id}/download`
Descarga el Word (.docx) aprobado.

**Response 200:**  
`Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`  
`Content-Disposition: attachment; filename="informe_Murui_Muina_v2.docx"`

---

### GET `/api/reports/{report_id}/download-zip`
Descarga ZIP con Word + mapas PNG + GeoPackages.

**Response 200:** `Content-Type: application/zip`

---

### GET `/api/reports/history/{study_id}`
Historial de versiones del informe de un estudio.

**Response 200:**
```json
{
  "items": [
    { "id": "uuid", "version": 2, "estado": "aprobado", "generado_en": "...", "aprobado_en": "..." },
    { "id": "uuid", "version": 1, "estado": "exportado", "generado_en": "..." }
  ]
}
```

---

## MÓDULO: MAPA GEORREFERENCIADO `/api/map`

### GET `/api/map/resguardos`
Lista de resguardos/cabildos georreferenciados para el mapa interactivo.

**Query params:** `?estado=aprobado&departamento=Caquetá`

**Response 200 (GeoJSON):**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [-75.4000, 1.3744] },
      "properties": {
        "study_id": "uuid",
        "nombre_comunidad": "Cabildo Indígena Murui Muina",
        "pueblo_indigena": "Huitoto (Murui Muina)",
        "municipio": "La Montañita",
        "departamento": "Caquetá",
        "estado": "aprobado",
        "personas": 31,
        "familias": 14,
        "fecha_reconocimiento": "2026-05-15",
        "gobernador": "Luz Celida Perdomo Pakki"
      }
    }
  ]
}
```

---

### GET `/api/map/resguardos/{study_id}/layers`
Capas GeoJSON del estudio para el mapa interactivo.

**Response 200:** GeoJSON con todas las capas del estudio

---

## MÓDULO: AUDITORÍA `/api/audit`
*Solo accesible con rol `admin`*

### GET `/api/audit/log`
Bitácora de auditoría.

**Query params:** `?study_id=uuid&user_id=uuid&accion=generar_informe&from=2026-05-01&to=2026-05-16&page=1`

**Response 200:**
```json
{
  "total": 156,
  "items": [
    {
      "id": "uuid",
      "user": { "id": "uuid", "nombre": "David Verdooren" },
      "study": { "id": "uuid", "nombre": "Murui Muina" },
      "accion": "generar_informe",
      "detalle": { "version": 2, "parametros": { "buffer_metros": 50 } },
      "ip_address": "192.168.1.10",
      "created_at": "2026-05-14T08:40:00Z"
    }
  ]
}
```

---

## MÓDULO: NOTIFICACIONES `/api/notifications`

### GET `/api/notifications`
Lista notificaciones del usuario autenticado.

**Query params:** `?leida=false&limit=20`

**Response 200:**
```json
{
  "no_leidas": 3,
  "items": [
    {
      "id": "uuid",
      "tipo": "informe_listo",
      "titulo": "Informe listo para revisión",
      "mensaje": "El informe del Cabildo Murui Muina (v2) está listo para su revisión.",
      "study_id": "uuid",
      "leida": false,
      "created_at": "2026-05-14T08:46:00Z"
    }
  ]
}
```

---

### PUT `/api/notifications/{notification_id}/read`
Marca una notificación como leída.

**Response 204:** Sin cuerpo

---

## CÓDIGOS DE ERROR ESTÁNDAR

| Código | Significado |
|---|---|
| 400 | Bad Request — datos de entrada inválidos |
| 401 | Unauthorized — token ausente o expirado |
| 403 | Forbidden — sin permisos para esta operación |
| 404 | Not Found — recurso no existe |
| 409 | Conflict — operación no permitida en el estado actual |
| 422 | Unprocessable Entity — validación fallida (FastAPI) |
| 429 | Too Many Requests — rate limit superado |
| 500 | Internal Server Error — error del servidor |
| 503 | Service Unavailable — servicio temporalmente no disponible |

**Formato de error:**
```json
{
  "detail": "Mensaje de error en español",
  "code": "STUDY_NOT_IN_VALID_STATE",
  "context": { "estado_actual": "borrador", "estado_requerido": "corpus_ok" }
}
```

---

## WEBSOCKET — ACTUALIZACIONES EN TIEMPO REAL

### WS `/ws/tasks/{task_id}`
Canal WebSocket para recibir actualizaciones de progreso de tareas largas.

**Mensajes del servidor:**
```json
{ "tipo": "progreso", "porcentaje": 45, "paso_actual": "gis_buffers", "mensaje": "Generando buffers de influencia..." }
{ "tipo": "completado", "resultado": { "report_id": "uuid", "estado": "listo_revision" } }
{ "tipo": "error", "mensaje": "No se encontró proyecto QGIS en la FASE2" }
```
