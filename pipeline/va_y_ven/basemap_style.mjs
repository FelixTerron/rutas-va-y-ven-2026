// Genera style.json del mapa base: Protomaps «grayscale», etiquetas en español y una sola tipografía.
// Lo llama basemap.py:  node basemap_style.mjs <carpeta del paquete @protomaps/basemaps> <style.json>
// Los tres marcadores @...@ los sustituye web/js/mapa.js con las direcciones reales al cargar.
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [pkgDir, out] = process.argv.slice(2);
const { layers, namedFlavor } = await import(pathToFileURL(join(pkgDir, 'dist/esm/index.js')).href);

// Cursiva y mediana apuntan a la normal: se descargan 6 archivos de glifos en vez de 18 (≈ -95 KB).
const FONT = ['Noto Sans Regular'];
const ls = layers('protomaps', namedFlavor('grayscale'), { lang: 'es' })
  .map(l => (l.layout?.['text-font'] ? { ...l, layout: { ...l.layout, 'text-font': FONT } } : l));

writeFileSync(out, JSON.stringify({
  version: 8, name: 'Vanyven',
  glyphs: '@GLYPHS@/{fontstack}/{range}.pbf', sprite: '@SPRITE@/light',  // «grayscale» usa los íconos de «light»
  sources: { protomaps: { type: 'vector', url: 'pmtiles://@PMTILES@',
    attribution: '<a href="https://openstreetmap.org/copyright">© OpenStreetMap</a>' } },
  layers: ls,
}));
