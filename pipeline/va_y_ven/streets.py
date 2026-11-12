"""Red peatonal de OpenStreetMap para Mérida y su zona conurbada.

Se descarga una sola vez con osmnx (API Overpass) y se guarda en ``data/raw/osm/``.
Los datos de OpenStreetMap son © colaboradores de OpenStreetMap (licencia ODbL): hay que atribuirlos
y, si algún día se publican derivados, compartirlos bajo la misma licencia.

Uso (desde la raíz del repo):  PYTHONPATH=pipeline uv run python -m va_y_ven.streets
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import osmnx as ox

from va_y_ven import gtfs

OSM_DIR = gtfs.RAW_DIR / "osm"
GRAPH_PATH = OSM_DIR / "merida_walk.graphml"
BUFFER_DEG = 0.02  # ~2 km alrededor de las paradas: calles que aún caen en el área urbana


def bbox() -> tuple[float, float, float, float]:
    """(oeste, sur, este, norte) = paradas con servicio de Mérida + margen."""
    x0, y0, x1, y1 = gtfs.stops_served("weekday").total_bounds
    return (x0 - BUFFER_DEG, y0 - BUFFER_DEG, x1 + BUFFER_DEG, y1 + BUFFER_DEG)


def walk_graph(path: Path = GRAPH_PATH) -> nx.MultiDiGraph:
    """Red peatonal (bidireccional, longitudes en metros). La descarga la primera vez."""
    if path.exists():
        return ox.load_graphml(path)
    OSM_DIR.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(OSM_DIR / "cache")
    ox.settings.requests_timeout = 900
    ox.settings.log_console = True
    graph = ox.graph_from_bbox(bbox=bbox(), network_type="walk", simplify=True)
    ox.save_graphml(graph, path)
    return graph


if __name__ == "__main__":
    g = walk_graph()
    print(f"Red peatonal: {g.number_of_nodes():,} nodos, {g.number_of_edges():,} tramos")
    print(f"Guardada en {GRAPH_PATH}")
