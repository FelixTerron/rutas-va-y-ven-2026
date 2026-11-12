"""Genera un visor HTML autocontenido con dos mapas:

1. **Acceso a paradas**: distancia caminando (por calles) a la parada más cercana.
2. **Rutas por calle**: cuántas rutas base distintas pasan por cada punto de calle.

Salida: ``data/processed/mapa.html`` (se abre con doble clic; no se versiona porque incrusta datos
de la ATY). Mapa base: OpenFreeMap (requiere internet).

MapLibre GL JS se descarga del registro de npm, se **verifica contra una huella SHA-512 fijada en
este archivo** y solo se extraen dos archivos del paquete (nada se instala ni se ejecuta).

Uso (desde la raíz del repo):  PYTHONPATH=pipeline uv run python -m va_y_ven.viewer
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import statistics
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from va_y_ven import access, coverage, gtfs

# Serie 5 a propósito: la 6.x es solo ESM en varios módulos y no cabe en un HTML único.
# 5.24.0 (2026-04-23). La 5.24.1 (2026-11-11) endurece la sanitización de atribuciones de fuentes
# externas; aquí la atribución es una cadena fija propia, así que no aplica a este visor local.
MAPLIBRE_VERSION = "5.24.0"
# Huella publicada por el registro de npm el 2026-11-11; si cambia, la descarga se rechaza.
MAPLIBRE_INTEGRITY = (
    "sha512-ALyFxgtd5R+65UqZ/++lOqwWcC0SNho9c27fYSyLmG7AfnAul2o46F05aDJGPbFU57wos9dgcIySHs0Xe6ia3A=="
)
MAPLIBRE_URL = f"https://registry.npmjs.org/maplibre-gl/-/maplibre-gl-{MAPLIBRE_VERSION}.tgz"
VENDOR_DIR = gtfs.RAW_DIR / "vendor"
DAYS = {"weekday": "Día hábil", "saturday": "Sábado", "sunday": "Domingo"}


def maplibre_assets() -> tuple[str, str]:
    """(css, js) de MapLibre, verificados contra la huella fijada."""
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    tgz = VENDOR_DIR / f"maplibre-gl-{MAPLIBRE_VERSION}.tgz"
    if not tgz.exists():
        request = urllib.request.Request(MAPLIBRE_URL, headers={"User-Agent": "va-y-ven-map/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            tgz.write_bytes(response.read())
    data = tgz.read_bytes()
    digest = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if digest != MAPLIBRE_INTEGRITY:
        tgz.unlink()
        raise RuntimeError(f"Huella de MapLibre no coincide: {digest}")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        css = tar.extractfile("package/dist/maplibre-gl.css").read().decode("utf-8")  # type: ignore[union-attr]
        js = tar.extractfile("package/dist/maplibre-gl.js").read().decode("utf-8")  # type: ignore[union-attr]
    if "</script" in js.lower():
        js = js.replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT")
    return css, js


def _flat(gdf, *columns) -> list[int]:
    """Puntos en una lista plana de enteros: lon*1e5, lat*1e5 y las columnas dadas (compacto)."""
    cols = [np.round(gdf.geometry.x * 1e5), np.round(gdf.geometry.y * 1e5)]
    cols += [np.asarray(gdf[c]) for c in columns]
    return np.column_stack(cols).astype(np.int64).ravel().tolist()


# Cuadrícula de la vista de ciudad: celdas de ~100 m definidas en grados (no en UTM) para que, en el
# mapa, queden alineadas con la pantalla y sin huecos. El JS usa las mismas constantes (DATA.grid).
GRID_M = 100.0
LAT0 = 20.97  # latitud de referencia de Mérida para convertir metros a grados de longitud
DLAT = GRID_M / 111_195.0
DLON = DLAT / np.cos(np.radians(LAT0))
# Bloques para cargar los puntos solo de la zona visible (~1.1 km por lado).
BLOCK_DEG = 0.01
BLOCK_LON0, BLOCK_LAT0 = -90.0, 20.0


# Celdas sin calle propia pero casi rodeadas por celdas con calle (p. ej. el interior de una manzana
# grande) se rellenan con la mediana de sus vecinas, marcadas como estimadas.
FILL_MIN_NEIGHBORS = 7
_NEIGHBORS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]


def _snap_unreached(median):
    """Una mediana entre MAX_M y UNREACHED_M mezcla calles alcanzables con las marcadas 9999 (p. ej.
    5074 m, que no es una distancia real): se lleva a UNREACHED_M. Vale para valores y arreglos."""
    return np.where(np.asarray(median) > access.MAX_M, access.UNREACHED_M, median)


def _holes(cells: dict[tuple[int, int], int]) -> list[tuple[int, int, int, int, int]]:
    """Celdas vacías con vecinas suficientes: (ix, iy, mediana, mín, máx) de las vecinas."""
    candidates = {(x + dx, y + dy) for x, y in cells for dx, dy in _NEIGHBORS} - cells.keys()
    out = []
    for x, y in candidates:
        vals = [cells[n] for dx, dy in _NEIGHBORS if (n := (x + dx, y + dy)) in cells]
        if len(vals) >= FILL_MIN_NEIGHBORS:
            median = int(_snap_unreached(round(statistics.median(vals))))
            out.append((x, y, median, min(vals), max(vals)))
    return out


def _grid(walk) -> tuple[list[int], int, int]:
    """Cuadrícula [ix, iy, mediana, mín, máx, estimada] por celda de ~100 m.

    Devuelve (lista plana, n.º de celdas, n.º de celdas estimadas por relleno de huecos).
    """
    cells = pd.DataFrame(
        {
            "ix": np.floor(walk.geometry.x / DLON).astype(np.int64),
            "iy": np.floor(walk.geometry.y / DLAT).astype(np.int64),
            "d": walk["walk_m"].to_numpy(),
        }
    )
    g = cells.groupby(["ix", "iy"])["d"].agg(["median", "min", "max"]).reset_index()
    g["median"] = _snap_unreached(g["median"].round())
    g["est"] = 0
    occupied = zip(g["ix"], g["iy"], g["median"], strict=True)
    holes = _holes({(int(x), int(y)): int(m) for x, y, m in occupied})
    if holes:
        filled = pd.DataFrame(holes, columns=["ix", "iy", "median", "min", "max"]).assign(est=1)
        g = pd.concat([g, filled], ignore_index=True)
    columns = ["ix", "iy", "median", "min", "max", "est"]
    flat = g[columns].to_numpy().astype(np.int64).ravel().tolist()
    return flat, len(g), len(holes)


def _dots(walk) -> dict:
    """Puntos ordenados por bloque de ~1 km, con índice para cargar solo los de la zona visible."""
    bx = np.floor((walk.geometry.x - BLOCK_LON0) / BLOCK_DEG).astype(np.int64)
    by = np.floor((walk.geometry.y - BLOCK_LAT0) / BLOCK_DEG).astype(np.int64)
    key = (bx * 1000 + by).to_numpy()
    order = np.argsort(key, kind="stable")
    keys, starts, counts = np.unique(key[order], return_index=True, return_counts=True)
    return {
        "flat": _flat(walk.iloc[order], "walk_m"),
        "keys": keys.tolist(),
        "starts": starts.tolist(),
        "counts": counts.tolist(),
    }


def build_data() -> dict:
    """Datos de cada tipo de día para el visor (ver ``viewer_template.html`` para el formato)."""
    route_sets: dict[str, int] = {}
    days = {}
    for day, label in DAYS.items():
        # Mapa 2: rutas por calle
        density = coverage.route_density(day).to_crs(4326)
        density["set_id"] = density["routes"].map(
            lambda r: route_sets.setdefault(r, len(route_sets))
        )
        used = {r for s in density["routes"].unique() for r in s.split(",")}
        # Mapa 1: acceso caminando a la parada más cercana
        stops = gtfs.stops_served(day)
        walk, info = access.walk_access(day, stops=stops)
        walk = walk.to_crs(4326)
        w = walk["walk_m"].to_numpy()
        edges = [200, 400, 800, access.MAX_M]
        klass = np.digitize(w, edges, right=True)  # 0..3 = tramos; 4 = más de 2 km / sin conexión
        pct = [round(float((klass == k).mean() * 100), 1) for k in range(5)]
        grid, n_cells, n_filled = _grid(walk)
        days[day] = {
            "label": label,
            "routes": {
                "flat": _flat(density, "n_routes", "set_id"),
                "stats": {
                    "routes": len(used),
                    "km": round(len(density) * 10 / 1000),
                    "max": int(density["n_routes"].max()),
                    "median": float(density["n_routes"].median()),
                    "single_pct": round(float((density["n_routes"] == 1).mean() * 100), 1),
                },
            },
            "access": {
                "grid": grid,
                "dots": _dots(walk),
                "stats": {
                    "km": round(len(walk) * info["step_m"] / 1000),
                    "pct": pct,
                    "stops": info["stops"],
                    "cells": n_cells,
                    "filled": n_filled,
                },
            },
            # [lon*1e5, lat*1e5, nombre, viajes al día, rutas base que paran]
            "stops": [
                [round(p.x * 1e5), round(p.y * 1e5), n, int(t), int(r)]
                for p, n, t, r in zip(
                    stops.geometry, stops["stop_name"], stops["trips"], stops["base_routes"],
                    strict=True,
                )
            ],
        }
        print(
            f"{label}: {len(density):,} puntos de rutas, {len(walk):,} puntos de acceso, "
            f"{n_cells:,} celdas ({n_filled:,} estimadas)"
        )
    grid = {"dlon": DLON, "dlat": DLAT, "fill_min": FILL_MIN_NEIGHBORS}
    blocks = {"lon0": BLOCK_LON0, "lat0": BLOCK_LAT0, "deg": BLOCK_DEG}
    return {"sets": list(route_sets), "grid": grid, "blocks": blocks, "days": days}


def build(out: Path | None = None) -> Path:
    css, js = maplibre_assets()
    raw = json.dumps(build_data(), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    # gzip + base64 (el visor lo descomprime con DecompressionStream); mtime=0 = salida reproducible
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    data_gz = base64.b64encode(packed).decode("ascii")
    print(f"Datos: {len(raw) / 1e6:.1f} MB -> {len(packed) / 1e6:.1f} MB comprimidos")
    html = (
        (Path(__file__).parent / "viewer_template.html")
        .read_text(encoding="utf-8")
        .replace("/*__MAPLIBRE_CSS__*/", css)
        .replace("/*__MAPLIBRE_JS__*/", js)
        .replace("/*__DATA_GZ__*/", data_gz)
    )
    out = out or coverage.OUT_DIR / "mapa.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Guardado: {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


if __name__ == "__main__":
    build()
