"""
Servicio GIS: orquesta la búsqueda de GeoPackages del corpus,
ejecuta el motor de análisis espacial y persiste los resultados en BD.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.studies.models import GISResult, Study, StudyCorpus
from app.gis.engine import run_full_analysis, load_layers, LAYER_STYLES

settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_study_or_404(db: AsyncSession, study_id: UUID) -> Study:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudio no encontrado")
    return study


def _find_layers_dir(corpus_files: list[StudyCorpus]) -> Path | None:
    """
    Busca el directorio que contiene los GeoPackages de las capas principales.
    Prioriza la carpeta con más capas PUNT encontradas.
    """
    gpkg_paths = [
        Path(f.ruta_local)
        for f in corpus_files
        if f.tipo_archivo == "gpkg" and f.ruta_local and Path(f.ruta_local).exists()
    ]
    if not gpkg_paths:
        return None

    # Agrupar por directorio y contar cuántas capas principales tiene cada uno
    dir_counts: dict[Path, int] = {}
    for p in gpkg_paths:
        d = p.parent
        is_main = any(name in p.stem for name in LAYER_STYLES)
        dir_counts[d] = dir_counts.get(d, 0) + (1 if is_main else 0)

    best = max(dir_counts, key=lambda d: dir_counts[d])
    return best if dir_counts[best] > 0 else (gpkg_paths[0].parent if gpkg_paths else None)


# ── Análisis SIG ──────────────────────────────────────────────────────────────

async def run_study_gis(
    db: AsyncSession, study_id: UUID
) -> dict:
    """
    Ejecuta el análisis SIG completo para un estudio:
      1. Localiza los GeoPackages en el corpus descargado.
      2. Corre buffers, matrices de distancia y solapamientos.
      3. Genera mapas PNG.
      4. Persiste GISResult en BD.
      5. Transiciona el estudio a 'listo_revision'.

    Retorna un resumen de los resultados.
    """
    study = await _get_study_or_404(db, study_id)

    if study.estado not in ("corpus_ok", "procesando"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El análisis SIG requiere estado 'corpus_ok' o 'procesando'. "
                   f"Estado actual: '{study.estado}'.",
        )

    # Marcar como procesando
    study.estado = "procesando"
    await db.flush()

    # Buscar GeoPackages del corpus
    corpus_result = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.study_id == study_id,
            StudyCorpus.tipo_archivo == "gpkg",
            StudyCorpus.estado == "descargado",
        )
    )
    corpus_gpkg = list(corpus_result.scalars().all())

    layers_dir = _find_layers_dir(corpus_gpkg)

    if not layers_dir:
        study.estado = "error"
        study.error_msg = "No se encontraron GeoPackages de capas SIG en el corpus."
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se encontraron GeoPackages. Sincronice el corpus primero.",
        )

    # Ejecutar análisis
    try:
        analysis = run_full_analysis(layers_dir, buffer_m=study.buffer_metros)
    except Exception as e:
        study.estado = "error"
        study.error_msg = f"Error en análisis SIG: {e}"
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Error en análisis SIG: {e}")

    # Directorio de salida para mapas
    maps_dir = Path(settings.FILES_BASE_PATH) / str(study_id) / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    # Eliminar resultados anteriores de este estudio
    old_results = await db.execute(
        select(GISResult).where(GISResult.study_id == study_id)
    )
    for old in old_results.scalars().all():
        await db.delete(old)

    now = datetime.now(timezone.utc)
    saved: list[dict] = []

    # Guardar matrices de distancia
    for matrix in analysis["matrices_distancia"]:
        r = GISResult(
            study_id=study_id,
            tipo_resultado="matriz_distancia",
            parametros={"buffer_metros": study.buffer_metros},
            resultado_json=matrix,
            generado_en=now,
        )
        db.add(r)
        saved.append({"tipo": "matriz_distancia", "capas": matrix["capas"]})

    # Guardar solapamientos
    for overlap in analysis["solapamientos"]:
        r = GISResult(
            study_id=study_id,
            tipo_resultado="solapamiento",
            parametros={"buffer_metros": study.buffer_metros},
            resultado_json=overlap,
            generado_en=now,
        )
        db.add(r)
        saved.append({"tipo": "solapamiento", "capas": overlap["capas"]})

    # Guardar mapa general
    if analysis.get("mapa_general_png"):
        png_path = maps_dir / "mapa_general.png"
        png_path.write_bytes(analysis["mapa_general_png"])
        r = GISResult(
            study_id=study_id,
            tipo_resultado="mapa_general",
            parametros={"buffer_metros": study.buffer_metros},
            resultado_json={"n_capas": len(analysis["capas_cargadas"])},
            archivo_path=str(png_path),
            generado_en=now,
        )
        db.add(r)
        saved.append({"tipo": "mapa_general", "path": str(png_path)})

    # Guardar mapas por capa
    for nombre_capa, png_bytes in analysis.get("mapas_por_capa_png", {}).items():
        png_path = maps_dir / f"mapa_{nombre_capa}.png"
        png_path.write_bytes(png_bytes)
        r = GISResult(
            study_id=study_id,
            tipo_resultado=f"mapa_capa_{nombre_capa}",
            parametros={"capa": nombre_capa, "buffer_metros": study.buffer_metros},
            resultado_json={"nombre_capa": nombre_capa},
            archivo_path=str(png_path),
            generado_en=now,
        )
        db.add(r)
        saved.append({"tipo": f"mapa_capa_{nombre_capa}", "path": str(png_path)})

    # Transicionar estado
    study.estado = "listo_revision"
    study.error_msg = None
    await db.flush()

    return {
        "study_id": str(study_id),
        "capas_analizadas": analysis["capas_cargadas"],
        "n_puntos_por_capa": analysis["n_puntos_por_capa"],
        "buffer_metros": study.buffer_metros,
        "resultados_guardados": len(saved),
        "layers_dir": str(layers_dir),
    }


# ── GeoJSON para mapa ─────────────────────────────────────────────────────────

async def get_study_geojson(db: AsyncSession, study_id: UUID) -> dict:
    """
    Retorna un GeoJSON FeatureCollection con los puntos de las capas SIG
    del estudio (leídos directamente desde los GeoPackages del corpus).
    """
    study = await _get_study_or_404(db, study_id)

    corpus_result = await db.execute(
        select(StudyCorpus).where(
            StudyCorpus.study_id == study_id,
            StudyCorpus.tipo_archivo == "gpkg",
            StudyCorpus.estado == "descargado",
        )
    )
    corpus_gpkg = list(corpus_result.scalars().all())
    layers_dir = _find_layers_dir(corpus_gpkg)

    if not layers_dir:
        return {"type": "FeatureCollection", "features": []}

    layers = load_layers(layers_dir)
    features: list[dict] = []

    layer_colors = {
        "Practicas_Culturales_PUNT":    "#B22222",
        "Expresiones_Simbolicas_PUNT":  "#C8922A",
        "Entornos_Territoriales_PUNT":  "#2E7D32",
        "Procesos_Organizativos_PUNT":  "#1A3A5C",
    }
    layer_labels = {
        "Practicas_Culturales_PUNT":    "Prácticas Culturales",
        "Expresiones_Simbolicas_PUNT":  "Expresiones Simbólicas",
        "Entornos_Territoriales_PUNT":  "Entornos Territoriales",
        "Procesos_Organizativos_PUNT":  "Procesos Organizativos",
    }

    for name, gdf in layers.items():
        gdf_geo = gdf.to_crs("EPSG:4326")
        for _, row in gdf_geo.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            props = {
                k: (str(v) if v is not None else None)
                for k, v in row.items()
                if k != "geometry"
            }
            props["capa"] = name
            props["capa_label"] = layer_labels.get(name, name)
            props["color"] = layer_colors.get(name, "#666666")
            props["study_id"] = str(study_id)
            props["comunidad"] = study.nombre_comunidad

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [geom.x, geom.y],
                },
                "properties": props,
            })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "study_id": str(study_id),
            "nombre_comunidad": study.nombre_comunidad,
            "total_puntos": len(features),
            "capas": list(layers.keys()),
        },
    }
