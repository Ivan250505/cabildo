from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.auth.service import get_current_user, require_tecnico
from app.auth.models import User
from app.gis import service
from app.studies.models import GISResult, Study

router = APIRouter(prefix="/api/studies/{study_id}/gis", tags=["gis"])


async def _bg_gis(study_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await service.run_study_gis(db, study_id)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            # Si falla (sin GPKGs u otro error), volver a corpus_ok para no bloquear el flujo
            async with AsyncSessionLocal() as db2:
                result = await db2.execute(select(Study).where(Study.id == study_id))
                study = result.scalar_one_or_none()
                if study and study.estado == "procesando":
                    study.estado = "corpus_ok"
                    study.error_msg = f"SIG omitido: {str(exc)[:200]}"
                    await db2.commit()


@router.post("/analyze", status_code=202)
async def analyze_study(
    study_id: UUID,
    background_tasks: BackgroundTasks,
    _: User = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    """
    Lanza el análisis SIG en segundo plano.
    Devuelve 202 inmediatamente. Seguir el progreso via GET /studies/{id} (campo estado).
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    background_tasks.add_task(_bg_gis, study_id)
    return {"status": "procesando", "study_id": str(study_id)}


@router.get("/geojson")
async def study_geojson(
    study_id: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GeoJSON FeatureCollection con los puntos SIG del estudio."""
    return await service.get_study_geojson(db, study_id)


@router.get("/maps/{tipo_resultado}")
async def get_map_image(
    study_id: UUID,
    tipo_resultado: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descarga el mapa PNG de un resultado SIG."""
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
