"""Lectura del GTFS de la ATY: rutas base, calendarios y trazos (shapes).

Conceptos:
- ``route_id``: identificador del GTFS (174). Incluye variantes de una misma ruta (R78 y R78.1).
- **ruta base**: el número de ruta sin la variante (117). Es la unidad que se cuenta en el mapa
  de calor.
- tipo de día: ``weekday`` (miércoles típico), ``saturday``, ``sunday``. Se define por los días
  que marca ``calendar.txt``, lo que deja fuera servicios especiales como el de la Feria de
  Xmatkuil (solo viernes).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
GTFS_DIR = RAW_DIR / "gtfs"

# Tipo de día -> columna de calendar.txt que debe valer 1.
DAY_TYPES = {"weekday": "wednesday", "saturday": "saturday", "sunday": "sunday"}


def ensure_extracted(gtfs_dir: Path = GTFS_DIR) -> Path:
    """Extrae el zip más reciente de data/raw/ si aún no hay GTFS descomprimido."""
    if (gtfs_dir / "routes.txt").exists():
        return gtfs_dir
    zips = sorted(RAW_DIR.glob("gtfs_export_*.zip"))
    if not zips:
        raise FileNotFoundError("No hay GTFS en data/raw/. Ejecuta: python -m va_y_ven.download")
    with zipfile.ZipFile(zips[-1]) as z:
        z.extractall(gtfs_dir)
    return gtfs_dir


def base_route(route_short_name: str) -> str:
    """'R78.1' -> '78'; 'R1001' -> '1001'. Une las variantes de una misma ruta."""
    match = re.match(r"R?(\d+)", route_short_name)
    return match.group(1) if match else route_short_name


def service_ids(day_type: str, gtfs_dir: Path = GTFS_DIR) -> set[str]:
    """service_id que operan en el tipo de día indicado, según calendar.txt."""
    column = DAY_TYPES[day_type]
    calendar = pd.read_csv(gtfs_dir / "calendar.txt", dtype=str)
    return set(calendar.loc[calendar[column] == "1", "service_id"])


def routes(gtfs_dir: Path = GTFS_DIR) -> pd.DataFrame:
    """Una fila por route_id, con su ruta base."""
    df = pd.read_csv(gtfs_dir / "routes.txt", dtype=str)
    df["base_route"] = df["route_short_name"].map(base_route)
    return df


def shape_routes(day_type: str = "weekday", gtfs_dir: Path = GTFS_DIR) -> pd.DataFrame:
    """Qué rutas usan cada trazo en el tipo de día: columnas shape_id, route_id, base_route."""
    trips = pd.read_csv(
        gtfs_dir / "trips.txt", dtype=str, usecols=["route_id", "service_id", "shape_id"]
    )
    trips = trips[trips["service_id"].isin(service_ids(day_type, gtfs_dir))]
    pairs = trips[["shape_id", "route_id"]].drop_duplicates()
    return pairs.merge(routes(gtfs_dir)[["route_id", "base_route"]], on="route_id")


def shapes(gtfs_dir: Path = GTFS_DIR) -> gpd.GeoDataFrame:
    """Trazos como líneas (EPSG:4326), una por shape_id."""
    pts = pd.read_csv(
        gtfs_dir / "shapes.txt",
        usecols=["shape_id", "shape_pt_sequence", "shape_pt_lat", "shape_pt_lon"],
        dtype={"shape_id": str},
    ).sort_values(["shape_id", "shape_pt_sequence"])
    lines = {
        sid: LineString(zip(g["shape_pt_lon"], g["shape_pt_lat"], strict=True))
        for sid, g in pts.groupby("shape_id")
        if len(g) >= 2
    }
    return gpd.GeoDataFrame({"shape_id": list(lines)}, geometry=list(lines.values()), crs=4326)
