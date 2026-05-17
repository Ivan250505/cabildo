"""
SIG engine: buffers, distance matrices, spatial overlaps, and thematic map generation.
Always uses EPSG:3116 (Colombia Magna-Sirgas / Bogotá) for metric calculations,
then reprojects to EPSG:4326 for storage and EPSG:3857 for basemap rendering.
"""
from __future__ import annotations

import io
import itertools
from pathlib import Path
from typing import TypeAlias

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from pyproj import CRS
from shapely.geometry import MultiPoint

matplotlib.use("Agg")  # non-interactive backend for server use

# ── CRS constants ─────────────────────────────────────────────────────────────

CRS_GEO = CRS.from_epsg(4326)     # geographic — storage
CRS_COL = CRS.from_epsg(3116)     # Colombia metric — calculations
CRS_WEB = CRS.from_epsg(3857)     # Web Mercator — basemap tiles

# ── Layer colours (institutional palette) ─────────────────────────────────────

LAYER_STYLES: dict[str, dict] = {
    "Practicas_Culturales_PUNT":    {"color": "#B22222", "label": "Prácticas Culturales"},
    "Expresiones_Simbolicas_PUNT":  {"color": "#C8922A", "label": "Expresiones Simbólicas"},
    "Entornos_Territoriales_PUNT":  {"color": "#2E7D32", "label": "Entornos Territoriales"},
    "Procesos_Organizativos_PUNT":  {"color": "#1A3A5C", "label": "Procesos Organizativos"},
}

LayerName: TypeAlias = str


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_layer(path: str | Path, layer_name: str | None = None) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path, layer=layer_name)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_GEO)
    return gdf


def load_layers(base_dir: str | Path) -> dict[LayerName, gpd.GeoDataFrame]:
    """
    Load all four main SIG layers from a directory containing .gpkg files.
    Skips layers with 0 features (template layers not yet populated).
    """
    base_dir = Path(base_dir)
    layers: dict[LayerName, gpd.GeoDataFrame] = {}
    for name in LAYER_STYLES:
        gpkg = base_dir / f"{name}.gpkg"
        if gpkg.exists():
            gdf = load_layer(gpkg)
            if len(gdf) > 0:
                layers[name] = gdf
    return layers


# ── Buffers ───────────────────────────────────────────────────────────────────

def compute_buffers(
    gdf: gpd.GeoDataFrame, buffer_m: float = 50
) -> gpd.GeoDataFrame:
    """Return a new GDF with buffer polygons, preserving native metric CRS."""
    projected = _to_metric(gdf)
    buffered = projected.copy()
    buffered["geometry"] = projected.geometry.buffer(buffer_m)
    return buffered


def buffer_all_layers(
    layers: dict[LayerName, gpd.GeoDataFrame], buffer_m: float = 50
) -> dict[LayerName, gpd.GeoDataFrame]:
    return {name: compute_buffers(gdf, buffer_m) for name, gdf in layers.items()}


# ── Distance matrix ───────────────────────────────────────────────────────────

def _to_metric(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject to a metric CRS. Prefers CRS_COL; if native CRS is already metric, keeps it."""
    if gdf.crs and gdf.crs.is_projected:
        return gdf  # already in a metric CRS (e.g. ESRI:103599)
    return gdf.to_crs(CRS_COL)


def _centroid_col(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    projected = _to_metric(gdf)
    projected = projected.copy()
    projected["_centroid"] = projected.geometry.centroid
    return projected


def pairwise_distance_matrix(
    gdf_a: gpd.GeoDataFrame, gdf_b: gpd.GeoDataFrame, name_a: str, name_b: str
) -> dict:
    """
    Compute nearest-neighbour distance (metres) from every point in layer A
    to layer B and vice-versa. Returns summary statistics.
    """
    pa = _centroid_col(gdf_a)
    pb = _centroid_col(gdf_b)

    centroids_b = gpd.GeoDataFrame(geometry=pb["_centroid"].values, crs=pb.crs)

    distances: list[float] = []
    for geom in pa["_centroid"]:
        dists = centroids_b.geometry.distance(geom)
        distances.append(float(dists.min()))

    arr = np.array(distances)
    return {
        "capas": [name_a, name_b],
        "n_puntos_a": len(pa),
        "n_puntos_b": len(pb),
        "distancia_min_m": round(float(arr.min()), 2),
        "distancia_max_m": round(float(arr.max()), 2),
        "distancia_media_m": round(float(arr.mean()), 2),
        "distancia_mediana_m": round(float(np.median(arr)), 2),
    }


def compute_distance_matrices(
    layers: dict[LayerName, gpd.GeoDataFrame],
) -> list[dict]:
    """Compute the 6 pairwise distance matrices for the 4 main layers (C(4,2) = 6)."""
    results = []
    for name_a, name_b in itertools.combinations(layers.keys(), 2):
        matrix = pairwise_distance_matrix(
            layers[name_a], layers[name_b], name_a, name_b
        )
        results.append(matrix)
    return results


# ── Spatial overlaps ──────────────────────────────────────────────────────────

def compute_overlap(
    buffers_a: gpd.GeoDataFrame,
    buffers_b: gpd.GeoDataFrame,
    name_a: str,
    name_b: str,
) -> dict:
    """
    Spatial intersection between two buffered layers.
    Returns total overlap area (m²) and overlap GeoDataFrame.
    """
    union_a = _to_metric(buffers_a).geometry.unary_union
    union_b = _to_metric(buffers_b).geometry.unary_union
    intersection = union_a.intersection(union_b)

    area_a = union_a.area
    area_b = union_b.area
    area_overlap = intersection.area

    return {
        "capas": [name_a, name_b],
        "area_buffer_a_m2": round(area_a, 2),
        "area_buffer_b_m2": round(area_b, 2),
        "area_interseccion_m2": round(area_overlap, 2),
        "porcentaje_interseccion_a": round(area_overlap / area_a * 100, 2) if area_a else 0,
        "porcentaje_interseccion_b": round(area_overlap / area_b * 100, 2) if area_b else 0,
        "hay_solapamiento": area_overlap > 0,
    }


def compute_all_overlaps(
    buffered_layers: dict[LayerName, gpd.GeoDataFrame],
) -> list[dict]:
    """Compute the 6 pairwise overlaps for the 4 buffered main layers."""
    results = []
    keys = list(buffered_layers.keys())
    for name_a, name_b in itertools.combinations(keys, 2):
        overlap = compute_overlap(
            buffered_layers[name_a], buffered_layers[name_b], name_a, name_b
        )
        results.append(overlap)
    return results


# ── Map generation ────────────────────────────────────────────────────────────

def _add_basemap(ax, crs_str: str = "EPSG:3857") -> None:
    """Add OpenStreetMap basemap tiles to the axes. Silently skips if offline."""
    try:
        import contextily as ctx
        ctx.add_basemap(ax, crs=crs_str, source=ctx.providers.OpenStreetMap.Mapnik, zoom=17)
    except Exception:
        pass  # network unavailable — map renders without basemap


def generate_overview_map(
    layers: dict[LayerName, gpd.GeoDataFrame],
    buffered_layers: dict[LayerName, gpd.GeoDataFrame],
    buffer_m: float = 50,
    title: str = "Mapa de Distribución Territorial",
    dpi: int = 200,
) -> bytes:
    """Generate the overview thematic map. Returns PNG bytes."""
    fig, ax = plt.subplots(figsize=(14, 10))

    # Compute combined extent in Web Mercator for basemap alignment
    all_geoms = []
    for gdf in layers.values():
        all_geoms.append(gdf.to_crs(CRS_WEB))

    # Draw buffers (semi-transparent)
    for name, buf_gdf in buffered_layers.items():
        style = LAYER_STYLES.get(name, {"color": "#888888"})
        buf_gdf.to_crs(CRS_WEB).plot(
            ax=ax, color=style["color"], alpha=0.15, edgecolor=style["color"],
            linewidth=0.5,
        )

    # Draw points on top
    handles = []
    for name, gdf in layers.items():
        style = LAYER_STYLES.get(name, {"color": "#888888", "label": name})
        gdf_web = gdf.to_crs(CRS_WEB)
        gdf_web.plot(
            ax=ax, color=style["color"], markersize=40, marker="o",
            edgecolor="white", linewidth=0.8, zorder=5,
        )
        handles.append(
            plt.Line2D(
                [0], [0], marker="o", color="w", markerfacecolor=style["color"],
                markersize=9, label=style["label"],
            )
        )

    _add_basemap(ax, crs_str="EPSG:3857")

    ax.legend(handles=handles, loc="lower right", framealpha=0.9, fontsize=9)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_axis_off()

    fig.text(
        0.01, 0.01,
        f"Buffer: {buffer_m} m  |  CRS: EPSG:4326  |  Fuente: EtnoSIG",
        fontsize=7, color="#666666",
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_layer_map(
    layer_name: str,
    gdf: gpd.GeoDataFrame,
    buffer_gdf: gpd.GeoDataFrame,
    title: str | None = None,
    dpi: int = 200,
) -> bytes:
    """Generate a single-layer thematic map. Returns PNG bytes."""
    style = LAYER_STYLES.get(layer_name, {"color": "#1A3A5C", "label": layer_name})
    title = title or style.get("label", layer_name)

    fig, ax = plt.subplots(figsize=(12, 9))

    buffer_gdf.to_crs(CRS_WEB).plot(
        ax=ax, color=style["color"], alpha=0.2,
        edgecolor=style["color"], linewidth=0.6,
    )
    gdf.to_crs(CRS_WEB).plot(
        ax=ax, color=style["color"], markersize=50, marker="o",
        edgecolor="white", linewidth=0.8, zorder=5,
    )

    _add_basemap(ax, crs_str="EPSG:3857")

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_axis_off()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Full analysis pipeline ────────────────────────────────────────────────────

def run_full_analysis(
    layers_dir: str | Path,
    buffer_m: float = 50,
) -> dict:
    """
    Run the complete SIG analysis for a study.
    Returns a dict with all numeric results and map PNG bytes.
    """
    layers = load_layers(layers_dir)
    if not layers:
        raise ValueError(f"No se encontraron capas SIG en: {layers_dir}")

    buffered = buffer_all_layers(layers, buffer_m)
    distance_matrices = compute_distance_matrices(layers)
    overlaps = compute_all_overlaps(buffered)
    overview_png = generate_overview_map(layers, buffered, buffer_m)

    layer_maps: dict[str, bytes] = {}
    for name, gdf in layers.items():
        layer_maps[name] = generate_layer_map(name, gdf, buffered[name])

    return {
        "capas_cargadas": list(layers.keys()),
        "n_puntos_por_capa": {name: len(gdf) for name, gdf in layers.items()},
        "buffer_metros": buffer_m,
        "matrices_distancia": distance_matrices,
        "solapamientos": overlaps,
        "mapa_general_png": overview_png,
        "mapas_por_capa_png": layer_maps,
    }
