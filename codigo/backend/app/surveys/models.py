"""Modelos del módulo de encuestas/formularios dinámicos.

Diseño genérico: catálogo (survey_type, survey_section, survey_question) define la
estructura de los formularios; las instancias (survey_response + survey_answer/person/evidence)
guardan las respuestas reales del usuario.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


SURVEY_FASES = ("FASE1", "FASE2")

SURVEY_TIPO_DATO = (
    "text", "textarea", "number", "date", "boolean",
    "select", "multiselect",
    "table_persons", "evidence_list", "journal_entries",
    "file",
)

SURVEY_RESPONSE_ESTADOS = ("borrador", "en_revision", "completada")

EVIDENCE_CATEGORIAS = ("amenaza", "consecuencia", "mitigacion", "fortaleza", "general")


# ── Catálogo ────────────────────────────────────────────────────────────────────

class SurveyType(Base):
    __tablename__ = "survey_type"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    fase: Mapped[str] = mapped_column(SAEnum(*SURVEY_FASES, name="survey_fase"), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sections: Mapped[list["SurveySection"]] = relationship(
        "SurveySection", back_populates="survey_type",
        cascade="all, delete-orphan", order_by="SurveySection.orden",
    )


class SurveySection(Base):
    __tablename__ = "survey_section"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_type.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    survey_type: Mapped["SurveyType"] = relationship("SurveyType", back_populates="sections")
    questions: Mapped[list["SurveyQuestion"]] = relationship(
        "SurveyQuestion", back_populates="section",
        cascade="all, delete-orphan", order_by="SurveyQuestion.orden",
    )

    __table_args__ = (UniqueConstraint("survey_type_id", "code", name="uq_survey_section_type_code"),)


class SurveyQuestion(Base):
    __tablename__ = "survey_question"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_section.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_dato: Mapped[str] = mapped_column(
        SAEnum(*SURVEY_TIPO_DATO, name="survey_tipo_dato"), nullable=False,
    )
    opciones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ayuda: Mapped[str | None] = mapped_column(Text)
    validaciones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    section: Mapped["SurveySection"] = relationship("SurveySection", back_populates="questions")

    __table_args__ = (UniqueConstraint("section_id", "code", name="uq_survey_question_section_code"),)


# ── Instancias ──────────────────────────────────────────────────────────────────

class SurveyResponse(Base):
    __tablename__ = "survey_response"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    survey_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_type.id"), nullable=False, index=True,
    )
    estado: Mapped[str] = mapped_column(
        SAEnum(*SURVEY_RESPONSE_ESTADOS, name="survey_response_estado"),
        nullable=False, default="borrador",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_url: Mapped[str | None] = mapped_column(Text)
    corpus_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("study_corpus.id", ondelete="SET NULL"), nullable=True,
    )

    answers: Mapped[list["SurveyAnswer"]] = relationship(
        "SurveyAnswer", back_populates="response", cascade="all, delete-orphan",
    )
    persons: Mapped[list["SurveyPerson"]] = relationship(
        "SurveyPerson", back_populates="response", cascade="all, delete-orphan",
    )
    evidences: Mapped[list["SurveyEvidence"]] = relationship(
        "SurveyEvidence", back_populates="response", cascade="all, delete-orphan",
    )
    journal_entries: Mapped[list["SurveyJournalEntry"]] = relationship(
        "SurveyJournalEntry", back_populates="response", cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("study_id", "survey_type_id", name="uq_survey_response_study_type"),
    )


class SurveyAnswer(Base):
    __tablename__ = "survey_answer"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_response.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    valor_texto: Mapped[str | None] = mapped_column(Text)
    valor_numero: Mapped[float | None] = mapped_column(Numeric)
    valor_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valor_bool: Mapped[bool | None] = mapped_column(Boolean)
    valor_json: Mapped[dict | list | None] = mapped_column(JSONB)

    response: Mapped["SurveyResponse"] = relationship("SurveyResponse", back_populates="answers")

    __table_args__ = (
        UniqueConstraint("response_id", "question_id", name="uq_survey_answer_response_question"),
    )


class SurveyPerson(Base):
    """Filas de tablas de personas (autocenso, actores clave, registro asistencia, etc.)."""
    __tablename__ = "survey_person"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_response.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(50))
    genero: Mapped[str | None] = mapped_column(String(20))
    edad: Mapped[int | None] = mapped_column(Integer)
    cargo: Mapped[str | None] = mapped_column(String(200))
    ocupacion: Mapped[str | None] = mapped_column(String(200))
    escolaridad: Mapped[str | None] = mapped_column(String(100))
    contacto: Mapped[str | None] = mapped_column(String(200))
    pueblo: Mapped[str | None] = mapped_column(String(200))
    extra: Mapped[dict | None] = mapped_column(JSONB)

    response: Mapped["SurveyResponse"] = relationship("SurveyResponse", back_populates="persons")


class SurveyEvidence(Base):
    """Filas de listas de evidencias (árbol de riesgos, evidencias de ficha comisión, etc.)."""
    __tablename__ = "survey_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_response.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    categoria: Mapped[str] = mapped_column(
        SAEnum(*EVIDENCE_CATEGORIAS, name="survey_evidence_categoria"),
        nullable=False, default="general",
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)

    response: Mapped["SurveyResponse"] = relationship("SurveyResponse", back_populates="evidences")


class SurveyJournalEntry(Base):
    """Entradas tipo blog/timeline para encuestas narrativas (Diario de Campo, Apuntes)."""
    __tablename__ = "survey_journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_response.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    titulo: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    contenido: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSONB)
    extra: Mapped[dict | None] = mapped_column(JSONB)

    response: Mapped["SurveyResponse"] = relationship("SurveyResponse", back_populates="journal_entries")
