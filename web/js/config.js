// Ajustes que cambian al publicar. Todo lo demás del sitio los importa de aquí.

// Archivos ligeros generados por `va_y_ven.public_data`. En local, el servidor se abre en la raíz
// del repo (ver CLAUDE.md) y la ruta es relativa a la página.
export const DATA_BASE = '../data/processed/public';

// Mapa base de OpenFreeMap (estilo claro: se lee mejor al sol y deja ver los colores de las rutas).
export const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';

// PROTOTIPO (2026-11-27, se quita al decidir): mapa base autohospedado de Protomaps, se activa con
// ?base=light|grayscale|white|dark. Lo genera el proceso descrito en docs/DECISIONS.md (web/vendor/basemap/).
export const BASEMAP_DIR = 'vendor/basemap';
export const BASEMAP_FLAVORS = ['light', 'grayscale', 'white', 'dark'];

// Vista inicial: Mérida y su zona conurbada. En pantallas angostas se aleja un poco más.
export const MERIDA = { center: [-89.62, 20.97], zoom: 11.3, zoomNarrow: 10.2 };
