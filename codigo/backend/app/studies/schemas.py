from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Literal

from app.studies.models import STUDY_STATES, CORPUS_FILE_TYPES, CORPUS_ROLES, LOCATION_TIPOS


# ── Study ─────────────────────────────────────────────────────────────────────

class StudyCreate(BaseModel):
    nombre_comunidad: str = Field(..., max_length=300)
    pueblo_indigena: str | None = Field(None, max_length=200)
    municipio: str = Field(..., max_length=200)
    departamento: str = Field(..., max_length=200)
    vereda: str | None = Field(None, max_length=200)
    nit_comunidad: str | None = Field(None, max_length=20)
    contrato_referencia: str | None = Field(None, max_length=100)
    notas_adicionales: str | None = None
    lat: float | None = None
    lng: float | None = None
    url_drive_fase1: str | None = None
    url_drive_fase2: str | None = None
    url_drive_fase3: str | None = None
    buffer_metros: int = Field(50, ge=10, le=500)
    responsable_id: UUID | None = None
    modo_creacion: Literal["drive_existente", "encuestas_nuevas"] = "drive_existente"


class StudyUpdate(BaseModel):
    nombre_comunidad: str | None = Field(None, max_length=300)
    pueblo_indigena: str | None = Field(None, max_length=200)
    municipio: str | None = Field(None, max_length=200)
    departamento: str | None = Field(None, max_length=200)
    vereda: str | None = None
    nit_comunidad: str | None = None
    contrato_referencia: str | None = None
    notas_adicionales: str | None = None
    lat: float | None = None
    lng: float | None = None
    url_drive_fase1: str | None = None
    url_drive_fase2: str | None = None
    url_drive_fase3: str | None = None
    buffer_metros: int | None = Field(None, ge=10, le=500)
    responsable_id: UUID | None = None


class StudyStateTransition(BaseModel):
    estado: Literal[STUDY_STATES]
    error_msg: str | None = None


class StudySummary(BaseModel):
    id: UUID
    nombre_comunidad: str
    pueblo_indigena: str | None
    municipio: str
    departamento: str
    estado: str
    responsable_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudyResponse(BaseModel):
    id: UUID
    nombre_comunidad: str
    pueblo_indigena: str | None
    municipio: str
    departamento: str
    vereda: str | None
    nit_comunidad: str | None
    contrato_referencia: str | None
    notas_adicionales: str | None
    lat: float | None
    lng: float | None
    estado: str
    modo_creacion: str
    error_msg: str | None
    url_drive_fase1: str | None
    url_drive_fase2: str | None
    url_drive_fase3: str | None
    drive_folder_id: str | None
    buffer_metros: int
    responsable_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudyListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[StudySummary]


# ── StudyCorpus ────────────────────────────────────────────────────────────────

class CorpusFileCreate(BaseModel):
    fase: Literal["FASE1", "FASE2", "FASE3"]
    nombre_archivo: str = Field(..., max_length=500)
    drive_file_id: str = Field(..., max_length=200)
    tipo_archivo: Literal[CORPUS_FILE_TYPES]
    rol_en_corpus: Literal[CORPUS_ROLES] | None = None
    tamanio_bytes: int | None = None


class CorpusFileResponse(BaseModel):
    id: UUID
    study_id: UUID
    fase: str
    nombre_archivo: str
    drive_file_id: str
    tipo_archivo: str
    rol_en_corpus: str | None
    clasificacion_fuente: str | None
    clasificacion_confianza: float | None
    notas_clasificacion: str | None
    tamanio_bytes: int | None
    ruta_local: str | None
    estado: str
    error_msg: str | None
    sync_at: datetime
    procesado_en: datetime | None

    model_config = {"from_attributes": True}


# ── Clasificación de archivos ─────────────────────────────────────────────────

class CorpusClasificarRequest(BaseModel):
    """Parámetros para POST /api/studies/{id}/corpus/clasificar."""
    ignore_existing: bool = False     # True = reclasificar también los ya clasificados (no toca 'manual')
    use_ai_fallback: bool = True      # False = solo heurística, sin tokens IA


class CorpusRolOverrideRequest(BaseModel):
    """Body de PATCH /api/studies/{id}/corpus/{file_id}/rol."""
    rol: Literal[CORPUS_ROLES]
    notas: str | None = None


class CorpusClasificacionItem(BaseModel):
    file_id: str
    nombre: str
    rol: str | None
    fuente: str
    confianza: float
    omitido: bool = False
    notas: str | None = None


class CorpusClasificarResponse(BaseModel):
    study_id: str
    total_archivos: int
    clasificados: int
    omitidos: int
    fallback_otro: int
    por_fuente: dict[str, int]
    archivos: list[CorpusClasificacionItem]


# ── Datos estructurados por archivo (Sprint Drive B) ──────────────────────────

class CorpusDatosResponse(BaseModel):
    file_id: str
    study_id: str
    nombre_archivo: str
    rol_en_corpus: str | None
    esquema_version: str | None
    extraido_con_modelo: str | None
    extraido_en: str | None
    hash_sha256: str | None
    tiene_datos: bool
    datos_estructurados: dict | None
    template_si_vacio: dict | None


class CorpusDatosUpdateRequest(BaseModel):
    datos: dict


class CorpusDatosUpdateResponse(BaseModel):
    file_id: str
    datos_estructurados: dict
    warnings: list[str]
    esquema_version: str | None


# ── Consolidado del estudio (Sprint Drive E) ──────────────────────────────────

class ConsolidadoOverrideItem(BaseModel):
    path: str = Field(..., description="Dot-notation: 'poblacion.personas' o 'identificacion.nit'")
    valor: object
    nota: str | None = None


class ConsolidadoOverrideRequest(BaseModel):
    overrides: list[ConsolidadoOverrideItem]
    merge: bool = Field(True, description="Si false, reemplaza todos los overrides existentes")


class ConsolidadoOverrideResponse(BaseModel):
    study_id: str
    overrides: dict
    total: int


# ── CorpusExtraction ───────────────────────────────────────────────────────────

class ExtractionResponse(BaseModel):
    id: UUID
    study_id: UUID
    tipo_dato: str
    valor: str | None
    fuente_archivo: str | None
    confianza: float | None
    extraido_en: datetime

    model_config = {"from_attributes": True}


# ── StudyLocation ─────────────────────────────────────────────────────────────

class StudyLocationOut(BaseModel):
    id: UUID
    study_id: UUID
    nombre: str
    tipo: str
    lat: float
    lng: float
    descripcion: str | None
    fuente_archivo: str | None
    confianza: float | None
    extraido_en: datetime

    model_config = {"from_attributes": True}


# ── GISResult ─────────────────────────────────────────────────────────────────

class GISResultResponse(BaseModel):
    id: UUID
    study_id: UUID
    tipo_resultado: str
    parametros: dict | None
    resultado_json: dict | None
    archivo_path: str | None
    generado_en: datetime

    model_config = {"from_attributes": True}


# ── Report ────────────────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    id: UUID
    study_id: UUID
    version: int
    estado: str
    archivo_docx: str | None
    archivo_zip: str | None
    hash_docx: str | None
    drive_file_id: str | None
    drive_url: str | None
    generado_por: UUID | None
    aprobado_por: UUID | None
    parametros: dict | None
    error_msg: str | None
    generado_en: datetime
    aprobado_en: datetime | None
    exportado_en: datetime | None

    model_config = {"from_attributes": True}
