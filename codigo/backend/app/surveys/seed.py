"""Seed idempotente del catálogo de encuestas.

Llamado desde el lifespan de main.py al arrancar. Inserta los 8 tipos de encuesta
si no existen. Las secciones y preguntas se llenan progresivamente por sprint:
- Sprint 01: ficha_precampo
- Sprint 03: acta_inicio, registro_asistencia
- Sprint 04: ficha_comision
- Sprint 05: diario_campo, apuntes_reuniones
- Sprint 06: arbol_riesgos
- Sprint 07: autocenso
"""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.surveys.models import SurveyQuestion, SurveySection, SurveyType

logger = logging.getLogger(__name__)


# Definición declarativa del catálogo. Para agregar/quitar encuestas, editar acá.
SURVEY_TYPES_SEED: list[dict] = [
    {
        "code": "ficha_precampo",
        "nombre": "Ficha de Pre-campo",
        "descripcion": "Instrumento preparatorio diligenciado antes de la visita de campo.",
        "fase": "FASE1",
        "orden": 1,
    },
    {
        "code": "autocenso",
        "nombre": "Autocenso / Censo Comunidad",
        "descripcion": "Listado nominal de personas que integran la comunidad indígena.",
        "fase": "FASE1",
        "orden": 2,
    },
    {
        "code": "acta_inicio",
        "nombre": "Acta de Inicio",
        "descripcion": "Acta de concertación entre el equipo investigador y la comunidad.",
        "fase": "FASE2",
        "orden": 1,
    },
    {
        "code": "registro_asistencia",
        "nombre": "Registro de Asistencia",
        "descripcion": "Listado formal de participantes en actividades de campo.",
        "fase": "FASE2",
        "orden": 2,
    },
    {
        "code": "ficha_comision",
        "nombre": "Ficha de Comisión",
        "descripcion": "Instrumento técnico oficial diligenciado tras el trabajo de campo.",
        "fase": "FASE2",
        "orden": 3,
    },
    {
        "code": "diario_campo",
        "nombre": "Diario de Campo",
        "descripcion": "Registro etnográfico diario del investigador durante la visita.",
        "fase": "FASE2",
        "orden": 4,
    },
    {
        "code": "apuntes_reuniones",
        "nombre": "Apuntes de Reuniones",
        "descripcion": "Notas cualitativas de grupos focales y conversaciones informales.",
        "fase": "FASE2",
        "orden": 5,
    },
    {
        "code": "arbol_riesgos",
        "nombre": "Árbol de Riesgos",
        "descripcion": "Diagnóstico participativo de amenazas, consecuencias, mitigaciones y fortalezas.",
        "fase": "FASE2",
        "orden": 6,
    },
]


async def seed_survey_catalog(db: AsyncSession) -> None:
    """Inserta los survey_type que no existan. Idempotente — corre en cada arranque."""
    result = await db.execute(select(SurveyType.code))
    existing_codes = {row[0] for row in result.all()}

    nuevos = 0
    for entry in SURVEY_TYPES_SEED:
        if entry["code"] in existing_codes:
            continue
        db.add(SurveyType(
            code=entry["code"],
            nombre=entry["nombre"],
            descripcion=entry.get("descripcion"),
            fase=entry["fase"],
            orden=entry["orden"],
            version=1,
            activo=True,
        ))
        nuevos += 1

    if nuevos:
        logger.info("Seed encuestas: %d tipos insertados", nuevos)
    else:
        logger.debug("Seed encuestas: catálogo ya estaba completo")


# ── Helper genérico para sembrar secciones + preguntas ──────────────────────────

async def _seed_type_structure(
    db: AsyncSession,
    type_code: str,
    sections_data: list[dict],
) -> None:
    """Inserta secciones y preguntas de un survey_type si aún no existen.

    sections_data: lista de {code, titulo, descripcion?, orden, questions: [...]}.
    Cada question: {code, label, tipo_dato, opciones?, required?, orden, ayuda?, validaciones?}.
    Idempotente: compara por (survey_type_id, section.code) y (section_id, question.code).
    """
    type_row = (await db.execute(select(SurveyType).where(SurveyType.code == type_code))).scalar_one_or_none()
    if not type_row:
        logger.warning("Seed de %s: tipo no existe en catálogo, salteando", type_code)
        return

    existing_sections = await db.execute(
        select(SurveySection).where(SurveySection.survey_type_id == type_row.id)
    )
    sections_by_code: dict[str, SurveySection] = {s.code: s for s in existing_sections.scalars().all()}

    nuevas_secs = 0
    nuevas_preg = 0

    for sec_data in sections_data:
        sec = sections_by_code.get(sec_data["code"])
        if not sec:
            sec = SurveySection(
                survey_type_id=type_row.id,
                code=sec_data["code"],
                titulo=sec_data["titulo"],
                descripcion=sec_data.get("descripcion"),
                orden=sec_data["orden"],
            )
            db.add(sec)
            await db.flush()
            sections_by_code[sec.code] = sec
            nuevas_secs += 1

        # Cargar preguntas existentes de esta sección
        q_rows = await db.execute(select(SurveyQuestion).where(SurveyQuestion.section_id == sec.id))
        existing_q: dict[str, SurveyQuestion] = {q.code: q for q in q_rows.scalars().all()}

        for q_data in sec_data.get("questions", []):
            if q_data["code"] in existing_q:
                continue
            db.add(SurveyQuestion(
                section_id=sec.id,
                code=q_data["code"],
                label=q_data["label"],
                tipo_dato=q_data["tipo_dato"],
                opciones=q_data.get("opciones"),
                required=q_data.get("required", False),
                orden=q_data["orden"],
                ayuda=q_data.get("ayuda"),
                validaciones=q_data.get("validaciones"),
            ))
            nuevas_preg += 1

    if nuevas_secs or nuevas_preg:
        logger.info("Seed %s: %d secciones, %d preguntas insertadas", type_code, nuevas_secs, nuevas_preg)


# ── F1-01 Ficha de Pre-campo ────────────────────────────────────────────────────

FICHA_PRECAMPO_SECTIONS: list[dict] = [
    {
        "code": "identificacion",
        "titulo": "§1 — Identificación de la comunidad",
        "orden": 1,
        "questions": [
            {"code": "nombre_oficial", "label": "Nombre oficial de la comunidad", "tipo_dato": "text", "required": True, "orden": 1},
            {"code": "autodenominacion", "label": "Autodenominación (en lengua propia)", "tipo_dato": "text", "orden": 2},
            {"code": "pueblo_indigena", "label": "Pueblo indígena de pertenencia", "tipo_dato": "text", "required": True, "orden": 3},
            {"code": "nit", "label": "NIT de la comunidad", "tipo_dato": "text", "orden": 4},
            {"code": "forma_organizacion", "label": "Forma de organización",
             "tipo_dato": "select", "orden": 5,
             "opciones": ["Cabildo", "Consejo Indígena", "Asociación", "Resguardo", "Otra"]},
            {"code": "fecha_constitucion", "label": "Fecha de constitución jurídica", "tipo_dato": "date", "orden": 6},
        ],
    },
    {
        "code": "actores_clave",
        "titulo": "§2 — Actores clave de la comunidad",
        "descripcion": "Gobernador/a, Cacique, Vicegobernador/a, Secretaria, Tesorera, etc.",
        "orden": 2,
        "questions": [
            {"code": "actores", "label": "Listado de actores clave (autoridades y contactos)",
             "tipo_dato": "table_persons", "orden": 1,
             "validaciones": {"fields": ["nombre", "documento", "cargo", "contacto"]},
             "ayuda": "Agrega cada autoridad con su nombre, número de documento, cargo y contacto telefónico/email"},
        ],
    },
    {
        "code": "ubicacion",
        "titulo": "§3 — Ubicación y territorio",
        "orden": 3,
        "questions": [
            {"code": "departamento", "label": "Departamento", "tipo_dato": "text", "required": True, "orden": 1},
            {"code": "municipio", "label": "Municipio", "tipo_dato": "text", "required": True, "orden": 2},
            {"code": "vereda", "label": "Vereda / Corregimiento", "tipo_dato": "text", "orden": 3},
            {"code": "direccion", "label": "Dirección o referencia del predio", "tipo_dato": "text", "orden": 4},
            {"code": "lat", "label": "Latitud (grados decimales)", "tipo_dato": "number", "orden": 5,
             "ayuda": "Ejemplo: 1.3744"},
            {"code": "lng", "label": "Longitud (grados decimales)", "tipo_dato": "number", "orden": 6,
             "ayuda": "Ejemplo: -75.4000"},
            {"code": "plus_code", "label": "Plus Code (opcional)", "tipo_dato": "text", "orden": 7,
             "ayuda": "Ej: 9J72+5V Milán"},
            {"code": "altitud_msnm", "label": "Altitud (m.s.n.m.)", "tipo_dato": "number", "orden": 8},
            {"code": "area_predio_ha", "label": "Área del predio (hectáreas)", "tipo_dato": "number", "orden": 9},
            {"code": "tipo_tenencia", "label": "Tipo de tenencia del predio",
             "tipo_dato": "select", "orden": 10,
             "opciones": ["Propiedad colectiva", "Comodato", "Donación informal", "Donación con escritura", "Territorio ancestral reclamado", "Otra"]},
            {"code": "contexto_etcr", "label": "Contexto territorial especial (ETCR, ZRC, etc.)", "tipo_dato": "textarea", "orden": 11},
            {"code": "categoria_territorial", "label": "Categoría territorial",
             "tipo_dato": "select", "orden": 12,
             "opciones": ["Rural disperso", "Rural concentrado", "Urbano", "Mixto"]},
            {"code": "clima", "label": "Clima predominante", "tipo_dato": "text", "orden": 13},
        ],
    },
    {
        "code": "origen_estudio",
        "titulo": "§4 — Origen y justificación del estudio",
        "orden": 4,
        "questions": [
            {"code": "entidad_ejecutora", "label": "Entidad ejecutora", "tipo_dato": "text", "required": True, "orden": 1,
             "ayuda": "Ej: Universidad de Cartagena"},
            {"code": "contrato_referencia", "label": "Número de contrato", "tipo_dato": "text", "orden": 2,
             "ayuda": "Ej: UC-CPS-MINTERIOR-023-2026"},
            {"code": "coordinadora", "label": "Coordinadora o responsable institucional", "tipo_dato": "text", "orden": 3},
            {"code": "profesional_responsable", "label": "Profesional responsable del estudio", "tipo_dato": "text", "orden": 4},
            {"code": "objetivo_estudio", "label": "Objetivo del estudio", "tipo_dato": "textarea", "required": True, "orden": 5},
            {"code": "antecedentes_tramite", "label": "Antecedentes del trámite (solicitudes previas, peticiones, derechos de petición)",
             "tipo_dato": "textarea", "orden": 6},
        ],
    },
    {
        "code": "criterios_seleccion",
        "titulo": "§5 — Criterios de selección del caso",
        "descripcion": "Razones por las que se priorizó esta comunidad para el estudio",
        "orden": 5,
        "questions": [
            {"code": "criterios", "label": "Criterios aplicados", "tipo_dato": "textarea", "orden": 1,
             "ayuda": "Ej: pobreza extrema, falta de registro, solicitud comunitaria, riesgo territorial"},
            {"code": "priorizacion_institucional", "label": "Priorización institucional / entidad solicitante", "tipo_dato": "text", "orden": 2},
        ],
    },
    {
        "code": "composicion",
        "titulo": "§6 — Análisis de composición del grupo",
        "orden": 6,
        "questions": [
            {"code": "n_familias_actual", "label": "Número actual de familias", "tipo_dato": "number", "orden": 1},
            {"code": "n_personas_actual", "label": "Número actual de personas", "tipo_dato": "number", "orden": 2},
            {"code": "fuente_demografica", "label": "Fuente del dato demográfico",
             "tipo_dato": "select", "orden": 3,
             "opciones": ["Autocenso comunitario", "Censo cabildo", "DANE", "Otra"]},
            {"code": "fecha_dato_demografico", "label": "Fecha del dato demográfico", "tipo_dato": "date", "orden": 4},
            {"code": "evolucion_demografica", "label": "Evolución demográfica histórica",
             "tipo_dato": "textarea", "orden": 5,
             "ayuda": "Describe la evolución año por año si está disponible (ej: 2016: 15 hogares / 28 personas; 2023: 37 fam / 102 pers; 2026: 14 fam / 31 pers depurado)"},
            {"code": "estructura_etaria", "label": "Estructura por edad y género (descripción)", "tipo_dato": "textarea", "orden": 6},
            {"code": "discrepancia_poblacion", "label": "Discrepancias entre fuentes (si las hay)", "tipo_dato": "textarea", "orden": 7},
        ],
    },
    {
        "code": "etnografia",
        "titulo": "§7 — Datos etnográficos e historiográficos",
        "orden": 7,
        "questions": [
            {"code": "historia_oral", "label": "Resumen de historia oral (origen, mito, fundación)",
             "tipo_dato": "textarea", "orden": 1,
             "ayuda": "Lugar ancestral, mito de origen, clanes, asentamiento, despojo, reubicación"},
            {"code": "cosmovision_basica", "label": "Cosmovisión básica del pueblo", "tipo_dato": "textarea", "orden": 2,
             "ayuda": "Ej: 'Gente de Centro', hijos del tabaco/coca/yuca dulce, etc."},
            {"code": "clanes_principales", "label": "Clanes principales del pueblo (con traducción si está)", "tipo_dato": "textarea", "orden": 3},
            {"code": "lengua_indigena", "label": "Lengua indígena propia", "tipo_dato": "text", "orden": 4},
            {"code": "nivel_uso_lengua", "label": "Nivel de uso de la lengua",
             "tipo_dato": "select", "orden": 5,
             "opciones": ["Hablada por todos", "Hablada por mayores", "En recuperación", "Casi perdida", "Solo en rituales"]},
            {"code": "practicas_culturales_clave", "label": "Prácticas culturales clave", "tipo_dato": "textarea", "orden": 6,
             "ayuda": "Mambeo, ceremonias, calendario ecológico, rituales, etc."},
        ],
    },
    {
        "code": "relaciones_institucionales",
        "titulo": "§8 — Relaciones institucionales conocidas",
        "descripcion": "Entidades públicas/privadas/organizativas que tienen relación con la comunidad",
        "orden": 8,
        "questions": [
            {"code": "instituciones", "label": "Listado de instituciones relevantes",
             "tipo_dato": "table_persons", "orden": 1,
             "validaciones": {"fields": ["nombre", "cargo", "contacto", "pueblo"]},
             "ayuda": "Usa el campo 'nombre' para la institución, 'cargo' para el tipo (Alcaldía/ONG/Universidad/etc.), 'pueblo' para indicar el estado de la relación (activa, pendiente, conflicto)"},
            {"code": "registro_mininterior", "label": "¿Tiene registro ante el Ministerio del Interior?",
             "tipo_dato": "boolean", "orden": 2},
            {"code": "trámites_pendientes", "label": "Trámites pendientes con entidades", "tipo_dato": "textarea", "orden": 3},
        ],
    },
    {
        "code": "anexos",
        "titulo": "§9 — Anexos identificados del acervo",
        "descripcion": "Documentos disponibles que se adjuntarán al estudio",
        "orden": 9,
        "questions": [
            {"code": "anexos_disponibles", "label": "Anexos disponibles del acervo",
             "tipo_dato": "multiselect", "orden": 1,
             "opciones": [
                 "Reglamento Interno",
                 "Acta de Elección",
                 "Acta de Posesión",
                 "Autocenso depurado",
                 "Censo histórico",
                 "RUT comunidad",
                 "CC de autoridades",
                 "Reseña histórica",
                 "Mapa territorial",
                 "Solicitud formal a Ministerio",
                 "Solicitud a ACOTRI u organización",
                 "Otro",
             ]},
            {"code": "notas_anexos", "label": "Notas sobre los anexos", "tipo_dato": "textarea", "orden": 2},
        ],
    },
]


async def seed_ficha_precampo(db: AsyncSession) -> None:
    """Sembrar las secciones y preguntas de Ficha de Pre-campo (F1-01)."""
    await _seed_type_structure(db, "ficha_precampo", FICHA_PRECAMPO_SECTIONS)


# ── F2-04 Acta de Inicio ───────────────────────────────────────────────────────

ACTA_INICIO_SECTIONS: list[dict] = [
    {
        "code": "encabezado",
        "titulo": "§1 — Encabezado del acta",
        "orden": 1,
        "questions": [
            {"code": "fecha_acta", "label": "Fecha del acta", "tipo_dato": "date", "required": True, "orden": 1},
            {"code": "lugar_acta", "label": "Lugar de la concertación", "tipo_dato": "text", "required": True, "orden": 2,
             "ayuda": "Ej: Maloka Comunitaria, Vereda Semillas de Paz"},
            {"code": "contrato_referencia", "label": "Contrato o convenio de referencia", "tipo_dato": "text", "orden": 3,
             "ayuda": "Ej: UC-CPS-MINTERIOR-023-2026"},
            {"code": "entidad_ejecutora", "label": "Entidad ejecutora", "tipo_dato": "text", "orden": 4},
        ],
    },
    {
        "code": "objeto_compromisos",
        "titulo": "§2 — Objeto y compromisos",
        "orden": 2,
        "questions": [
            {"code": "objeto_concertacion", "label": "Objeto de la concertación", "tipo_dato": "textarea", "required": True, "orden": 1,
             "ayuda": "Propósito del acta: por qué se realiza el estudio etnológico"},
            {"code": "metodologia", "label": "Metodología acordada",
             "tipo_dato": "multiselect", "orden": 2,
             "opciones": [
                 "Investigación de Acción Participativa (IAP)",
                 "Grupos focales",
                 "Entrevistas semi-estructuradas",
                 "Observación participante",
                 "Recorrido territorial",
                 "Revisión documental",
                 "Cartografía social",
                 "Árbol de problemas",
             ]},
            {"code": "compromisos_equipo", "label": "Compromisos del equipo investigador", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Ej: confidencialidad, retorno de información, respeto a usos y costumbres"},
            {"code": "compromisos_comunidad", "label": "Compromisos de la comunidad", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Ej: asistencia a reuniones, participación en talleres, facilitar acceso al territorio"},
            {"code": "actividades_acordadas", "label": "Actividades acordadas y cronograma", "tipo_dato": "textarea", "orden": 5},
            {"code": "consentimiento_informado", "label": "¿La comunidad otorga consentimiento informado para el estudio?", "tipo_dato": "boolean", "orden": 6, "required": True},
        ],
    },
    {
        "code": "firmantes",
        "titulo": "§3 — Autoridades firmantes",
        "descripcion": "Autoridades tradicionales que firman el acta en representación de la comunidad",
        "orden": 3,
        "questions": [
            {"code": "autoridades", "label": "Listado de autoridades firmantes",
             "tipo_dato": "table_persons", "orden": 1,
             "validaciones": {"fields": ["nombre", "documento", "cargo", "pueblo"]},
             "ayuda": "Nombre completo, número de documento, cargo en el cabildo, pueblo de origen si aplica"},
            {"code": "equipo_firmante", "label": "Equipo investigador firmante",
             "tipo_dato": "table_persons", "orden": 2,
             "validaciones": {"fields": ["nombre", "documento", "cargo", "contacto"]}},
            {"code": "observaciones_acta", "label": "Observaciones del acta", "tipo_dato": "textarea", "orden": 3},
        ],
    },
]


async def seed_acta_inicio(db: AsyncSession) -> None:
    """Sembrar Acta de Inicio (F2-04)."""
    await _seed_type_structure(db, "acta_inicio", ACTA_INICIO_SECTIONS)


# ── F2-03 Registro de Asistencia ───────────────────────────────────────────────

REGISTRO_ASISTENCIA_SECTIONS: list[dict] = [
    {
        "code": "datos_actividad",
        "titulo": "§1 — Datos de la actividad",
        "orden": 1,
        "questions": [
            {"code": "fecha_actividad", "label": "Fecha de la actividad", "tipo_dato": "date", "required": True, "orden": 1},
            {"code": "hora_inicio", "label": "Hora de inicio", "tipo_dato": "text", "orden": 2,
             "ayuda": "Formato 24h, ej: 08:00"},
            {"code": "hora_fin", "label": "Hora de finalización", "tipo_dato": "text", "orden": 3},
            {"code": "lugar", "label": "Lugar", "tipo_dato": "text", "required": True, "orden": 4},
            {"code": "tipo_actividad", "label": "Tipo de actividad",
             "tipo_dato": "select", "required": True, "orden": 5,
             "opciones": [
                 "Reunión comunitaria",
                 "Taller",
                 "Grupo focal",
                 "Asamblea general",
                 "Entrevista colectiva",
                 "Recorrido territorial",
                 "Ritual / ceremonia",
                 "Otra",
             ]},
            {"code": "facilitador", "label": "Facilitador o responsable", "tipo_dato": "text", "orden": 6},
            {"code": "objetivo", "label": "Objetivo de la actividad", "tipo_dato": "textarea", "orden": 7},
        ],
    },
    {
        "code": "asistentes",
        "titulo": "§2 — Asistentes",
        "descripcion": "Listado de personas que asistieron y firmaron",
        "orden": 2,
        "questions": [
            {"code": "asistentes_lista", "label": "Listado de asistentes",
             "tipo_dato": "table_persons", "orden": 1,
             "validaciones": {"fields": ["nombre", "documento", "genero", "cargo", "pueblo"]},
             "ayuda": "Nombre completo, documento, género (F/M/Otro), cargo en la comunidad, pueblo de origen"},
            {"code": "total_asistentes", "label": "Total de asistentes (contado)", "tipo_dato": "number", "orden": 2},
            {"code": "porcentaje_participacion", "label": "Porcentaje aproximado sobre la comunidad", "tipo_dato": "number", "orden": 3,
             "ayuda": "0 a 100"},
        ],
    },
    {
        "code": "cierre",
        "titulo": "§3 — Observaciones y cierre",
        "orden": 3,
        "questions": [
            {"code": "temas_tratados", "label": "Temas tratados", "tipo_dato": "textarea", "orden": 1},
            {"code": "acuerdos", "label": "Acuerdos alcanzados", "tipo_dato": "textarea", "orden": 2},
            {"code": "observaciones", "label": "Observaciones generales", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Dinámica de la reunión, dificultades, hallazgos imprevistos"},
        ],
    },
]


async def seed_registro_asistencia(db: AsyncSession) -> None:
    """Sembrar Registro de Asistencia (F2-03)."""
    await _seed_type_structure(db, "registro_asistencia", REGISTRO_ASISTENCIA_SECTIONS)


# ── F2-01 Ficha de Comisión ────────────────────────────────────────────────────
# El instrumento técnico más completo de FASE 2. Estructura:
#   §1 Encabezado institucional
#   §2 Actividades ejecutadas
#   §3 Actores contactados
#   §4.1 Dimensión Subjetiva
#   §4.2 Dimensión Intrarelacional
#   §4.3 Dimensión Interrelacional
#   §4.4 Dimensión Existencial / Prospectiva
#   §4.5 Dimensión de Riesgo
#   §5 Evidencias recolectadas
#   §6 Balance del profesional

FICHA_COMISION_SECTIONS: list[dict] = [
    {
        "code": "encabezado_institucional",
        "titulo": "§1 — Encabezado institucional",
        "orden": 1,
        "questions": [
            {"code": "nombre_proyecto", "label": "Nombre del proyecto / estudio", "tipo_dato": "text", "required": True, "orden": 1},
            {"code": "contrato_referencia", "label": "Número de contrato", "tipo_dato": "text", "orden": 2,
             "ayuda": "Ej: UC-CPS-MINTERIOR-023-2026"},
            {"code": "entidad_ejecutora", "label": "Entidad ejecutora", "tipo_dato": "text", "orden": 3},
            {"code": "profesional_responsable", "label": "Profesional responsable", "tipo_dato": "text", "required": True, "orden": 4},
            {"code": "apoyo_profesional", "label": "Apoyo profesional / co-investigador", "tipo_dato": "text", "orden": 5},
            {"code": "coordinadora", "label": "Coordinadora institucional", "tipo_dato": "text", "orden": 6},
            {"code": "fecha_inicio_visita", "label": "Fecha de inicio de la visita", "tipo_dato": "date", "required": True, "orden": 7},
            {"code": "fecha_fin_visita", "label": "Fecha de finalización de la visita", "tipo_dato": "date", "required": True, "orden": 8},
            {"code": "rutas_transporte", "label": "Rutas y medios de transporte usados", "tipo_dato": "textarea", "orden": 9,
             "ayuda": "Ej: Florencia → La Tigrera (vehículo, 1h) → La Montañita (moto, 1.5h) → Semillas de Paz (a pie, 2h)"},
            {"code": "duracion_total_h", "label": "Duración total efectiva en campo (horas)", "tipo_dato": "number", "orden": 10},
        ],
    },
    {
        "code": "actividades",
        "titulo": "§2 — Actividades ejecutadas",
        "descripcion": "Actividades realizadas durante la visita de campo con fecha, lugar y participantes",
        "orden": 2,
        "questions": [
            {"code": "tipos_actividades", "label": "Tipos de actividades ejecutadas",
             "tipo_dato": "multiselect", "orden": 1,
             "opciones": [
                 "Reunión comunitaria",
                 "Asamblea general",
                 "Grupo focal",
                 "Entrevista individual",
                 "Entrevista colectiva",
                 "Observación participante",
                 "Recorrido territorial",
                 "Cartografía social",
                 "Árbol de problemas",
                 "Ritual / ceremonia",
                 "Revisión documental",
             ]},
            {"code": "descripcion_actividades", "label": "Descripción detallada de actividades", "tipo_dato": "textarea", "orden": 2,
             "ayuda": "Por cada actividad: qué, cuándo, dónde, quiénes participaron, qué resultados"},
            {"code": "cronograma_real", "label": "Cronograma real cumplido", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Día por día, hora por hora si es posible"},
            {"code": "ajustes_metodologia", "label": "Ajustes a la metodología durante el campo", "tipo_dato": "textarea", "orden": 4},
        ],
    },
    {
        "code": "actores_contactados",
        "titulo": "§3 — Actores contactados",
        "descripcion": "Personas con quienes se interactuó durante el trabajo de campo",
        "orden": 3,
        "questions": [
            {"code": "actores", "label": "Listado de actores contactados",
             "tipo_dato": "table_persons", "orden": 1,
             "validaciones": {"fields": ["nombre", "documento", "cargo", "pueblo", "contacto"]},
             "ayuda": "Nombre completo, documento, cargo en la comunidad, pueblo, tipo de contacto (presencial/telefónico/escrito)"},
            {"code": "n_actores_total", "label": "Total de personas contactadas", "tipo_dato": "number", "orden": 2},
            {"code": "porcentaje_comunidad", "label": "Porcentaje aproximado sobre el total de la comunidad", "tipo_dato": "number", "orden": 3},
        ],
    },
    # ── §4 DIMENSIONES (5 sub-secciones presentadas como secciones consecutivas) ──
    {
        "code": "dim_subjetiva",
        "titulo": "§4.1 — Dimensión Subjetiva",
        "descripcion": "Autodenominación, cosmogonía, identidad, tipos de afiliación",
        "orden": 4,
        "questions": [
            {"code": "autodenominacion_campo", "label": "Autodenominación confirmada en campo", "tipo_dato": "text", "orden": 1},
            {"code": "cosmogonia_observada", "label": "Cosmogonía / mito de origen observado", "tipo_dato": "textarea", "orden": 2,
             "ayuda": "Lo que la comunidad relata sobre su origen, lugares sagrados, símbolos identitarios"},
            {"code": "tipos_afiliacion", "label": "Tipos de afiliación dentro del grupo", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Ej: fundadores, adherentes, miembros por matrimonio, alianzas interétnicas"},
            {"code": "capas_reconocimiento", "label": "Capas de reconocimiento (interno → externo)", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Cómo se reconocen entre ellos, ante otras comunidades, ante el Estado"},
            {"code": "elementos_identitarios", "label": "Elementos identitarios destacados", "tipo_dato": "textarea", "orden": 5,
             "ayuda": "Lengua, vestido, objetos sagrados, prácticas rituales, alimentación"},
            {"code": "uso_lengua_observado", "label": "Uso observado de la lengua propia", "tipo_dato": "textarea", "orden": 6},
        ],
    },
    {
        "code": "dim_intrarelacional",
        "titulo": "§4.2 — Dimensión Intrarelacional",
        "descripcion": "Cohesión interna, gobierno propio, instancias de decisión",
        "orden": 5,
        "questions": [
            {"code": "instancias_decision", "label": "Instancias de decisión (orden y función)", "tipo_dato": "textarea", "orden": 1,
             "ayuda": "Ej: Mambeadero (primaria/nocturna) → Asamblea General → Junta Directiva"},
            {"code": "cargos_funciones", "label": "Cargos y funciones observadas en campo", "tipo_dato": "textarea", "orden": 2},
            {"code": "dinamica_reunion", "label": "Dinámica de las reuniones (cómo se decide)", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Quórum, votación, consenso, tiempos, lugar"},
            {"code": "sanciones_aplicadas", "label": "Sanciones aplicadas o ejemplos de aplicación", "tipo_dato": "textarea", "orden": 4},
            {"code": "normas_convivencia", "label": "Normas de convivencia observadas", "tipo_dato": "textarea", "orden": 5},
            {"code": "tensiones_internas", "label": "Tensiones internas detectadas", "tipo_dato": "textarea", "orden": 6,
             "ayuda": "Disputas, facciones, conflictos generacionales o de género"},
            {"code": "participacion_reuniones", "label": "Participación en reuniones (asistencia real)", "tipo_dato": "textarea", "orden": 7},
        ],
    },
    {
        "code": "dim_interrelacional",
        "titulo": "§4.3 — Dimensión Interrelacional",
        "descripcion": "Relaciones con instituciones, organizaciones indígenas, vecinos y otros pueblos",
        "orden": 6,
        "questions": [
            {"code": "rel_administraciones", "label": "Relación con administraciones públicas", "tipo_dato": "textarea", "orden": 1,
             "ayuda": "Alcaldía, Gobernación, Ministerio del Interior, ANT, CORPOAMAZONIA, ICBF, etc."},
            {"code": "rel_organizaciones_indigenas", "label": "Relación con organizaciones indígenas", "tipo_dato": "textarea", "orden": 2,
             "ayuda": "ACOTRI, OPIAC, ONIC, regionales, etc."},
            {"code": "rel_vecinos_colonos", "label": "Relación con vecinos / colonos", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Convivencia, conflictos, discriminación, alianzas"},
            {"code": "rel_otros_pueblos", "label": "Relación con otros pueblos indígenas", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Ej: pacto Murui-Coreguaje, intercambios culturales, alianzas matrimoniales"},
            {"code": "rel_academia_ongs", "label": "Relación con academia / ONGs / iglesias", "tipo_dato": "textarea", "orden": 5},
            {"code": "tramites_estado", "label": "Estado actual de trámites institucionales", "tipo_dato": "textarea", "orden": 6,
             "ayuda": "Registro Mininterior, ANT, Acto Administrativo, etc."},
        ],
    },
    {
        "code": "dim_existencial",
        "titulo": "§4.4 — Dimensión Existencial / Prospectiva",
        "descripcion": "Prioridades, plan de vida, sueños comunitarios",
        "orden": 7,
        "questions": [
            {"code": "prioridades_comunidad", "label": "Prioridades identificadas por la comunidad", "tipo_dato": "textarea", "orden": 1,
             "ayuda": "En orden de importancia según la propia comunidad"},
            {"code": "plan_vida_estado", "label": "Estado del Plan de Vida",
             "tipo_dato": "select", "orden": 2,
             "opciones": [
                 "Sin iniciar",
                 "En elaboración con apoyo externo",
                 "Elaborado, sin implementar",
                 "En implementación",
                 "Completado y vigente",
             ]},
            {"code": "sueños_proyectos", "label": "Sueños y proyectos específicos", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Ej: maloka grande, escuela propia, puesto de salud, ampliación territorial"},
            {"code": "procesos_curso", "label": "Procesos en curso al momento de la visita", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Depuración censal, regularización de documentos, trámites institucionales"},
            {"code": "retorno_dispersos", "label": "Situación de miembros dispersos / retorno", "tipo_dato": "textarea", "orden": 5},
        ],
    },
    {
        "code": "dim_riesgo",
        "titulo": "§4.5 — Dimensión de Riesgo",
        "descripcion": "Amenazas internas y externas a la comunidad",
        "orden": 8,
        "questions": [
            {"code": "amenazas_externas", "label": "Amenazas externas identificadas", "tipo_dato": "textarea", "required": True, "orden": 1,
             "ayuda": "Grupos armados, extorsión, presión territorial, megaproyectos, etc."},
            {"code": "amenazas_internas", "label": "Amenazas internas / pérdidas culturales", "tipo_dato": "textarea", "orden": 2,
             "ayuda": "Pérdida de lengua, dispersión, ruptura intergeneracional, etc."},
            {"code": "riesgos_seguridad", "label": "Riesgos de seguridad para autoridades", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Ej: amenazas, extorsión, prohibición de reuniones"},
            {"code": "riesgo_territorial", "label": "Riesgo territorial", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Insuficiencia de tierra, hambre, falta de agua, acceso a servicios"},
            {"code": "riesgo_educativo_salud", "label": "Riesgos en educación y salud", "tipo_dato": "textarea", "orden": 5},
            {"code": "subregistro", "label": "Casos de subregistro identificados", "tipo_dato": "textarea", "orden": 6,
             "ayuda": "Ej: Médico Tradicional sin cédula, niños sin registro civil"},
            {"code": "fortalezas_preservar", "label": "Fortalezas a preservar", "tipo_dato": "textarea", "orden": 7,
             "ayuda": "Lo que la comunidad tiene como recurso ante las amenazas"},
        ],
    },
    {
        "code": "evidencias",
        "titulo": "§5 — Evidencias recolectadas",
        "descripcion": "Productos del trabajo de campo que se anexan al expediente",
        "orden": 9,
        "questions": [
            {"code": "tipos_evidencias", "label": "Tipos de evidencias recolectadas",
             "tipo_dato": "multiselect", "orden": 1,
             "opciones": [
                 "Acta de inicio",
                 "Registro de asistencia",
                 "Fotografías",
                 "Audio (entrevistas)",
                 "Video",
                 "Cartografía social",
                 "Árbol de riesgos",
                 "Apuntes / diario de campo",
                 "Mapa territorial",
                 "Capas SIG",
                 "Documentos comunitarios entregados",
             ]},
            {"code": "n_audios", "label": "Número de audios", "tipo_dato": "number", "orden": 2},
            {"code": "n_fotografias", "label": "Número de fotografías", "tipo_dato": "number", "orden": 3},
            {"code": "descripcion_evidencias", "label": "Descripción detallada de evidencias", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Para cada evidencia: identificador, fecha, contenido, autor"},
            {"code": "ubicacion_evidencias", "label": "Ubicación de las evidencias", "tipo_dato": "textarea", "orden": 5,
             "ayuda": "Carpeta de Drive, expediente físico, etc."},
        ],
    },
    {
        "code": "balance",
        "titulo": "§6 — Balance del profesional",
        "descripcion": "Reflexión analítica del investigador al cierre del trabajo de campo",
        "orden": 10,
        "questions": [
            {"code": "hallazgos_principales", "label": "Hallazgos principales", "tipo_dato": "textarea", "required": True, "orden": 1,
             "ayuda": "Las 3-5 cosas más importantes que confirma o aporta el trabajo de campo"},
            {"code": "reflexion_metodologica", "label": "Reflexión metodológica", "tipo_dato": "textarea", "orden": 2,
             "ayuda": "Qué funcionó, qué no, qué se mejoraría"},
            {"code": "lectura_etnologica", "label": "Lectura etnológica del caso", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Interpretación profesional sobre la condición de pueblo indígena del grupo"},
            {"code": "concepto_preliminar", "label": "Concepto preliminar",
             "tipo_dato": "select", "orden": 4,
             "opciones": [
                 "Favorable al registro",
                 "Favorable con condicionantes",
                 "Requiere ampliación de información",
                 "Desfavorable",
                 "Sin pronunciamiento aún",
             ]},
            {"code": "recomendaciones_estado", "label": "Recomendaciones al Estado", "tipo_dato": "textarea", "orden": 5,
             "ayuda": "Acciones que se recomiendan a Mininterior, Alcaldía, ANT u otras entidades"},
            {"code": "proximos_pasos", "label": "Próximos pasos del estudio", "tipo_dato": "textarea", "orden": 6},
        ],
    },
]


async def seed_ficha_comision(db: AsyncSession) -> None:
    """Sembrar Ficha de Comisión (F2-01)."""
    await _seed_type_structure(db, "ficha_comision", FICHA_COMISION_SECTIONS)


# ── F2-02 Diario de Campo ──────────────────────────────────────────────────────

DIARIO_CAMPO_SECTIONS: list[dict] = [
    {
        "code": "datos_diario",
        "titulo": "§1 — Datos generales del diario",
        "orden": 1,
        "questions": [
            {"code": "periodo_inicio", "label": "Inicio del período registrado", "tipo_dato": "date", "required": True, "orden": 1},
            {"code": "periodo_fin", "label": "Fin del período registrado", "tipo_dato": "date", "required": True, "orden": 2},
            {"code": "investigador", "label": "Investigador / autor del diario", "tipo_dato": "text", "required": True, "orden": 3},
            {"code": "metodologia_observ", "label": "Metodología de observación", "tipo_dato": "textarea", "orden": 4,
             "ayuda": "Ej: observación participante, recorridos territoriales, conversaciones informales"},
            {"code": "contexto_general", "label": "Contexto general del trabajo de campo", "tipo_dato": "textarea", "orden": 5},
        ],
    },
    {
        "code": "entradas_diarias",
        "titulo": "§2 — Entradas diarias",
        "descripcion": "Registro día a día. Cada entrada captura observaciones, eventos y reflexiones.",
        "orden": 2,
        "questions": [
            {"code": "entradas", "label": "Entradas del diario",
             "tipo_dato": "journal_entries", "orden": 1,
             "ayuda": "Agrega una entrada por día. Incluye fecha, título corto, contenido descriptivo y tags temáticos (ej: ritual, política interna, territorio)"},
        ],
    },
    {
        "code": "conclusiones_diario",
        "titulo": "§3 — Conclusiones del diario",
        "orden": 3,
        "questions": [
            {"code": "hallazgos_clave", "label": "Hallazgos clave del período", "tipo_dato": "textarea", "orden": 1,
             "ayuda": "Las 3-5 observaciones más significativas"},
            {"code": "tensiones_observadas", "label": "Tensiones / contradicciones observadas", "tipo_dato": "textarea", "orden": 2},
            {"code": "preguntas_abiertas", "label": "Preguntas abiertas para futuras visitas", "tipo_dato": "textarea", "orden": 3},
            {"code": "reflexion_metodologica", "label": "Reflexión metodológica final", "tipo_dato": "textarea", "orden": 4},
        ],
    },
]


async def seed_diario_campo(db: AsyncSession) -> None:
    """Sembrar Diario de Campo (F2-02)."""
    await _seed_type_structure(db, "diario_campo", DIARIO_CAMPO_SECTIONS)


# ── F2-07 Apuntes de Reuniones ────────────────────────────────────────────────

APUNTES_REUNIONES_SECTIONS: list[dict] = [
    {
        "code": "contexto_apuntes",
        "titulo": "§1 — Contexto",
        "orden": 1,
        "questions": [
            {"code": "fechas_reuniones", "label": "Fechas de las reuniones cubiertas", "tipo_dato": "text", "orden": 1,
             "ayuda": "Lista libre o rango. Ej: 15-17 marzo 2026; o 'visita de campo marzo 2026'"},
            {"code": "lugares", "label": "Lugares donde se realizaron", "tipo_dato": "text", "orden": 2},
            {"code": "investigador", "label": "Investigador que toma los apuntes", "tipo_dato": "text", "required": True, "orden": 3},
        ],
    },
    {
        "code": "apuntes_tematicos",
        "titulo": "§2 — Apuntes por tema",
        "descripcion": "Notas cualitativas organizadas por tema. Cada apunte captura una conversación o tema específico.",
        "orden": 2,
        "questions": [
            {"code": "apuntes", "label": "Apuntes",
             "tipo_dato": "journal_entries", "orden": 1,
             "ayuda": "Una entrada por tema o conversación. Título = tema. Contenido = datos recopilados, citas textuales, personas mencionadas. Tags = temas (mambeo, mujeres, territorio, etc.)"},
        ],
    },
    {
        "code": "sintesis_apuntes",
        "titulo": "§3 — Síntesis",
        "orden": 3,
        "questions": [
            {"code": "sintesis_general", "label": "Síntesis general de los apuntes", "tipo_dato": "textarea", "orden": 1},
            {"code": "temas_recurrentes", "label": "Temas recurrentes detectados", "tipo_dato": "textarea", "orden": 2},
            {"code": "personas_clave", "label": "Personas clave mencionadas o consultadas", "tipo_dato": "textarea", "orden": 3,
             "ayuda": "Sin necesidad de datos completos — referencias para futuras consultas"},
        ],
    },
]


async def seed_apuntes_reuniones(db: AsyncSession) -> None:
    """Sembrar Apuntes de Reuniones (F2-07)."""
    await _seed_type_structure(db, "apuntes_reuniones", APUNTES_REUNIONES_SECTIONS)

