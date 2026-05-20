"""
Capa de extracción con IA intercambiable.

Proveedor se selecciona vía config: AI_PROVIDER = claude | openai | gemini | none
Si AI_PROVIDER = "none" o no hay API key, se omite y solo corre spaCy.

Cada proveedor implementa el mismo método:
  extract(text, filename) -> list[dict]  donde cada dict es:
  {"tipo_dato": str, "valor": str, "confianza": float}
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Máximo de caracteres enviados por chunk a la IA (evitar límites de contexto).
# A mayor tamaño → menos llamadas y menor costo, pero más riesgo de truncado en respuesta.
_CHUNK_SIZE = 40_000

# Si el texto extraído supera este umbral, se omite el resumen IA para ahorrar tokens.
# La extracción estructurada (entidades) sigue corriéndose; el resumen es redundante en docs grandes.
_SKIP_SUMMARY_THRESHOLD = 200_000

_PROMPT_TEMPLATE = """Eres un experto en análisis de estudios etnológicos colombianos para el Ministerio del Interior.
El siguiente texto proviene del documento "{filename}" que hace parte del corpus de reconocimiento de un cabildo indígena.

Extrae ÚNICAMENTE datos que estén EXPLÍCITAMENTE mencionados en el texto. No inventes ni inferis información.

Responde SOLO con un JSON array válido. Cada elemento debe tener exactamente estas tres claves:
{{"tipo_dato": string, "valor": string, "confianza": número entre 0 y 1}}

TIPOS DE DATOS A EXTRAER (usa exactamente estos nombres):

=== IDENTIFICACIÓN BÁSICA ===
- familias_count         → número exacto de familias del cabildo
- personas_count         → número exacto de personas o miembros
- fecha_censo            → fecha del censo o registro poblacional
- fuente_censo           → institución del censo (DANE, Ministerio, autocenso, cabildo, etc.)
- nombre_comunidad       → nombre oficial del cabildo o comunidad
- pueblo_indigena        → pueblo o etnia indígena
- municipio              → municipio de ubicación
- departamento           → departamento de ubicación
- vereda                 → vereda o corregimiento
- resguardo              → nombre del resguardo indígena (si aplica)
- representante_legal    → nombre completo del gobernador o representante legal
- nit                    → NIT de la comunidad
- contrato_referencia    → número o referencia del contrato del estudio
- discrepancia_poblacion → descripción de discrepancia entre fuentes de población

=== HISTORIA Y ORIGEN ===
- narrativa_origen       → cómo surgió la comunidad, de dónde vienen, quiénes fueron los fundadores
- trayectoria_migratoria → migraciones, desplazamientos, rutas históricas del pueblo
- fecha_historica        → fechas importantes del proceso histórico de la comunidad
- evento_historico       → eventos relevantes: fundación, desplazamiento, conflicto, acuerdo, etc.

=== IDENTIDAD ÉTNICA ===
- clan_indigena          → clan, linaje o grupo familiar extendido dentro del pueblo
- nombre_indigena        → nombre en lengua propia de la comunidad o del pueblo
- autoidentificacion     → declaración de auto-reconocimiento como pueblo indígena
- lengua_indigena        → nombre de la lengua propia del pueblo
- nivel_uso_lengua       → estado de uso o vitalidad de la lengua (hablantes, generaciones, etc.)

=== CULTURA Y PRÁCTICAS ===
- actividad_cultural     → práctica o actividad cultural propia identificada
- actividad_subsistencia → actividad económica de subsistencia: agricultura, pesca, caza, artesanía
- herramienta_tradicional → herramientas o implementos de uso tradicional
- planta_sagrada         → planta medicinal o sagrada y su uso específico
- lugar_sagrado          → sitio sagrado o de valor cultural especial con nombre o descripción
- tecnologia_espiritual  → práctica chamánica, medicina tradicional o ritual de curación

=== COSMOVISIÓN Y ESPIRITUALIDAD ===
- cosmogonia             → creencias, cosmovisión, mitos de origen, relación espiritual con la naturaleza
- ritual_central         → ritual o ceremonia colectiva principal
- elemento_sagrado       → objeto sagrado, símbolo identitario o instrumento ceremonial

=== ORGANIZACIÓN Y GOBIERNO ===
- estructura_politica    → descripción de la estructura organizativa del cabildo
- autoridad_cargo        → cargo específico con nombre si está disponible (gobernador, fiscal, secretario, vocal, etc.)
- reglamento_interno_detalle → estatuto, reglamento interno o norma del cabildo

=== RELACIONES EXTERNAS ===
- alianza_interetnica    → relaciones o alianzas con otros pueblos indígenas o cabildos
- relacion_institucional → relación con entidades del Estado, ONGs, iglesias, universidades
- actores_externos       → actores externos que afectan a la comunidad (empresas, colonos, etc.)

=== PROSPECTIVA ===
- amenaza_seguridad      → amenaza identificada al territorio, la cultura o la comunidad
- despojo_historico      → despojo territorial o cultural sufrido históricamente
- vision_futuro          → proyecto, aspiración o plan de la comunidad hacia el futuro
- actividad_economica    → actividad económica actual relevante para el sustento

=== GEORREFERENCIACIÓN (MUY IMPORTANTE) ===
- coordenada_gps    → coordenadas GPS exactas de un lugar identificado en el texto. FORMATO OBLIGATORIO del valor: "NombreDelLugar|lat_decimal|lng_decimal" (ejemplo: "Maloka Murui Muina|1.3744|-75.4000" o "La Chorrera|0.8833|-73.0167"). Convierte DMS a decimal si el texto muestra grados/minutos/segundos. Extrae UNA entrada por lugar con coordenadas.
- plus_code         → código Plus/Open Location Code de Google (ej: "9J72+5V Milán"). Incluye el municipio de referencia junto al código.
- sitio_geografico  → lugar geográfico nombrado relevante para el mapa, sin coordenadas exactas (ej: "Río Igaraparaná" o "Corregimiento La Chorrera, Amazonas"). FORMATO: "NombreDelLugar|descripción breve de su relevancia". Solo extrae lugares con nombre propio explícito.

No incluyas valores vacíos, genéricos ni inferidos. Si el texto no contiene datos extraíbles, devuelve [].

Texto a analizar:
{text}"""


def _safe_parse(raw: str) -> list[dict]:
    """Extrae el JSON array de la respuesta del modelo, tolerando texto alrededor."""
    raw = raw.strip()
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        if not isinstance(data, list):
            return []
        validated = []
        for item in data:
            if (
                isinstance(item, dict)
                and "tipo_dato" in item
                and "valor" in item
                and item.get("valor")
                and str(item["valor"]).strip()
            ):
                validated.append({
                    "tipo_dato": str(item["tipo_dato"]),
                    "valor": str(item["valor"]).strip()[:500],
                    "confianza": float(item.get("confianza", 0.9)),
                })
        return validated
    except (json.JSONDecodeError, ValueError):
        return []


def _chunk(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    chunks = []
    for i in range(0, len(text), size):
        chunk = text[i : i + size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


_SUMMARY_PROMPT = """Eres un asistente experto en estudios etnológicos colombianos para el Ministerio del Interior.
Lee el siguiente documento "{filename}" y genera un resumen ESTRUCTURADO en español.

{role_guide}

Responde EXACTAMENTE con este formato (sin viñetas extra, sin encabezados de sección distintos):

**Tipo de documento:** [un sólo término: acta de elección / reglamento interno / autocenso / etc.]
**Emisor / autor:** [quién firma o emite — persona, cabildo, institución; si no se menciona pon "No especificado"]
**Fecha:** [fecha que aparece en el documento o "No especificada"]
**Datos clave:**
- [dato 1]
- [dato 2]
- [dato 3]
- (entre 3 y 6 viñetas con la información más relevante del documento, citando cifras, nombres propios y fechas concretas)
**Síntesis:** [2-3 oraciones explicando de qué trata el documento y para qué sirve]

Reglas:
- NO inventes datos. Si algo no está en el texto, omítelo o escribe "No especificado".
- Cita cifras y nombres tal como aparecen.
- Usa lenguaje formal y conciso.
- Si el texto está incompleto o es muy corto, responde igual con los datos que sí estén disponibles.

Documento:
{text}
"""


# Guías específicas por rol_en_corpus para FASE 1 — extraídas del análisis documental
# (DOCUMENTACION/10_REQUERIMIENTOS_INFORME_FASE3.md en docs/requerimientos-informes)
_ROLE_GUIDES: dict[str, str] = {
    "solicitud_formal": (
        "Este es una SOLICITUD FORMAL dirigida a una entidad. Identifica especialmente: "
        "entidad receptora (Ministerio, Alcaldía, ACOTRI, etc.), peticionarios o firmantes, "
        "número de radicado si existe, propósito de la solicitud (afiliación, registro, atención, etc.), "
        "fecha de radicación, y número de firmas o avales si aparecen."
    ),
    "reglamento": (
        "Este es un REGLAMENTO INTERNO de un cabildo indígena. Identifica especialmente: "
        "estructura de cargos (cacique, gobernador, fiscal, secretaria, abuela consejera, etc.), "
        "tipos de afiliación, cuotas o multas con sus montos en pesos colombianos, "
        "principios fundacionales (ej. lenguaje sobre tabaco/coca/yuca dulce), "
        "instancias de decisión (asambleas, mambeadero, frecuencia), "
        "y causales de sanción o expulsión."
    ),
    "acta_eleccion": (
        "Este es un ACTA DE ELECCIÓN de autoridades del cabildo. Identifica especialmente: "
        "fecha y lugar de la elección, cargos elegidos con su nombre y número de cédula, "
        "total de asistentes, votos por candidato si aparecen, y entidad que avala (Alcaldía u otra)."
    ),
    "acta_posesion": (
        "Este es un ACTA DE POSESIÓN ante autoridad pública. Identifica especialmente: "
        "fecha y lugar de la posesión, nombre del Alcalde u oficial que posesiona, "
        "cargos posesionados con su nombre y cédula, vigencia del periodo (años), "
        "y número del acto administrativo."
    ),
    "autocenso_depurado": (
        "Este es un AUTOCENSO DEPURADO de la comunidad indígena. Identifica especialmente: "
        "número total de personas registradas, número de familias, rango etario, "
        "roles dentro de la comunidad (sabedoras, gobernadora, médico tradicional, etc.), "
        "y diferencias respecto al censo total no depurado si se menciona."
    ),
    "autocenso": (
        "Este es un AUTOCENSO de la comunidad indígena. Identifica especialmente: "
        "número total de personas, número de familias, fecha del registro, "
        "estructura por edades o sexo si aparece, y entidad o líder que coordina el registro."
    ),
    "censo_comunidad": (
        "Este es un CENSO formal de la comunidad. Identifica especialmente: "
        "número total de personas y familias, año o fecha del censo, "
        "fuente o institución que lo realizó (cabildo, DANE, Ministerio, etc.), "
        "y distribución por edad o sexo si aparece."
    ),
    "ficha_precampo": (
        "Esta es una FICHA DE PRE-CAMPO con información preparatoria de la comunidad. Identifica: "
        "nombre oficial y autodenominación de la comunidad, municipio y vereda, "
        "coordenadas o código de ubicación (plus code, lat/lng), autoridades y actores clave con contacto, "
        "instituciones presentes en la zona, vías de acceso y distancia a la cabecera, "
        "evolución demográfica (familias y personas por año), y riesgos o puntos de atención."
    ),
    "rut_comunidad": (
        "Este es un RUT (Registro Único Tributario DIAN) de la comunidad. Identifica: "
        "NIT, razón social oficial, dirección registrada, fecha de inscripción, "
        "actividad económica reportada, y representante legal."
    ),
    "resena_historica": (
        "Esta es una RESEÑA HISTÓRICA del pueblo indígena. Identifica especialmente: "
        "lugar de origen ancestral, mito o cosmogonía de origen, clanes del pueblo y sus traducciones, "
        "fechas y procesos históricos relevantes (asentamiento, despojo, desplazamiento), "
        "nombres de colonos o terratenientes que aparecen, "
        "elementos sagrados perdidos o vigentes (maguaré, río, lugares), "
        "y proceso de recuperación o reubicación contemporánea."
    ),
    "mapa_territorial": (
        "Este es un MAPA o documento sobre el territorio. Identifica especialmente: "
        "extensión en hectáreas o kilómetros, coordenadas o puntos de referencia geográficos, "
        "vereda y municipio, tipo de tenencia (propio, comodato, donación, ancestral), "
        "ríos y accidentes geográficos nombrados."
    ),
    "base_datos_dane": (
        "Este es información del DANE o base estadística regional. Identifica: "
        "área geográfica cubierta, indicadores reportados (población, vivienda, etnia), "
        "año de los datos, fuente exacta del DANE, y cifras destacables del municipio o departamento."
    ),
}

_DEFAULT_ROLE_GUIDE = (
    "Identifica especialmente: tipo de documento, comunidad o cabildo referido, ubicación "
    "(municipio/departamento), institución emisora, fechas relevantes, cifras de población si aparecen, "
    "nombres de autoridades, y propósito principal del documento."
)


def _build_summary_prompt(text: str, filename: str, rol: str | None) -> str:
    role_key = (rol or "").strip().lower()
    role_guide = _ROLE_GUIDES.get(role_key, _DEFAULT_ROLE_GUIDE)
    return _SUMMARY_PROMPT.format(filename=filename, text=text[:8000], role_guide=role_guide)

# ── Base class ────────────────────────────────────────────────────────────────

class AIExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, filename: str) -> list[dict]:
        """Return list of {tipo_dato, valor, confianza} dicts."""

    def summarize(self, text: str, filename: str, rol: str | None = None) -> str | None:
        """Generate a human-readable summary of the document.

        rol: optional rol_en_corpus (e.g. 'reglamento', 'autocenso', 'ficha_precampo') so the
        prompt can target the right fields. Override in subclasses.
        """
        return None


# ── Claude (Anthropic) ────────────────────────────────────────────────────────

class ClaudeExtractor(AIExtractor):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def extract(self, text: str, filename: str) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(text):
            prompt = _PROMPT_TEMPLATE.format(filename=filename, text=chunk)
            try:
                msg = self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text if msg.content else ""
                results.extend(_safe_parse(raw))
            except Exception as e:
                logger.warning("Claude extraction error on %s: %s", filename, e)
        return results

    def summarize(self, text: str, filename: str, rol: str | None = None) -> str | None:
        prompt = _build_summary_prompt(text, filename, rol)
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            return (msg.content[0].text or "").strip() or None
        except Exception as e:
            logger.warning("Claude summarize error on %s: %s", filename, e)
            return None


# ── OpenAI (ChatGPT) ──────────────────────────────────────────────────────────

class OpenAIExtractor(AIExtractor):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def extract(self, text: str, filename: str) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(text):
            prompt = _PROMPT_TEMPLATE.format(filename=filename, text=chunk)
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    temperature=0,
                )
                raw = resp.choices[0].message.content or ""
                results.extend(_safe_parse(raw))
            except Exception as e:
                logger.warning("OpenAI extraction error on %s: %s", filename, e)
        return results

    def summarize(self, text: str, filename: str, rol: str | None = None) -> str | None:
        prompt = _build_summary_prompt(text, filename, rol)
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3,
            )
            return (resp.choices[0].message.content or "").strip() or None
        except Exception as e:
            logger.warning("OpenAI summarize error on %s: %s", filename, e)
            return None


# ── Gemini (Google) ───────────────────────────────────────────────────────────

class GeminiExtractor(AIExtractor):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-lite"):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model_name = model or "gemini-2.0-flash-lite"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _generate(self, prompt: str, retries: int = 1) -> str:
        """Llamada con un único retry corto. En 429 propaga el error de inmediato."""
        import time
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                return resp.text or ""
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if "429" in msg or "rate" in msg or "quota" in msg:
                    raise
                if "404" in msg or "not found" in msg or "permission" in msg or "auth" in msg:
                    raise
                time.sleep(2 ** attempt)
        if last_err:
            raise last_err
        return ""

    def extract(self, text: str, filename: str) -> list[dict]:
        results: list[dict] = []
        for chunk in _chunk(text):
            prompt = _PROMPT_TEMPLATE.format(filename=filename, text=chunk)
            try:
                raw = self._generate(prompt)
                results.extend(_safe_parse(raw))
            except Exception as e:
                logger.warning("Gemini extraction error on %s: %s", filename, e)
        return results

    def summarize(self, text: str, filename: str, rol: str | None = None) -> str | None:
        prompt = _build_summary_prompt(text, filename, rol)
        # NO atrapamos la excepción: el caller decide cómo manejarla (p. ej. el endpoint
        # /api/quick/summarize traduce 429/404 en mensajes legibles). El pipeline batch
        # de estudios sigue tolerante porque usa otro flujo.
        raw = self._generate(prompt)
        return raw.strip() or None


# ── Factory ───────────────────────────────────────────────────────────────────

def get_ai_extractor(provider: str, api_key: str, model: str) -> AIExtractor | None:
    """
    Returns the right extractor for the configured provider.
    Returns None if provider is 'none' or api_key is empty.
    """
    provider = provider.lower().strip()
    if provider == "none" or not api_key:
        return None
    try:
        if provider == "claude":
            return ClaudeExtractor(api_key=api_key, model=model or "claude-haiku-4-5-20251001")
        if provider in ("openai", "chatgpt"):
            return OpenAIExtractor(api_key=api_key, model=model or "gpt-4o-mini")
        if provider == "gemini":
            return GeminiExtractor(api_key=api_key, model=model or "gemini-2.0-flash-lite")
        logger.warning("AI_PROVIDER '%s' no reconocido. Usando solo spaCy.", provider)
    except ImportError as e:
        logger.error(
            "Librería para AI_PROVIDER='%s' no instalada (%s). "
            "Agrega el paquete a requirements.txt y redeploya. Usando solo spaCy.",
            provider, e,
        )
    except Exception as e:
        logger.error("Error inicializando extractor IA (%s): %s. Usando solo spaCy.", provider, e)
    return None
