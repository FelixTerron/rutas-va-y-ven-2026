// Prueba de humo del visor, sin dependencias: abre data/processed/mapa.html en Chrome (sin ventana) y
// comprueba lo que ya nos falló alguna vez: errores de JavaScript, panel que no cabe, cifras ausentes.
// Usa el WebSocket de Node >= 22 y el Chrome instalado; no instala nada.
//
// Uso (desde la raíz del repo; ver CLAUDE.md para activar Node):
//   node pipeline/tests/viewer_smoke.mjs [ruta/al/mapa.html]
// Otro Chrome: CHROME="/ruta/al/binario" node pipeline/tests/viewer_smoke.mjs
// Sale con código 1 si algo falla.
import { join, resolve } from 'node:path';
import { openChrome, sleep } from './cdp.mjs';

const root = resolve(import.meta.dirname, '../..');
const html = resolve(process.argv[2] ?? join(root, 'data/processed/mapa.html'));

let chrome;  // se abre dentro del try; el perro guardián lo cierra si la prueba se cuelga
const dog = setTimeout(async () => { console.error('FALLA: tiempo agotado (200 s)'); await chrome?.close(); process.exit(1); }, 200_000);

const failures = [];
const check = (ok, what, detail = '') => {
  console.log(`${ok ? 'ok   ' : 'FALLA'} ${what}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures.push(what);
};

try {
  chrome = await openChrome();
  const { send, ev, jsErrors } = chrome;

  // Pantalla baja a propósito (la peor que queremos soportar): el panel debe caber sin desplazarse.
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 700, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'file://' + html });
  let rendered = false;
  for (let i = 0; i < 160 && !rendered; i++) {
    await sleep(500);
    rendered = await ev('typeof map!=="undefined" && !!map.getLayer && !!map.getLayer("grid") && map.queryRenderedFeatures({layers:["grid"]}).length>1000');
  }
  check(rendered, 'el mapa de acceso se dibuja (cuadrícula con más de 1000 celdas visibles)');
  if (!rendered) throw new Error('sin mapa no hay nada más que revisar');
  await sleep(1500);

  // Aviso de bienvenida: aparece al entrar, no tapa el panel ni los créditos y «Más información» abre Consideraciones.
  const apart = (a, b) => `(()=>{const x=document.getElementById("${a}").getBoundingClientRect(),y=document.getElementById("${b}").getBoundingClientRect();
    return x.right<=y.left||y.right<=x.left||x.bottom<=y.top||y.bottom<=x.top})()`;
  check(await ev('!!document.getElementById("notice") && document.getElementById("notice").getBoundingClientRect().height>0'),
    'aviso de bienvenida visible al entrar');
  check(/no pertenece ni está afiliado a la ATY, a ningún gobierno ni a ningún partido\s+político/i.test(await ev('document.getElementById("notice").innerText')),
    'el aviso dice que no hay afiliación');
  check((await ev(apart('notice', 'panel'))) && (await ev(apart('notice', 'credits'))), 'el aviso no tapa el panel ni los créditos');
  await ev('document.getElementById("noticemore").click()'); await sleep(400);
  check(await ev('document.getElementById("info").open'), '«Más información» abre las Consideraciones');
  await ev('document.getElementById("infoclose").click()'); await sleep(300);

  const fits = () => ev('(()=>{const p=document.getElementById("panel");return p.scrollHeight<=p.clientHeight})()');
  const text = id => ev(`document.getElementById("${id}").innerText`);
  const num = s => parseFloat(s.replace('%', ''));

  for (const [i, day] of ['Día hábil', 'Sábado', 'Domingo'].entries()) {
    await ev(`document.querySelectorAll("#days button")[${i}].click()`); await sleep(1800);
    const rows = await ev('[...document.querySelectorAll("#classrows label.row")].map(r=>[...r.querySelectorAll("b")].map(b=>b.textContent))');
    check(rows.length === 5 && rows.every(r => r.length === 2), `${day}: 5 rangos con dos columnas (Calle y Personas)`);
    for (const col of [0, 1]) {
      const sum = rows.reduce((s, r) => s + num(r[col]), 0);
      check(Math.abs(sum - 100) < 0.6, `${day}: la columna ${col ? 'Personas' : 'Calle'} suma 100 %`, sum.toFixed(1));
    }
    check(/\d+(\.\d)?% de las personas a ≤ 400 m/.test(await text('headline')), `${day}: línea de resumen con la cifra principal`);
  }
  await ev('document.querySelectorAll("#days button")[0].click()'); await sleep(1200);

  check(await fits(), 'acceso: el panel cabe sin desplazarse en 700 px de alto');
  const hover = await ev('(()=>{const r=document.getElementById("hover").getBoundingClientRect();return r.bottom<=innerHeight && r.top>=0})()');
  check(hover, 'acceso: el recuadro del cursor queda a la vista');

  await ev('document.querySelector("#modes [data-mode=routes]").click()'); await sleep(1500);
  check(await fits(), 'rutas: el panel cabe sin desplazarse en 700 px de alto');
  check(/rutas base/.test(await text('headline')), 'rutas: línea de resumen');
  await ev('document.querySelector("#modes [data-mode=access]").click()'); await sleep(1000);

  await ev('document.getElementById("infobtn").click()'); await sleep(500);
  const stats = await text('stats');
  check(/de la calle está a ≤ 400 m/.test(stats) && /de las personas, a ≤ 400 m \(entre \d+ y \d+ %\)/.test(stats),
    'Consideraciones: cifras con el rango de personas');
  check(/\d[\d,]* personas \(\d/.test(await text('nostreet')), 'Consideraciones: personas sin calle cercana con su cifra');
  const info = await text('info');
  check(/Fuente: INEGI, Censo de Población y Vivienda 2020/.test(info) && /no cifras del INEGI/.test(info),
    'Consideraciones: crédito a INEGI y aviso de análisis propio (términos de libre uso)');
  check(/No pertenece ni está afiliado a la Agencia de Transporte de\s+Yucatán \(ATY\), a ningún gobierno ni a ningún partido político/.test(info),
    'Consideraciones: aviso de proyecto independiente y sin afiliación');
  await ev('document.getElementById("infoclose").click()'); await sleep(300);

  await ev('document.getElementById("helpbtn").click()'); await sleep(500);
  check((await text('help')).includes('Personas'), 'la guía «Cómo usar» menciona la columna Personas');
  await ev('document.getElementById("helpclose").click()');

  check(/no afiliado a la ATY ni a gobiernos o partidos/.test(await text('panel')), 'el panel declara que no hay afiliación');
  const credits = await text('credits');
  check(/no afiliado a la ATY, a ningún gobierno ni a ningún partido político/.test(credits) &&
    /Fuente: ATY \(GTFS\); INEGI, Censo de Población y Vivienda 2020/.test(credits), 'franja de créditos: sin afiliación y fuentes');
  const clear = await ev(`(()=>{const c=document.getElementById("credits").getBoundingClientRect(),p=document.getElementById("panel").getBoundingClientRect();
    return c.top>=0 && c.bottom<=innerHeight && (c.top>=p.bottom || c.left>=p.right)})()`);
  check(clear, 'la franja de créditos queda a la vista y no tapa el panel (700 px de alto)');
  const slim = await ev('(()=>{const e=document.getElementById("credits");return [e.getBoundingClientRect().height,+getComputedStyle(e).opacity]})()');
  check(slim[0] <= 34 && slim[1] <= 0.7, 'la franja de créditos es discreta (≤ 34 px de alto, opacidad ≤ 0.7)', `${Math.round(slim[0])} px, opacidad ${slim[1]}`);
  const free = await ev(`(()=>{const c=document.getElementById("credits").getBoundingClientRect();
    return [...document.querySelectorAll(".maplibregl-ctrl-attrib,.maplibregl-ctrl-scale,.maplibregl-ctrl-zoom-in")].every(e=>{const r=e.getBoundingClientRect();
      return r.width===0||c.right<=r.left||r.right<=c.left||c.bottom<=r.top||r.bottom<=c.top})})()`);
  check(free, 'la franja de créditos no se encima con la atribución, la escala ni el zoom del mapa');
  await ev('document.getElementById("noticeclose").click()'); await sleep(200);
  check(await ev('!document.getElementById("notice")'), 'la × cierra el aviso');
  check(/no afiliado a la ATY/.test(await text('credits')), 'tras cerrar el aviso, la franja de créditos sigue visible');
  check(jsErrors.length === 0, 'sin errores de JavaScript', jsErrors.slice(0, 3).join(' | '));
} catch (e) {
  failures.push(String(e.message ?? e)); console.error('FALLA:', e.message ?? e);
} finally { clearTimeout(dog); await chrome?.close(); }

console.log(failures.length ? `\n${failures.length} comprobación(es) fallaron` : '\nTodas las comprobaciones pasaron');
process.exit(failures.length ? 1 : 0);
