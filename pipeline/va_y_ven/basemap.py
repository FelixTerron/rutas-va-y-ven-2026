"""Mapa base autohospedado de la web: recorte de Mérida de Protomaps (PMTiles) más estilo e íconos.

Genera ``web/vendor/basemap/`` (no se versiona; ~6.7 MB). Todo lo que se descarga se verifica
contra una huella fijada aquí; si no coincide, se rechaza. Los datos del mapa son de OpenStreetMap
(ODbL, crédito «© OpenStreetMap»); el diseño de Protomaps es CC0 y su código BSD-3
(ver ``docs/DATA_SOURCES.md``).

Uso (desde la raíz del repo; hace falta Node, ver CLAUDE.md para activarlo):
    PYTHONPATH=pipeline uv run python -m va_y_ven.basemap           # conserva el recorte
    PYTHONPATH=pipeline uv run python -m va_y_ven.basemap 20261201  # recorte nuevo (esa fecha)

Las compilaciones diarias de Protomaps se retiran con el tiempo: para actualizar, pasar una fecha
reciente (https://maps.protomaps.com/builds/) y, si todo se ve bien, subir ``BUILD``.
"""

from __future__ import annotations

import base64
import hashlib
import io
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

from va_y_ven import gtfs

HERE = Path(__file__).resolve().parent
OUT = gtfs.ROOT / "web" / "vendor" / "basemap"
VENDOR = gtfs.RAW_DIR / "vendor"

BUILD = "20261125"  # compilación diaria de Protomaps de la que se recorta
# lon/lat mín-máx; cubre las 105 rutas (lon -89.781..-89.481, lat 20.789..21.213)
BBOX = "-89.85,20.74,-89.40,21.26"

# shortcut: solo hay huella para macOS con Apple Silicon (la máquina de desarrollo); otra plataforma
# necesita fijar la huella de su zip (la publica GitHub en la página de la versión).
CLI_VERSION = "1.31.2"
CLI_URL = (
    f"https://github.com/protomaps/go-pmtiles/releases/download/v{CLI_VERSION}/"
    f"go-pmtiles-{CLI_VERSION}_Darwin_arm64.zip"
)
CLI_SHA256 = "40528f7f616fcbf91207cd48c8fc023d213f6d86c0cbf1f748732803d1880f3d"

# Huellas SHA-512 del registro de npm (sin scripts de instalación; no se toca package.json).
NPM = {
    "pmtiles": (
        "4.5.0",
        "sha512-CBeD4SoUluFziGdy/8k7FOjQxQy486n+929W/tWophauvMICpkZ26vGBWhDt/6b1FZQWNaf4jFdT/5"
        "+q0Wii5w==",
    ),
    "@protomaps/basemaps": (
        "5.7.2",
        "sha512-K1Yk6bWdULulYg+R2QRVXx4NzJZan5YQhpejEG0c1/sXruJrfPIPZuakpf3jwAgVmjIRVQwAv+yRaf"
        "DeN0aaUQ==",
    ),
}

# Fuentes (Noto Sans Regular, OFL) e íconos de protomaps/basemaps-assets: commit y SHA-256 fijos.
ASSETS_URL = (
    "https://raw.githubusercontent.com/protomaps/basemaps-assets/"
    "028c18f713baecad011301ff7a69acc39bcc2ae7"
)
_FONT = "fonts/Noto Sans Regular/"
ASSETS = {
    _FONT + "0-255.pbf": "62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397",
    _FONT + "256-511.pbf": "2eca7561f9f566bcacfda5dd04fb5880baec1328ec0f5484678289a13994de8a",
    _FONT + "512-767.pbf": "6abc80badad0e823e228ab739515be257c8b33bc68bb077dd873030e9b2d143a",
    _FONT + "768-1023.pbf": "537ccbee79180f4f8b3f6d2bdd27df979260ce1a0358c40d7aa7db505d9b03aa",
    _FONT + "7680-7935.pbf": "b9100ec886dff647198802c41d1ca6df9e6f82325179d8d71e3d377b5fe8682e",
    _FONT + "8192-8447.pbf": "8ea977a587352fe31b4159ffdbc9a40be79056f2472017c742ea1e4a931864b9",
    "sprites/v4/light.json": "bfac76cf7ed5c2aa2992695904056a1c6b07785b7fd20e6c640cb44fd6244a2e",
    "sprites/v4/light@2x.json": "1fb5b123fbe35d2e1f6ac171513ce01df89e671273a417ee89c44886a4c132f0",
    "sprites/v4/light.png": "b6a34640917bdc57d0bd080836db33376371a3312ebe7b849045268015de3481",
    "sprites/v4/light@2x.png": "23f6e9df27c2e9a14385763980a24e3608966bfc8192a106058bc2ca959ab563",
}


def verified(data: bytes, expected: str, what: str) -> bytes:
    """``data`` si su huella es ``expected`` (``sha512-<base64>`` de npm o SHA-256 en hex)."""
    if expected.startswith("sha512-"):
        got = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    else:
        got = hashlib.sha256(data).hexdigest()
    if got != expected:
        raise RuntimeError(f"La huella de {what} no coincide: {got}")
    return data


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "va-y-ven-map/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        return response.read()


def _cached(path: Path, url: str, expected: str) -> bytes:
    """Descarga una vez a ``data/raw/vendor/`` y verifica siempre, también lo ya guardado."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_fetch(url))
    try:
        return verified(path.read_bytes(), expected, path.name)
    except RuntimeError:
        path.unlink()
        raise


def _npm_package(name: str) -> bytes:
    version, integrity = NPM[name]
    slug = name.removeprefix("@").replace("/", "-")
    url = f"https://registry.npmjs.org/{name}/-/{name.split('/')[-1]}-{version}.tgz"
    return _cached(VENDOR / f"{slug}-{version}.tgz", url, integrity)


def _cli() -> Path:
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise SystemExit("pmtiles: solo hay huella fijada para macOS arm64 (ver CLI_URL).")
    folder = VENDOR / f"pmtiles-{CLI_VERSION}"
    zipped = _cached(folder / "go-pmtiles.zip", CLI_URL, CLI_SHA256)
    exe = folder / "pmtiles"
    if not exe.exists():
        with zipfile.ZipFile(io.BytesIO(zipped)) as z:
            exe.write_bytes(z.read("pmtiles"))
        exe.chmod(0o755)
    return exe


def _pmtiles_js() -> bytes:
    with tarfile.open(fileobj=io.BytesIO(_npm_package("pmtiles")), mode="r:gz") as tar:
        return tar.extractfile("package/dist/pmtiles.js").read()  # type: ignore[union-attr]


def build(date: str | None = None, out: Path = OUT) -> Path:
    """Genera ``out``. Con ``date`` (o si falta el recorte) vuelve a recortar de esa compilación."""
    if shutil.which("node") is None:
        raise SystemExit('Falta Node: eval "$(fnm env --shell bash)" && fnm use')
    out.mkdir(parents=True, exist_ok=True)
    tiles = out / "merida.pmtiles"
    for old in out.iterdir():  # lo generado antes; el recorte se conserva
        if old != tiles:
            shutil.rmtree(old) if old.is_dir() else old.unlink()

    if date or not tiles.exists():
        part = tiles.with_name("merida.pmtiles.part")
        part.unlink(missing_ok=True)
        source = f"https://build.protomaps.com/{date or BUILD}.pmtiles"
        subprocess.run([str(_cli()), "extract", source, str(part), f"--bbox={BBOX}"], check=True)
        part.replace(tiles)

    (out / "pmtiles.js").write_bytes(_pmtiles_js())
    pkg = VENDOR / f"protomaps-basemaps-{NPM['@protomaps/basemaps'][0]}"
    shutil.rmtree(pkg, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(_npm_package("@protomaps/basemaps")), mode="r:gz") as tar:
        tar.extractall(pkg, filter="data")
    style = [str(HERE / "basemap_style.mjs"), str(pkg / "package"), str(out / "style.json")]
    subprocess.run(["node", *style], check=True)

    for rel, sha in ASSETS.items():
        dest = out / rel.replace("sprites/v4/", "sprites/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(verified(_fetch(f"{ASSETS_URL}/{quote(rel)}"), sha, rel))
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"Mapa base (huellas verificadas) -> {out} ({size / 1e6:.1f} MB)")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else None)
