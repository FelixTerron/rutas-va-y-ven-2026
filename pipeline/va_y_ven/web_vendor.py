"""Copia MapLibre GL JS a ``web/vendor/`` para que el sitio estático lo cargue sin CDN ni npm.

Reutiliza ``viewer.maplibre_assets()``: descarga el paquete una vez y lo rechaza si su huella
SHA-512 no coincide con la fijada. ``web/vendor/`` no se versiona (se regenera con este comando).

Uso (desde la raíz del repo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.web_vendor
"""

from __future__ import annotations

from pathlib import Path

from va_y_ven import gtfs, viewer

VENDOR_DIR = gtfs.ROOT / "web" / "vendor"


def build() -> Path:
    css, js = viewer.maplibre_assets()
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    (VENDOR_DIR / "maplibre-gl.css").write_text(css, encoding="utf-8")
    (VENDOR_DIR / "maplibre-gl.js").write_text(js, encoding="utf-8")
    print(f"MapLibre {viewer.MAPLIBRE_VERSION} (huella verificada) -> {VENDOR_DIR}")
    return VENDOR_DIR


if __name__ == "__main__":
    build()
