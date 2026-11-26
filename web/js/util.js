// Utilidades pequeñas. Los colores y números vienen de datos ajenos (el GTFS): se validan aquí
// antes de usarlos en estilos o en rutas de archivo.

/** Color hexadecimal de la ruta (sin #) -> '#rrggbb'; gris si el dato no es válido. */
export const safeColor = c => (/^[0-9A-Fa-f]{6}$/.test(c) ? `#${c}` : '#555555');

/** Número de ruta válido como parte de un nombre de archivo (solo dígitos). */
export const isRouteNumber = s => typeof s === 'string' && /^[0-9]+$/.test(s);

/** Texto blanco o negro, el que dé más contraste sobre el fondo ('#rrggbb'). */
export function textOn(hex) {
  const [r, g, b] = [1, 3, 5].map(i => {
    const v = parseInt(hex.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return 1.05 / (lum + 0.05) >= (lum + 0.05) / 0.05 ? '#ffffff' : '#111111';
}
