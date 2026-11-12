"""Mapa de calor 1: cuántas rutas base distintas pasan por cada punto de calle.

Método (sin descargas externas, 100 % reproducible desde el GTFS):
1. Se muestrea cada trazo (shape) con un punto cada ``step_m`` metros.
2. Se unifican puntos que caen en la misma celda de ``step_m`` (cada punto ~ ``step_m`` m de calle).
3. Para cada punto se cuentan las **rutas base distintas** con algún trazo a menos de ``tol_m`` m.

Salida: ``data/processed/route_density_<day_type>.gpkg``
(puntos en EPSG:4326 con ``n_routes`` y ``routes``).

Uso (desde la raíz del repo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.coverage [weekday|saturday|sunday]
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from va_y_ven import gtfs

CRS_METERS = gtfs.CRS_METERS
OUT_DIR = gtfs.ROOT / "data" / "processed"


def route_density(
    day_type: str = "weekday", step_m: float = 10.0, tol_m: float = 12.0
) -> gpd.GeoDataFrame:
    sr = gtfs.shape_routes(day_type)
    sh = gtfs.shapes()
    sh = sh[sh["shape_id"].isin(sr["shape_id"])].reset_index(drop=True).to_crs(CRS_METERS)

    # 1) muestreo de puntos a lo largo de cada trazo
    xs, ys = [], []
    for geom in sh.geometry:
        dist = np.append(np.arange(0, geom.length, step_m), geom.length)
        pts = shapely.line_interpolate_point(geom, dist)
        xs.append(shapely.get_x(pts))
        ys.append(shapely.get_y(pts))
    cells = pd.DataFrame({"x": np.concatenate(xs), "y": np.concatenate(ys)})

    # 2) un solo punto por celda
    cells["cx"] = (cells["x"] // step_m).astype(np.int64)
    cells["cy"] = (cells["y"] // step_m).astype(np.int64)
    cells = cells.drop_duplicates(["cx", "cy"]).reset_index(drop=True)
    points = shapely.points(cells["x"].to_numpy(), cells["y"].to_numpy())

    # 3) rutas base distintas a menos de tol_m de cada punto
    tree = shapely.STRtree(sh.geometry.to_numpy())
    point_idx, shape_idx = tree.query(points, predicate="dwithin", distance=tol_m)
    pairs = pd.DataFrame({"pt": point_idx, "shape_id": sh["shape_id"].to_numpy()[shape_idx]})
    pairs = pairs.merge(sr[["shape_id", "base_route"]], on="shape_id")
    pairs = pairs.drop_duplicates(["pt", "base_route"])
    agg = pairs.groupby("pt")["base_route"].agg(
        n_routes="nunique", routes=lambda s: ",".join(sorted(s, key=lambda r: (len(r), r)))
    )

    out = gpd.GeoDataFrame(
        {"n_routes": 0, "routes": ""}, geometry=points, index=range(len(points)), crs=CRS_METERS
    )
    out.loc[agg.index, ["n_routes", "routes"]] = agg[["n_routes", "routes"]].to_numpy()
    out["n_routes"] = out["n_routes"].astype(int)
    return out


def summary(density: gpd.GeoDataFrame, step_m: float = 10.0) -> str:
    n = density["n_routes"]
    km = len(density) * step_m / 1000
    bins = pd.cut(n, [0, 1, 2, 4, 9, 19, 10_000], labels=["1", "2", "3-4", "5-9", "10-19", "20+"])
    share = (bins.value_counts(sort=False) / len(density) * 100).round(1)
    lines = [
        f"puntos: {len(density):,} (~{km:,.0f} km de calle con servicio)",
        f"n_routes: mín {n.min()} | mediana {n.median():.0f} | máx {n.max()}",
        "% de la calle con servicio, por número de rutas: "
        + ", ".join(f"{k}: {v}%" for k, v in share.items()),
    ]
    return "\n".join(lines)


def main(day_type: str = "weekday") -> Path:
    density = route_density(day_type)
    print(summary(density))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"route_density_{day_type}.gpkg"
    density.to_crs(4326).to_file(path, driver="GPKG")
    print(f"Guardado: {path}")
    return path


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "weekday")
