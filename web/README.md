# web/

Sitio estático de **Vanyven** (vista pública): páginas HTML y módulos JavaScript nativos, **sin empaquetador** (decisión del 2026-11-25; ver `docs/DECISIONS.md`).

| Archivo | Qué es |
|---|---|
| `index.html` | Inicio: «Abrir el mapa», aviso de privacidad y de independencia. No carga el mapa ni hace peticiones externas. |
| `mapa.html` | Mapa vacío con selector de ruta (número o nombre) y ficha de paradero. |
| `js/config.js` | Lo que cambia al publicar: dónde están los datos y el mapa base, y la vista inicial. |
| `js/search.js`, `js/util.js` | Funciones puras (búsqueda sin acentos, validación de colores y números de ruta). |
| `js/selector.js`, `js/card.js`, `js/mapa.js` | Selector (combobox accesible), ficha única y mapa. |
| `css/vanyven.css` | Estilos, móvil primero. |
| `vendor/` | MapLibre GL JS y el mapa base propio en `vendor/basemap/` (**no se versionan**; se generan con los comandos de abajo). |

Los datos salen de `data/processed/public/` (no se versiona; ver `pipeline/va_y_ven/public_data.py`). La web nunca lee el GTFS crudo.

## Probar en local (desde la raíz del repo)
```bash
PYTHONPATH=pipeline uv run python -m va_y_ven.public_data   # datos ligeros (1 s)
PYTHONPATH=pipeline uv run python -m va_y_ven.web_vendor    # MapLibre verificado por huella (una vez)
eval "$(fnm env --shell bash)" && fnm use                   # Node (el estilo se genera con @protomaps/basemaps)
PYTHONPATH=pipeline uv run python -m va_y_ven.basemap       # mapa base de Mérida, 6.7 MB, huellas verificadas (una vez)
PYTHONPATH=pipeline uv run python -m va_y_ven.serve         # solo esta máquina; abrir http://127.0.0.1:8000/web/
eval "$(fnm env --shell bash)" && fnm use && node pipeline/tests/web_smoke.mjs   # prueba de humo
```
**Probar en un celular (misma red Wi-Fi):** `PYTHONPATH=pipeline uv run python -m va_y_ven.serve --lan` imprime una dirección tipo `http://192.168.x.x:8000/web/`; ábrela en el celular. Escucha solo en la dirección de tu Wi-Fi y solo sirve `web/` y los datos públicos; úsalo en una red de confianza (tu casa), no en un café. Si no abre: revisa que el celular esté en la misma red (no en la de invitados, que a veces aísla equipos) y que macOS permita las conexiones entrantes.

`va_y_ven.serve` reemplaza a `python -m http.server`: solo sirve `web/` y los datos públicos, solo en `127.0.0.1`, y entiende peticiones por rangos (el mapa autohospedado las necesita; `http.server` las ignora).

**Mapa base propio:** Protomaps (PMTiles) recortado a Mérida, servido desde `vendor/basemap/` con `pmtiles.js`; la página no pide nada a terceros. Estilo «grayscale» con etiquetas en español y una sola tipografía. Decisión y mediciones en `docs/DECISIONS.md`.
