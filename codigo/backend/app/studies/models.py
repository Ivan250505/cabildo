import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, Numeric, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


STUDY_STATES = (
    "borrador", "sincronizando", "corpus_ok", "procesando",
    "listo_revision", "en_revision", "aprobado", "exportado", "error"
)

CORPUS_FILE_TYPES = ("pdf", "docx", "xlsx", "qgz", "gpkg", "shp", "jpg", "heic", "mp4", "mp3", "otro")

CORPUS_ROLES = (
    "solicitud_formal", "reglamento", "acta_eleccion", "acta_posesion",
    "autocenso_depurado", "autocenso", "censo_comunidad", "ficha_precampo",
    "rut_comunidad", "resena_historica", "mapa_territorial", "base_datos_dane",
    "acta_inicio", "cronograma", "diario_campo", "ficha_comision",
    "apuntes_reuniones", "arbol_riesgo", "cartografia_social", "registro_asistencia",
    "proyecto_qgis", "geopackage", "evidencia_foto",
    "concepto_etnologico", "borrador_acto_administrativo", "otro",
)


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_comunidad: Mapped[str] = mapped_column(String(300), nullable=False)
    pueblo_indigena: Mapped[str | None] = mapped_column(String(200))
    municipio: Mapped[str] = mapped_column(String(200), nullable=False)
    departamento: Mapped[str] = mapped_column(String(200), nullable=False)
    vereda: Mapped[str | None] = mapped_column(String(200))
    nit_comunidad: Mapped[str | None] = mapped_column(String(20))
    contrato_referencia: Mapped[str | None] = mapped_column(String(100))
    notas_adicionales: Mapped[str | None] = mapped_column(Text)

    lat: Mapped[float | None] = mapped_column(Numeric(10, 8))
    lng: Mapped[float | None] = mapped_column(Numeric(11, 8))

    estado: Mapped[str] = mapped_column(
        SAEnum(*STUDY_STATES, name="study_estado"), nullable=False, default="borrador"
    )
    error_msg: Mapped[str | None] = mapped_column(Text)

    url_drive_fase1: Mapped[str | None] = mapped_column(Text)
    url_drive_fase2: Mapped[str | None] = mapped_column(Text)
    url_drive_fase3: Mapped[str | None] = mapped_column(Text)
    drive_folder_id: Mapped[str | None] = mapped_column(String(200))

    buffer_metros: Mapped[int] = mapped_column(Integer, default=50)

    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    corpus: Mapped[list["StudyCorpus"]] = relationship(
        "StudyCorpus", back_populates="study", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="study", cascade="all, delete-orphan"
    )


class StudyCorpus(Base):
    __tablename__ = "study_corpus"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    fase: Mapped[str] = mapped_column(SAEnum("FASE1", "FASE2", "FASE3", name="corpus_fase"), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    drive_file_id: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(
        SAEnum(*CORPUS_FILE_TYPES, name="corpus_tipo"), nullable=False
    )
    rol_en_corpus: Mapped[str | None] = mapped_column(
        SAEnum(*CORPUS_ROLES, name="corpus_rol"), nullable=True
    )
    tamanio_bytes: Mapped[int | None] = mapped_column(Integer)
    ruta_local: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(
        SAEnum("pendiente", "descargado", "procesado", "error", name="corpus_estado"),
        default="pendiente",
    )
    error_msg: Mapped[str | None] = mapped_column(Text)
    sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    procesado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    study: Mapped["Study"] = relationship("Study", back_populates="corpus")


class CorpusExtraction(Base):
    __tablename__ = "corpus_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_dato: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[str | None] = mapped_column(Text)
    fuente_archivo: Mapped[str | None] = mapped_column(String(500))
    confianza: Mapped[float | None] = mapped_column(Numeric(4, 3))
    extraido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GISResult(Base):
    __tablename__ = "gis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_resultado: Mapped[str] = mapped_column(String(100), nullable=False)
    parametros: Mapped[dict | None] = mapped_column(JSON)
    resultado_json: Mapped[dict | None] = mapped_column(JSON)
    archivo_path: Mapped[str | None] = mapped_column(Text)
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estado: Mapped[str] = mapped_column(
        SAEnum("generando", "listo_revision", "en_revision", "aprobado", "exportado", "error",
               name="report_estado"),
        nullable=False, default="generando",
    )
    archivo_docx: Mapped[str | None] = mapped_column(Text)
    archivo_zip: Mapped[str | None] = mapped_column(Text)
    hash_docx: Mapped[str | None] = mapped_column(String(64))
    drive_file_id: Mapped[str | None] = mapped_column(String(200))
    drive_url: Mapped[str | None] = mapped_column(Text)
    generado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    aprobado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    parametros: Mapped[dict | None] = mapped_column(JSON)
    error_msg: Mapped[str | None] = mapped_column(Text)
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exportado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    study: Mapped["Study"] = relationship("Study", back_populates="reports")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    study_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("studies.id"))
    accion: Mapped[str] = mapped_column(String(200), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
