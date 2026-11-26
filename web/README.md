# web/

Sitio estático de **Vanyven** (vista pública): páginas HTML y módulos JavaScript nativos, **sin empaquetador** (decisión del 2026-11-25; ver `docs/DECISIONS.md`).

| Archivo | Qué es |
|---|---|
| `index.html` | Inicio: «Abrir el mapa», aviso de privacidad y de independencia. No carga el mapa ni hace peticiones externas. |
| `mapa.html` | Mapa vacío con selector de ruta (número o nombre) y ficha de paradero. |
| `js/config.js` | Lo que cambia al publicar: dónde están los datos, estilo del mapa y vista inicial. |
| `js/search.js`, `js/util.js` | Funciones puras (búsqueda sin acentos, validación de colores y números de ruta). |
| `js/selector.js`, `js/card.js`, `js/mapa.js` | Selector (combobox accesible), ficha única y mapa. |
| `css/vanyven.css` | Estilos, móvil primero. |
| `vendor/` | MapLibre GL JS (**no se versiona**; se genera con el comando de abajo). |

Los datos salen de `data/processed/public/` (no se versiona; ver `pipeline/va_y_ven/public_data.py`). La web nunca lee el GTFS crudo.

## Probar en local (desde la raíz del repo)
```bash
PYTHONPATH=pipeline uv run python -m va_y_ven.public_data   # datos ligeros (1 s)
PYTHONPATH=pipeline uv run python -m va_y_ven.web_vendor    # MapLibre verificado por huella (una vez)
python -m http.server --bind 127.0.0.1                      # solo esta máquina; abrir http://127.0.0.1:8000/web/
eval "$(fnm env --shell bash)" && fnm use && node pipeline/tests/web_smoke.mjs   # prueba de humo
```
Importa `--bind 127.0.0.1`: sin él, el servidor escucha en toda la red y serviría también `data/raw/`.
