# CLAUDE.md

Mapa interactivo de rutas Va y Ven (Yucatán). Proyecto personal; objetivos y estructura en `README.md`.
Nombre del portal: **Vanyven** (decisión del 2026-11-24; juego de palabras con «Va y Ven», sin afiliación a la ATY).

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
- Python ≥ 3.11 gestionado con `uv`; lint con `ruff` (`uv run ruff check pipeline`); pruebas con
  `PYTHONPATH=pipeline uv run python pipeline/tests/test_pipeline.py` (sin dependencias nuevas). Prueba de humo del visor
  (después de `viewer`; Node vía `fnm`, usa el Chrome instalado, sin paquetes): `node pipeline/tests/viewer_smoke.mjs`.
- Código del pipeline en `pipeline/va_y_ven/`. Ejecutar con `PYTHONPATH=pipeline uv run python -m va_y_ven.<modulo>`.
- Web: sitio estático **sin empaquetador** (páginas y módulos JS nativos + MapLibre GL JS verificado por huella) en
  `web/` (decisión 2026-11-25: TypeScript/Vite descartado por ahora; en local, `PYTHONPATH=pipeline uv run python -m va_y_ven.serve` desde la raíz
  del repo (solo `web/`, solo 127.0.0.1, con rangos; ver `web/README.md`); prueba de humo: `node pipeline/tests/web_smoke.mjs`).
  Node 24.22.2 vía `fnm` (`.node-version`),
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
  peatonal de OSM, una vez), `coverage`, `access` y `population` `[weekday|saturday|sunday]`, `viewer` (genera
  `data/processed/mapa.html`, ~30 s; `open data/processed/mapa.html` para verlo) y `public_data` (archivos ligeros de la
  vista pública en `data/processed/public/`, ~1 s) `web_vendor` (copia MapLibre verificado a `web/vendor/`, no se versiona), `basemap` (mapa base propio de la web en `web/vendor/basemap/`, huellas verificadas; necesita Node) y `serve` (servidor local de la web; `--lan` lo abre a tu Wi-Fi para probar en el celular).
- Visor: toda función nueva se describe en la ventana «? Cómo usar» (`viewer_template.html`, `<dialog id="help">`) y
  sus límites en «Consideraciones». Decisión del usuario: el visor informa, **no califica** el servicio (sin umbrales
  de «frecuente»/«bueno»/«malo»).
- Visor: MapLibre 5.24.0 incrustado y verificado por huella; sin `file://` + URLs `blob:` (ver `docs/DECISIONS.md`).
- Alcance: solo Mérida y zona conurbada (`gtfs.shapes(area="merida")`); Valladolid y Tizimín quedan fuera.

## Estado
Hecho: descarga del GTFS (`download.py`), lectura (`gtfs.py`), rutas distintas por calle (`coverage.py`), acceso
caminando a la parada más cercana con la red de OSM (`streets.py`, `access.py`), visor HTML local (`viewer.py`) con
paradas, rutas y frecuencia estimada (7-9 h) por parada, guía y consideraciones, acceso ponderado por población
(INEGI, `population.py`: 72.8 % de las personas a ≤400 m, rango 58-85 %; el visor **requiere** `data/raw/inegi/`),
datos ligeros de la vista pública (`public_data.py`: 105 rutas, 219 KB comprimidos en total), 22 pruebas y dos pruebas de humo (visor y web; la web corre sin internet).
Ahora: el diseño de la vista pública está cerrado en lo esencial y se construye por fases (hoja de ruta en
`docs/DECISIONS.md`): hechas la fase 1 (datos) y la fase 2 (web mínima en `web/`: inicio, mapa con selector de ruta y ficha
de paradero, con mapa base propio de Protomaps desde el 2026-11-27); sigue la fase 3 (votos con valores de ejemplo; «Tu trayecto» espera los datos de colonias). Falta diseñar los
4 features de análisis. Pendientes: soporte táctil del visor de análisis (al final, no olvidar),
conciliar 174/117/205 rutas, nombres de calle.
Estado completo en `docs/ADDENDUM_2026-11-13.md`; decisiones en `docs/DECISIONS.md`.
