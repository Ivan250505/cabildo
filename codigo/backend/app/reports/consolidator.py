"""
Consolidador del estudio (Sprint Drive E).

Toma todos los `datos_estructurados` de los archivos del corpus y los fusiona
en un único `datos_estudio.json` con estructura espejo del informe FASE 3:

  - metadata
  - fuentes (archivos del corpus que aportaron datos)
  - identificacion          ← III del informe
  - poblacion               ← III (datos poblacionales)
  - historia                ← IV
  - identidad               ← V
  - caracterizacion_intrarelacional  ← VI.1
  - caracterizacion_interrelacional  ← VI.2
  - prospectiva             ← VII
  - territorio_y_sig        ← VIII

Reglas de fusión:

  - Campos únicos primitivos (nombre, NIT, lat, etc.): primer no-vacío gana;
    el resto se conserva como "candidatos" para auditoría.
  - Cifras de población: jerarquía autocenso_depurado > autocenso > censo
    > ficha_precampo. Otros valores entran en discrepancias.
  - Listas (autoridades, eventos, clanes, etc.): se unen y deduplican.
  - Narrativas (origen, cosmogonía, alcance): todas se conservan con su fuente.

Las decisiones manuales del usuario se aplican AL FINAL desde
study.consolidacion_overrides (cuando exista). Por ahora se devuelve el
consolidado automático.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.documents.doc_schemas import get_schema
from app.studies.models import GISResult, Study, StudyCorpus, StudyLocation


# ── Mapeo rol → secciones del consolidado ─────────────────────────────────────

ROL_A_SECCIONES: dict[str, list[str]] = {
    "ficha_precampo":      ["identificacion", "poblacion", "territorio_y_sig"],
    "autocenso":           ["poblacion", "identificacion"],
    "autocenso_depurado":  ["poblacion", "identificacion"],
    "censo_comunidad":     ["poblacion"],
    "resena_historica":    ["historia", "identidad"],
    "reglamento":          ["caracterizacion_intrarelacional", "identidad"],
    "acta_eleccion":       ["identificacion", "caracterizacion_intrarelacional"],
    "acta_posesion":       ["identificacion", "caracterizacion_intrarelacional"],
    "ficha_comision":      ["caracterizacion_intrarelacional", "caracterizacion_interrelacional", "prospectiva"],
    "diario_campo":        ["caracterizacion_intrarelacional", "historia"],
    "acta_inicio":         ["identificacion"],
    "arbol_riesgo":        ["prospectiva"],
    "apuntes_reuniones":   ["caracterizacion_interrelacional"],
    "registro_asistencia": ["identificacion"],
    "evidencia_foto":      ["territorio_y_sig"],
    "generico":            [],
}


# Prioridad para resolver conflictos de cifras de población (mayor → preferido)
PRIORIDAD_POBLACION: dict[str, int] = {
    "autocenso_depurado": 100,
    "autocenso": 80,
    "censo_comunidad": 60,
    "ficha_precampo": 50,
    "ficha_comision": 30,
}


# ── Estructura vacía del consolidado ──────────────────────────────────────────

def _empty_consolidated(study: Study) -> dict[str, Any]:
    return {
        "metadata": {
            "study_id": str(study.id),
            "nombre_comunidad": study.nombre_comunidad,
            "pueblo_indigena": study.pueblo_indigena,
            "municipio": study.municipio,
            "departamento": study.departamento,
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "archivos_consolidados": 0,
            "archivos_con_datos": 0,
            "archivos_sin_datos": 0,
            "discrepancias_count": 0,
        },
        "fuentes": [],
        "identificacion": {
            "nombre_comunidad": None,
            "pueblo_indigena": None,
            "autodenominacion": None,
            "municipio": None,
            "vereda": None,
            "departamento": None,
            "nit": None,
            "representante_legal": None,
            "autoridades": [],
            "candidatos": {},
        },
        "poblacion": {
            "personas": None,
            "familias": None,
            "fecha_censo": None,
            "fuente_censo": None,
            "distribucion_por_sexo": None,
            "distribucion_por_edad": [],
            "evolucion_demografica": [],
            "discrepancias": [],
        },
        "historia": {
            "lugar_origen": None,
            "narrativa_origen": [],
            "cosmogonia": [],
            "clanes": [],
            "eventos_historicos": [],
            "actores_externos_historicos": [],
            "elementos_sagrados": [],
            "proceso_recuperacion": [],
            "trayectoria_migratoria": [],
        },
        "identidad": {
            "autoidentificacion": [],
            "lengua_indigena": None,
            "nivel_uso_lengua": None,
            "clanes": [],
            "principios_fundacionales": [],
        },
        "caracterizacion_intrarelacional": {
            "actividades_culturales": [],
            "rituales": [],
            "lugares_sagrados": [],
            "plantas_sagradas": [],
            "actividades_subsistencia": [],
            "herramientas_tradicionales": [],
            "estructura_cargos": [],
            "instancias_decision": [],
            "reglamento_resumen": [],
            "hallazgos_campo": [],
        },
        "caracterizacion_interrelacional": {
            "alianzas_interetnicas": [],
            "relaciones_institucionales": [],
            "actores_externos": [],
            "acuerdos_recientes": [],
        },
        "prospectiva": {
            "amenazas_externas": [],
            "amenazas_internas": [],
            "causas_raiz": [],
            "efectos": [],
            "mitigaciones_propuestas": [],
            "vision_futuro": [],
            "despojos_historicos": [],
        },
        "territorio_y_sig": {
            "extension_ha": None,
            "tipo_tenencia": None,
            "vias_acceso": None,
            "distancia_cabecera_km": None,
            "coordenadas_centrales": {"lat": float(study.lat) if study.lat is not None else None,
                                       "lng": float(study.lng) if study.lng is not None else None,
                                       "plus_code": None},
            "ubicaciones": [],
            "resultados_sig": [],
            "evidencias_geograficas": [],
        },
    }


# ── Helpers de merge ──────────────────────────────────────────────────────────

def _add_unique(target: dict, key: str, valor: Any, fuente: str, confianza: float = 0.9) -> None:
    """Asigna un campo único si está vacío; si no, lo agrega a 'candidatos' para auditoría."""
    if valor in (None, "", [], {}):
        return
    if target.get(key) in (None, ""):
        target[key] = {"valor": valor, "fuente": fuente, "confianza": confianza}
    else:
        existing_value = target[key].get("valor") if isinstance(target[key], dict) else target[key]
        if str(existing_value).strip().lower() == str(valor).strip().lower():
            return  # mismo valor, no es candidato
        target.setdefault("candidatos", {}).setdefault(key, []).append(
            {"valor": valor, "fuente": fuente, "confianza": confianza}
        )


def _add_to_list(target_list: list, item: Any, fuente: str, dedup_keys: list[str] | None = None) -> None:
    """Agrega un item con su fuente; deduplica si dedup_keys está dado."""
    if item in (None, "", [], {}):
        return
    if isinstance(item, dict):
        entry = {**item, "_fuente": fuente}
    else:
        entry = {"valor": item, "_fuente": fuente}

    if dedup_keys:
        # Verificar si ya existe un item con las mismas claves
        for existing in target_list:
            if all(
                str(existing.get(k, "")).strip().lower() == str(entry.get(k, "")).strip().lower()
                for k in dedup_keys
            ):
                # Ya está — registrar fuente adicional sin duplicar
                ya = existing.get("_fuentes_adicionales", [])
                if fuente not in ya and fuente != existing.get("_fuente"):
                    ya.append(fuente)
                    existing["_fuentes_adicionales"] = ya
                return
    target_list.append(entry)


def _add_narrative(target_list: list, texto: Any, fuente: str) -> None:
    """Agrega una narrativa con su fuente. Sin dedup — todas las versiones se conservan."""
    if not texto or not isinstance(texto, str) or not texto.strip():
        return
    target_list.append({"texto": texto.strip(), "fuente": fuente})


def _add_poblacion_cifra(
    pob: dict, campo: str, valor: int, fuente: str, rol: str, fecha: str | None
) -> None:
    """Resuelve cifras de población con jerarquía y registra discrepancias."""
    if valor is None:
        return
    try:
        valor = int(valor)
    except (ValueError, TypeError):
        return

    prioridad_nueva = PRIORIDAD_POBLACION.get(rol, 0)
    actual = pob.get(campo)
    if actual is None:
        pob[campo] = {"valor": valor, "fuente": fuente, "rol": rol,
                      "prioridad": prioridad_nueva, "fecha": fecha}
        return

    actual_valor = actual.get("valor") if isinstance(actual, dict) else None
    actual_fuente = actual.get("fuente") if isinstance(actual, dict) else None
    actual_prioridad = actual.get("prioridad", 0) if isinstance(actual, dict) else 0

    if valor == actual_valor:
        return  # mismo valor, no es discrepancia

    if prioridad_nueva > actual_prioridad:
        # El nuevo gana — el viejo va a discrepancias
        pob.setdefault("discrepancias", []).append({
            "campo": campo,
            "valor_a": valor, "fuente_a": fuente, "rol_a": rol,
            "valor_b": actual_valor, "fuente_b": actual_fuente,
            "preferido": "a",
        })
        pob[campo] = {"valor": valor, "fuente": fuente, "rol": rol,
                      "prioridad": prioridad_nueva, "fecha": fecha}
    else:
        # El viejo se mantiene; el nuevo va a discrepancias
        pob.setdefault("discrepancias", []).append({
            "campo": campo,
            "valor_a": actual_valor, "fuente_a": actual_fuente, "rol_a": actual.get("rol"),
            "valor_b": valor, "fuente_b": fuente, "rol_b": rol,
            "preferido": "a",
        })


# ── Mergers por rol ───────────────────────────────────────────────────────────

def _merge_ficha_precampo(consolidated: dict, datos: dict, fuente: str) -> None:
    ident = consolidated["identificacion"]
    pob = consolidated["poblacion"]
    terr = consolidated["territorio_y_sig"]

    _add_unique(ident, "nombre_comunidad", datos.get("comunidad_nombre_oficial"), fuente)
    _add_unique(ident, "autodenominacion", datos.get("comunidad_autodenominacion"), fuente)
    ub = datos.get("ubicacion") or {}
    _add_unique(ident, "municipio", ub.get("municipio"), fuente)
    _add_unique(ident, "vereda", ub.get("vereda"), fuente)
    _add_unique(ident, "departamento", ub.get("departamento"), fuente)

    for a in (datos.get("autoridades_clave") or []):
        _add_to_list(ident["autoridades"], a, fuente, dedup_keys=["nombre", "cargo"])

    coord = datos.get("coordenadas") or {}
    if coord.get("lat") is not None and coord.get("lng") is not None:
        if terr["coordenadas_centrales"].get("lat") is None:
            terr["coordenadas_centrales"] = {
                "lat": coord.get("lat"), "lng": coord.get("lng"),
                "plus_code": coord.get("plus_code"), "fuente": fuente,
            }
    if datos.get("vias_acceso"):
        terr["vias_acceso"] = {"valor": datos["vias_acceso"], "fuente": fuente}
    if datos.get("distancia_cabecera_km") is not None:
        terr["distancia_cabecera_km"] = {"valor": datos["distancia_cabecera_km"], "fuente": fuente}

    for ev in (datos.get("evolucion_demografica") or []):
        _add_to_list(pob["evolucion_demografica"], ev, fuente, dedup_keys=["anio"])

    # Última cifra de la evolución demográfica como "personas"/"familias" base
    if datos.get("evolucion_demografica"):
        ultimo = sorted(datos["evolucion_demografica"], key=lambda e: (e.get("anio") or 0))[-1]
        _add_poblacion_cifra(pob, "personas", ultimo.get("personas"), fuente, "ficha_precampo", str(ultimo.get("anio")))
        _add_poblacion_cifra(pob, "familias", ultimo.get("familias"), fuente, "ficha_precampo", str(ultimo.get("anio")))

    for r in (datos.get("riesgos_identificados") or []):
        _add_to_list(consolidated["prospectiva"]["amenazas_externas"], {"descripcion": r}, fuente, dedup_keys=["descripcion"])

    for inst in (datos.get("instituciones_presentes") or []):
        _add_to_list(consolidated["caracterizacion_interrelacional"]["relaciones_institucionales"],
                     {"institucion": inst}, fuente, dedup_keys=["institucion"])


def _merge_autocenso(consolidated: dict, datos: dict, fuente: str, rol: str) -> None:
    pob = consolidated["poblacion"]
    fecha = datos.get("fecha_registro")

    _add_poblacion_cifra(pob, "personas", datos.get("total_personas"), fuente, rol, fecha)
    _add_poblacion_cifra(pob, "familias", datos.get("total_familias"), fuente, rol, fecha)

    if datos.get("fecha_registro") and not pob.get("fecha_censo"):
        pob["fecha_censo"] = {"valor": datos["fecha_registro"], "fuente": fuente}
    if datos.get("coordinador_registro") and not pob.get("fuente_censo"):
        pob["fuente_censo"] = {"valor": datos["coordinador_registro"], "fuente": fuente}

    if datos.get("distribucion_por_sexo"):
        d = datos["distribucion_por_sexo"]
        if any(v is not None and v != 0 for v in d.values()):
            pob["distribucion_por_sexo"] = {**d, "_fuente": fuente}

    for ed in (datos.get("distribucion_por_edad") or []):
        _add_to_list(pob["distribucion_por_edad"], ed, fuente, dedup_keys=["rango"])

    if datos.get("discrepancia_con_censo_general"):
        pob["discrepancias"].append({
            "campo": "narrativa",
            "texto": datos["discrepancia_con_censo_general"],
            "fuente": fuente,
        })


def _merge_resena_historica(consolidated: dict, datos: dict, fuente: str) -> None:
    hist = consolidated["historia"]
    ident = consolidated["identidad"]

    _add_unique(hist, "lugar_origen", datos.get("lugar_origen_ancestral"), fuente)
    _add_narrative(hist["narrativa_origen"], datos.get("narrativa_origen"), fuente)
    _add_narrative(hist["cosmogonia"], datos.get("cosmogonia"), fuente)
    _add_narrative(hist["proceso_recuperacion"], datos.get("proceso_recuperacion"), fuente)

    for clan in (datos.get("clanes") or []):
        _add_to_list(hist["clanes"], clan, fuente, dedup_keys=["nombre"])
        _add_to_list(ident["clanes"], clan, fuente, dedup_keys=["nombre"])

    for ev in (datos.get("eventos_historicos") or []):
        _add_to_list(hist["eventos_historicos"], ev, fuente, dedup_keys=["anio", "evento"])

    for actor in (datos.get("actores_externos_historicos") or []):
        _add_to_list(hist["actores_externos_historicos"], {"actor": actor}, fuente, dedup_keys=["actor"])

    for el in (datos.get("elementos_sagrados") or []):
        _add_to_list(hist["elementos_sagrados"], el, fuente, dedup_keys=["elemento"])


def _merge_reglamento(consolidated: dict, datos: dict, fuente: str) -> None:
    intra = consolidated["caracterizacion_intrarelacional"]
    ident = consolidated["identidad"]

    for c in (datos.get("estructura_cargos") or []):
        _add_to_list(intra["estructura_cargos"], c, fuente, dedup_keys=["cargo"])
    for inst in (datos.get("instancias_decision") or []):
        _add_to_list(intra["instancias_decision"], inst, fuente, dedup_keys=["nombre"])
    for p in (datos.get("principios_fundacionales") or []):
        _add_to_list(ident["principios_fundacionales"], {"principio": p}, fuente, dedup_keys=["principio"])
    if datos.get("cabildo_o_comunidad"):
        _add_unique(consolidated["identificacion"], "nombre_comunidad", datos["cabildo_o_comunidad"], fuente, confianza=0.7)
    if datos.get("cuotas_y_multas") or datos.get("causales_sancion"):
        # Resumen para builder
        intra["reglamento_resumen"].append({
            "fuente": fuente,
            "cuotas_y_multas": datos.get("cuotas_y_multas") or [],
            "causales_sancion": datos.get("causales_sancion") or [],
            "fecha_aprobacion": datos.get("fecha_aprobacion"),
        })


def _merge_acta_eleccion(consolidated: dict, datos: dict, fuente: str) -> None:
    intra = consolidated["caracterizacion_intrarelacional"]
    for c in (datos.get("cargos_elegidos") or []):
        _add_to_list(intra["estructura_cargos"], {
            "cargo": c.get("cargo"),
            "nombre_titular": c.get("nombre"),
            "cedula": c.get("cedula"),
            "fecha_eleccion": datos.get("fecha"),
        }, fuente, dedup_keys=["cargo"])
    if datos.get("avalado_por"):
        _add_to_list(
            consolidated["caracterizacion_interrelacional"]["relaciones_institucionales"],
            {"institucion": datos["avalado_por"], "tipo": "aval_eleccion"},
            fuente, dedup_keys=["institucion"]
        )


def _merge_acta_posesion(consolidated: dict, datos: dict, fuente: str) -> None:
    intra = consolidated["caracterizacion_intrarelacional"]
    for c in (datos.get("cargos_posesionados") or []):
        _add_to_list(intra["estructura_cargos"], {
            "cargo": c.get("cargo"),
            "nombre_titular": c.get("nombre"),
            "cedula": c.get("cedula"),
            "fecha_posesion": datos.get("fecha"),
            "alcalde_posesion": datos.get("alcalde_u_oficial"),
        }, fuente, dedup_keys=["cargo"])
    if datos.get("alcalde_u_oficial"):
        _add_to_list(
            consolidated["caracterizacion_interrelacional"]["relaciones_institucionales"],
            {"institucion": datos["alcalde_u_oficial"], "tipo": "alcalde_posesion"},
            fuente, dedup_keys=["institucion"]
        )


def _merge_ficha_comision(consolidated: dict, datos: dict, fuente: str) -> None:
    intra = consolidated["caracterizacion_intrarelacional"]
    inter = consolidated["caracterizacion_interrelacional"]
    pros = consolidated["prospectiva"]

    for h in (datos.get("hallazgos_intrarelacional") or []):
        _add_to_list(intra["hallazgos_campo"], {"texto": h}, fuente, dedup_keys=["texto"])
    for h in (datos.get("hallazgos_interrelacional") or []):
        _add_to_list(inter["actores_externos"], {"texto": h}, fuente, dedup_keys=["texto"])
    for h in (datos.get("hallazgos_espiritual") or []):
        _add_to_list(intra["rituales"], {"texto": h}, fuente, dedup_keys=["texto"])
    for h in (datos.get("hallazgos_territorial") or []):
        _add_to_list(intra["hallazgos_campo"], {"texto": h, "categoria": "territorial"}, fuente, dedup_keys=["texto"])
    for h in (datos.get("hallazgos_organizativo") or []):
        _add_to_list(intra["hallazgos_campo"], {"texto": h, "categoria": "organizativo"}, fuente, dedup_keys=["texto"])
    if datos.get("conclusiones_visita"):
        _add_narrative(pros["vision_futuro"], datos["conclusiones_visita"], fuente)


def _merge_diario_campo(consolidated: dict, datos: dict, fuente: str) -> None:
    intra = consolidated["caracterizacion_intrarelacional"]
    for entry in (datos.get("entradas") or []):
        if entry.get("narrativa"):
            _add_to_list(intra["hallazgos_campo"], {
                "fecha": entry.get("fecha"),
                "lugar": entry.get("lugar"),
                "texto": entry.get("narrativa"),
            }, fuente, dedup_keys=["fecha", "lugar"])


def _merge_arbol_riesgo(consolidated: dict, datos: dict, fuente: str) -> None:
    pros = consolidated["prospectiva"]
    for a in (datos.get("amenazas_externas") or []):
        _add_to_list(pros["amenazas_externas"], a, fuente, dedup_keys=["descripcion"])
    for a in (datos.get("amenazas_internas") or []):
        _add_to_list(pros["amenazas_internas"], a, fuente, dedup_keys=["descripcion"])
    for c in (datos.get("causas_raiz") or []):
        _add_to_list(pros["causas_raiz"], {"texto": c}, fuente, dedup_keys=["texto"])
    for e in (datos.get("efectos") or []):
        _add_to_list(pros["efectos"], {"texto": e}, fuente, dedup_keys=["texto"])
    for m in (datos.get("mitigaciones_propuestas") or []):
        _add_to_list(pros["mitigaciones_propuestas"], m, fuente, dedup_keys=["accion"])


def _merge_acta_inicio(consolidated: dict, datos: dict, fuente: str) -> None:
    if datos.get("comunidad"):
        _add_unique(consolidated["identificacion"], "nombre_comunidad", datos["comunidad"], fuente, confianza=0.8)
    if datos.get("alcance_estudio"):
        consolidated["metadata"].setdefault("alcance_estudio", []).append(
            {"texto": datos["alcance_estudio"], "fuente": fuente}
        )


def _merge_apuntes_reuniones(consolidated: dict, datos: dict, fuente: str) -> None:
    inter = consolidated["caracterizacion_interrelacional"]
    for acuerdo in (datos.get("acuerdos") or []):
        _add_to_list(inter["acuerdos_recientes"], {"texto": acuerdo, "fecha": datos.get("fecha")},
                     fuente, dedup_keys=["texto"])


def _merge_evidencia_foto(consolidated: dict, datos: dict, fuente: str) -> None:
    terr = consolidated["territorio_y_sig"]
    ubic = datos.get("ubicacion_sugerida")
    if isinstance(ubic, dict) and ubic.get("lat") is not None:
        _add_to_list(terr["evidencias_geograficas"], {
            "nombre": ubic.get("nombre"),
            "lat": ubic.get("lat"),
            "lng": ubic.get("lng"),
            "descripcion": ubic.get("descripcion"),
        }, fuente, dedup_keys=["lat", "lng"])


_MERGERS = {
    "ficha_precampo": _merge_ficha_precampo,
    "autocenso": lambda c, d, f: _merge_autocenso(c, d, f, "autocenso"),
    "autocenso_depurado": lambda c, d, f: _merge_autocenso(c, d, f, "autocenso_depurado"),
    "censo_comunidad": lambda c, d, f: _merge_autocenso(c, d, f, "censo_comunidad"),
    "resena_historica": _merge_resena_historica,
    "reglamento": _merge_reglamento,
    "acta_eleccion": _merge_acta_eleccion,
    "acta_posesion": _merge_acta_posesion,
    "ficha_comision": _merge_ficha_comision,
    "diario_campo": _merge_diario_campo,
    "arbol_riesgo": _merge_arbol_riesgo,
    "acta_inicio": _merge_acta_inicio,
    "apuntes_reuniones": _merge_apuntes_reuniones,
    "evidencia_foto": _merge_evidencia_foto,
}


# ── Función principal ─────────────────────────────────────────────────────────

async def consolidate_study(db: AsyncSession, study_id: UUID) -> dict[str, Any]:
    """
    Construye el consolidado del estudio a partir de todos sus archivos con
    datos_estructurados, sus StudyLocations y sus GISResults.

    Idempotente y reentrante — no escribe nada en BD, solo lee.
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")

    consolidated = _empty_consolidated(study)

    # 1) Archivos del corpus con datos
    corpus_result = await db.execute(
        select(StudyCorpus).where(StudyCorpus.study_id == study_id)
    )
    archivos = list(corpus_result.scalars().all())

    procesados_con_datos = 0
    procesados_sin_datos = 0

    for f in archivos:
        consolidated["fuentes"].append({
            "file_id": str(f.id),
            "nombre_archivo": f.nombre_archivo,
            "rol": f.rol_en_corpus,
            "esquema_version": f.esquema_version,
            "extraido_con_modelo": f.extraido_con_modelo,
            "extraido_en": f.extraido_en_v2.isoformat() if f.extraido_en_v2 else None,
            "fuente_extraccion": f.fuente_extraccion,
            "tiene_datos": f.datos_estructurados is not None,
        })

        if not f.datos_estructurados:
            procesados_sin_datos += 1
            continue

        procesados_con_datos += 1
        merger = _MERGERS.get(f.rol_en_corpus or "")
        if merger:
            try:
                merger(consolidated, f.datos_estructurados, f.nombre_archivo)
            except Exception as e:
                logger.warning("Merger falló para %s (rol=%s): %s", f.nombre_archivo, f.rol_en_corpus, e)

    # 2) StudyLocations → territorio_y_sig.ubicaciones
    loc_result = await db.execute(
        select(StudyLocation).where(StudyLocation.study_id == study_id)
    )
    for loc in loc_result.scalars().all():
        consolidated["territorio_y_sig"]["ubicaciones"].append({
            "nombre": loc.nombre,
            "tipo": loc.tipo,
            "lat": float(loc.lat),
            "lng": float(loc.lng),
            "descripcion": loc.descripcion,
            "fuente_archivo": loc.fuente_archivo,
        })

    # 3) GISResults → territorio_y_sig.resultados_sig
    gis_result = await db.execute(
        select(GISResult).where(GISResult.study_id == study_id)
    )
    for r in gis_result.scalars().all():
        consolidated["territorio_y_sig"]["resultados_sig"].append({
            "tipo_resultado": r.tipo_resultado,
            "resultado_json": r.resultado_json,
            "generado_en": r.generado_en.isoformat() if r.generado_en else None,
        })

    # 4) Actualizar metadata
    consolidated["metadata"]["archivos_consolidados"] = len(archivos)
    consolidated["metadata"]["archivos_con_datos"] = procesados_con_datos
    consolidated["metadata"]["archivos_sin_datos"] = procesados_sin_datos
    consolidated["metadata"]["discrepancias_count"] = len(consolidated["poblacion"].get("discrepancias", []))

    return consolidated


def flatten_consolidated_value(v: Any) -> Any:
    """Helper para builder/writer: si un valor es {valor, fuente}, devuelve solo el valor."""
    if isinstance(v, dict) and "valor" in v and "fuente" in v:
        return v["valor"]
    return v


# ── Overrides manuales del usuario ────────────────────────────────────────────

def _set_path(obj: dict, path: str, value: Any) -> None:
    """Asigna obj[a][b][c] = value para path = 'a.b.c'. Crea dicts si hace falta."""
    parts = path.split(".")
    cur: Any = obj
    for p in parts[:-1]:
        if not isinstance(cur, dict):
            return
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    if isinstance(cur, dict):
        cur[parts[-1]] = value


def apply_overrides(consolidated: dict, overrides: dict | None) -> dict:
    """
    Aplica los overrides manuales sobre el consolidado. Cada override sigue el formato:

        { "<path>": { "valor": ..., "fuente": "manual", "nota": ... } }

    El path usa dot-notation contra la raíz del consolidado, ej:
      "poblacion.personas" → consolidated["poblacion"]["personas"] = {"valor": ..., "fuente": "manual", ...}
      "identificacion.nit"  → consolidated["identificacion"]["nit"]  = {...}
    """
    if not overrides:
        return consolidated
    consolidated.setdefault("metadata", {})["overrides_aplicados"] = len(overrides)
    for path, decision in overrides.items():
        if not isinstance(decision, dict) or "valor" not in decision:
            continue
        valor_struct = {
            "valor": decision["valor"],
            "fuente": decision.get("fuente", "manual"),
            "confianza": 1.000,
            "nota": decision.get("nota"),
            "override": True,
        }
        _set_path(consolidated, path, valor_struct)
    return consolidated


async def consolidate_study_with_overrides(db: AsyncSession, study_id: UUID) -> dict[str, Any]:
    """consolidate_study + applies study.consolidacion_overrides al final."""
    consolidated = await consolidate_study(db, study_id)
    result = await db.execute(select(Study.consolidacion_overrides).where(Study.id == study_id))
    overrides = result.scalar_one_or_none()
    return apply_overrides(consolidated, overrides)
