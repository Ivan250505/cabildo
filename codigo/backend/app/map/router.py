"""
Endpoints del mapa principal de EtnoSIG.
Alimentan el mapa Leaflet del frontend con GeoJSON de todos los estudios/resguardos.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import get_current_user
from app.auth.models import User
from app.studies.models import Study

router = APIRouter(prefix="/api/map", tags=["map"])

# Colores por estado del estudio para el marcador del mapa
_ESTADO_COLOR: dict[str, str] = {
    "borrador":        "#9E9E9E",
    "sincronizando":   "#2196F3",
    "corpus_ok":       "#03A9F4",
    "procesando":      "#FF9800",
    "listo_revision":  "#8BC34A",
    "en_revision":     "#4CAF50",
    "aprobado":        "#1A3A5C",
    "exportado":       "#B22222",
    "error":           "#F44336",
}


@router.get("/resguardos")
async def resguardos_geojson(
    estado: str | None = Query(None, description="Filtrar por estado del estudio"),
    departamento: str | None = Query(None, description="Filtrar por departamento"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GeoJSON FeatureCollection con todos los estudios que tienen coordenadas.
    Usado por el mapa principal de Leaflet para mostrar los marcadores de resguardos.
    """
    query = select(Study).where(
        Study.lat.is_not(None),
        Study.lng.is_not(None),
    )
    if estado:
        query = query.where(Study.estado == estado)
    if departamento:
        query = query.where(Study.departamento.ilike(f"%{departamento}%"))

    result = await db.execute(query)
    studies = result.scalars().all()

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(s.lng), float(s.lat)],
            },
            "properties": {
                "id": str(s.id),
                "nombre_comunidad": s.nombre_comunidad,
                "pueblo_indigena": s.pueblo_indigena,
                "municipio": s.municipio,
                "departamento": s.departamento,
                "estado": s.estado,
                "color": _ESTADO_COLOR.get(s.estado, "#9E9E9E"),
                "contrato_referencia": s.contrato_referencia,
            },
        }
        for s in studies
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total": len(features),
            "estados_disponibles": list(_ESTADO_COLOR.keys()),
        },
    }


@router.get("/resguardos/{study_id}")
async def resguardo_detail_geojson(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GeoJSON de un solo resguardo con información completa.
    El frontend lo usa al hacer clic sobre un marcador.
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    if study.lat is None or study.lng is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "metadata": {"message": "El estudio no tiene coordenadas registradas"},
        }

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(study.lng), float(study.lat)],
                },
                "properties": {
                    "id": str(study.id),
                    "nombre_comunidad": study.nombre_comunidad,
                    "pueblo_indigena": study.pueblo_indigena,
                    "municipio": study.municipio,
                    "departamento": study.departamento,
                    "vereda": study.vereda,
                    "nit_comunidad": study.nit_comunidad,
                    "contrato_referencia": study.contrato_referencia,
                    "estado": study.estado,
                    "color": _ESTADO_COLOR.get(study.estado, "#9E9E9E"),
                    "buffer_metros": study.buffer_metros,
                    "url_drive_fase1": study.url_drive_fase1,
                    "url_drive_fase2": study.url_drive_fase2,
                    "url_drive_fase3": study.url_drive_fase3,
                },
            }
        ],
    }


@router.get("/leyenda")
async def get_leyenda(_: User = Depends(get_current_user)):
    """
    Retorna la leyenda del mapa: colores por estado y capas SIG.
    El frontend la usa para renderizar el panel de leyenda de Leaflet.
    """
    return {
        "estados": [
            {"estado": estado, "color": color, "label": estado.replace("_", " ").title()}
            for estado, color in _ESTADO_COLOR.items()
        ],
        "capas_sig": [
            {"id": "Practicas_Culturales_PUNT",   "color": "#B22222", "label": "Prácticas Culturales"},
            {"id": "Expresiones_Simbolicas_PUNT",  "color": "#C8922A", "label": "Expresiones Simbólicas"},
            {"id": "Entornos_Territoriales_PUNT",  "color": "#2E7D32", "label": "Entornos Territoriales"},
            {"id": "Procesos_Organizativos_PUNT",  "color": "#1A3A5C", "label": "Procesos Organizativos"},
        ],
    }
