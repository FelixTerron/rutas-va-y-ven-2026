"""Mapa 2: distancia caminando (por la red de calles) a la parada más cercana con servicio.

Método:
1. Red peatonal de OpenStreetMap (``streets.walk_graph``), proyectada a metros (UTM 16N).
2. Cada parada con servicio ese tipo de día se proyecta al punto más cercano de la red (tramo +
   posición) y aporta distancia inicial a los dos extremos de ese tramo.
3. Dijkstra multi-origen (con tope ``MAX_M``) da la distancia mínima por calles de cada nodo a
   alguna parada.
4. Se muestrea cada ``step_m`` metros de calle; la distancia de un punto es
   ``min(d_u + s, d_v + (L - s))`` y, si hay paradas en el mismo tramo, ``|s - s_parada| + desvío``.

Salida: ``data/processed/access_<day_type>.gpkg`` (puntos EPSG:4326 con ``walk_m``;
``UNREACHED_M`` = más lejos que ``MAX_M`` o sin conexión). Solo se conservan puntos a
<= ``KEEP_RADIUS_M`` en línea recta de una parada, para no mostrar caminos rurales lejanos del
área de servicio.

Uso (desde la raíz del repo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.access [weekday|saturday|sunday]
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import shapely

from va_y_ven import gtfs, streets

CRS_METERS = gtfs.CRS_METERS
OUT_DIR = gtfs.ROOT / "data" / "processed"
MAX_M = 2000.0  # tope de la búsqueda de Dijkstra
UNREACHED_M = 9999
KEEP_RADIUS_M = 2500.0  # conservar calles a <= esto (línea recta) de alguna parada
MAX_SNAP_M = 150.0  # una parada a más de esto de cualquier calle peatonal se descarta
CLASSES = [(200, "≤200 m"), (400, "201-400 m"), (800, "401-800 m"), (MAX_M, "801-2000 m")]


@functools.cache
def walk_edges() -> gpd.GeoDataFrame:
    """Tramos de la red peatonal en metros, uno por tramo no dirigido (se calcula una sola vez).

    La red trae ambos sentidos. Se conserva la orientación de la fila elegida: la geometría siempre
    corre del nodo ``u`` (s = 0) al ``v``. Dos tramos distintos entre los mismos nodos (p. ej. un
    camino curvo y uno recto) se conservan los dos; ver ``shortest_by_pair`` para el grafo.
    """
    graph = ox.project_graph(streets.walk_graph(), to_crs=CRS_METERS)
    _, edges = ox.graph_to_gdfs(graph)
    edges = edges.reset_index()  # u, v, key, geometry, length...
    edges["lo"] = edges[["u", "v"]].min(axis=1)
    edges["hi"] = edges[["u", "v"]].max(axis=1)
    edges["len_m"] = edges.geometry.length
    edges["len_key"] = edges["len_m"].round(1)  # ida y vuelta pueden diferir en el último decimal
    return edges.drop_duplicates(["lo", "hi", "len_key"]).reset_index(drop=True)


def shortest_by_pair(u, v, length) -> pd.DataFrame:
    """Largo mínimo por par de nodos. ``nx.Graph`` guarda una sola arista por par y se queda con la
    última que recibe: si fuera la larga, las distancias saldrían de más."""
    df = pd.DataFrame({"lo": np.minimum(u, v), "hi": np.maximum(u, v), "len_m": length})
    return df.groupby(["lo", "hi"], as_index=False)["len_m"].min()


def walk_access(
    day_type: str = "weekday", step_m: float = 25.0, stops: gpd.GeoDataFrame | None = None
) -> tuple[gpd.GeoDataFrame, dict]:
    """``stops``: paradas ya leídas (``gtfs.stops_served``); si no se pasan, se leen aquí."""
    if stops is None:
        stops = gtfs.stops_served(day_type)
    stops = stops.to_crs(CRS_METERS)
    edges = walk_edges()
    lines = edges.geometry.to_numpy()
    start, end = edges["u"].to_numpy(), edges["v"].to_numpy()

    # Parada -> tramo más cercano y posición sobre él.
    tree = shapely.STRtree(lines)
    stop_pts = stops.geometry.to_numpy()
    edge_idx = tree.nearest(stop_pts)
    snap = shapely.distance(stop_pts, lines[edge_idx])
    s_stop = shapely.line_locate_point(lines[edge_idx], stop_pts)
    ok = snap <= MAX_SNAP_M
    dropped = int((~ok).sum())
    edge_idx, snap, s_stop = edge_idx[ok], snap[ok], s_stop[ok]

    # Dijkstra multi-origen con una fuente virtual "S".
    g = nx.Graph()
    pairs = shortest_by_pair(start, end, edges["len_m"].to_numpy())
    g.add_weighted_edges_from(zip(pairs["lo"], pairs["hi"], pairs["len_m"], strict=True))
    lengths = edges["len_m"].to_numpy()
    for e, d0, s in zip(edge_idx, snap, s_stop, strict=True):
        for node, extra in ((start[e], s), (end[e], lengths[e] - s)):
            w = d0 + extra
            if not g.has_edge("S", node) or g["S"][node]["weight"] > w:
                g.add_edge("S", node, weight=w)
    dist = nx.single_source_dijkstra_path_length(g, "S", cutoff=MAX_M, weight="weight")
    dist.pop("S", None)

    # Muestreo cada step_m metros de cada tramo.
    n_pts = np.maximum(1, np.round(lengths / step_m)).astype(int)
    e_idx = np.repeat(np.arange(len(edges)), n_pts)
    starts = np.cumsum(n_pts) - n_pts
    k = np.arange(n_pts.sum()) - np.repeat(starts, n_pts)
    s = (k + 0.5) * np.repeat(lengths / n_pts, n_pts)
    d_start = np.array([dist.get(n, np.inf) for n in start])[e_idx]
    d_end = np.array([dist.get(n, np.inf) for n in end])[e_idx]
    walk = np.minimum(d_start + s, d_end + (lengths[e_idx] - s))

    # Paradas ubicadas sobre el mismo tramo: pueden estar más cerca que por los extremos.
    by_edge = pd.DataFrame({"e": edge_idx, "d0": snap, "s": s_stop}).groupby("e")
    first = pd.Series(np.arange(len(e_idx)), index=e_idx).groupby(level=0).min()
    for e, grp in by_edge:
        sl = slice(first[e], first[e] + n_pts[e])
        offset = np.abs(s[sl][None, :] - grp["s"].to_numpy()[:, None])
        cand = np.min(grp["d0"].to_numpy()[:, None] + offset, axis=0)
        walk[sl] = np.minimum(walk[sl], cand)

    walk = np.where(np.isfinite(walk) & (walk <= MAX_M), walk, UNREACHED_M)
    points = shapely.line_interpolate_point(lines[e_idx], s)

    # Conservar solo calles cerca (en línea recta) del área de servicio.
    stop_tree = shapely.STRtree(stop_pts)
    near = stop_tree.nearest(points)
    keep = shapely.distance(points, stop_pts[near]) <= KEEP_RADIUS_M

    out = gpd.GeoDataFrame(
        {"walk_m": np.round(walk[keep]).astype(int)}, geometry=points[keep], crs=CRS_METERS
    )
    info = {"stops": int(ok.sum()), "stops_dropped": dropped, "step_m": step_m,
            "edges": len(edges), "nodes_reached": len(dist)}
    return out, info


def summary(access: gpd.GeoDataFrame, info: dict) -> str:
    km = len(access) * info["step_m"] / 1000
    w = access["walk_m"]
    lines = [
        f"paradas usadas: {info['stops']:,} "
        f"(descartadas por estar lejos de calles: {info['stops_dropped']})",
        f"calle analizada: {len(access):,} puntos (~{km:,.0f} km)",
    ]
    lo = 0
    for hi, label in CLASSES:
        share = ((w > lo) & (w <= hi)).mean() * 100 if lo else (w <= hi).mean() * 100
        lines.append(f"  {label:>11}: {share:5.1f} % de la calle")
        lo = hi
    unreached = (w == UNREACHED_M).mean() * 100
    lines.append(f"  {'sin acceso':>11}: {unreached:5.1f} % (>{MAX_M:.0f} m o desconectada)")
    return "\n".join(lines)


def main(day_type: str = "weekday") -> Path:
    access, info = walk_access(day_type)
    print(summary(access, info))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"access_{day_type}.gpkg"
    access.to_crs(4326).to_file(path, driver="GPKG")
    print(f"Guardado: {path}")
    return path


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "weekday")
