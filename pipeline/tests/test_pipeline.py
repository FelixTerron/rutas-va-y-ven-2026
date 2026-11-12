"""Pruebas de la lógica delicada del pipeline, con datos inventados (no descargan nada).

Sin dependencias nuevas: son funciones ``test_*`` (también corren con pytest, si se añade).
Uso (desde la raíz del repo):  PYTHONPATH=pipeline uv run python pipeline/tests/test_pipeline.py
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point

from va_y_ven import access, viewer

UNREACHED = access.UNREACHED_M


def _ring(center: tuple[int, int], values: list[int]) -> dict[tuple[int, int], int]:
    """Las 8 celdas alrededor de ``center`` con los valores dados (en orden)."""
    cx, cy = center
    around = [(cx + dx, cy + dy) for dx, dy in viewer._NEIGHBORS]
    return dict(zip(around, values, strict=True))


def test_holes_fill_enclosed_cell_with_neighbor_median():
    cells = _ring((0, 0), [100, 100, 100, 100, 300, 300, 300, 300])
    holes = viewer._holes(cells)
    assert (0, 0, 200, 100, 300) in holes  # mediana, mín y máx de las vecinas


def test_holes_do_not_fill_cell_with_too_few_neighbors():
    cells = _ring((0, 0), [100] * 8)
    too_many = 8 - viewer.FILL_MIN_NEIGHBORS + 1  # con esas menos, quedan bajo el mínimo
    for gone in list(cells)[:too_many]:
        del cells[gone]
    assert all((x, y) != (0, 0) for x, y, *_ in viewer._holes(cells))


def test_holes_never_invent_a_distance_between_2km_and_unreached():
    # 4 vecinas a 100 m y 4 sin conexión: la mediana ingenua sería ~5050 m, que no existe.
    holes = viewer._holes(_ring((0, 0), [100] * 4 + [UNREACHED] * 4))
    medians = {m for x, y, m, *_ in holes if (x, y) == (0, 0)}
    assert medians == {UNREACHED}


def test_grid_cell_with_reachable_and_unreachable_streets_is_unreached():
    # Dos puntos en la misma celda: uno a 100 m y otro sin conexión. Antes salía 5050 m.
    x, y = -89.62, 20.97
    walk = gpd.GeoDataFrame(
        {"walk_m": [100, UNREACHED]}, geometry=[Point(x, y), Point(x + 1e-6, y)], crs=4326
    )
    flat, n_cells, _ = viewer._grid(walk)
    ix, iy, median, lo, hi, est = flat[:6]
    assert (median, lo, hi, est) == (UNREACHED, 100, UNREACHED, 0)


def test_shortest_edge_wins_between_the_same_two_nodes():
    pairs = access.shortest_by_pair(np.array([1, 2]), np.array([2, 1]), np.array([120.0, 50.0]))
    assert len(pairs) == 1 and pairs["len_m"].iloc[0] == 50.0


def test_walk_uses_shortest_of_parallel_ways():
    """Dos tramos entre los nodos 1 y 2 (recto de 100 m y curvo de ~224 m, el curvo al final de la
    lista) y uno más de 2 a 3. Con una parada junto al nodo 1, los puntos del tramo 2-3 deben
    medirse por el recto (~100 m + lo recorrido), no por el curvo."""
    ways = {
        (1, 2): LineString([(0, 0), (100, 0)]),
        (2, 3): LineString([(100, 0), (200, 0)]),
        (1, 2, "curvo"): LineString([(0, 0), (50, 100), (100, 0)]),
    }
    rows = [
        {"u": k[0], "v": k[1], "geometry": g, "lo": k[0], "hi": k[1], "len_m": g.length,
         "len_key": round(g.length, 1)}
        for k, g in ways.items()
    ]
    edges = gpd.GeoDataFrame(rows, geometry="geometry", crs=access.CRS_METERS)
    stops = gpd.GeoDataFrame(
        {"stop_id": ["a"]}, geometry=[Point(0, 5)], crs=access.CRS_METERS
    )
    original = access.walk_edges
    access.walk_edges = lambda: edges
    try:
        walk, _ = access.walk_access(stops=stops, step_m=25.0)
    finally:
        access.walk_edges = original
    on_2_3 = walk[walk.geometry.x > 110]
    assert on_2_3["walk_m"].min() <= 125, on_2_3["walk_m"].min()  # con el bug salía ~236


if __name__ == "__main__":
    tests = {n: f for n, f in globals().items() if n.startswith("test_")}
    for name, fn in tests.items():
        fn()
        print(f"ok  {name}")
    print(f"{len(tests)} pruebas pasaron")
