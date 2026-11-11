# Decisiones

Registro breve: qué se decidió, cuándo y por qué. Lo no decidido queda marcado como abierto.

## Decididas

### 2026-11-09 — Alcance geográfico
Solo lo que Va y Ven cubre: área metropolitana de Mérida y zonas conurbadas. **Por qué:** es lo que el feed oficial describe.

### 2026-11-09 — Fuente de datos: GTFS oficial de la ATY
**Por qué:** existe, está activo y trae horarios y trazados. Ver `docs/DATA_SOURCES.md`.

### 2026-11-09 — Python para datos, TypeScript + MapLibre para el mapa
**Por qué:** Python es donde hay comodidad y valor didáctico (análisis reproducible); el navegador requiere JS. Sitio estático, sin backend.

### 2026-11-09 — Datos crudos y derivados fuera de git (por ahora)
**Por qué:** el GTFS pesa ~200 MB y la licencia no está confirmada.

### 2026-11-09 — Claude no ejecuta comandos de escritura de git
El usuario hace todos los commits y pushes. Reforzado con reglas `deny` en `.claude/settings.json`.

### 2026-11-10 — Público prioritario: especialista/analista
El producto debe servir para análisis de diseño y optimización de rutas. Dos mapas de calor objetivo:
1. **Intensidad de tránsito por calle** (cuántos viajes/camiones pasan por cada tramo, por franja horaria). Viable con el GTFS (`shapes` × `trips` × `calendar`); costo bajo. Mide servicio *programado*, no operación real.
2. **Abordajes por paradero** (personas que suben en cada parada). **El GTFS no trae demanda.** Opciones: datos de validaciones de la ATY (no encontrados públicos), proxies (oferta por parada, población/empleo con datos del INEGI) o reporte colaborativo (ver más abajo). Ver `docs/DATA_SOURCES.md`.
(El mapa 1 se redefinió el mismo día como "número de rutas distintas por calle"; ver abajo.)

### 2026-11-10 — Mapa de calor 1: número de rutas distintas por calle
Definición del usuario: la "temperatura" de cada calle es **cuántas rutas distintas** pasan por ella (no cuántos camiones ni viajes). Calles de valor alto = concentración de transporte público; valor cero = zonas sin servicio. Sirve para ver cobertura y carencias.
Hallazgos del GTFS (2026-11-10): 174 `route_id` = **117 rutas base** (variantes `.1`/`.2`/`A`/`B` de un mismo número); los trazos (`shapes`) son 291. Calendarios: `L-V`, `Sabado`, `Domingo` más especiales (`Viernes Feria Xmatkuil` con ~14 mil viajes, `V-S`, `L-M-X-J`, `Domingo_aeropuerto`) que se excluyen de la línea base.
**Decidido (usuario, 2026-11-10):** unidad = ruta base; día entre semana por defecto (también sábado y domingo).

**Método implementado (2026-11-11), `pipeline/va_y_ven/coverage.py`:** se muestrean los trazos cada 10 m, se unifican en celdas de 10 m y a cada punto se le cuentan las rutas base distintas con algún trazo a menos de 12 m. No descarga nada: se reproduce solo con el GTFS. *Cambio respecto a lo acordado:* en vez de alinear a calles de OSM se contó sobre los trazos mismos, porque la red abarca ~173 km (Mérida, Valladolid y Tizimín) y descargar de OSM un polígono de ~1,600 km² en franjas delgadas es pesado y frágil. Las calles de OSM quedan como paso posterior opcional, para ponerles nombre.

**Resultado (día entre semana):** 112 de las 117 rutas base operan; ~1,417 km de calle con servicio (141,746 puntos); mediana 2 rutas por punto, máximo 28 en el Centro de Mérida (lat 20.966, lon −89.621). El 49 % de la calle con servicio tiene una sola ruta y solo 3 % tiene 10 o más. La estructura es radial hacia el Centro.
**Sensibilidad a la tolerancia:** el máximo (28) y la forma general no cambian de 6 a 30 m; el % de calle con una sola ruta va de 52 % (6 m) a 44 % (30 m), porque trazos casi paralelos se fusionan o no. Se eligió 12 m.
**Límites:** cuenta rutas, no frecuencia; es servicio programado, no operación real; una calle con 2 rutas de 5 minutos de frecuencia y otra con 2 de 60 minutos valen lo mismo.

**Alcance geográfico (corrección):** además del área metropolitana de Mérida, el feed incluye sistemas locales en **Valladolid** y **Tizimín** (grupos aislados a ~150 km).

### 2026-11-10 — Abordajes por paradero: reporte colaborativo (idea futura)
Idea del usuario: que las personas marquen en el mapa dónde esperan su camión. Aporta "demanda declarada", pero requiere un backend (base de datos), aviso de privacidad (son ubicaciones de personas), moderación contra spam y asumir que la muestra tiene sesgo (no es representativa). Choca con "sitio estático" y con "trabajo privado"; se evalúa al definir las features finales.

### 2026-11-10 — Repo de GitHub: público, con la regla de que ningún dato de la ATY entra a git
Se decidió que no hace falta pasarlo a privado por ahora. Lo que importa es que **no se versionen datos** (`data/raw/` y `data/processed/` están en `.gitignore`; revisar `git status` antes de cada commit). Sigue sin publicarse mapa, datos derivados ni hosting hasta aclarar las condiciones de los datos. Riesgo real: un commit accidental de datos queda para siempre en el historial aunque se borre después; si preocupa, pasar a privado es gratis y reversible.

### 2026-11-10 — Node.js 24.22.2 (LTS) con fnm, y pnpm 12.17.0 con Corepack
**Por qué:** oleadas de ataques de cadena de suministro a npm en 2026 (familia Shai-Hulud / ChainDrop, agosto: cientos de paquetes comprometidos mediante scripts `preinstall`).
- **Node 24 y no 26:** verificado en nodejs.org (`dist/index.json` y `schedule.json` de nodejs/Release). Node 24 "Krypton" es LTS de mantenimiento, soporte hasta 2028-04-30; Node 26 "Lithium" pasó a LTS activo el 2026-10-28 (muy reciente). Migrar a 26 después es sencillo.
- **Instalado con:** `brew install fnm` + `fnm install 24.22.2`; versión fijada en `.node-version`. Firma del binario verificada con `codesign` (Node.js Foundation, cadena de Apple).
- **pnpm 12.17.0, no 12.19.0:** se fija la última versión con >1 semana publicada (la 12.19.0 salió el 2026-11-10). Se activa con Corepack (incluido en Node 24), que la ancla a una versión exacta.
- **Defensas de pnpm** (confirmadas en https://pnpm.io/supply-chain-security): `minimumReleaseAge` 1 día por defecto, `blockExoticSubdeps` activo, scripts de dependencias bloqueados salvo los listados en `allowBuilds` (`strictDepBuilds` activo).
- **Reglas al crear `web/`:** subir `minimumReleaseAge` a 10080 (7 días), activar `trustPolicy: no-downgrade`, `allowBuilds` solo con lo estrictamente necesario, lockfile siempre versionado, instalar con `pnpm install --frozen-lockfile`, y revisar cada dependencia nueva antes de añadirla.
- **Pendiente:** verificar empíricamente los valores por defecto efectivos al crear el primer `package.json` (no se pudieron leer con `pnpm config get`).

### 2026-11-11 — Dependencias de Python con defensas de cadena de suministro
`geopandas`, `osmnx` y `matplotlib` (29 paquetes en total, ver `uv.lock`). En `pyproject.toml`: `exclude-newer = "2026-11-03T00:00:00Z"` (ignora versiones publicadas después; se sube a mano al actualizar) y `no-build = true` (solo wheels ya compiladas, nunca se ejecuta código de construcción). Efecto visible: `ruff` bajó de 0.17.4 a 0.17.3 por ser la 0.17.4 posterior a la fecha de corte.

## Abiertas
- **Nombres de calle (OSM):** poner nombre a los puntos de `route_density` para que los analistas lean "Calle 60: 28 rutas". Evaluar descarga solo del casco urbano.
- **Mapa 2 de oferta:** frecuencia (salidas por hora) por tramo, complemento natural del conteo de rutas.
- **Conciliar cifras de rutas:** 174 `route_id`, 117 rutas base (112 en día hábil) vs. 205 de un estudio de 2025.
- **Elemento distintivo para el público casual:** animación de camiones / isócronas / modo reto / otro (sin decidir; la prioridad ahora es el público analista).
- **Hosting:** Cloudflare Pages o GitHub Pages.
- **Mapa base:** proveedor de teselas gratuito o PMTiles autohospedado (los tiles públicos de OSM no son para producción).
- **Licencia del repo y de los datos derivados.**
