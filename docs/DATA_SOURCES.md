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

### Quién publica el feed (verificado el 2026-11-18)
- **Indicios de que es de la ATY:** `feed_info.txt` y `agency.txt` nombran como publicador y contacto a la ATY (transporteyucatan.org.mx); la página de inicio de la ATY tiene un recuadro «GTFS — Descargar» (su enlace `/gtfs` respondió 404 a `curl`; no se pudo ver a dónde lleva); el catálogo de Mobility Database lo registra como «Official Feed» (issue #1692, abierto por la cuenta `mobilitydataio`, no por la ATY).
- **Quién lo aloja:** `transit-scheduler.com` («Plataforma Institucional GTFS», código abierto, autor Juan Monroy Andrade, repo `transit-scheduler-backend`), un servicio **de terceros**; el feed se regenera a diario (hay un export del 2026-11-18; el nuestro es del 2026-11-06). No consta por escrito que la ATY lo haya contratado ni autorizado su uso por terceros.
- No se revisaron los términos de `transit-scheduler.com`.

### Pendientes
- [ ] **Licencia / términos de uso.** No se encontró licencia en el feed (GTFS no tiene campo de licencia), ni en el issue, ni en la página de la ATY, ni en la plataforma. Por decisión del usuario (recordada el 2026-11-25) **no se pedirá permiso a la ATY**: se publicará con atribución y aviso de no afiliación. Ver `docs/DECISIONS.md` (riesgos de publicar sin licencia).
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

## Mapa base de la vista pública: Protomaps (PMTiles autohospedado) (adoptado el 2026-11-27)

| Campo | Valor |
|---|---|
| Datos | Compilación diaria de Protomaps `20261125` (`build.protomaps.com`), recortada a Mérida (lon -89.85..-89.40, lat 20.74..21.26; cubre las 105 rutas), zoom 0-15, 6.0 MB. Datos de **OpenStreetMap (ODbL)**. Se recorta una vez con `pmtiles extract` (lee unos pocos MB por rangos; Protomaps desaconseja enlazar directo a las compilaciones) y se sirve desde `web/vendor/basemap/` (no se versiona) |
| Estilo | `@protomaps/basemaps` 5.7.2, «grayscale» (el que mejor resalta las rutas), etiquetas en español, una sola tipografía (Noto Sans Regular, SIL OFL). Íconos: sprite «light» de `protomaps/basemaps-assets`. Diseño CC0 y código BSD-3 según el paquete |
| Atribución | En el mapa «© OpenStreetMap» (del estilo) y en el pie de la página «© OpenStreetMap contributors, Protomaps» |
| Privacidad | La página del mapa **no pide nada a terceros** (CSP `connect-src 'self'`); quien aloje el sitio verá la IP como en cualquier página. Se cierra lo que dejaba abierto OpenFreeMap (IP hacia OpenFreeMap y Cloudflare) |
| Verificación | `va_y_ven.basemap` rechaza cualquier descarga cuya huella no coincida: binario `pmtiles` 1.31.2 (SHA-256 de GitHub; **solo macOS arm64**), `pmtiles.js` 4.5.0 y `@protomaps/basemaps` 5.7.2 (SHA-512 del registro de npm) y fuentes e íconos (SHA-256, commit fijo). Sin scripts de instalación; no se tocó `package.json` |
| Riesgos | Las compilaciones diarias se retiran con el tiempo: para actualizar hay que pasar una fecha reciente. Los datos envejecen (recorte de 2026-11-25): refrescar de vez en cuando. No se leyeron los términos de uso de `build.protomaps.com` más allá de la nota sobre enlazar directo (uso: una descarga de 6 MB) |

## Mapa base de OpenFreeMap (registro histórico, 2026-11-26) y MapLibre GL JS

*Desde el 2026-11-27 la **vista pública ya no usa OpenFreeMap** (ver la sección anterior); lo sigue usando el visor de análisis, que es local y no se publica. Lo de abajo queda como registro de lo leído.*

| Campo | Valor |
|---|---|
| Teselas y estilos | OpenFreeMap — `https://tiles.openfreemap.org/styles/positron` (vista pública, claro) y `.../dark` (visor de análisis). Datos de OpenStreetMap (ODbL) y OpenMapTiles |
| Atribución | La del estilo (se muestra en el mapa) y, en el pie de la página, «© OpenStreetMap contributors, OpenFreeMap» |
| Privacidad | Al abrir la página del mapa, **el navegador pide las teselas directamente a OpenFreeMap**, que recibe la dirección IP de la persona. La página de inicio no hace ninguna petición externa. **Por verificar antes de publicar:** la política de privacidad y los términos de uso de OpenFreeMap, y reflejarlo en el aviso de privacidad si hace falta |
| Lectura de términos y privacidad (2026-11-26) | Páginas oficiales: `openfreemap.org/tos/` (actualizada el 24-nov-2026, hace dos días), `/privacy/` (8-oct-2026), `/quick_start/` y los repositorios `hyperknot/openfreemap` y `openfreemap-styles`. **Sin registro, claves ni cookies**; «no limits on the number of map views or requests»; uso comercial permitido; **atribución obligatoria**; servicio «as-is», **sin SLA y puede discontinuarse sin aviso**; los términos prohíben recolectar datos del servicio «in automated ways» (salvo descargas offline con límites: 3,000 teselas, 50 MB, 4 peticiones en paralelo). **Registros:** los de acceso son anónimos y «do not contain IP addresses»; los de **error pueden incluir la IP y la URL pedida (se borran a los 7 días)** y, ante abuso o incidente de seguridad, se puede registrar la IP hasta 30 días. Los términos y la política mencionan que pueden usar **Cloudflare como CDN**. El README dice que `.org` no pasa por Cloudflare, pero **comprobé el 2026-11-26 que `tiles.openfreemap.org` responde con `server: cloudflare` y `cf-ray`**: sí pasa. Todo lo que carga el estilo `positron` (estilo, sprites, fuentes y teselas) sale de `tiles.openfreemap.org` |
| Licencias de los estilos | Código BSD 3-Clause y diseño CC BY 4.0; **Positron está «derivado de CartoDB Basemaps», con diseño CC BY 3.0** (según el `LICENSE.md` del repo de estilos). Fuentes Noto Sans (SIL OFL 1.1), iconos Maki (CC0). **Por decidir:** si conviene acreditar también a CARTO en los créditos (la guía de inicio solo exige OpenMapTiles y OpenStreetMap) |
| Riesgos para Vanyven | (1) Sin SLA: el mapa base puede caer o cambiar; la salida es autohospedar PMTiles (ver «Abiertas»). (2) La IP de quien abre el mapa llega a OpenFreeMap y a Cloudflare: **no la ve Vanyven**, pero el aviso de privacidad no lo dice (decisión del usuario pendiente). (3) Las pruebas de humo cargan el mapa real en cada ejecución: pocas peticiones, pero no repetirlas en bucle. (4) No leí el `LICENSE.md` del repo principal ni los archivos de sprites y glifos |
| MapLibre GL JS | 5.24.0, copiado a `web/vendor/` (ignorado por git) con `va_y_ven.web_vendor`, que rechaza el paquete si su huella SHA-512 no coincide con la fijada |

## Población: INEGI, Censo de Población y Vivienda 2020 (por manzana)

Descargados el 2026-11-13 (directo con `curl`, sin pasar por el navegador). Públicos; **no se versionan** (`data/raw/` ignorado).

| Archivo | Qué es | Tamaño | SHA-256 |
|---|---|---|---|
| `data/raw/inegi/ageb_mza_urbana_31_cpv2020_csv.zip` | «Principales resultados por AGEB y manzana urbana», Yucatán: 230 columnas, una fila por entidad/municipio/localidad/AGEB/manzana (modificado por INEGI el 2021-07-26) | 6,044,441 B | `5cc69c7a9f0f248e1e19f960b4498a5459d4bedbc1bdc5dd7f98bfac44f99180` |
| `data/raw/inegi/mg2020_31_yucatan.zip` | Marco Geoestadístico del Censo 2020, Yucatán (shapefiles de manzanas `31m`, localidades, AGEB, municipios; modificado el 2021-01-25) | 50,570,164 B | `c486f642edbae13e51e219374d15f432758d565f86bc83472e6ec2c70b1e8f81` |

- **URLs:** `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip` y `https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/31_yucatan.zip`. Descritos en la [ficha técnica del producto](https://www.inegi.org.mx/contenidos/programas/ccpv/2020/doc/fd_agebmza_urbana_cpv2020.pdf). Hay otro Marco Geoestadístico más reciente (`794551132173`, diciembre de 2024) que **no** se usó: las claves deben coincidir con las del Censo 2020.
- **Extraídos en** `data/raw/inegi/censo2020_ageb_mza/` y `data/raw/inegi/mg2020/` (de este último se omitió `catalogos/`: un archivo con nombre mal codificado no se puede escribir en macOS).
- **Unión:** clave de 16 dígitos = ENTIDAD(2) + MUN(3) + LOC(4) + AGEB(4) + MZA(3) en la tabla; `CVEGEO` en el shapefile. Niveles de la tabla: MZA `000` = total de AGEB; AGEB `0000` = total de localidad; LOC `0000` = total de municipio.
- **CRS del shapefile:** Lambert cónica conforme ITRF2008 de México; hay que reproyectar.
- **Licencia (leída el 2026-11-18):** «Términos de Libre Uso de la Información del INEGI», https://www.inegi.org.mx/contenidos/inegi/doc/terminos_info.pdf (sha256 `8900206b…925d62`; el documento no trae fecha ni versión y INEGI «se reserva el derecho a modificarlos en cualquier momento»: releer antes de publicar). Permite copiar y distribuir (sin alterar ni suprimir los metadatos), difundir, adaptar, reordenar, extraer y **explotar comercialmente** la información como insumo de otros productos. Obligaciones: (f) dar crédito al INEGI como autor con la forma «Fuente: INEGI, nombre del producto, fecha de actualización»; (g) avisar al usuario final de cualquier análisis o transformación y no presentarlo como hecho por el INEGI; (h) no aparentar postura oficial ni aval, integración, patrocinio o apoyo del INEGI. El INEGI no responde por la interpretación de los resultados. Los términos del sitio (`terminos_sitio.pdf`, sha256 `4496431c…ab63359`) solo regulan el uso de inegi.org.mx. Cumplimiento: el pie del visor dice «Fuente: INEGI, Censo de Población y Vivienda 2020»; la sección «Población» de las consideraciones cita también el Marco Geoestadístico 2020 y aclara que el análisis es propio y no del INEGI. No se redistribuyen los archivos originales (`data/raw/` no se versiona).
- **Uso en el proyecto:** `pipeline/va_y_ven/population.py` (población por distancia a una parada); el visor muestra solo porcentajes agregados y la atribución «población: INEGI, Censo de Población y Vivienda 2020» en el pie.
- **Límites:** el Censo es de 2020 (seis años de antigüedad); solo manzanas urbanas tienen cifras; en columnas distintas de la población total hay valores reservados por confidencialidad (`*`) y `N/D`.

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
