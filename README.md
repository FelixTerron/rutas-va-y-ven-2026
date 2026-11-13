# Mapa de rutas Va y Ven

Mapa interactivo y abierto de las rutas del transporte público **Va y Ven** (Mérida, Yucatán, y su zona conurbada).

Dos objetivos:
- **Especialistas y analistas (prioridad):** análisis reproducibles para diseño y optimización de rutas, con mapas de calor de intensidad de tránsito por calle y de abordajes por paradero.
- **Cualquier persona:** una experiencia visual, interactiva y divertida, no solo "otro mapa de rutas" (por definir).

> Estado: hay un visor local (`viewer`, ver abajo) con acceso a paradas, rutas por calle y frecuencia estimada por parada; trabajo **privado** hasta aclarar las condiciones de uso de los datos. Estado completo en `docs/ADDENDUM_2026-11-13.md`; pendientes en `docs/DECISIONS.md`.

## Estructura

| Carpeta | Contenido |
|---|---|
| `pipeline/` | Python: descarga y transforma el GTFS en archivos ligeros |
| `data/raw/` | GTFS crudo descargado (no se versiona) |
| `data/processed/` | Archivos derivados que consume la web (no se versionan por ahora) |
| `notebooks/` | Cuadernos de análisis y material didáctico |
| `web/` | Aplicación del mapa (pendiente) |
| `docs/` | Fuentes de datos y decisiones |

## Empezar

Requiere [uv](https://docs.astral.sh/uv/).

```bash
uv sync
PYTHONPATH=pipeline uv run python -m va_y_ven.download   # descarga el GTFS a data/raw/
PYTHONPATH=pipeline uv run python -m va_y_ven.streets    # red peatonal de OSM (una vez)
PYTHONPATH=pipeline uv run python -m va_y_ven.viewer     # genera data/processed/mapa.html (~30 s)
open data/processed/mapa.html
```

## Datos

Fuente: GTFS oficial de la Agencia de Transporte de Yucatán (ATY). Detalles, pendientes y licencia en
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). Este proyecto no está afiliado a la ATY.
