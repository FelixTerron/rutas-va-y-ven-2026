// Prueba de humo del visor, sin dependencias: abre data/processed/mapa.html en Chrome (sin ventana) y
// comprueba lo que ya nos falló alguna vez: errores de JavaScript, panel que no cabe, cifras ausentes.
// Usa el WebSocket de Node >= 22 y el Chrome instalado; no instala nada.
//
// Uso (desde la raíz del repo; ver CLAUDE.md para activar Node):
//   node pipeline/tests/viewer_smoke.mjs [ruta/al/mapa.html]
// Otro Chrome: CHROME="/ruta/al/binario" node pipeline/tests/viewer_smoke.mjs
// Sale con código 1 si algo falla.
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '../..');
const html = resolve(process.argv[2] ?? join(root, 'data/processed/mapa.html'));
const CHROME = process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const profile = mkdtempSync(join(tmpdir(), 'viewer-smoke-'));
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', '--enable-unsafe-swiftshader',
  '--use-angle=swiftshader', `--user-data-dir=${profile}`, '--window-size=1400,900', 'about:blank'], { stdio: 'ignore' });
const closed = new Promise(r => chrome.once('exit', r));
const cleanup = async () => {  // Chrome sigue escribiendo en su perfil hasta salir: esperar antes de borrarlo
  chrome.kill();
  await Promise.race([closed, sleep(5000)]);
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
};
const dog = setTimeout(async () => { console.error('FALLA: tiempo agotado (200 s)'); await cleanup(); process.exit(1); }, 200_000);

const failures = [];
const check = (ok, what, detail = '') => {
  console.log(`${ok ? 'ok   ' : 'FALLA'} ${what}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures.push(what);
};

try {
  let port;  // con --remote-debugging-port=0, Chrome escribe el puerto elegido en este archivo
  for (let i = 0; i < 80 && !port; i++) {
    try { port = readFileSync(join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]; } catch { await sleep(250); }
  }
  if (!port) throw new Error('Chrome no abrió el puerto de depuración; ¿es correcta la ruta CHROME?');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise(r => (ws.onopen = r));

  let id = 0;
  const pending = new Map(), jsErrors = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown') {
      jsErrors.push((m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 160));
    }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      jsErrors.push(m.params.args.map(a => a.value ?? a.description).join(' ').slice(0, 160));
    }
  };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
  await send('Runtime.enable'); await send('Page.enable');

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
  await ev('document.getElementById("infoclose").click()'); await sleep(300);

  await ev('document.getElementById("helpbtn").click()'); await sleep(500);
  check((await text('help')).includes('Personas'), 'la guía «Cómo usar» menciona la columna Personas');
  await ev('document.getElementById("helpclose").click()');

  check(/Fuente: INEGI/.test(await text('panel')), 'el pie del panel cita a INEGI');
  check(jsErrors.length === 0, 'sin errores de JavaScript', jsErrors.slice(0, 3).join(' | '));
  ws.close();
} catch (e) {
  failures.push(String(e.message ?? e)); console.error('FALLA:', e.message ?? e);
} finally { clearTimeout(dog); await cleanup(); }

console.log(failures.length ? `\n${failures.length} comprobación(es) fallaron` : '\nTodas las comprobaciones pasaron');
process.exit(failures.length ? 1 : 0);
