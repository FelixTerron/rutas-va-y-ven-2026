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
- [ ] **Licencia / términos de uso.** No se encontró licencia en el feed (GTFS no tiene campo de licencia), ni en el issue, ni en la página de la ATY, ni en la plataforma. Confirmar con la ATY **por escrito** antes de publicar el mapa o redistribuir el GTFS o datos derivados. Ver `docs/DECISIONS.md` (riesgos de publicar sin licencia).
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
