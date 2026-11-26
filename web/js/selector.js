// Selector de ruta: campo de búsqueda con lista (patrón «combobox» accesible).
import { filterRoutes } from './search.js';
import { safeColor, textOn } from './util.js';

/**
 * Conecta el selector del HTML. ``index``: ``[[ruta, nombre, color], ...]``.
 * ``onSelect(ruta)`` y ``onClear()`` avisan a la página; ``setSelected(ruta|null)`` cambia el
 * valor desde fuera (por la dirección o por un botón de la ficha).
 */
export function createSelector(index, { onSelect, onClear }) {
  const $ = id => document.getElementById(id);
  const input = $('route-input'), list = $('route-list'), clear = $('route-clear'), swatch = $('swatch');
  const byNum = new Map(index.map(r => [r[0], r]));
  let selected = null, active = -1, shown = [];

  const label = r => `${r[0]} · ${r[1]}`;

  function render(rows) {
    shown = rows;
    list.replaceChildren();
    if (!rows.length) {
      const li = document.createElement('li');
      li.className = 'empty';
      li.setAttribute('role', 'option');
      li.setAttribute('aria-disabled', 'true');
      li.textContent = 'Ninguna ruta coincide con lo que escribiste.';
      list.append(li);
    }
    rows.forEach((r, i) => {
      const li = document.createElement('li');
      li.id = `opt-${r[0]}`;
      li.setAttribute('role', 'option');
      li.dataset.route = r[0];
      const num = document.createElement('span');
      num.className = 'num';
      num.textContent = r[0];
      num.style.background = safeColor(r[2]);
      num.style.color = textOn(safeColor(r[2]));
      const name = document.createElement('span');
      name.textContent = r[1];
      li.append(num, name);
      li.setAttribute('aria-selected', String(i === active));
      list.append(li);
    });
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function setActive(i) {
    active = shown.length ? (i + shown.length) % shown.length : -1;
    for (const li of list.children) li.setAttribute('aria-selected', String(li.dataset.route === shown[active]?.[0]));
    const li = shown[active] && $(`opt-${shown[active][0]}`);
    if (li) { input.setAttribute('aria-activedescendant', li.id); li.scrollIntoView({ block: 'nearest' }); }
    else input.removeAttribute('aria-activedescendant');
  }

  function close() {
    list.hidden = true;
    active = -1;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    input.value = selected ? label(byNum.get(selected)) : '';
  }

  function show(route) {
    selected = route;
    const row = route && byNum.get(route);
    clear.hidden = !row;
    swatch.hidden = !row;
    if (row) swatch.style.background = safeColor(row[2]);
    input.value = row ? label(row) : '';
  }

  function choose(route) {
    show(route);
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.blur();  // en el celular, esconde el teclado
    onSelect(route);
  }

  input.addEventListener('focus', () => { input.select(); render(index); });
  input.addEventListener('input', () => { active = 0; render(filterRoutes(index, input.value)); setActive(0); });
  input.addEventListener('blur', close);
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (list.hidden) render(filterRoutes(index, ''));
      setActive(active + (e.key === 'ArrowDown' ? 1 : -1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (!list.hidden && shown[active]) choose(shown[active][0]);
    } else if (e.key === 'Escape') { close(); input.blur(); }
  });
  // mousedown también se dispara al tocar: evitarlo mantiene el foco y la lista abierta hasta el clic
  list.addEventListener('mousedown', e => e.preventDefault());
  list.addEventListener('click', e => {
    const li = e.target.closest('li[data-route]');
    if (li) choose(li.dataset.route);
  });
  clear.addEventListener('click', () => { show(null); onClear(); input.focus(); });

  return { setSelected: show };
}
