// Ayudante común de las pruebas de humo: abre el Chrome instalado (sin ventana) y lo maneja por el
// protocolo de depuración (CDP). Sin dependencias: usa el WebSocket de Node >= 22.
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export const sleep = ms => new Promise(r => setTimeout(r, ms));
const CHROME = process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

/**
 * Devuelve ``{ send, ev, jsErrors, close }``. ``ev(expr)`` evalúa JavaScript en la página y devuelve
 * el valor. ``jsErrors`` junta excepciones y ``console.error``; con ``captureLog`` también los
 * errores del navegador (políticas de seguridad bloqueadas, recursos que no cargan).
 */
export async function openChrome({ captureLog = false, windowSize = '1400,900' } = {}) {
  const profile = mkdtempSync(join(tmpdir(), 'smoke-'));
  const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', '--enable-unsafe-swiftshader',
    '--use-angle=swiftshader', `--user-data-dir=${profile}`, `--window-size=${windowSize}`, 'about:blank'], { stdio: 'ignore' });
  const closed = new Promise(r => chrome.once('exit', r));
  const close = async () => {  // Chrome sigue escribiendo en su perfil hasta salir: esperar antes de borrarlo
    chrome.kill();
    await Promise.race([closed, sleep(5000)]);
    rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
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
    ws.onmessage = e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
      if (m.method === 'Runtime.exceptionThrown') {
        jsErrors.push((m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 160));
      }
      if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
        jsErrors.push(m.params.args.map(a => a.value ?? a.description).join(' ').slice(0, 160));
      }
      if (captureLog && m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
        jsErrors.push(`${m.params.entry.text} ${m.params.entry.url ?? ''}`.slice(0, 200));
      }
    };
    const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
    const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
    await send('Runtime.enable'); await send('Page.enable');
    if (captureLog) await send('Log.enable');
    return { send, ev, jsErrors, close: async () => { ws.close(); await close(); } };
  } catch (e) { await close(); throw e; }
}
