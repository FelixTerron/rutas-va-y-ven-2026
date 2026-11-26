// Búsqueda de rutas por número o por nombre. Función pura: no toca la página.

/** Minúsculas y sin acentos, para que «Periférico», «periferico» y «PERIFERICO» coincidan. */
export const normalize = s => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();

/**
 * ``index``: ``[[ruta, nombre, color], ...]`` en orden numérico. Devuelve las que coinciden con
 * ``query``: primero el número exacto, luego los números que empiezan así y al final los nombres
 * que contienen todas las palabras. Con solo dígitos se busca únicamente por número.
 */
export function filterRoutes(index, query) {
  const q = normalize(query).replace(/^ruta\s+/, '');
  if (!q) return index;
  const digits = /^[0-9]+$/.test(q);
  const words = q.split(/\s+/);
  const tiers = [[], [], []];
  for (const row of index) {
    const [num, name] = row;
    if (num === q) tiers[0].push(row);
    else if (num.startsWith(q)) tiers[1].push(row);
    else if (!digits) {
      const n = normalize(name);
      if (words.every(w => n.includes(w))) tiers[2].push(row);
    }
  }
  return tiers.flat();
}
