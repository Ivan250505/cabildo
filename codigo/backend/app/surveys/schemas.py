"""Schemas Pydantic del módulo de encuestas."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Catálogo (resumen) ─────────────────────────────────────────────────────────

class SurveyTypeSummary(BaseModel):
    id: UUID
    code: str
    nombre: str
    descripcion: str | None
    fase: str
    orden: int
    version: int
    activo: bool

    model_config = {"from_attributes": True}


class SurveyResponseSummary(BaseModel):
    """Vista resumen del estado de una encuesta para un estudio."""
    survey_type_code: str
    survey_type_nombre: str
    fase: str
    orden: int
    estado: str  # "no_iniciada" | "borrador" | "en_revision" | "completada"
    response_id: UUID | None
    updated_at: datetime | None
    completed_at: datetime | None


# ── Catálogo (detalle completo) ────────────────────────────────────────────────

class SurveyQuestionOut(BaseModel):
    id: UUID
    code: str
    label: str
    tipo_dato: str
    opciones: dict | list | None = None
    required: bool
    orden: int
    ayuda: str | None = None
    validaciones: dict | None = None

    model_config = {"from_attributes": True}


class SurveySectionOut(BaseModel):
    id: UUID
    code: str
    titulo: str
    descripcion: str | None = None
    orden: int
    questions: list[SurveyQuestionOut]

    model_config = {"from_attributes": True}


class SurveyTypeFull(BaseModel):
    id: UUID
    code: str
    nombre: str
    descripcion: str | None
    fase: str
    orden: int
    version: int
    sections: list[SurveySectionOut]

    model_config = {"from_attributes": True}


# ── Respuestas (instancias) ────────────────────────────────────────────────────

class SurveyAnswerOut(BaseModel):
    question_code: str
    question_id: UUID
    valor_texto: str | None = None
    valor_numero: float | None = None
    valor_fecha: datetime | None = None
    valor_bool: bool | None = None
    valor_json: Any | None = None


class SurveyPersonOut(BaseModel):
    id: UUID
    question_code: str
    orden: int
    nombre: str
    documento: str | None = None
    genero: str | None = None
    edad: int | None = None
    cargo: str | None = None
    ocupacion: str | None = None
    escolaridad: str | None = None
    contacto: str | None = None
    pueblo: str | None = None
    extra: dict | None = None


class SurveyEvidenceOut(BaseModel):
    id: UUID
    question_code: str
    categoria: str
    orden: int
    titulo: str
    descripcion: str | None = None


class SurveyJournalEntryOut(BaseModel):
    id: UUID
    question_code: str
    orden: int
    fecha: datetime | None = None
    titulo: str
    contenido: str | None = None
    tags: list[str] | None = None
    extra: dict | None = None


class SurveyResponseDetail(BaseModel):
    id: UUID
    study_id: UUID
    survey_type_code: str
    survey_type_nombre: str
    fase: str
    estado: str
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    pdf_url: str | None
    answers: list[SurveyAnswerOut]
    persons: list[SurveyPersonOut]
    evidences: list[SurveyEvidenceOut]
    journal_entries: list[SurveyJournalEntryOut] = []


# ── Inputs ─────────────────────────────────────────────────────────────────────

class AnswerInput(BaseModel):
    question_code: str = Field(..., max_length=100)
    valor_texto: str | None = None
    valor_numero: float | None = None
    valor_fecha: datetime | None = None
    valor_bool: bool | None = None
    valor_json: Any | None = None


class AnswersBulkInput(BaseModel):
    answers: list[AnswerInput]


class PersonInput(BaseModel):
    orden: int = 0
    nombre: str = Field(..., max_length=300)
    documento: str | None = Field(None, max_length=50)
    genero: str | None = Field(None, max_length=20)
    edad: int | None = None
    cargo: str | None = Field(None, max_length=200)
    ocupacion: str | None = Field(None, max_length=200)
    escolaridad: str | None = Field(None, max_length=100)
    contacto: str | None = Field(None, max_length=200)
    pueblo: str | None = Field(None, max_length=200)
    extra: dict | None = None


class PersonsReplaceInput(BaseModel):
    question_code: str
    persons: list[PersonInput]


class JournalEntryInput(BaseModel):
    orden: int = 0
    fecha: datetime | None = None
    titulo: str = Field("", max_length=300)
    contenido: str | None = None
    tags: list[str] | None = None
    extra: dict | None = None


class JournalEntriesReplaceInput(BaseModel):
    question_code: str
    entries: list[JournalEntryInput]
