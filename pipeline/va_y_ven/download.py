"""Descarga el GTFS oficial de la ATY a data/raw/ y registra su procedencia.

Uso (desde la raíz del repo):  PYTHONPATH=pipeline uv run python -m va_y_ven.download

Solo usa la librería estándar. No extrae el zip: eso lo hará el paso de ingesta.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

GTFS_URL = "https://transit-scheduler.com/api/export-gtfs/latest"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
TIMEOUT_S = 120


def download(url: str = GTFS_URL, dest_dir: Path = RAW_DIR) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "va-y-ven-map/0.1"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:  # noqa: S310
        body = response.read()
        disposition = response.headers.get("content-disposition", "")
        last_modified = response.headers.get("last-modified")

    match = re.search(r'filename="?([^";]+)"?', disposition)
    filename = match.group(1) if match else "gtfs_export.zip"
    zip_path = dest_dir / filename
    zip_path.write_bytes(body)

    # Registro de procedencia: de dónde, cuándo y qué exactamente se descargó.
    manifest = {
        "source_url": url,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "server_last_modified": last_modified,
        "file": zip_path.name,
        "size_bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    (dest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return zip_path


if __name__ == "__main__":
    path = download()
    print(f"Descargado: {path} ({path.stat().st_size / 1e6:.1f} MB)")
