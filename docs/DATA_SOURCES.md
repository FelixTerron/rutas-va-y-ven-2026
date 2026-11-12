# Fuentes de datos

## GTFS oficial de Va-y-Ven (ATY)

| Campo | Valor |
|---|---|
| Publicador | Agencia de Transporte de Yucatán (ATY) — https://transporteyucatan.org.mx/ |
| URL del feed | https://transit-scheduler.com/api/export-gtfs/latest (sin autenticación) |
| Catálogo | Solicitud de alta en Mobility Database: MobilityData/mobility-database-catalogs#1692 (abierta al 2026-11-09) |
| Revisado | 2026-11-09: versión 11.7, vigencia 2026-01-01 a 2026-12-31 |
| Contenido | 174 rutas, 3,252 paradas, 50,535 viajes, ~74 mil puntos de `shapes`, ~1.59 M de `stop_times`, tarifas |
| Descarga | `data/raw/` (ignorado por git); `manifest.json` guarda fecha, tamaño y SHA-256 |

### Pendientes
- [ ] **Licencia / términos de uso.** No se encontró licencia en el feed ni en el issue. Confirmar con la ATY antes de redistribuir el GTFS o datos derivados.
- [ ] **Cobertura.** El feed trae 174 `route_id`; un estudio de 2025 menciona 205 rutas. Medir si son variantes o rutas faltantes.
- [ ] **Estabilidad de la URL.** Es un servicio de terceros; registrar versión del feed en cada descarga.

## Red peatonal: OpenStreetMap

| Campo | Valor |
|---|---|
| Fuente | OpenStreetMap vía API Overpass, con `osmnx` (`network_type="walk"`) |
| Descarga | 2026-11-11, caja de las paradas con servicio + ~2 km; 79,051 nodos, 239,452 tramos dirigidos |
| Ubicación | `data/raw/osm/merida_walk.graphml` (~93 MB, ignorado por git); código en `pipeline/va_y_ven/streets.py` |
| Licencia | ODbL © colaboradores de OpenStreetMap: atribuir; si se publican derivados, compartirlos bajo la misma licencia |
| Vigencia | Es una foto de esa fecha; si cambia la red vial o se mapean cruces nuevos, hay que volver a descargar |

## Demanda / abordajes por parada (para el mapa de calor de pasajeros)

**Estado (2026-11-10):** no se encontró ningún dato público de validaciones, ascensos por parada ni afluencia desglosada. Solo hay cifras sueltas en prensa (p. ej. la ATY reporta ~10 % menos afluencia en vacaciones escolares; filas largas en rutas como la 28 y la 74). El GTFS no incluye demanda.

| Opción | Qué da | Costo / riesgo |
|---|---|---|
| Solicitar a la ATY validaciones de la tarjeta/app, agregadas por parada, hora y día | Abordajes reales | Depende de que el sistema registre la parada (muchos solo registran ruta y hora); trámite lento; exigir anonimización |
| Proxy de **oferta**: salidas programadas por parada (`stop_times`) | Servicio ofrecido, no demanda | Bajo; ya disponible |
| Proxy de **demanda potencial**: población y empleo en el área de influencia (~400-800 m) de cada parada, con Censo INEGI (AGEB/manzana) y DENUE | Estimación razonable de dónde se *esperaría* demanda | Medio; datos abiertos, por verificar descarga y año |
| Conteos propios en campo (muestreo en paraderos clave) | Calibración/validación de los modelos | Alto en tiempo; muy valioso para tesis/estudios |
| Reporte colaborativo: usuarios marcan en el mapa dónde esperan su camión | Demanda declarada, por zona y hora | Requiere backend, aviso de privacidad y moderación; muestra sesgada (no representativa) |

Recomendación: construir primero el mapa de oferta (gratis), luego el de demanda potencial, y solicitar a la ATY los datos reales en paralelo; si llegan, sustituyen al modelo.

## Referencias de validación (no son fuente)
- Metro Route Atlas, mapa de Mérida: https://metrorouteatlas.net/cities/mexico/meridaYUC.html
