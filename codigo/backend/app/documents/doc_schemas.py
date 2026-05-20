"""
Esquemas JSON estructurados por tipo de archivo (Sprint Drive B).

Cada esquema declara:
  - version: identificador de versión (ej. "v1"). Cambiar de versión INVALIDA
    los datos extraídos con versiones anteriores y obliga a reprocesar.
  - template: estructura ejemplar con todos los campos posibles para ese tipo.
    Los valores son None / [] / {} (sentinelas) que el extractor del Sprint C
    irá llenando.
  - dedup_keys: para campos que son listas, indica qué claves definen la
    identidad de un ítem (para deduplicar al consolidar varios archivos).
  - flatten: reglas que aplanan los campos primitivos del JSON a filas en la
    tabla derivada corpus_extractions (tipo_dato, valor).

Fuente de verdad de qué campos pide cada tipo:
  DOCUMENTACION/CATALOGO_TIPOS_ARCHIVO.md
"""
from __future__ import annotations

from typing import Any


# ── Esquema ficha_precampo ────────────────────────────────────────────────────

_FICHA_PRECAMPO = {
    "version": "ficha_precampo:v1",
    "template": {
        "comunidad_nombre_oficial": None,
        "comunidad_autodenominacion": None,
        "ubicacion": {"municipio": None, "vereda": None, "departamento": None},
        "coordenadas": {"lat": None, "lng": None, "plus_code": None},
        "vias_acceso": None,
        "distancia_cabecera_km": None,
        "autoridades_clave": [],          # [{nombre, cargo, contacto}]
        "instituciones_presentes": [],    # [str]
        "evolucion_demografica": [],      # [{anio, familias, personas}]
        "riesgos_identificados": [],      # [str]
        "extra": {},
    },
    "dedup_keys": {
        "autoridades_clave": ["nombre", "cargo"],
        "evolucion_demografica": ["anio"],
    },
    "flatten": [
        {"path": "comunidad_nombre_oficial", "tipo_dato": "nombre_comunidad"},
        {"path": "comunidad_autodenominacion", "tipo_dato": "autodenominacion"},
        {"path": "ubicacion.municipio", "tipo_dato": "municipio"},
        {"path": "ubicacion.vereda", "tipo_dato": "vereda"},
        {"path": "ubicacion.departamento", "tipo_dato": "departamento"},
        {"path": "coordenadas.lat", "tipo_dato": "coord_lat"},
        {"path": "coordenadas.lng", "tipo_dato": "coord_lng"},
        {"path": "coordenadas.plus_code", "tipo_dato": "plus_code"},
        {"path": "distancia_cabecera_km", "tipo_dato": "distancia_cabecera_km"},
        {"path": "vias_acceso", "tipo_dato": "vias_acceso"},
    ],
}


# ── Esquema reglamento ────────────────────────────────────────────────────────

_REGLAMENTO = {
    "version": "reglamento:v1",
    "template": {
        "fecha_aprobacion": None,
        "cabildo_o_comunidad": None,
        "principios_fundacionales": [],   # [str]
        "estructura_cargos": [],          # [{cargo, funciones, periodo_anios}]
        "tipos_afiliacion": [],           # [str]
        "cuotas_y_multas": [],            # [{concepto, monto_cop, periodicidad}]
        "instancias_decision": [],        # [{nombre, frecuencia, descripcion}]
        "causales_sancion": [],           # [str]
        "extra": {},
    },
    "dedup_keys": {
        "estructura_cargos": ["cargo"],
        "cuotas_y_multas": ["concepto"],
        "instancias_decision": ["nombre"],
    },
    "flatten": [
        {"path": "fecha_aprobacion", "tipo_dato": "fecha_reglamento"},
        {"path": "cabildo_o_comunidad", "tipo_dato": "nombre_comunidad"},
    ],
}


# ── Esquema acta_eleccion ─────────────────────────────────────────────────────

_ACTA_ELECCION = {
    "version": "acta_eleccion:v1",
    "template": {
        "fecha": None,
        "lugar": None,
        "convocada_por": None,
        "total_asistentes": None,
        "cargos_elegidos": [],   # [{cargo, nombre, cedula, votos}]
        "avalado_por": None,
        "observaciones": None,
        "extra": {},
    },
    "dedup_keys": {
        "cargos_elegidos": ["cargo", "cedula"],
    },
    "flatten": [
        {"path": "fecha", "tipo_dato": "fecha_eleccion"},
        {"path": "lugar", "tipo_dato": "lugar_eleccion"},
        {"path": "total_asistentes", "tipo_dato": "asistentes_eleccion"},
        {"path": "avalado_por", "tipo_dato": "aval_eleccion"},
    ],
}


# ── Esquema acta_posesion ─────────────────────────────────────────────────────

_ACTA_POSESION = {
    "version": "acta_posesion:v1",
    "template": {
        "fecha": None,
        "lugar": None,
        "alcalde_u_oficial": None,
        "cargos_posesionados": [],   # [{cargo, nombre, cedula}]
        "vigencia_anios": None,
        "numero_acto_administrativo": None,
        "extra": {},
    },
    "dedup_keys": {
        "cargos_posesionados": ["cargo", "cedula"],
    },
    "flatten": [
        {"path": "fecha", "tipo_dato": "fecha_posesion"},
        {"path": "alcalde_u_oficial", "tipo_dato": "autoridad_posesion"},
        {"path": "vigencia_anios", "tipo_dato": "vigencia_periodo_anios"},
        {"path": "numero_acto_administrativo", "tipo_dato": "num_acto_administrativo"},
    ],
}


# ── Esquemas autocenso / autocenso_depurado ───────────────────────────────────

_AUTOCENSO_BASE = {
    "version": "autocenso:v1",
    "template": {
        "fecha_registro": None,
        "total_personas": None,
        "total_familias": None,
        "coordinador_registro": None,
        "distribucion_por_edad": [],     # [{rango, cantidad}]
        "distribucion_por_sexo": {"femenino": None, "masculino": None, "otro": None},
        "jefes_de_hogar": [],            # [{nombre, edad, rol_comunidad, cedula}]
        "discrepancia_con_censo_general": None,
        "extra": {},
    },
    "dedup_keys": {
        "distribucion_por_edad": ["rango"],
        "jefes_de_hogar": ["cedula"],
    },
    "flatten": [
        {"path": "fecha_registro", "tipo_dato": "fecha_censo"},
        {"path": "total_personas", "tipo_dato": "personas_count"},
        {"path": "total_familias", "tipo_dato": "familias_count"},
        {"path": "coordinador_registro", "tipo_dato": "fuente_censo"},
        {"path": "discrepancia_con_censo_general", "tipo_dato": "discrepancia_poblacion"},
        {"path": "distribucion_por_sexo.femenino", "tipo_dato": "personas_femenino"},
        {"path": "distribucion_por_sexo.masculino", "tipo_dato": "personas_masculino"},
    ],
}


# ── Esquema resena_historica ──────────────────────────────────────────────────

_RESENA_HISTORICA = {
    "version": "resena_historica:v1",
    "template": {
        "lugar_origen_ancestral": None,
        "narrativa_origen": None,
        "cosmogonia": None,
        "clanes": [],                 # [{nombre, traduccion, descripcion}]
        "eventos_historicos": [],     # [{anio, evento, descripcion}]
        "actores_externos_historicos": [],   # [str] colonos, terratenientes, etc.
        "elementos_sagrados": [],     # [{elemento, estado_actual, descripcion}]
        "proceso_recuperacion": None,
        "extra": {},
    },
    "dedup_keys": {
        "clanes": ["nombre"],
        "eventos_historicos": ["anio", "evento"],
        "elementos_sagrados": ["elemento"],
    },
    "flatten": [
        {"path": "lugar_origen_ancestral", "tipo_dato": "lugar_origen"},
        {"path": "narrativa_origen", "tipo_dato": "narrativa_origen"},
        {"path": "cosmogonia", "tipo_dato": "cosmogonia"},
        {"path": "proceso_recuperacion", "tipo_dato": "proceso_recuperacion"},
    ],
}


# ── Esquema ficha_comision ────────────────────────────────────────────────────

_FICHA_COMISION = {
    "version": "ficha_comision:v1",
    "template": {
        "fechas_visita": [],           # [str] "YYYY-MM-DD"
        "comunidad_visitada": None,
        "comisionados": [],            # [{nombre, rol}]
        "hallazgos_intrarelacional": [],   # [str]
        "hallazgos_interrelacional": [],   # [str]
        "hallazgos_espiritual": [],        # [str]
        "hallazgos_territorial": [],       # [str]
        "hallazgos_organizativo": [],      # [str]
        "conclusiones_visita": None,
        "extra": {},
    },
    "dedup_keys": {
        "comisionados": ["nombre"],
    },
    "flatten": [
        {"path": "comunidad_visitada", "tipo_dato": "nombre_comunidad"},
        {"path": "conclusiones_visita", "tipo_dato": "conclusion_comision"},
    ],
}


# ── Esquema diario_campo ──────────────────────────────────────────────────────

_DIARIO_CAMPO = {
    "version": "diario_campo:v1",
    "template": {
        "autor": None,
        "fechas_cubiertas": {"inicio": None, "fin": None},
        "entradas": [],   # [{fecha, lugar, narrativa, observaciones_culturales, personas_encontradas}]
        "extra": {},
    },
    "dedup_keys": {
        "entradas": ["fecha", "lugar"],
    },
    "flatten": [
        {"path": "autor", "tipo_dato": "autor_diario"},
        {"path": "fechas_cubiertas.inicio", "tipo_dato": "diario_fecha_inicio"},
        {"path": "fechas_cubiertas.fin", "tipo_dato": "diario_fecha_fin"},
    ],
}


# ── Esquema acta_inicio ───────────────────────────────────────────────────────

_ACTA_INICIO = {
    "version": "acta_inicio:v1",
    "template": {
        "fecha_inicio": None,
        "comunidad": None,
        "equipo_responsable": [],   # [{nombre, rol, institucion}]
        "alcance_estudio": None,
        "compromisos_asumidos": [],   # [{parte, compromiso}]
        "duracion_estimada": None,
        "extra": {},
    },
    "dedup_keys": {
        "equipo_responsable": ["nombre"],
        "compromisos_asumidos": ["parte", "compromiso"],
    },
    "flatten": [
        {"path": "fecha_inicio", "tipo_dato": "fecha_inicio_estudio"},
        {"path": "comunidad", "tipo_dato": "nombre_comunidad"},
        {"path": "alcance_estudio", "tipo_dato": "alcance_estudio"},
        {"path": "duracion_estimada", "tipo_dato": "duracion_estimada"},
    ],
}


# ── Esquema arbol_riesgo ──────────────────────────────────────────────────────

_ARBOL_RIESGO = {
    "version": "arbol_riesgo:v1",
    "template": {
        "amenazas_externas": [],   # [{descripcion, gravedad, actor}]
        "amenazas_internas": [],   # [{descripcion, gravedad}]
        "causas_raiz": [],         # [str]
        "efectos": [],             # [str]
        "mitigaciones_propuestas": [],   # [{accion, responsable, plazo}]
        "extra": {},
    },
    "dedup_keys": {
        "amenazas_externas": ["descripcion"],
        "amenazas_internas": ["descripcion"],
        "mitigaciones_propuestas": ["accion"],
    },
    "flatten": [],
}


# ── Esquema registro_asistencia ───────────────────────────────────────────────

_REGISTRO_ASISTENCIA = {
    "version": "registro_asistencia:v1",
    "template": {
        "fecha_evento": None,
        "lugar_evento": None,
        "tipo_evento": None,
        "asistentes": [],   # [{nombre, cedula, cargo, firma}]
        "total_asistentes": None,
        "extra": {},
    },
    "dedup_keys": {
        "asistentes": ["cedula"],
    },
    "flatten": [
        {"path": "fecha_evento", "tipo_dato": "fecha_evento"},
        {"path": "lugar_evento", "tipo_dato": "lugar_evento"},
        {"path": "tipo_evento", "tipo_dato": "tipo_evento"},
        {"path": "total_asistentes", "tipo_dato": "total_asistentes"},
    ],
}


# ── Esquema apuntes_reuniones ─────────────────────────────────────────────────

_APUNTES_REUNIONES = {
    "version": "apuntes_reuniones:v1",
    "template": {
        "fecha": None,
        "asistentes": [],   # [{nombre, cargo}]
        "temas_tratados": [],   # [str]
        "acuerdos": [],         # [str]
        "proximos_pasos": [],   # [str]
        "extra": {},
    },
    "dedup_keys": {
        "asistentes": ["nombre"],
    },
    "flatten": [
        {"path": "fecha", "tipo_dato": "fecha_reunion"},
    ],
}


# ── Esquema genérico (fallback) ───────────────────────────────────────────────

_GENERICO = {
    "version": "generico:v1",
    "template": {
        "tipo_documento_inferido": None,
        "emisor_o_autor": None,
        "fecha": None,
        "datos_clave": [],   # [str]
        "personas_mencionadas": [],   # [{nombre, cargo_o_rol}]
        "lugares_mencionados": [],    # [str]
        "cifras_relevantes": [],      # [{cifra, contexto}]
        "extra": {},
    },
    "dedup_keys": {
        "personas_mencionadas": ["nombre"],
    },
    "flatten": [
        {"path": "fecha", "tipo_dato": "fecha"},
        {"path": "emisor_o_autor", "tipo_dato": "emisor"},
        {"path": "tipo_documento_inferido", "tipo_dato": "tipo_documento"},
    ],
}


# ── Registro central ──────────────────────────────────────────────────────────

SCHEMAS: dict[str, dict[str, Any]] = {
    "ficha_precampo":      _FICHA_PRECAMPO,
    "reglamento":          _REGLAMENTO,
    "acta_eleccion":       _ACTA_ELECCION,
    "acta_posesion":       _ACTA_POSESION,
    "autocenso":           _AUTOCENSO_BASE,
    "autocenso_depurado":  {**_AUTOCENSO_BASE, "version": "autocenso_depurado:v1"},
    "censo_comunidad":     {**_AUTOCENSO_BASE, "version": "censo_comunidad:v1"},
    "resena_historica":    _RESENA_HISTORICA,
    "ficha_comision":      _FICHA_COMISION,
    "diario_campo":        _DIARIO_CAMPO,
    "acta_inicio":         _ACTA_INICIO,
    "arbol_riesgo":        _ARBOL_RIESGO,
    "registro_asistencia": _REGISTRO_ASISTENCIA,
    "apuntes_reuniones":   _APUNTES_REUNIONES,
    "generico":            _GENERICO,
}


def get_schema(rol: str | None) -> dict[str, Any]:
    """Devuelve el esquema correspondiente al rol; cae a 'generico' si no hay match."""
    if not rol:
        return _GENERICO
    return SCHEMAS.get(rol, _GENERICO)


def schema_template(rol: str | None) -> dict[str, Any]:
    """Devuelve una copia limpia del template para inicializar datos_estructurados."""
    import copy
    return copy.deepcopy(get_schema(rol)["template"])


def schema_version(rol: str | None) -> str:
    return get_schema(rol)["version"]
