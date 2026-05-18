from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Literal

from app.studies.models import STUDY_STATES, CORPUS_FILE_TYPES, CORPUS_ROLES


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
    tamanio_bytes: int | None
    ruta_local: str | None
    estado: str
    error_msg: str | None
    sync_at: datetime
    procesado_en: datetime | None

    model_config = {"from_attributes": True}


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
