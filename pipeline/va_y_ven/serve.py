"""Servidor local de la web: solo ``web/`` y ``data/processed/public/``, solo en esta máquina.

Reemplaza a ``python -m http.server``, que (1) escucha en toda la red y serviría también
``data/raw/`` y (2) ignora las peticiones por rangos (``Range``) que necesita el mapa base
autohospedado (PMTiles).

Uso (desde la raíz del repo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.serve [puerto]   # abrir http://127.0.0.1:8000/web/
"""

from __future__ import annotations

import mimetypes
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from va_y_ven import gtfs

ALLOWED = [gtfs.ROOT / "web", gtfs.ROOT / "data" / "processed" / "public"]
CHUNK = 1 << 16
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/x-protobuf", ".pbf")


def parse_range(header: str, size: int) -> tuple[int, int] | None:
    """``Range: bytes=a-b`` -> (inicio, fin) incluyentes; ``None`` sin rango; ``ValueError`` si no.

    Solo un rango, como piden los navegadores y PMTiles. ``bytes=-n`` son los últimos ``n`` bytes.
    """
    if not header:
        return None
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not m or (not m[1] and not m[2]):
        raise ValueError(header)
    if not m[1]:  # últimos n bytes
        n = int(m[2])
        if n == 0:
            raise ValueError(header)
        return max(size - n, 0), size - 1
    start = int(m[1])
    end = min(int(m[2]), size - 1) if m[2] else size - 1
    if start >= size or end < start:
        raise ValueError(header)
    return start, end


def allowed_file(path: str) -> Path | None:
    """Archivo bajo las carpetas permitidas, o ``None`` (``..`` y enlaces que salen)."""
    file = (gtfs.ROOT / unquote(path).lstrip("/")).resolve()
    if file.is_file() and any(file.is_relative_to(a.resolve()) for a in ALLOWED):
        return file
    return None


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self.serve(send_body=False)

    def do_GET(self) -> None:
        self.serve(send_body=True)

    def serve(self, send_body: bool) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/web/")
            self.end_headers()
            return
        if path.endswith("/"):
            path += "index.html"
        file = allowed_file(path)
        if file is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        size = file.stat().st_size
        try:
            span = parse_range(self.headers.get("Range", ""), size)
        except ValueError:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        start, end = span if span else (0, size - 1)
        self.send_response(HTTPStatus.PARTIAL_CONTENT if span else HTTPStatus.OK)
        kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        if span:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not send_body:
            return
        try:
            with file.open("rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0 and (chunk := f.read(min(CHUNK, left))):
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):  # el navegador canceló (es normal)
            pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Sirviendo http://127.0.0.1:{port}/web/ (solo esta máquina; Ctrl+C para salir)")
        server.serve_forever()


if __name__ == "__main__":
    main()
