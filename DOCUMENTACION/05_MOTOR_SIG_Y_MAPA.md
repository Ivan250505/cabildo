# EtnoSIG — Motor SIG y Mapa Georreferenciado
## Especificación Técnica Detallada

---

## 1. Capas SIG — Definición Completa

### 1.1 Capas Puntuales (PUNT) — Análisis Principal

Las cuatro capas puntuales son el núcleo del análisis geoespacial. Se levantan en campo con GPS.

#### PUNT — Prácticas Culturales
| Atributo | Tipo | Descripción |
|---|---|---|
| id | integer | Identificador único del punto |
| nombre | string | Nombre descriptivo del sitio/práctica |
| tipo_practica | string | Enum: Pesca, Medicina, Caza, Cocina, Agricultura, Artesanía, Ritual, Ceremonia, Minga, Transmisión_Saberes |
| descripcion | text | Descripción detallada |
| fecha_registro | date | Fecha de levantamiento GPS |
| responsable | string | Quien levantó el punto |
| foto_referencia | string | ID de foto asociada |
| geometry | Point (WGS84) | Coordenadas GPS |

#### PUNT — Expresiones Simbólicas
| Atributo | Tipo | Descripción |
|---|---|---|
| id | integer | — |
| nombre | string | — |
| tipo_expresion | string | Enum: Lugar_Sagrado, Sitio_Memoria, Elemento_Simbólico, Cementerio_Ancestral, Sitio_Arqueológico |
| descripcion | text | — |
| estado_conservacion | string | Bien conservado / Deteriorado / En riesgo |
| geometry | Point | — |

#### PUNT — Entornos Territoriales
| Atributo | Tipo | Descripción |
|---|---|---|
| id | integer | — |
| nombre | string | — |
| tipo_entorno | string | Enum: Zona_Uso_Tradicional, Cultivo, Protección_Ambiental, Territorio_Ancestral, Zona_Riesgo, Zona_Conflicto |
| uso_actual | string | — |
| uso_tradicional | string | — |
| geometry | Point | — |

#### PUNT — Procesos Organizativos
| Atributo | Tipo | Descripción |
|---|---|---|
| id | integer | — |
| nombre | string | — |
| tipo_proceso | string | Enum: Asamblea, Gobierno_Propio, Organización_Productiva, Control_Territorial, Guardia_Indígena, Mambeadero |
| frecuencia | string | Diaria/Semanal/Mensual/Eventual |
| geometry | Point | — |

### 1.2 Capas Poligonales (POL) — Soporte Topográfico

| Capa | Atributos clave |
|---|---|
| Infraestructura_Comunitaria_POL | tipo (Maloca/Vivienda/Taller/Comedor/Asamblea/Cementerio), estado, area_m2 |
| Zonas_Ambientales_POL | tipo (Bosque/Selva/Humedal/Deforestación/Recuperación), cobertura_ha |
| Actividades_Extractivas_POL | tipo (Minería/Hidrocarburos/Forestal/Agroindustria), impacto |

### 1.3 Capas Lineales (LIN) — Conectividad

| Capa | Atributos clave |
|---|---|
| Hidrografia_LIN | tipo (Río/Quebrada/Caño/Laguna), nombre, navegabilidad |
| Vias_Vehiculares_LIN | tipo (Pavimentada/Sin_pavimentar/Servidumbre), estado |
| Caminos_Senderos_LIN | tipo (Cotidiano/Ancestral), valor_espiritual (bool) |
| Linderos_Cercas_LIN | tipo (Con_cerca/Sin_cerca), propietario_colindante |

---

## 2. Algoritmos de Análisis Espacial

### 2.1 Buffers de Influencia

**Propósito:** Determinar el área de influencia de cada práctica/elemento cultural.

```python
from geopandas import GeoDataFrame
import geopandas as gpd

CRS_COLOMBIA = "EPSG:3116"  # MAGNA-SIRGAS / Colombia Bogota (metros)
CRS_WGS84   = "EPSG:4326"  # Geográfico (grados)

def calcular_buffers(capas: dict, radio_metros: int = 50) -> dict:
    """
    capas: {"PC": GeoDataFrame, "ES": GeoDataFrame, "ET": GeoDataFrame, "PO": GeoDataFrame}
    Retorna: {"Buffer_PC": GeoDataFrame, "Buffer_ES": ..., ...}
    """
    resultados = {}
    for codigo, gdf in capas.items():
        gdf_m = gdf.to_crs(CRS_COLOMBIA)
        buffer_geom = gdf_m.geometry.buffer(radio_metros)
        union = buffer_geom.union_all()
        buffer_gdf = gpd.GeoDataFrame(
            [{"capa": codigo, "radio_m": radio_metros, "area_m2": union.area}],
            geometry=[union],
            crs=CRS_COLOMBIA
        ).to_crs(CRS_WGS84)
        resultados[f"Buffer_{codigo}"] = buffer_gdf
    return resultados
```

### 2.2 Matrices de Distancia

**Propósito:** Medir proximidad espacial entre elementos de capas distintas (ej: rituales ↔ gobierno).

```python
import pandas as pd
from itertools import combinations

def calcular_todas_las_matrices(capas: dict) -> dict:
    """
    Genera las 6 matrices de distancia entre pares de capas.
    """
    codigos = list(capas.keys())  # ["PC", "ES", "ET", "PO"]
    matrices = {}
    for a, b in combinations(codigos, 2):
        clave = f"Matriz_{a}_{b}"
        matrices[clave] = _calcular_matriz_par(capas[a], capas[b])
    return matrices

def _calcular_matriz_par(gdf_a: GeoDataFrame, gdf_b: GeoDataFrame) -> pd.DataFrame:
    a_m = gdf_a.to_crs(CRS_COLOMBIA)
    b_m = gdf_b.to_crs(CRS_COLOMBIA)
    filas = []
    for _, fila_a in a_m.iterrows():
        for _, fila_b in b_m.iterrows():
            dist = fila_a.geometry.distance(fila_b.geometry)
            filas.append({
                "punto_a": fila_a.get("nombre", str(fila_a.name)),
                "tipo_a": fila_a.get("tipo_practica") or fila_a.get("tipo_expresion") or fila_a.get("tipo_entorno") or fila_a.get("tipo_proceso"),
                "punto_b": fila_b.get("nombre", str(fila_b.name)),
                "tipo_b": fila_b.get("tipo_practica") or fila_b.get("tipo_expresion") or fila_b.get("tipo_entorno") or fila_b.get("tipo_proceso"),
                "distancia_m": round(dist, 2),
                "distancia_categoria": _categorizar_distancia(dist)
            })
    return pd.DataFrame(filas).sort_values("distancia_m")

def _categorizar_distancia(dist_m: float) -> str:
    if dist_m < 10: return "Adyacente"
    if dist_m < 50: return "Próximo"
    if dist_m < 200: return "Cercano"
    if dist_m < 1000: return "Moderado"
    return "Distante"
```

### 2.3 Superposiciones Territoriales

**Propósito:** Identificar solapamientos espaciales entre zonas de influencia de distintas capas (evidencia de co-presencia cultural).

```python
def calcular_todas_las_superposiciones(buffers: dict) -> dict:
    """
    buffers: {"Buffer_PC": GDF, "Buffer_ES": GDF, "Buffer_ET": GDF, "Buffer_PO": GDF}
    """
    codigos = ["PC", "ES", "ET", "PO"]
    interpretaciones = {
        ("PC", "ES"): "Paisajes culturales — prácticas cotidianas y memoria simbólica comparten espacio",
        ("PC", "ET"): "Uso cultural del territorio — actividades sobre entornos específicos",
        ("PC", "PO"): "Cultura y gobierno integrados — prácticas bajo liderazgo organizativo",
        ("ES", "ET"): "Emplazamiento de lugares sagrados en entornos territoriales",
        ("ES", "PO"): "Autoridad sobre el patrimonio simbólico — gobernanza cultural",
        ("ET", "PO"): "Control territorial organizado — respuesta organizativa a condiciones",
    }
    resultados = {}
    for a, b in combinations(codigos, 2):
        buffer_a = buffers[f"Buffer_{a}"].to_crs(CRS_COLOMBIA)
        buffer_b = buffers[f"Buffer_{b}"].to_crs(CRS_COLOMBIA)
        geom_a = buffer_a.geometry.union_all()
        geom_b = buffer_b.geometry.union_all()
        interseccion = geom_a.intersection(geom_b)
        resultados[f"Superposicion_{a}_{b}"] = {
            "area_a_m2": round(geom_a.area, 2),
            "area_b_m2": round(geom_b.area, 2),
            "interseccion_m2": round(interseccion.area, 2),
            "porcentaje_solapamiento": round(interseccion.area / min(geom_a.area, geom_b.area) * 100, 1) if not interseccion.is_empty else 0,
            "interpretacion": interpretaciones.get((a, b), "")
        }
    return resultados
```

### 2.4 Generación de Mapas Temáticos

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import contextily as ctx
from matplotlib_scalebar.scalebar import ScaleBar

COLORES_CAPAS = {
    "PC": "#B22222",  # Rojo — Prácticas Culturales
    "ES": "#C8922A",  # Oro   — Expresiones Simbólicas
    "ET": "#1A3A5C",  # Navy  — Entornos Territoriales
    "PO": "#16a34a",  # Verde — Procesos Organizativos
}

SIMBOLOS_CAPAS = {
    "PC": "o",   # círculo
    "ES": "^",   # triángulo
    "ET": "s",   # cuadrado
    "PO": "D",   # diamante
}

def generar_mapa_capa(
    capa_principal: GeoDataFrame,
    codigo: str,
    capas_soporte: dict,
    titulo: str,
    output_path: str,
    dpi: int = 300
) -> str:
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    # Capas de soporte (en escala de grises, fondo)
    for nombre, gdf in capas_soporte.items():
        gdf.to_crs("EPSG:3857").plot(ax=ax, color="#AAAAAA", alpha=0.3, linewidth=0.5)
    
    # Capa principal
    capa_m = capa_principal.to_crs("EPSG:3857")
    capa_m.plot(
        ax=ax,
        color=COLORES_CAPAS[codigo],
        marker=SIMBOLOS_CAPAS[codigo],
        markersize=10,
        edgecolor="white",
        linewidth=0.5,
        zorder=5
    )
    
    # Tiles de fondo
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=14)
    
    # Título
    ax.set_title(titulo, fontsize=14, fontweight="bold", color="#1A3A5C", pad=15)
    ax.set_axis_off()
    
    # Escala
    ax.add_artist(ScaleBar(1, location="lower_right"))
    
    # Norte (flecha)
    ax.annotate("N", xy=(0.96, 0.96), xytext=(0.96, 0.91),
                xycoords="axes fraction",
                arrowprops=dict(facecolor="black", width=2),
                ha="center", fontsize=10, fontweight="bold")
    
    # Leyenda
    patch = mpatches.Patch(color=COLORES_CAPAS[codigo], label=titulo)
    ax.legend(handles=[patch], loc="lower left", framealpha=0.8)
    
    # Fuente
    fig.text(0.01, 0.01, "Fuente: Levantamiento GPS en campo — Universidad de Cartagena 2026",
             fontsize=7, color="gray")
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def generar_mapa_integrado(capas: dict, capas_soporte: dict, output_path: str) -> str:
    """Mapa con las 4 capas superpuestas."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    
    for codigo, gdf in capas.items():
        gdf.to_crs("EPSG:3857").plot(
            ax=ax, color=COLORES_CAPAS[codigo],
            marker=SIMBOLOS_CAPAS[codigo], markersize=9,
            edgecolor="white", linewidth=0.5, label=_nombre_capa(codigo), zorder=5
        )
    
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=14)
    ax.set_title("Mapa Integrado — Análisis SIG Comunidad Indígena", fontsize=14,
                fontweight="bold", color="#1A3A5C", pad=15)
    ax.set_axis_off()
    ax.legend(loc="lower left", framealpha=0.9)
    ax.add_artist(ScaleBar(1, location="lower_right"))
    fig.text(0.01, 0.01, "Fuente: Universidad de Cartagena — Contrato UC-CPS-MINTERIOR-023-2026",
             fontsize=7, color="gray")
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path

def _nombre_capa(codigo: str) -> str:
    nombres = {"PC": "Prácticas Culturales", "ES": "Expresiones Simbólicas",
               "ET": "Entornos Territoriales", "PO": "Procesos Organizativos"}
    return nombres.get(codigo, codigo)
```

---

## 3. Lectura de Proyectos QGIS

```python
import fiona
import geopandas as gpd

NOMBRES_CAPAS_ESPERADAS = {
    "PC": ["PracticasCulturales", "Practicas_Culturales", "PUNT_PC"],
    "ES": ["ExpresionesSimbólicas", "Expresiones_Simbolicas", "PUNT_ES"],
    "ET": ["EntornosTerritoriales", "Entornos_Territoriales", "PUNT_ET"],
    "PO": ["ProcesosOrganizativos", "Procesos_Organizativos", "PUNT_PO"],
}

def leer_geopackage(ruta_gpkg: str) -> dict:
    """Lee un GeoPackage y retorna las 4 capas principales + capas de soporte."""
    capas_disponibles = fiona.listlayers(ruta_gpkg)
    capas_principales = {}
    capas_soporte = {}
    
    for capa_nombre in capas_disponibles:
        codigo = _identificar_capa(capa_nombre)
        gdf = gpd.read_file(ruta_gpkg, layer=capa_nombre)
        if codigo:
            capas_principales[codigo] = gdf
        else:
            capas_soporte[capa_nombre] = gdf
    
    # Validar que las 4 capas principales existen
    faltantes = [c for c in ["PC", "ES", "ET", "PO"] if c not in capas_principales]
    if faltantes:
        raise ValueError(f"Capas faltantes en GeoPackage: {faltantes}")
    
    return {"principales": capas_principales, "soporte": capas_soporte}

def _identificar_capa(nombre: str) -> str | None:
    nombre_lower = nombre.lower().replace(" ", "_").replace("á","a").replace("é","e")
    for codigo, variantes in NOMBRES_CAPAS_ESPERADAS.items():
        for variante in variantes:
            if variante.lower() in nombre_lower:
                return codigo
    return None
```

---

## 4. Mapa Interactivo Web (Leaflet.js)

### 4.1 Inicialización del Mapa

```javascript
// frontend/js/pages/map_view.js

const COLOMBIA_CENTER = [4.5, -74.0];
const COLOMBIA_ZOOM   = 5;

const COLORES_ESTADO = {
  "en_proceso":  "#1A3A5C",  // navy
  "aprobado":    "#B22222",  // rojo institucional
  "exportado":   "#C8922A",  // oro
};

function initMap() {
  const map = L.map("map-container", {
    center: COLOMBIA_CENTER,
    zoom: COLOMBIA_ZOOM,
    zoomControl: true,
  });

  // Tile base — OpenStreetMap
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 18,
  }).addTo(map);

  // Cargar resguardos desde API
  loadResguardos(map);
  
  return map;
}

async function loadResguardos(map) {
  const departamento = document.getElementById("filtro-departamento").value;
  const url = `/api/map/resguardos${departamento ? "?departamento=" + departamento : ""}`;
  const res = await apiFetch(url);
  const geojson = await res.json();
  
  L.geoJSON(geojson, {
    pointToLayer: (feature, latlng) => {
      const color = COLORES_ESTADO[feature.properties.estado] || "#888";
      return L.circleMarker(latlng, {
        radius: 8,
        fillColor: color,
        color: "white",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9,
      });
    },
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      layer.bindPopup(`
        <div class="map-popup">
          <strong style="color:#1A3A5C; font-size:14px">${p.nombre_comunidad}</strong><br>
          <em>${p.pueblo_indigena}</em><br>
          <hr style="margin:6px 0">
          <b>Municipio:</b> ${p.municipio}, ${p.departamento}<br>
          <b>Población:</b> ${p.personas} personas / ${p.familias} familias<br>
          <b>Estado:</b> <span style="color:${COLORES_ESTADO[p.estado]}">${p.estado}</span><br>
          <b>Gobernador/a:</b> ${p.gobernador || "—"}<br>
          <hr style="margin:6px 0">
          <a href="/estudios/${p.study_id}" style="color:#B22222">Ver detalle del estudio →</a>
        </div>
      `, { maxWidth: 280 });
    }
  }).addTo(map);
}
```

### 4.2 Leyenda del Mapa

```javascript
function addLegend(map) {
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "map-legend");
    div.innerHTML = `
      <h4>Estado del Estudio</h4>
      <div><span style="background:#1A3A5C"></span> En proceso</div>
      <div><span style="background:#B22222"></span> Aprobado</div>
      <div><span style="background:#C8922A"></span> Exportado</div>
    `;
    return div;
  };
  legend.addTo(map);
}
```

---

## 5. Validación de Resultados SIG

El sistema debe validar que sus resultados coincidan con los producidos manualmente en QGIS.

### Test de Reproducibilidad

```python
# tests/test_gis.py

def test_buffers_murui_muina():
    """Valida que los buffers coincidan con los calculados en QGIS."""
    capas = leer_geopackage("tests/fixtures/ETNIA1_MURUI_MUINA.gpkg")
    buffers = calcular_buffers(capas["principales"], radio_metros=50)
    
    # Valores de referencia del análisis manual en QGIS
    assert abs(buffers["Buffer_PC"].geometry.area.sum() - 12450.3) < 100  # m² ±100
    assert abs(buffers["Buffer_PO"].geometry.area.sum() - 3200.4) < 100

def test_distancia_ritual_gobierno():
    """Valida la distancia Rituales → Asambleas_Gobierno del ejemplo Murui Muina."""
    # Dato de referencia del informe: 4.82 metros
    capas = leer_geopackage("tests/fixtures/ETNIA1_MURUI_MUINA.gpkg")
    matriz = _calcular_matriz_par(capas["principales"]["PC"], capas["principales"]["PO"])
    rituales_gobierno = matriz[
        (matriz["tipo_a"] == "Ritual") & (matriz["tipo_b"].str.contains("Asamblea"))
    ]
    assert rituales_gobierno["distancia_m"].min() == pytest.approx(4.82, abs=0.5)
```

---

## 6. CRS y Proyecciones Utilizadas

| CRS | EPSG | Uso |
|---|---|---|
| WGS84 | 4326 | Almacenamiento y transferencia (Google Drive, API) |
| MAGNA-SIRGAS Colombia Bogota | 3116 | Cálculos de distancia y área (metros) |
| Web Mercator | 3857 | Visualización en mapas web con Leaflet/Contextily |

```python
# Regla: 
# - Almacén: EPSG:4326
# - Cálculo: EPSG:3116 (reproyectar antes, restaurar después)
# - Visualización: EPSG:3857 (contextily lo maneja internamente)
```
