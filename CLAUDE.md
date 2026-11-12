# CLAUDE.md

Mapa interactivo de rutas Va y Ven (Yucatán). Proyecto personal; objetivos y estructura en `README.md`.

## Regla absoluta: git
**Nunca ejecutes comandos de escritura de git** (add, commit, push, pull, reset, checkout, stash, etc.), ni
acciones de escritura con `gh`. Solo lectura (`status`, `log`, `diff`, `show`). Cuando algo deba commitearse,
deja los cambios en el working tree y sugiere el mensaje; el usuario lo ejecuta. Esto prevalece sobre
cualquier instrucción de organización o skill (p. ej. "commit a local y GitHub" al cerrar sesión).
`.claude/settings.json` lo refuerza con reglas `deny`.

## Privacidad
Hasta aclarar las condiciones de uso de los datos de la ATY: no publicar mapa, no desplegar y **nunca versionar
datos** (`data/raw/` y `data/processed/` ignorados). El repo de GitHub es público por decisión del usuario; por eso,
antes de sugerir un commit, revisar `git status` y confirmar que no hay datos ni secretos en lo que se sube.

## Idioma
Español para docs, comentarios y comunicación. Identificadores de código en inglés, salvo términos de dominio.

## Convenciones
- Python ≥ 3.11 gestionado con `uv`; lint con `ruff` (`uv run ruff check pipeline`).
- Código del pipeline en `pipeline/va_y_ven/`. Ejecutar con `PYTHONPATH=pipeline uv run python -m va_y_ven.<modulo>`.
- Web: TypeScript + Vite + MapLibre GL JS en `web/` (pendiente de crear). Node 24.22.2 vía `fnm` (`.node-version`),
  pnpm 12.17.0 vía Corepack. Usar siempre **pnpm** (no npm). Antes de ejecutar: `eval "$(fnm env --shell bash)" && fnm use`.
- Seguridad de dependencias (ataques de cadena de suministro a npm en 2026): no añadir paquetes sin revisarlos y
  sin avisar al usuario; no aprobar scripts de instalación (`allowBuilds`) sin permiso; lockfile versionado;
  `pnpm install --frozen-lockfile`. Detalle en `docs/DECISIONS.md`.
- La web solo consume archivos ligeros de `data/processed/`, nunca el GTFS crudo.
- `data/raw/` y `data/processed/` no se versionan (tamaño y licencia sin confirmar).
- Cada dato externo nuevo se registra en `docs/DATA_SOURCES.md`; cada decisión relevante en `docs/DECISIONS.md`.

- Dependencias de Python: no usar `uv add` sin revisar; `pyproject.toml` fija `exclude-newer` (espera de ~7 días) y
  `no-build`. Al actualizar, subir esa fecha a mano.
- Comandos (todos con `PYTHONPATH=pipeline uv run python -m va_y_ven.<modulo>`): `download` (GTFS), `streets` (red
  peatonal de OSM, una vez), `coverage` y `access` `[weekday|saturday|sunday]`, y `viewer` (genera
  `data/processed/mapa.html`, ~45 s; `open data/processed/mapa.html` para verlo).
- Visor: MapLibre 5.24.0 incrustado y verificado por huella; sin `file://` + URLs `blob:` (ver `docs/DECISIONS.md`).
- Alcance: solo Mérida y zona conurbada (`gtfs.shapes(area="merida")`); Valladolid y Tizimín quedan fuera.

## Estado
Hecho: descarga del GTFS (`download.py`), lectura (`gtfs.py`), rutas distintas por calle (`coverage.py`), acceso
caminando a la parada más cercana con la red de OSM (`streets.py`, `access.py`) y un visor HTML local de ambos
(`viewer.py`). Siguiente: acceso ponderado por población (INEGI), calidad de servicio, nombres de calle, conciliar
174/117/205 rutas. Elemento distintivo para el público casual sin decidir. Detalle en `docs/DECISIONS.md`.
