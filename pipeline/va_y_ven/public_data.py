"""Archivos ligeros de la vista pública (Vanyven): un índice de rutas y un archivo por ruta.

Decisiones (ver ``docs/DECISIONS.md``, «Formatos de datos de la vista pública»): rutas base con
servicio de día hábil en Mérida (105), ambos sentidos, solo el trazo más usado de cada sentido,
trazo simplificado a 5 m, coordenadas con 5 decimales y nombres de paradero sin el sufijo
``_número``.

Salida (no se versiona; ``data/processed/`` está ignorado):
- ``public/index.json``: ``[[ruta, nombre, color], ...]`` en orden numérico.
- ``public/routes/<ruta>.json``: ``{"route", "name", "color", "directions": [{"direction_id",
  "headsign", "line", "stops"}]}``. ``line`` es ``[[lon, lat], ...]``; ``stops`` va en el orden del
  recorrido, cada uno ``[id, lat, lon, nombre]`` (el ``id`` es el número del paradero).

Uso (desde la raíz del repo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.public_data
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from va_y_ven import gtfs

OUT_DIR = gtfs.ROOT / "data" / "processed" / "public"
SIMPLIFY_M = 5.0
DECIMALS = 5  # 1e-5 grados ~ 1.1 m


def clean_name(name: str) -> str:
    """'Parque Caucel_2050' -> 'Parque Caucel' (el número del paradero ya va en el id)."""
    return re.sub(r"_\d+$", "", name)


def main_trips(trips: pd.DataFrame) -> pd.DataFrame:
    """Por (ruta base, sentido): el trazo con más viajes y un viaje que lo usa.

    ``trips``: columnas base_route, direction_id, shape_id, trip_id, trip_headsign. Los empates se
    resuelven por ``shape_id`` y ``trip_id`` para que el resultado sea siempre el mismo.
    """
    if not trips["base_route"].str.fullmatch(r"[0-9]+").all():
        # el nombre del archivo sale del GTFS (dato ajeno): una ruta con "/" o ".." escribiría fuera
        raise ValueError("Hay rutas base no numéricas; no sirven como nombre de archivo")
    key = ["base_route", "direction_id"]
    counts = trips.groupby([*key, "shape_id"]).size().rename("n").reset_index()
    best = counts.sort_values(["n", "shape_id"], ascending=[False, True]).drop_duplicates(key)
    first = trips.sort_values("trip_id").drop_duplicates([*key, "shape_id"])
    return best.merge(first[[*key, "shape_id", "trip_id", "trip_headsign"]], on=[*key, "shape_id"])


def simplify_lines(
    lines: gpd.GeoSeries, tol_m: float = SIMPLIFY_M
) -> dict[str, list[list[float]]]:
    """Trazos (EPSG:4326, índice = shape_id) simplificados: ``{shape_id: [[lon, lat], ...]}``.

    La simplificación conserva siempre el primer y el último punto.
    """
    simple = lines.to_crs(gtfs.CRS_METERS).simplify(tol_m).to_crs(4326)
    return {
        sid: [[round(x, DECIMALS), round(y, DECIMALS)] for x, y in geom.coords]
        for sid, geom in simple.items()
    }


def stops_by_trip(stop_times: pd.DataFrame) -> dict[str, list[str]]:
    """Paraderos de cada viaje en orden de recorrido (``stop_sequence`` se ordena como número)."""
    ordered = stop_times.assign(seq=stop_times["stop_sequence"].astype(int))
    ordered = ordered.sort_values(["trip_id", "seq"])
    return {t: grp["stop_id"].tolist() for t, grp in ordered.groupby("trip_id")}


def build() -> Path:
    g = gtfs.GTFS_DIR
    trips = pd.read_csv(
        g / "trips.txt",
        dtype=str,
        usecols=["trip_id", "route_id", "service_id", "direction_id", "shape_id", "trip_headsign"],
    )
    trips = trips[trips["service_id"].isin(gtfs.service_ids("weekday"))]
    shapes = gtfs.shapes().set_index("shape_id")
    trips = trips[trips["shape_id"].isin(shapes.index)]
    route_cols = ["route_id", "base_route", "route_long_name", "route_color"]
    trips = trips.merge(gtfs.routes()[route_cols], on="route_id")
    trips["direction_id"] = trips["direction_id"].fillna("0")  # el GTFS permite omitirlo

    best = main_trips(trips)
    lines = simplify_lines(shapes.geometry.loc[best["shape_id"].unique()])
    stop_times = pd.read_csv(
        g / "stop_times.txt", dtype=str, usecols=["trip_id", "stop_id", "stop_sequence"]
    )
    stop_times = stop_times[stop_times["trip_id"].isin(best["trip_id"])]
    trip_stops = stops_by_trip(stop_times)
    stops = pd.read_csv(g / "stops.txt", dtype={"stop_id": str}).set_index("stop_id")

    # Nombre y color de cada ruta base: los de su variante con más viajes.
    by_route = trips.groupby(["base_route", "route_long_name", "route_color"]).size().rename("n")
    info = (
        by_route.reset_index()
        .sort_values(["n", "route_long_name"], ascending=[False, True])
        .drop_duplicates("base_route")
        .set_index("base_route")
    )

    def stop_row(stop_id: str) -> list:
        s = stops.loc[stop_id]  # KeyError si el GTFS cita un paradero que no existe: falla fuerte
        name = "" if pd.isna(s["stop_name"]) else clean_name(s["stop_name"])
        return [stop_id, round(s["stop_lat"], DECIMALS), round(s["stop_lon"], DECIMALS), name]

    routes_dir = OUT_DIR / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)
    for old in routes_dir.glob("*.json"):  # no dejar rutas que ya no existen
        old.unlink()
    dump = lambda obj: json.dumps(obj, separators=(",", ":"), ensure_ascii=False)  # noqa: E731
    bases = gtfs.sorted_routes(best["base_route"]).split(",")
    for base in bases:
        directions = [
            {
                "direction_id": r.direction_id,
                "headsign": r.trip_headsign if isinstance(r.trip_headsign, str) else "",
                "line": lines[r.shape_id],
                "stops": [stop_row(s) for s in trip_stops[r.trip_id]],
            }
            for r in best[best["base_route"] == base].sort_values("direction_id").itertuples()
        ]
        payload = {
            "route": base,
            "name": info.at[base, "route_long_name"],
            "color": info.at[base, "route_color"],
            "directions": directions,
        }
        (routes_dir / f"{base}.json").write_text(dump(payload), encoding="utf-8")
    index = [[b, info.at[b, "route_long_name"], info.at[b, "route_color"]] for b in bases]
    (OUT_DIR / "index.json").write_text(dump(index), encoding="utf-8")
    print(f"{len(bases)} rutas base, {len(best)} sentidos -> {OUT_DIR}")
    return OUT_DIR


if __name__ == "__main__":
    build()
