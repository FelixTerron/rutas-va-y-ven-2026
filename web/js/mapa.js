// Página del mapa: el mapa empieza vacío; al elegir una ruta se dibujan sus dos sentidos y sus paraderos.
import { DATA_BASE, STYLE_URL, MERIDA } from './config.js';
import { isRouteNumber, safeColor } from './util.js';
import { createSelector } from './selector.js';
import { createCard } from './card.js';

const $ = id => document.getElementById(id);
const hint = $('hint'), legend = $('legend'), statusEl = $('status');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const TAP_RADIUS = 12;  // px: el paradero más cercano al toque cuenta, aunque el punto sea pequeño
const empty = () => ({ type: 'FeatureCollection', features: [] });

async function fetchJson(path) {
  const r = await fetch(`${DATA_BASE}/${path}`);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

/** Flecha blanca que apunta al este; MapLibre la gira siguiendo la línea. */
function chevron() {
  const s = 32, c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d');
  g.strokeStyle = '#fff'; g.lineWidth = 6; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); g.moveTo(10, 6); g.lineTo(22, 16); g.lineTo(10, 26); g.stroke();
  return g.getImageData(0, 0, s, s);
}

function say(el, msg) { el.textContent = msg; el.hidden = !msg; }

async function main() {
  if (typeof maplibregl === 'undefined') {
    say(hint, 'Falta MapLibre. En la raíz del repo: PYTHONPATH=pipeline uv run python -m va_y_ven.web_vendor');
    return;
  }
  let index;
  try { index = await fetchJson('index.json'); } catch {
    say(hint, 'No se pudo cargar la lista de rutas. Revisa tu conexión e intenta de nuevo.');
    return;
  }
  const routeInfo = new Map(index.map(r => [r[0], r]));
  const cache = new Map();
  let stops = new Map(), current = null, token = 0;

  let map;
  try {
    map = new maplibregl.Map({
      container: 'map', style: STYLE_URL, center: MERIDA.center, minZoom: 8, maxZoom: 18,
      zoom: innerWidth < 600 ? MERIDA.zoomNarrow : MERIDA.zoom, dragRotate: false, pitchWithRotate: false,
    });
  } catch {
    say(hint, 'Tu navegador no puede mostrar el mapa (necesita WebGL).');
    return;
  }
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  window.vanyven = { map };  // para la prueba de humo (pipeline/tests/web_smoke.mjs)
  const loaded = new Promise(r => map.once('load', r));
  map.on('error', e => { if (!map.isStyleLoaded()) say(statusEl, 'No se pudo cargar el mapa base. Revisa tu conexión.'); console.error(e.error?.message); });

  const card = createCard(routeInfo, num => select(num, openStopId));
  let openStopId = null;
  // El selector se puede usar mientras el mapa base carga; las capas aún no existen, así que se espera.
  const selector = createSelector(index, { onSelect: num => loaded.then(() => select(num)), onClear: () => loaded.then(clearRoute) });

  await loaded;
  map.addImage('chevron', chevron(), { pixelRatio: 2 });
  map.addSource('route-lines', { type: 'geojson', data: empty() });
  map.addSource('route-stops', { type: 'geojson', data: empty() });
  map.addSource('stop-selected', { type: 'geojson', data: empty() });
  const offset = ['interpolate', ['linear'], ['zoom'], 10, 1.5, 14, 3, 17, 6];  // separa los sentidos
  map.addLayer({ id: 'route-casing', type: 'line', source: 'route-lines',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 7, 17, 13], 'line-offset': offset } });
  map.addLayer({ id: 'route-line', type: 'line', source: 'route-lines',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': ['get', 'color'], 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 2, 14, 4, 17, 9], 'line-offset': offset } });
  map.addLayer({ id: 'route-arrows', type: 'symbol', source: 'route-lines', minzoom: 14,
    layout: { 'symbol-placement': 'line', 'symbol-spacing': 80, 'icon-image': 'chevron', 'icon-size': ['interpolate', ['linear'], ['zoom'], 14, 0.55, 17, 1],
      'icon-allow-overlap': true, 'icon-ignore-placement': true, 'icon-rotation-alignment': 'map' } });
  map.addLayer({ id: 'route-stops', type: 'circle', source: 'route-stops',
    paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 2.5, 14, 4, 17, 7], 'circle-color': '#ffffff',
      'circle-stroke-color': ['get', 'color'], 'circle-stroke-width': 2 } });
  map.addLayer({ id: 'stop-selected', type: 'circle', source: 'stop-selected',
    paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 7, 17, 12], 'circle-color': 'rgba(0,0,0,0)',
      'circle-stroke-color': '#111111', 'circle-stroke-width': 3 } });

  function openStop(id) {
    const s = stops.get(id);
    if (!s) return closeStop();
    openStopId = id;
    card.show(s, current?.route);
    map.getSource('stop-selected').setData({ type: 'Feature', geometry: { type: 'Point', coordinates: s.lonlat }, properties: {} });
    // si la ficha tapa el paradero, se desplaza el mapa lo justo para dejarlo a la vista
    const covered = map.project(s.lonlat).y > map.getContainer().clientHeight - card.root.offsetHeight - 40;
    if (covered) map.easeTo({ center: s.lonlat, offset: [0, -card.root.offsetHeight / 2], duration: reduceMotion ? 0 : 300 });
  }
  function closeStop() {
    openStopId = null;
    if (!card.root.hidden) card.hide();
    map.getSource('stop-selected').setData(empty());
  }
  card.root.addEventListener('closed', () => { openStopId = null; map.getSource('stop-selected').setData(empty()); });

  function draw(data) {
    const lines = [], points = new Map(), all = new maplibregl.LngLatBounds();
    const color = safeColor(data.color);
    for (const d of data.directions) {
      lines.push({ type: 'Feature', properties: { color }, geometry: { type: 'LineString', coordinates: d.line } });
      d.line.forEach(p => all.extend(p));
      // El destino del GTFS es el nombre de la ruta en ambos sentidos: cada sentido va «hacia» su último
      // paradero. En ese último paradero el camión termina, así que no se anota como destino de ahí.
      const last = d.stops.at(-1);
      for (const [id, lat, lon, name, routes] of d.stops) {
        const s = points.get(id) ?? { id, name, lonlat: [lon, lat], routes: routes.split(','), towards: [] };
        if (id !== last[0] && !s.towards.includes(last[3])) s.towards.push(last[3]);
        points.set(id, s);
      }
    }
    stops = points;
    map.getSource('route-lines').setData({ type: 'FeatureCollection', features: lines });
    map.getSource('route-stops').setData({
      type: 'FeatureCollection',
      features: [...points.values()].map(s => ({ type: 'Feature', properties: { id: s.id, color }, geometry: { type: 'Point', coordinates: s.lonlat } })),
    });
    legend.textContent = 'Sentidos: ' + data.directions.map(d => `hacia ${d.stops.at(-1)[3] || 'el último paradero'}`).join(' · ');
    legend.hidden = false;
    map.fitBounds(all, { padding: { top: 40, bottom: 70, left: 30, right: 30 }, maxZoom: 15, duration: reduceMotion ? 0 : 700 });
  }

  async function select(num, keepStop = null) {
    if (!isRouteNumber(num) || !routeInfo.has(num)) return;
    const mine = ++token;
    selector.setSelected(num);
    hint.hidden = true;
    say(statusEl, 'Cargando ruta…');
    let data = cache.get(num);
    try { data ??= await fetchJson(`routes/${num}.json`); } catch {
      if (mine === token) say(statusEl, 'No se pudo cargar la ruta. Revisa tu conexión e intenta de nuevo.');
      return;
    }
    if (mine !== token) return;  // el usuario eligió otra mientras cargaba
    cache.set(num, data);
    current = data;
    say(statusEl, '');
    history.replaceState(null, '', `?ruta=${num}`);
    draw(data);
    if (keepStop && stops.has(keepStop)) openStop(keepStop); else closeStop();
  }

  function clearRoute() {
    token++;
    current = null; stops = new Map();
    for (const s of ['route-lines', 'route-stops']) map.getSource(s).setData(empty());
    closeStop();
    legend.hidden = true; say(statusEl, ''); hint.hidden = false;
    history.replaceState(null, '', location.pathname);
  }

  map.on('click', e => {
    const { x, y } = e.point, r = TAP_RADIUS;
    let best = null, bestD = Infinity;
    for (const f of map.queryRenderedFeatures([[x - r, y - r], [x + r, y + r]], { layers: ['route-stops'] })) {
      const p = map.project(f.geometry.coordinates), d = Math.hypot(p.x - x, p.y - y);
      if (d < bestD) { best = f.properties.id; bestD = d; }
    }
    if (best !== null && bestD <= r) openStop(best); else closeStop();
  });
  map.on('mousemove', e => {
    const { x, y } = e.point, r = TAP_RADIUS;
    map.getCanvas().style.cursor = map.queryRenderedFeatures([[x - r, y - r], [x + r, y + r]], { layers: ['route-stops'] }).length ? 'pointer' : '';
  });

  const fromUrl = new URLSearchParams(location.search).get('ruta');
  if (isRouteNumber(fromUrl) && routeInfo.has(fromUrl)) select(fromUrl);
}

main();
