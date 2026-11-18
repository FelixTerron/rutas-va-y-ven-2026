"""Acceso ponderado por población: % de las personas (no de la calle) por distancia a una parada.

Datos (INEGI, Censo de Población y Vivienda 2020, ver ``docs/DATA_SOURCES.md``): población total por
manzana urbana (``POBTOT``) y los polígonos del Marco Geoestadístico 2020.

Método:
1. Manzanas urbanas con polígono cuyo centroide cae dentro del área de la red peatonal
   (``streets.bbox``: paradas con servicio + ~2 km). Las zonas rurales no tienen cifras por manzana.
2. **Cifra central:** cada manzana toma la distancia caminando (``walk_m``) del punto de calle más
   cercano a su centroide (``access.walk_access``), si está a <= ``MAX_SNAP_M``.
3. **Rango:** la distancia depende de por qué calle salga la gente de la manzana. Se repite el
   cálculo con la mejor calle del borde de la manzana (optimista) y con la peor (pesimista).
4. Sin calle cercana: si el centroide queda a más de ``access.KEEP_RADIUS_M`` en línea recta de toda
   parada, caminando serían más de 2 km (clase «más de 2 km»); si no, se reporta aparte
   (``no_street``) y no entra en los porcentajes.

Uso (desde la raíz del repo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.population [weekday|saturday|sunday]
"""

from __future__ import annotations

import functools
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from va_y_ven import access, gtfs, streets

INEGI_DIR = gtfs.RAW_DIR / "inegi"
CENSUS_CSV = (
    INEGI_DIR
    / "censo2020_ageb_mza/ageb_mza_urbana_31_cpv2020/conjunto_de_datos"
    / "conjunto_de_datos_ageb_urbana_31_cpv2020.csv"
)
BLOCKS_SHP = INEGI_DIR / "mg2020/conjunto_de_datos/31m.shp"
MAX_SNAP_M = 150.0  # una manzana a más de esto de cualquier punto de calle no se asigna
EDGE_REACH_M = 40.0  # calles "del borde": puntos de calle a <= esto del polígono de la manzana
EDGES = [200, 400, 800, access.MAX_M]  # mismos cortes que el mapa de acceso; clase 4 = más lejos


@functools.cache
def blocks() -> gpd.GeoDataFrame:
    """Manzanas urbanas del área de la red peatonal: polígonos (EPSG:32616), ``MUN`` y ``pob``."""
    if not CENSUS_CSV.exists() or not BLOCKS_SHP.exists():
        raise FileNotFoundError("Faltan los datos de INEGI: ver docs/DATA_SOURCES.md")
    cols = ["ENTIDAD", "MUN", "LOC", "AGEB", "MZA", "POBTOT"]
    table = pd.read_csv(CENSUS_CSV, dtype=str, usecols=cols)
    table = table[table["MZA"] != "000"]  # 000 = total de AGEB, no es una manzana
    table["CVEGEO"] = table["ENTIDAD"] + table["MUN"] + table["LOC"] + table["AGEB"] + table["MZA"]
    table["pob"] = pd.to_numeric(table["POBTOT"])  # POBTOT no trae valores reservados
    polygons = gpd.read_file(BLOCKS_SHP)[["CVEGEO", "geometry"]]
    both = polygons.merge(table[["CVEGEO", "MUN", "pob"]], on="CVEGEO")  # solo las que tienen ambos
    both = both.to_crs(access.CRS_METERS)
    west, south, east, north = streets.bbox()
    center = both.geometry.centroid.to_crs(4326)
    inside = (center.x >= west) & (center.x <= east) & (center.y >= south) & (center.y <= north)
    return both[inside].reset_index(drop=True)


def assign_classes(
    centroids: np.ndarray, points: gpd.GeoDataFrame, stops: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Clase de acceso (0..4, como en el mapa) de cada centroide, y qué manzanas no se asignan.

    ``centroids`` y ``stops``: arreglos de puntos (shapely, en metros); ``points``: salida de
    ``access.walk_access`` (puntos de calle con ``walk_m``). Devuelve ``(clase, sin_calle,
    en_calle)``: ``en_calle`` = hay un punto de calle a <= ``MAX_SNAP_M``; ``sin_calle`` = no lo hay
    pero sí una parada a <= ``access.KEEP_RADIUS_M`` (su clase no es válida).
    """
    street_pts = points.geometry.to_numpy()
    nearest = shapely.STRtree(street_pts).nearest(centroids)
    on_street = shapely.distance(centroids, street_pts[nearest]) <= MAX_SNAP_M
    klass = np.digitize(points["walk_m"].to_numpy()[nearest], EDGES, right=True)
    stop_dist = shapely.distance(centroids, stops[shapely.STRtree(stops).nearest(centroids)])
    far_from_stops = stop_dist > access.KEEP_RADIUS_M  # caminando serían más de 2 km
    klass = np.where(~on_street & far_from_stops, len(EDGES), klass)
    return klass, ~on_street & ~far_from_stops, on_street


def edge_walk(polygons: np.ndarray, points: gpd.GeoDataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Mejor y peor distancia caminando entre los puntos de calle del borde de cada manzana.

    Devuelve ``(mínimo, máximo)`` por manzana; ``nan`` si ningún punto de calle queda a
    <= ``EDGE_REACH_M`` del polígono.
    """
    street_pts = points.geometry.to_numpy()
    walk = points["walk_m"].to_numpy()
    reach = shapely.buffer(polygons, EDGE_REACH_M)
    which, hit = shapely.STRtree(street_pts).query(reach, predicate="intersects")
    per_block = pd.DataFrame({"i": which, "w": walk[hit]}).groupby("i")["w"].agg(["min", "max"])
    low, high = np.full(len(polygons), np.nan), np.full(len(polygons), np.nan)
    low[per_block.index.to_numpy()] = per_block["min"].to_numpy()
    high[per_block.index.to_numpy()] = per_block["max"].to_numpy()
    return low, high


def _shares(klass: np.ndarray, pob: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """% de la población válida en cada clase (0..4)."""
    by_class = np.bincount(klass[valid], weights=pob[valid], minlength=len(EDGES) + 1)
    return by_class / by_class.sum() * 100


def population_by_class(points: gpd.GeoDataFrame, stops: gpd.GeoDataFrame) -> dict:
    """Población por clase de acceso. ``points`` y ``stops`` en EPSG:32616.

    Devuelve ``pct`` (5 clases, % de la población asignada), ``le400`` y ``gt800`` (% a <= 400 m y
    a > 800 m), sus rangos ``le400_range`` / ``gt800_range`` (enteros, de menor a mayor: calle del
    borde optimista y pesimista), ``total`` (personas en la zona), ``no_street`` (personas sin
    calle cercana, fuera de los %) y ``blocks``.
    """
    b = blocks()
    pob = b["pob"].to_numpy()
    klass, no_street, on_street = assign_classes(
        b.geometry.centroid.to_numpy(), points, stops.geometry.to_numpy()
    )
    valid = ~no_street
    low, high = edge_walk(b.geometry.to_numpy(), points)

    def variant(walk: np.ndarray) -> np.ndarray:  # clase con la calle del borde elegida
        edge_class = np.digitize(walk, EDGES, right=True)
        return np.where(on_street & ~np.isnan(walk), edge_class, klass)

    def part(share: np.ndarray, cols: slice) -> float:  # suma de las clases indicadas
        return float(share[cols].sum())

    base = _shares(klass, pob, valid)
    best, worst = _shares(variant(low), pob, valid), _shares(variant(high), pob, valid)
    le400, gt800 = slice(0, 2), slice(3, 5)
    return {
        "pct": [round(float(v), 1) for v in base],
        "le400": round(part(base, le400), 1),
        "gt800": round(part(base, gt800), 1),
        "le400_range": [round(part(worst, le400)), round(part(best, le400))],
        "gt800_range": [round(part(best, gt800)), round(part(worst, gt800))],
        "total": int(pob.sum()),
        "no_street": int(pob[no_street].sum()),
        "blocks": len(b),
    }


def main(day_type: str = "weekday") -> dict:
    stops = gtfs.stops_served(day_type)
    points, _ = access.walk_access(day_type, stops=stops)
    r = population_by_class(points, stops.to_crs(access.CRS_METERS))
    labels = ["≤200 m", "201-400 m", "401-800 m", "801-2000 m", "más de 2 km / sin conexión"]
    print(f"{day_type}: {r['total']:,} personas en {r['blocks']:,} manzanas urbanas")
    for label, pct in zip(labels, r["pct"], strict=True):
        print(f"  {label:>27}: {pct:5.1f} % de la población")
    lo, hi = r["le400_range"]
    print(f"  ≤400 m: {r['le400']} % (entre {lo} y {hi} % según la calle del borde de la manzana)")
    lo, hi = r["gt800_range"]
    print(f"  >800 m: {r['gt800']} % (entre {lo} y {hi} %)")
    print(f"  sin calle cercana en OSM (fuera de los %): {r['no_street']:,} personas")
    return r


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "weekday")
