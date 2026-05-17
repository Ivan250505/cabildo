from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.service import get_current_user, require_tecnico
from app.auth.models import User
from app.gis import service
from app.studies.models import GISResult

router = APIRouter(prefix="/api/studies/{study_id}/gis", tags=["gis"])


@router.post("/analyze", status_code=202)
async def analyze_study(
    study_id: UUID,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Lanza el análisis SIG completo del estudio:
    buffers 50 m, matrices de distancia, solapamientos y mapas temáticos.
    El estudio debe estar en estado 'corpus_ok'.
    """
    summary = await service.run_study_gis(db, study_id)
    await db.commit()
    return summary


@router.get("/geojson")
async def study_geojson(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna GeoJSON FeatureCollection con los puntos SIG del estudio.
    Usado por el mapa Leaflet del frontend.
    """
    return await service.get_study_geojson(db, study_id)


@router.get("/maps/{tipo_resultado}")
async def get_map_image(
    study_id: UUID,
    tipo_resultado: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga el mapa PNG de un resultado SIG.
    tipo_resultado: 'mapa_general' | 'mapa_capa_Practicas_Culturales_PUNT' | etc.
    """
    result = await db.execute(
        select(GISResult).where(
            GISResult.study_id == study_id,
            GISResult.tipo_resultado == tipo_resultado,
        )
    )
    gis_result = result.scalar_one_or_none()
    if not gis_result or not gis_result.archivo_path:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mapa no encontrado")

    return FileResponse(
        path=gis_result.archivo_path,
        media_type="image/png",
        filename=f"{tipo_resultado}.png",
    )
