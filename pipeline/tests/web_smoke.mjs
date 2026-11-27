// Prueba de humo de la web pública (Vanyven), sin dependencias: sirve web/ y los datos ligeros con un
// servidor propio de Node (solo esas dos carpetas, nunca el GTFS crudo), abre Chrome sin ventana en
// tamaño de celular y de escritorio y comprueba lo que importa: que la búsqueda y la ficha funcionan,
// que hay una sola ficha abierta, que nada se sale de la pantalla, que no hay errores y que la
// página de inicio sigue siendo ligera. No necesita internet (el mapa base es propio).
//
// Antes: PYTHONPATH=pipeline uv run python -m va_y_ven.public_data, ... -m va_y_ven.web_vendor y ... -m va_y_ven.basemap
// Uso (desde la raíz del repo; ver CLAUDE.md para activar Node):
//   node pipeline/tests/web_smoke.mjs
// Sale con código 1 si algo falla.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, resolve, sep } from 'node:path';
import { gzipSync } from 'node:zlib';
import { openChrome, sleep } from './cdp.mjs';
import { filterRoutes, normalize } from '../../web/js/search.js';
import { isRouteNumber, safeColor, textOn } from '../../web/js/util.js';

const root = resolve(import.meta.dirname, '../..');
const HOME_BUDGET_KB = 150;  // la página de inicio (sin mapa), comprimida; propuesta de diseño, ver DECISIONS.md
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.pbf': 'application/x-protobuf' };

const failures = [];
const check = (ok, what, detail = '') => {
  console.log(`${ok ? 'ok   ' : 'FALLA'} ${what}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures.push(what);
};

// --- Servidor: solo /web/ y /data/processed/public/; anota cuánto pesó (comprimido) cada archivo
const served = new Map();
const allowed = [join(root, 'web') + sep, join(root, 'data/processed/public') + sep];
const server = createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = resolve(root, '.' + path);
  res.setHeader('Cache-Control', 'no-store');  // que cada carga se mida completa
  if (path === '/favicon.ico') return res.writeHead(204).end();
  if (!allowed.some(a => file.startsWith(a))) return res.writeHead(404).end('no');
  try {
    const body = await readFile(file);
    served.set(path, gzipSync(body).length);
    const type = TYPES[extname(file)] ?? 'application/octet-stream';
    const m = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range ?? '');  // PMTiles pide el mapa por rangos
    if (!m) return res.writeHead(200, { 'Content-Type': type }).end(body);
    const a = +m[1], b = m[2] === '' ? body.length - 1 : Math.min(+m[2], body.length - 1);
    res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${a}-${b}/${body.length}` }).end(body.subarray(a, b + 1));
  } catch { res.writeHead(404).end('no'); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

let chrome;
const dog = setTimeout(async () => { console.error('FALLA: tiempo agotado (300 s)'); await chrome?.close(); process.exit(1); }, 300_000);

try {
  // --- Funciones puras (sin navegador)
  check(normalize('Periférico ÑANDÚ') === 'periferico nandu', 'normalize quita acentos y mayúsculas');
  const idx = [['1', 'Centro - Norte', 'FF0000'], ['10', 'Xmatkuil', 'DB3A2F'], ['100', 'Periférico', '000000'], ['2', 'Calle 10', '00FF00']];
  const nums = q => filterRoutes(idx, q).map(r => r[0]).join(',');
  check(nums('10') === '10,100', 'buscar «10»: primero el número exacto y luego los que empiezan igual; solo por número', nums('10'));
  check(nums('periferico') === '100' && nums('ruta 10') === '10,100' && nums('xm zzz') === '' && nums('xm tku') === '10', 'buscar por nombre sin acentos y con «ruta 10»');
  check(nums('') === '1,10,100,2' && nums('zzz') === '', 'sin texto salen todas; sin coincidencias, ninguna');
  check(safeColor('DB3A2F') === '#DB3A2F' && safeColor('red;x') === '#555555', 'safeColor rechaza lo que no es un color hexadecimal');
  check(isRouteNumber('10') && !isRouteNumber('../x') && !isRouteNumber('1a') && !isRouteNumber(10), 'isRouteNumber solo acepta dígitos');
  check(textOn('#ffffff') === '#111111' && textOn('#000000') === '#ffffff', 'textOn elige el texto con más contraste');

  chrome = await openChrome({ captureLog: true });
  const { send, ev, jsErrors } = chrome;
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });  // sin ventana, la página no tendría foco
  const waitFor = async (expr, what, ms = 60_000) => {
    for (let t = 0; t < ms; t += 250) { if (await ev(expr)) return true; await sleep(250); }
    check(false, `tiempo agotado esperando: ${what}`); return false;
  };
  const go = async url => { served.clear(); await send('Page.navigate', { url: base + url }); await waitFor('document.readyState==="complete"', 'carga de ' + url); };
  const visible = sel => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});return !!e && !e.hidden && e.getBoundingClientRect().height>0})()`);
  const apart = (a, b) => ev(`(()=>{const x=document.querySelector(${JSON.stringify(a)}).getBoundingClientRect(),y=document.querySelector(${JSON.stringify(b)}).getBoundingClientRect();
    return x.right<=y.left||y.right<=x.left||x.bottom<=y.top||y.bottom<=x.top})()`);
  const noOverflow = () => ev('document.documentElement.scrollWidth<=innerWidth');
  const key = async (k, vk, text) => { for (const type of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', { type, key: k, code: k, windowsVirtualKeyCode: vk, ...(type === 'keyDown' && text ? { text } : {}) }); };
  const type = async text => { await ev('document.getElementById("route-input").focus(); document.getElementById("route-input").select()'); await send('Input.insertText', { text }); };
  const options = () => ev('[...document.querySelectorAll("#route-list li[data-route]")].map(l=>l.dataset.route)');

  for (const vp of [{ name: 'celular 390×844', w: 390, h: 844, mobile: true }, { name: 'escritorio 1280×700', w: 1280, h: 700, mobile: false }]) {
    console.log(`\n== ${vp.name}`);
    await send('Emulation.setDeviceMetricsOverride', { width: vp.w, height: vp.h, deviceScaleFactor: vp.mobile ? 2 : 1, mobile: vp.mobile });
    await send('Emulation.setTouchEmulationEnabled', { enabled: vp.mobile });
    const tap = async (x, y) => {
      if (vp.mobile) {
        await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
        await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      } else {
        for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 });
      }
    };

    // Inicio
    await go('/web/index.html');
    const home = await ev('document.body.innerText');
    check(/Abrir el mapa/.test(home), 'inicio: botón «Abrir el mapa»');
    check(await ev('document.querySelector("a.big-link").getAttribute("href")') === 'mapa.html', 'inicio: el botón lleva al mapa');
    check(/no recopila datos sobre cómo usas el transporte público: ni qué rutas tomas, ni de dónde a dónde, ni a qué hora/.test(home), 'inicio: aviso de privacidad aprobado');
    check(/no pertenece ni está afiliado a la ATY, a ningún gobierno ni a ningún partido político/.test(home), 'inicio: aviso de independencia');
    check(/ATY \(GTFS\)/.test(home) && /OpenStreetMap/.test(home) && /Protomaps/.test(home), 'inicio: fuentes citadas (ATY, OpenStreetMap, Protomaps)');
    check(!/sin fines de lucro/i.test(home), 'inicio: no se declara «sin fines de lucro»');
    check(await noOverflow(), 'inicio: nada se sale del ancho de la pantalla');
    const homeKb = [...served.values()].reduce((a, b) => a + b, 0) / 1024;
    check(homeKb <= HOME_BUDGET_KB && ![...served.keys()].some(p => p.includes('vendor')), `inicio: pesa ≤ ${HOME_BUDGET_KB} KB comprimidos y no carga el mapa`, `${homeKb.toFixed(1)} KB`);

    // Mapa vacío y selector
    await go('/web/mapa.html');
    if (!await waitFor('!!window.vanyven && !!vanyven.map.getLayer("stop-selected")', 'el mapa y sus capas')) continue;
    // El mapa base es propio: las calles salen de merida.pmtiles (leído por rangos) y solo se pidió a este servidor
    check(await waitFor('vanyven.map.querySourceFeatures("protomaps",{sourceLayer:"roads"}).length>0', 'teselas de calles del mapa base propio', 30_000),
      'mapa: el mapa base propio dibuja calles', `${[...served.keys()].filter(p => p.includes('basemap')).length} archivos de vendor/basemap`);
    check(await visible('#hint'), 'mapa: empieza vacío con la invitación a elegir una ruta');
    check(await noOverflow(), 'mapa: nada se sale del ancho de la pantalla');
    check(await ev('document.getElementById("route-input").getBoundingClientRect().height>=44'), 'selector: el campo mide al menos 44 px de alto');
    await ev('document.getElementById("route-input").focus()');
    check((await options()).length === 105, 'selector: al abrirlo salen las 105 rutas', String((await options()).length));
    await type('periferico');
    check((await options()).includes('2'), 'selector: «periferico» (sin acento) encuentra el Periférico');
    await type('10');
    const o10 = await options();
    check(o10[0] === '10' && o10.every(n => n.startsWith('10')), 'selector: «10» pone la ruta 10 primero y solo trae números que empiezan con 10', o10.slice(0, 4).join(','));
    await type('zzzz');
    check(await visible('#route-list li.empty'), 'selector: sin coincidencias avisa con un mensaje');
    // Tocar una opción de la lista con el dedo/ratón (no solo Enter): el campo pierde el foco y la lista no debe cerrarse antes del toque
    await ev('(()=>{const i=document.getElementById("route-input");i.blur();i.focus()})()');  // reabre la lista completa
    await sleep(300);
    const opt = await ev('(()=>{const r=document.querySelector("#route-list li[data-route=\\"2\\"]").getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()');
    await tap(opt[0], opt[1]);
    await waitFor('location.search==="?ruta=2"', 'elegir una opción tocándola');
    check((await ev('document.getElementById("route-input").value')).startsWith('2 · '), 'selector: tocar una opción de la lista elige esa ruta');
    await ev('document.getElementById("route-clear").click()');
    await sleep(300);
    await type('xmat');
    const ox = await options();
    check(ox.length >= 1, 'selector: «xmat» encuentra Xmatkuil', ox.join(','));
    await key('Enter', 13, '\r');
    const route = ox[0];
    await waitFor(`vanyven.map.queryRenderedFeatures({layers:["route-stops"]}).length>5`, 'paraderos de la ruta dibujados');
    check((await ev('document.getElementById("route-input").value')).startsWith(`${route} · `), 'selector: Enter elige la ruta y la muestra en el campo');
    check(!(await visible('#hint')), 'mapa: al elegir se oculta la invitación');
    check((await ev('location.search')) === `?ruta=${route}`, 'la dirección recuerda la ruta (se puede compartir)');
    check(await ev('vanyven.map.queryRenderedFeatures({layers:["route-line"]}).length>0'), 'mapa: se dibuja el recorrido');

    // Dos paraderos aislados (a >= 70 m de cualquier otro de la ruta), tomados de los datos; el mapa se
    // centra en cada uno y se toca a ~8 px del punto: el paradero más cercano al toque es el que cuenta
    const data = await (await fetch(`${base}/data/processed/public/routes/${route}.json`)).json();
    const uniq = new Map(data.directions.flatMap(d => d.stops).map(s => [s[0], s]));
    const all = [...uniq.values()];
    const dist = (p, q) => Math.hypot((p[1] - q[1]) * 111320, (p[2] - q[2]) * 111320 * Math.cos(p[1] * Math.PI / 180));
    const isolated = all.filter(s => all.every(o => o === s || dist(s, o) >= 70));
    const a = isolated[Math.floor(isolated.length / 3)];
    const b = isolated.find(s => a && dist(s, a) >= 1500) ?? isolated.at(-1);
    check(!!a && !!b && a !== b, 'prueba: hay dos paraderos aislados en la ruta', `${isolated.length} de ${all.length}`);
    const rect = await ev('(()=>{const r=document.getElementById("map").getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()');
    const [mw, mh] = [rect[2], rect[3]];
    const focusOn = async s => {
      await ev(`vanyven.map.jumpTo({center:[${s[2]},${s[1]}],zoom:16})`);
      await waitFor('vanyven.map.queryRenderedFeatures({layers:["route-stops"]}).length>0', 'paraderos a la vista tras acercar');
      await sleep(300);
    };
    const tapCenter = (dx = 6, dy = 6) => tap(rect[0] + mw / 2 + dx, rect[1] + mh / 2 + dy);
    const stopsPx = () => ev(`[...vanyven.map.queryRenderedFeatures({layers:["route-stops"]})].map(f=>{const p=vanyven.map.project(f.geometry.coordinates);return [f.properties.id,p.x,p.y]})`);
    let px = [];
    if (a && b) {
      await focusOn(a);
      await tapCenter();
      await waitFor('!document.getElementById("stop-card").hidden', 'ficha abierta');
      check(await ev('document.getElementById("card-id").innerText') === `Paradero n.º ${a[0]}`, 'ficha: un toque cerca del punto abre ese paradero', await ev('document.getElementById("card-id").innerText'));
      const name = await ev('document.getElementById("card-name").innerText');
      check(name === a[3] && !/_\d{3,}$/.test(name), 'ficha: muestra el nombre del paradero sin el sufijo del número', name);
      const chips = await ev('[...document.querySelectorAll("#card-routes button")].map(b=>b.textContent)');
      check(chips.join() === a[4].split(',').join(), 'ficha: muestra las rutas que pasan', chips.join(','));
      check(chips.includes(route), 'ficha: las rutas que pasan incluyen la ruta elegida');
      check(!/por hora|frecuencia|camiones|sentido|hacia/i.test(await ev('document.getElementById("stop-card").innerText')), 'ficha: no muestra estimaciones de frecuencia ni destinos (basta el número de la ruta)');
      check(await ev(`(()=>{const r=document.getElementById("stop-card").getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight})()`), 'ficha: cabe dentro de la pantalla');
      check(await apart('#stop-card', '.maplibregl-ctrl-attrib') && await apart('#stop-card', '.maplibregl-ctrl-zoom-in'), 'ficha: no tapa la atribución ni el zoom del mapa');

      await focusOn(b);
      await tapCenter();
      await waitFor(`document.getElementById("card-id").innerText==="Paradero n.º ${b[0]}"`, 'segunda ficha');
      check(await ev('[...document.querySelectorAll(".stop-card")].filter(e=>!e.hidden).length') === 1, 'ficha: solo hay una abierta a la vez');
      px = await stopsPx();

      // Tocar un lugar vacío cierra la ficha
      let empty;
      for (let x = 30; x < mw - 70 && !empty; x += 25) for (let y = 70; y < mh - 260 && !empty; y += 25) {
        if (px.every(o => Math.hypot(o[1] - x, o[2] - y) > 40)) empty = [x, y];
      }
      check(!!empty, 'prueba: hay un lugar vacío del mapa donde tocar');
      if (empty) { await tap(rect[0] + empty[0], rect[1] + empty[1]); await sleep(300); check(!(await visible('#stop-card')), 'ficha: tocar un lugar vacío del mapa la cierra'); }

      // Saltar a otra ruta desde la ficha: un paradero con varias rutas
      const multi = all.find(s => s[4].includes(',') && all.every(o => o === s || dist(s, o) >= 15));
      check(!!multi, 'prueba: hay un paradero con varias rutas');
      if (multi) {
        await focusOn(multi);
        await tapCenter(0, 0);
        await waitFor(`document.getElementById("card-id").innerText==="Paradero n.º ${multi[0]}"`, 'ficha del paradero con varias rutas');
        const other = (await ev('[...document.querySelectorAll("#card-routes button:not(:disabled)")].map(b=>b.textContent)')).find(n => n !== route);
        check(!!other, 'ficha: ofrece otra ruta que pasa por el paradero');
        await ev(`[...document.querySelectorAll("#card-routes button")].find(b=>b.textContent===${JSON.stringify(other)}).click()`);
        await waitFor(`location.search===${JSON.stringify('?ruta=' + other)}`, 'cambio de ruta desde la ficha');
        check((await ev('location.search')) === `?ruta=${other}`, 'ficha: tocar otra ruta la elige en el mapa', other);
        check(await ev('[...document.querySelectorAll(".stop-card")].filter(e=>!e.hidden).length') <= 1, 'ficha: tras cambiar de ruta sigue habiendo a lo sumo una');
      }
    }

    // Quitar la ruta
    await ev('document.getElementById("route-clear").click()');
    await sleep(500);
    check(await visible('#hint') && await ev('vanyven.map.queryRenderedFeatures({layers:["route-stops","route-line"]}).length') === 0 && !(await visible('#stop-card')),
      'mapa: «×» quita la ruta, los paraderos y la ficha y vuelve la invitación');
    check((await ev('location.search')) === '', 'la dirección vuelve a quedar sin ruta');

    // Direcciones: válida, y valores que no son un número de ruta
    await go(`/web/mapa.html?ruta=${route}`);
    await waitFor(`!!window.vanyven && !!vanyven.map.getLayer("route-line") && vanyven.map.queryRenderedFeatures({layers:["route-line"]}).length>0`, 'ruta desde la dirección');
    check((await ev('document.getElementById("route-input").value')).startsWith(`${route} · `), 'dirección con ?ruta=N: abre esa ruta');
    await go('/web/mapa.html?ruta=..%2F..%2Fraw');
    await waitFor('!!window.vanyven && !!vanyven.map.getLayer("stop-selected")', 'mapa con ruta inválida');
    await sleep(500);
    check(await visible('#hint') && ![...served.keys()].some(p => p.includes('/routes/')), 'dirección con ?ruta= inválida: se ignora y no pide ningún archivo');
  }

  // Lo que no debe servirse nunca
  const raw = await fetch(`${base}/data/raw/gtfs/stops.txt`);
  check(raw.status === 404 && (await fetch(`${base}/web/../README.md`)).status === 404, 'el servidor de prueba no expone data/raw ni el resto del repo');
  check(jsErrors.length === 0, 'sin errores de JavaScript ni del navegador', jsErrors.slice(0, 3).join(' | '));
} catch (e) {
  failures.push(String(e.message ?? e)); console.error('FALLA:', e.stack ?? e);
} finally { clearTimeout(dog); await chrome?.close(); server.close(); }

console.log(failures.length ? `\n${failures.length} comprobación(es) fallaron` : '\nTodas las comprobaciones pasaron');
process.exit(failures.length ? 1 : 0);
