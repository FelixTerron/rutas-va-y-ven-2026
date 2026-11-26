// Ficha del paradero: una sola en la página, así que nunca hay dos abiertas a la vez.
import { safeColor, textOn } from './util.js';

/**
 * ``routeInfo``: ``Map(ruta -> [ruta, nombre, color])``. ``onRoute(ruta)`` se llama al tocar una
 * de las rutas que pasan por el paradero. Todo el texto entra con textContent (los nombres vienen
 * de datos ajenos).
 */
export function createCard(routeInfo, onRoute) {
  const $ = id => document.getElementById(id);
  const root = $('stop-card');
  $('card-close').addEventListener('click', hide);
  document.addEventListener('keydown', e => {  // Escape en el selector solo cierra su lista
    if (e.key === 'Escape' && !root.hidden && e.target.id !== 'route-input') hide();
  });

  function show({ id, name, towards, routes }, currentRoute) {
    $('card-name').textContent = name || 'Paradero sin nombre';
    $('card-id').textContent = `Paradero n.º ${id}`;
    $('card-dir').textContent = towards.length ? `Sentido de esta ruta: hacia ${towards.join(' y hacia ')}` : '';
    const chips = $('card-routes');
    chips.replaceChildren();
    for (const num of routes) {
      const info = routeInfo.get(num);
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = num;
      if (info) {
        b.style.background = safeColor(info[2]);
        b.style.color = textOn(safeColor(info[2]));
        b.title = info[1];
        b.addEventListener('click', () => onRoute(num));
      } else b.disabled = true;  // ruta sin trazo en el mapa: se muestra el número, sin acción
      if (num === currentRoute) b.setAttribute('aria-current', 'true');
      li.append(b);
      chips.append(li);
    }
    root.hidden = false;
  }

  function hide() { root.hidden = true; root.dispatchEvent(new Event('closed')); }

  return { show, hide, root };
}
