# EtnoSIG — Integración Google Drive y Análisis con IA
## Especificación Técnica

---

## PARTE 1 — INTEGRACIÓN GOOGLE DRIVE

### 1.1 Configuración OAuth2

#### Prerrequisitos en Google Cloud Console
1. Crear proyecto en `console.cloud.google.com`
2. Habilitar **Google Drive API**
3. Crear credenciales OAuth2 Client ID (tipo: Web Application)
4. Configurar `redirect_uri`: `https://etnosig.simonky.com/api/drive/callback`
5. Scopes requeridos: `https://www.googleapis.com/auth/drive.readonly`

#### Flujo OAuth2 Detallado

```
USUARIO                    FRONTEND                    BACKEND                    GOOGLE
   │                           │                           │                          │
   │ Clic "Conectar Drive"     │                           │                          │
   │ ─────────────────────────▶│                           │                          │
   │                           │ GET /api/drive/auth-url   │                          │
   │                           │──────────────────────────▶│                          │
   │                           │                           │ Genera state (UUID)      │
   │                           │                           │ Guarda state en Redis    │
   │                           │         {auth_url}        │                          │
   │                           │◀──────────────────────────│                          │
   │                           │                           │                          │
   │ Redirige a Google         │                           │                          │
   │◀──────────────────────────│                           │                          │
   │                           │                           │                          │
   │ ─────────────────────────────────────────────────────────────────────────────────▶│
   │                           │                           │   Muestra pantalla       │
   │                           │                           │   de autorización        │
   │◀─────────────────────────────────────────────────────────────────────────────────│
   │ Acepta permisos           │                           │                          │
   │ ─────────────────────────────────────────────────────────────────────────────────▶│
   │                           │                           │   Redirige a callback    │
   │                           │                           │◀─────────────────────────│
   │                           │          ?code=...&state= │                          │
   │                           │                           │ Valida state             │
   │                           │                           │ Intercambia code         │
   │                           │                           │──────────────────────────▶│
   │                           │                           │   {access_token,         │
   │                           │                           │    refresh_token}        │
   │                           │                           │◀─────────────────────────│
   │                           │                           │ Cifra tokens             │
   │                           │                           │ Almacena en users DB     │
   │  Redirige /?drive_ok=true │                           │                          │
   │◀──────────────────────────│◀──────────────────────────│                          │
```

#### Implementación del Servicio Drive

```python
# backend/app/drive/service.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from cryptography.fernet import Fernet

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FERNET_KEY = settings.FERNET_KEY  # Para cifrar tokens en DB

class DriveService:
    def __init__(self, user: User):
        self.user = user
        self.creds = self._load_credentials()
    
    def _load_credentials(self) -> Credentials:
        """Descifra y carga las credenciales del usuario."""
        if not self.user.google_token:
            raise HTTPException(401, "Cuenta de Google no conectada")
        
        f = Fernet(FERNET_KEY)
        token_data = json.loads(f.decrypt(self.user.google_token.encode()))
        
        creds = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )
        
        # Auto-refrescar si expiró
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Guardar token refrescado
            self._save_credentials(creds)
        
        return creds
    
    def _get_service(self):
        return build("drive", "v3", credentials=self.creds)
    
    async def listar_archivos_carpeta(self, folder_url: str) -> list[dict]:
        """Lista todos los archivos en una carpeta de Drive (recursivo)."""
        folder_id = self._extraer_folder_id(folder_url)
        service = self._get_service()
        return self._listar_recursivo(service, folder_id, "")
    
    def _listar_recursivo(self, service, folder_id: str, prefijo: str) -> list[dict]:
        resultados = []
        page_token = None
        while True:
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                pageToken=page_token,
                pageSize=100
            ).execute()
            
            for archivo in response.get("files", []):
                ruta = f"{prefijo}/{archivo['name']}"
                if archivo["mimeType"] == "application/vnd.google-apps.folder":
                    # Recursión en subcarpetas
                    resultados.extend(self._listar_recursivo(service, archivo["id"], ruta))
                else:
                    resultados.append({
                        "drive_file_id": archivo["id"],
                        "nombre": archivo["name"],
                        "ruta_relativa": ruta,
                        "mime_type": archivo["mimeType"],
                        "tamanio_bytes": int(archivo.get("size", 0)),
                        "modificado_en": archivo.get("modifiedTime"),
                    })
            
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return resultados
    
    async def descargar_archivo(self, file_id: str, destino_path: str) -> str:
        """Descarga un archivo de Drive al servidor."""
        service = self._get_service()
        request = service.files().get_media(fileId=file_id)
        
        with open(destino_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        return destino_path
    
    @staticmethod
    def _extraer_folder_id(url: str) -> str:
        """Extrae el ID de carpeta de una URL de Google Drive."""
        # https://drive.google.com/drive/folders/1ABC123DEF456?usp=sharing
        import re
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError(f"URL de Drive inválida: {url}")
        return match.group(1)
```

### 1.2 Proceso de Sincronización

```python
# backend/tasks/gis_task.py (tarea asíncrona)

async def sync_drive_task(study_id: UUID, user_id: UUID):
    study = await study_repo.get_or_404(study_id)
    drive_svc = DriveService(user=await user_repo.get_or_404(user_id))
    
    temp_dir = Path(settings.TEMP_PATH) / str(study_id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Listar archivos por fase
    for fase, url in [("FASE1", study.url_drive_fase1),
                      ("FASE2", study.url_drive_fase2),
                      ("FASE3", study.url_drive_fase3)]:
        if not url:
            continue
        archivos = await drive_svc.listar_archivos_carpeta(url)
        
        for archivo in archivos:
            # Detectar tipo y rol
            tipo = _detectar_tipo(archivo["nombre"], archivo["mime_type"])
            rol  = _detectar_rol(archivo["nombre"], archivo["ruta_relativa"], fase)
            
            # Guardar en corpus
            corpus_entry = await corpus_repo.upsert({
                "study_id": study_id,
                "fase": fase,
                "nombre_archivo": archivo["nombre"],
                "drive_file_id": archivo["drive_file_id"],
                "tipo_archivo": tipo,
                "rol_en_corpus": rol,
                "tamanio_bytes": archivo["tamanio_bytes"],
                "estado": "pendiente",
            })
            
            # Descargar archivos procesables (no fotos en masa por ahora)
            if tipo in ["pdf", "docx", "xlsx", "qgz", "gpkg"]:
                dest = temp_dir / f"{fase}_{corpus_entry.id}_{archivo['nombre']}"
                await drive_svc.descargar_archivo(archivo["drive_file_id"], str(dest))
                await corpus_repo.update(corpus_entry.id, {"estado": "descargado"})
    
    await study_repo.update(study_id, {"estado": "corpus_ok"})
    await notification_svc.notificar_equipo(study_id, "corpus_sincronizado")
```

### 1.3 Clasificación de Archivos del Corpus

```python
TIPOS_POR_EXTENSION = {
    ".pdf": "pdf", ".docx": "docx", ".doc": "docx",
    ".xlsx": "xlsx", ".xls": "xlsx",
    ".qgz": "qgz", ".gpkg": "gpkg", ".shp": "shp",
    ".jpg": "jpg", ".jpeg": "jpg", ".heic": "heic",
    ".mp4": "mp4", ".mp3": "mp3", ".m4a": "mp3",
}

ROLES_POR_PATRON = {
    # FASE1
    r"solicitud.*formal": "solicitud_formal",
    r"reglamento.*interno": "reglamento",
    r"acta.*elecci": "acta_eleccion",
    r"acta.*posesi": "acta_posesion",
    r"mapa": "mapa_territorial",
    r"rese[ñn]a.*hist": "resena_historica",
    r"autocenso.*depurado|autocenso.*2026": "autocenso_depurado",
    r"autocenso": "autocenso",
    r"censo.*comunidad": "censo_comunidad",
    r"pre.campo|precamp": "ficha_precampo",
    r"rut": "rut_comunidad",
    r"bd.caqueta|base.*datos": "base_datos_dane",
    # FASE2
    r"acta.*inicio": "acta_inicio",
    r"cronograma": "cronograma",
    r"diario.*campo": "diario_campo",
    r"ficha.*comisi": "ficha_comision",
    r"apuntes.*reuni": "apuntes_reuniones",
    r"arbol.*riesgo|riesgo": "arbol_riesgo",
    r"cartograf": "cartografia_social",
    r"asistencia": "registro_asistencia",
    r"\.qgz$": "proyecto_qgis",
    r"\.gpkg$": "geopackage",
    # FASE3
    r"informe.*comunidad|concepto": "concepto_etnologico",
    r"acto.*administrativo|borrador.*acto": "borrador_acto_administrativo",
}
```

---

## PARTE 2 — ANÁLISIS CON INTELIGENCIA ARTIFICIAL

### 2.1 Motor NLP — spaCy

El motor usa **spaCy** con el modelo `es_core_news_lg` (español, grande) para extracción de entidades nombradas.

#### Instalación
```bash
pip install spacy
python -m spacy download es_core_news_lg
```

#### Pipeline de Extracción

```python
# backend/app/documents/nlp_extractor.py

import spacy
import re
from dataclasses import dataclass

nlp = spacy.load("es_core_news_lg")

@dataclass
class Extraccion:
    tipo_dato: str
    valor: str
    confianza: float
    fuente_texto: str  # fragmento de texto del que se extrajo

class NLPExtractor:
    
    def extraer_todo(self, texto: str, documento_rol: str) -> list[Extraccion]:
        """Pipeline completo de extracción según el rol del documento."""
        extracciones = []
        doc = nlp(texto)
        
        # Entidades generales de spaCy
        extracciones.extend(self._extraer_entidades_spacy(doc))
        
        # Patrones específicos por rol
        if documento_rol in ["acta_posesion", "acta_eleccion"]:
            extracciones.extend(self._extraer_autoridades(texto))
        
        if documento_rol in ["autocenso", "autocenso_depurado", "censo_comunidad"]:
            extracciones.extend(self._extraer_cifras_poblacionales(texto))
        
        if documento_rol == "ficha_precampo":
            extracciones.extend(self._extraer_datos_precampo(texto))
        
        if documento_rol in ["solicitud_formal", "reglamento"]:
            extracciones.extend(self._extraer_datos_juridicos(texto))
        
        return extracciones
    
    def _extraer_entidades_spacy(self, doc) -> list[Extraccion]:
        resultados = []
        for ent in doc.ents:
            if ent.label_ == "PER" and len(ent.text.split()) >= 2:
                resultados.append(Extraccion(
                    tipo_dato="persona_mencionada",
                    valor=ent.text.strip(),
                    confianza=0.85,
                    fuente_texto=ent.sent.text[:200]
                ))
            elif ent.label_ == "LOC":
                resultados.append(Extraccion(
                    tipo_dato="lugar_mencionado",
                    valor=ent.text.strip(),
                    confianza=0.80,
                    fuente_texto=ent.sent.text[:200]
                ))
            elif ent.label_ == "DATE":
                resultados.append(Extraccion(
                    tipo_dato="fecha_mencionada",
                    valor=ent.text.strip(),
                    confianza=0.90,
                    fuente_texto=ent.sent.text[:200]
                ))
        return resultados
    
    def _extraer_autoridades(self, texto: str) -> list[Extraccion]:
        """Extrae nombres de autoridades del cabildo."""
        extracciones = []
        patrones = [
            (r"gobernador[a]?\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})", "gobernador"),
            (r"cacique\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})", "cacique"),
            (r"secretar[ia]+\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})", "secretaria"),
            (r"tesorera?\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})", "tesorera"),
            (r"vicegobernador[a]?\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})", "vicegobernador"),
            (r"m[eé]dic[oa] tradicional\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})", "medico_tradicional"),
        ]
        for patron, cargo in patrones:
            for match in re.finditer(patron, texto, re.IGNORECASE):
                extracciones.append(Extraccion(
                    tipo_dato=f"{cargo}_nombre",
                    valor=match.group(1).strip(),
                    confianza=0.92,
                    fuente_texto=match.group(0)
                ))
        return extracciones
    
    def _extraer_cifras_poblacionales(self, texto: str) -> list[Extraccion]:
        """Extrae cifras de familias y personas."""
        extracciones = []
        patrones = [
            (r"(\d+)\s+familias", "familias"),
            (r"(\d+)\s+hogares", "familias"),  # hogares = familias
            (r"(\d+)\s+personas", "personas"),
            (r"(\d+)\s+miembros", "personas"),
            (r"(\d+)\s+integrantes", "personas"),
        ]
        for patron, tipo in patrones:
            for match in re.finditer(patron, texto, re.IGNORECASE):
                valor = int(match.group(1))
                if 0 < valor < 10000:  # Filtrar valores absurdos
                    extracciones.append(Extraccion(
                        tipo_dato=tipo,
                        valor=str(valor),
                        confianza=0.88,
                        fuente_texto=match.group(0)
                    ))
        return extracciones
    
    def _extraer_datos_precampo(self, texto: str) -> list[Extraccion]:
        """Extrae datos de la ficha de pre-campo."""
        extracciones = []
        patrones = [
            (r"NIT\s*[:\-]?\s*([\d\-]+)", "nit"),
            (r"tel[eé]fono\s*[:\-]?\s*([\d\s\+\-]{7,15})", "telefono_contacto"),
            (r"correo\s*[:\-]?\s*([\w\.\+\-]+@[\w\.\-]+\.\w+)", "email_contacto"),
            (r"municipio\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+?)(?:\n|,|\.|departamento)", "municipio"),
        ]
        for patron, tipo in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                extracciones.append(Extraccion(
                    tipo_dato=tipo,
                    valor=match.group(1).strip(),
                    confianza=0.87,
                    fuente_texto=match.group(0)
                ))
        return extracciones
    
    def _extraer_datos_juridicos(self, texto: str) -> list[Extraccion]:
        """Extrae referencias legales y fechas de constitución."""
        extracciones = []
        # Fecha de constitución/fundación
        patron_fecha_const = r"constituid[ao].*?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})"
        match = re.search(patron_fecha_const, texto, re.IGNORECASE)
        if match:
            extracciones.append(Extraccion(
                tipo_dato="fecha_constitucion",
                valor=match.group(1),
                confianza=0.91,
                fuente_texto=match.group(0)
            ))
        return extracciones
```

### 2.2 Análisis de Discrepancias Poblacionales

```python
# backend/app/analytics/population.py

from dataclasses import dataclass

@dataclass
class FuentePoblacional:
    nombre: str
    archivo: str
    familias: int | None
    personas: int | None

class PopulationAnalyzer:
    
    UMBRAL_DISCREPANCIA = 0.10  # 10%
    
    def analizar(self, extracciones: list[dict]) -> dict:
        fuentes = self._agrupar_por_fuente(extracciones)
        discrepancias = self._detectar_discrepancias(fuentes)
        recomendacion = self._generar_recomendacion(fuentes, discrepancias)
        
        return {
            "fuentes": [f.__dict__ for f in fuentes],
            "discrepancias": discrepancias,
            "recomendacion_informe": recomendacion,
        }
    
    def _detectar_discrepancias(self, fuentes: list[FuentePoblacional]) -> list[dict]:
        discrepancias = []
        for campo in ["familias", "personas"]:
            valores = [(f.nombre, getattr(f, campo)) for f in fuentes if getattr(f, campo)]
            if len(valores) < 2:
                continue
            min_val = min(v for _, v in valores)
            max_val = max(v for _, v in valores)
            if min_val == 0:
                continue
            diff_pct = (max_val - min_val) / min_val * 100
            if diff_pct > self.UMBRAL_DISCREPANCIA * 100:
                discrepancias.append({
                    "campo": campo,
                    "diferencia_porcentual": round(diff_pct, 1),
                    "min": min_val,
                    "max": max_val,
                    "nivel": "critica" if diff_pct > 50 else "moderada",
                    "fuentes_involucradas": [n for n, _ in valores],
                })
        return discrepancias
```

### 2.3 Cruce con Datos DANE

```python
# backend/app/analytics/dane.py

import httpx
import json
from datetime import datetime, timedelta

DANE_API = "https://www.datos.gov.co/resource/3s7n-2acv.json"

class DANEAnalyzer:
    
    async def obtener_datos_municipio(self, municipio: str, departamento: str) -> dict:
        # Verificar caché (30 días)
        cache_key = f"dane_{municipio}_{departamento}".lower().replace(" ", "_")
        cached = await cache_service.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Consultar API DANE
        async with httpx.AsyncClient() as client:
            resp = await client.get(DANE_API, params={
                "$where": f"municipio='{municipio}' AND departamento='{departamento}'",
                "$limit": 1
            }, timeout=30)
            resp.raise_for_status()
            datos_raw = resp.json()
        
        resultado = self._transformar_datos(datos_raw, municipio, departamento)
        
        # Cachear 30 días
        await cache_service.set(cache_key, json.dumps(resultado), ex=60*60*24*30)
        
        return resultado
    
    def _transformar_datos(self, datos_raw: list, municipio: str, depto: str) -> dict:
        if not datos_raw:
            return {"municipio": municipio, "departamento": depto, "datos": None}
        d = datos_raw[0]
        return {
            "municipio": municipio,
            "departamento": depto,
            "fuente": "CNPV 2018 — DANE",
            "datos": {
                "poblacion_total": int(d.get("total_personas", 0)),
                "poblacion_indigena_total": int(d.get("indigena", 0)),
                "porcentaje_indigena": round(int(d.get("indigena", 0)) / int(d.get("total_personas", 1)) * 100, 2),
                "hogares_total": int(d.get("total_hogares", 0)),
            }
        }
```

### 2.4 Generación de Red de Actores (organigrama)

```python
# backend/app/analytics/actors.py

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

JERARQUIA_CABILDO = {
    "nivel_0": ["Asamblea General"],
    "nivel_1": ["Junta Directiva"],
    "nivel_2": ["Gobernador/a", "Cacique", "Vicegobernador", "Secretaria/o", "Tesorera/o"],
    "nivel_3": ["Fiscal", "Médico Tradicional", "Consejero/a Mayor", "Abuela Consejera"],
}

COLORES_NIVEL = {
    "nivel_0": "#1A3A5C",
    "nivel_1": "#B22222",
    "nivel_2": "#C8922A",
    "nivel_3": "#16a34a",
}

def generar_organigrama(actores: list[dict], output_path: str) -> str:
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_axis_off()
    
    # Título
    ax.text(7, 9.5, "Estructura Organizativa del Cabildo",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#1A3A5C")
    
    # Dibuja nodos por nivel
    y_posiciones = {0: 8.5, 1: 7.0, 2: 5.2, 3: 3.0}
    
    for nivel_str, cargos in JERARQUIA_CABILDO.items():
        nivel_num = int(nivel_str.split("_")[1])
        y = y_posiciones[nivel_num]
        color = COLORES_NIVEL[nivel_str]
        
        total = len(cargos)
        x_inicio = (14 - total * 2.5) / 2 + 1.25
        
        for i, cargo in enumerate(cargos):
            x = x_inicio + i * 2.5
            # Buscar nombre real del actor
            nombre = _buscar_actor(actores, cargo)
            
            # Caja
            box = FancyBboxPatch((x-1.1, y-0.45), 2.2, 0.9,
                                  boxstyle="round,pad=0.05",
                                  facecolor=color, edgecolor="white",
                                  linewidth=1.5)
            ax.add_patch(box)
            
            # Cargo
            ax.text(x, y+0.15, cargo, ha="center", va="center",
                    fontsize=7, color="white", fontweight="bold")
            # Nombre
            if nombre:
                ax.text(x, y-0.2, nombre[:25], ha="center", va="center",
                        fontsize=6, color="rgba(255,255,255,0.85)")
        
        # Líneas de conexión al siguiente nivel
        if nivel_num < 3:
            y_siguiente = y_posiciones[nivel_num + 1]
            ax.plot([7, 7], [y - 0.45, y_siguiente + 0.45], "k-", linewidth=0.8, alpha=0.4)
    
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path

def _buscar_actor(actores: list[dict], cargo: str) -> str | None:
    cargo_lower = cargo.lower()
    for actor in actores:
        if cargo_lower in actor.get("cargo", "").lower():
            nombre = actor.get("nombre", "")
            partes = nombre.split()
            return " ".join(partes[:2]) if len(partes) >= 2 else nombre
    return None
```

### 2.5 Línea de Tiempo

```python
# backend/app/analytics/timeline.py

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import re

COLORES_EVENTO = {
    "despojo":      "#8B0000",
    "fundacion":    "#C8922A",
    "institucional":"#1A3A5C",
    "campo":        "#16a34a",
    "tramite":      "#0891b2",
    "amenaza":      "#B22222",
}

def generar_timeline(eventos: list[dict], output_path: str) -> str:
    # Ordenar eventos por fecha
    eventos_con_fecha = []
    for ev in eventos:
        fecha_dt = _parsear_fecha(ev.get("fecha", ""))
        if fecha_dt:
            eventos_con_fecha.append((fecha_dt, ev))
    
    eventos_con_fecha.sort(key=lambda x: x[0])
    
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.set_axis_off()
    
    fechas = [f for f, _ in eventos_con_fecha]
    min_fecha = min(fechas)
    max_fecha = max(fechas)
    
    # Línea base
    ax.axhline(y=0.5, xmin=0.02, xmax=0.98, color="#1A3A5C", linewidth=2)
    
    # Plotear eventos
    for i, (fecha, evento) in enumerate(eventos_con_fecha):
        x_norm = (fecha - min_fecha).days / max(1, (max_fecha - min_fecha).days)
        x = 0.05 + x_norm * 0.90
        
        color = COLORES_EVENTO.get(evento.get("tipo", "tramite"), "#888")
        alternado = i % 2  # Alternar arriba/abajo
        y_punto = 0.5
        y_texto = 0.70 if alternado else 0.30
        y_linea_fin = y_texto - 0.05 if alternado else y_texto + 0.05
        
        # Punto en la línea
        ax.plot(x, y_punto, "o", color=color, markersize=8, transform=ax.transAxes, zorder=5)
        
        # Línea vertical
        ax.plot([x, x], [y_punto, y_linea_fin], "-", color=color, linewidth=1,
                transform=ax.transAxes, alpha=0.6)
        
        # Etiqueta: año + descripción
        ax.text(x, y_texto + (0.05 if alternado else -0.05),
                f"{fecha.year}\n{evento['descripcion'][:40]}",
                ha="center", va="bottom" if alternado else "top",
                fontsize=6.5, color="#1C1C1C",
                transform=ax.transAxes, wrap=True)
    
    ax.set_title("Línea de Tiempo — Trayectoria Organizativa de la Comunidad",
                fontsize=12, fontweight="bold", color="#1A3A5C", pad=10)
    
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path

def _parsear_fecha(fecha_str: str) -> datetime | None:
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%Y", "%d de %B de %Y"]
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_str, fmt)
        except:
            continue
    # Solo año
    match = re.search(r"\b(\d{4})\b", fecha_str)
    if match:
        return datetime(int(match.group(1)), 1, 1)
    return None
```

---

## PARTE 3 — INTEGRACIÓN DE ANÁLISIS IA EN EL INFORME

### 3.1 Justificaciones Teóricas Estandarizadas

El sistema incluye textos predefinidos por tipo de análisis para insertar en el informe. Estos textos corresponden a las justificaciones teóricas y referencias académicas que el equipo de la Universidad de Cartagena ha estandarizado.

```python
# backend/app/reports/justificaciones.py

JUSTIFICACIONES = {
    "practicas_culturales": """
Las prácticas culturales registradas constituyen indicadores objetivos de la continuidad de la 
identidad étnica de la comunidad, conforme al criterio de autorreconocimiento establecido en el 
Convenio 169 de la OIT (Ley 21 de 1991). La georeferenciación de estas prácticas permite 
evidenciar su anclaje territorial, condición indispensable para el reconocimiento de la 
integración hombre-territorio como elemento definitorio de la identidad indígena 
(Corte Constitucional, Sentencia T-349 de 1996).
""",
    "buffer_influencia": """
Los buffers de influencia de {radio}m generados sobre las capas principales permiten delimitar 
el área de influencia cultural y territorial de cada elemento levantado en campo. Esta metodología, 
estándar en estudios de geografía cultural aplicada, posibilita la cuantificación del espacio 
culturalmente significativo y su eventual superposición con áreas de conflicto territorial 
(Escobar, 2010; Santos, 2000).
""",
    "superposicion_pc_po": """
La superposición entre las zonas de influencia de las Prácticas Culturales ({area_pc_m2:.0f} m²) 
y los Procesos Organizativos ({area_po_m2:.0f} m²) evidencia una integración espacial de 
{interseccion_m2:.0f} m² ({porcentaje:.1f}% de solapamiento), lo que confirma la 
co-presencia física del ejercicio cultural y el ejercicio del gobierno propio — condición 
que la jurisprudencia colombiana ha reconocido como evidencia de vigencia organizativa 
(Corte Constitucional, Sentencia SU-510 de 1998).
""",
}

def obtener_justificacion(tipo: str, parametros: dict = None) -> str:
    texto = JUSTIFICACIONES.get(tipo, "")
    if parametros:
        texto = texto.format(**parametros)
    return texto.strip()
```
