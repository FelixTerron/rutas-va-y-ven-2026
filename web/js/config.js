// Ajustes que cambian al publicar. Todo lo demás del sitio los importa de aquí.

// Archivos ligeros generados por `va_y_ven.public_data`. En local, el servidor se abre en la raíz
// del repo (ver CLAUDE.md) y la ruta es relativa a la página.
export const DATA_BASE = '../data/processed/public';

// Mapa base propio (Protomaps, recorte de Mérida), generado por `va_y_ven.basemap`; ruta relativa a la página.
export const BASEMAP_DIR = 'vendor/basemap';

// Vista inicial: Mérida y su zona conurbada. En pantallas angostas se aleja un poco más.
export const MERIDA = { center: [-89.62, 20.97], zoom: 11.3, zoomNarrow: 10.2 };
