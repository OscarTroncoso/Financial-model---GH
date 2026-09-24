# Contrato de datos — fase 2, paquete 0.4.0

El paquete `portfolio_data` añade descarga, validación, almacenamiento y features
sin cambiar las fórmulas ni el motor aceptados de `portfolio_lab` (versión interna
0.3.0). No implementa la fase 3 ni alimenta automáticamente operaciones.

## Capas y archivos

- `data/raw/<snapshot_id>/payload.dat`: contenido original recibido por el
  adaptador. En Yahoo es la salida de yfinance serializada con los campos OHLC,
  Adj Close, volumen y acciones corporativas; NO se afirma conservar el HTTP
  original de Yahoo. En BCE se conserva el cuerpo CSV original.
- `data/raw/<snapshot_id>/metadata.json`: instrumento, moneda, zona horaria,
  rango solicitado, instante real de ingestión, URL, versión de adaptador,
  versión de esquema, huella del código y SHA256 del contenido.
- `data/clean/<snapshot_id>/observations.parquet`: precios/tipos normalizados,
  valores positivos y unidades explícitas; manifiesto con hashes y filas.
- `data/features/<feature_id>/features.parquet`: retornos y volatilidad de cada
  serie; manifiesto con los snapshots exactos, configuración, fecha de decisión,
  código, versiones de DuckDB/tzdata y hashes lógicos/físicos.
- `data/catalog.duckdb`: índice consultable de snapshots limpios. Se registra
  después de validar y publicar los archivos. Las consultas as-of se ejecutan
  con DuckDB sobre los Parquet que el experimento fija explícitamente.

No se sobrescriben snapshots ni se elige automáticamente el más reciente. Una
repetición idéntica es idempotente. Una nueva descarga/revisión obtiene otro ID.
Las publicaciones usan renombrado en el mismo volumen; carpetas `.pending-*`
son intentos incompletos, no snapshots aceptados. Un fallo de normalización
conserva raw, pero no publica clean, features ni una entrada de catálogo.
Los checksums detectan alteraciones accidentales; no son una firma criptográfica
ni convierten el filesystem local en almacenamiento WORM.

## Tiempo y disponibilidad

Todos los instantes canónicos son UTC y requieren zona horaria. Cada fila
conserva `observation_time`, `ingested_at`, `available_to_model_time`, y campos
opcionales `published_at` y `revision_at`. Una fecha de sesión no se interpreta
como una fecha de publicación.

Para barras diarias, se usa conservadoramente la medianoche local siguiente como
fin de periodo, con conversión de zona/DST. No se finge que sea la hora exacta
de cierre o publicación. Una barra cuyo periodo aún no terminó se rechaza.

Los proveedores conectados no demuestran cuándo estuvo disponible cada versión
histórica. Por tanto:

`available_to_model_time >= max(observation_time, ingested_at, publicación y revisión conocidas)`.

Las filas de una descarga actual no se retrofechan. Una consulta anterior a su
ingestión no las devuelve. Se filtra disponibilidad ANTES de seleccionar la
última versión de cada observación; los conflictos con la misma disponibilidad
se rechazan. Los experimentos anteriores siguen fijados a sus IDs originales.

Esto permite análisis históricos descriptivos y modelos que hoy utilizan el
histórico descargado. NO demuestra que la versión actual de ese histórico fuera
conocida en una decisión antigua. Las pruebas históricas estrictas necesitarán
versiones documentadas o las que recojamos a partir de ahora. No hay un modo
silencioso de relajar ese requisito. Los campos de publicación/revisión están
preparados, pero no se fabrican para datos macro que aún no descargamos.

## Validación y ajustes

- Precios/tipos positivos y finitos; OHLC consistente, volumen y acciones
  corporativas presentes y no negativos; moneda y zona coinciden con metadata.
- Se rechazan duplicados, mezclas de moneda/unidad/base de precio, fechas fuera
  del rango y estados BCE no normales. No hay forward-fill ni sustituciones.
- La tolerancia de huecos y antigüedad es configurable en días naturales. No es
  un calendario completo de festivos de cada bolsa. El chequeo DST permite la
  diferencia de una hora al medir huecos.
- La antigüedad se mide respecto al último periodo observado, no respecto a la
  fecha de descarga. Descargar otra vez un histórico viejo no lo hace fresco.
- Yahoo: `auto_adjust=False`, `back_adjust=False`, `repair=False`, `keepna=True`,
  `actions=True`, `rounding=False`, `raise_errors=True`. Se selecciona Adj Close
  solo cuando esa es la base configurada; su ausencia es un error.
- Los ajustes siguen la convención del proveedor. Los ratios de Adj Close ya
  incorporan sus ajustes: no se vuelven a sumar dividendos o aplicar splits.
  No se etiqueta Close de Yahoo como precio original inmutable libre de ajustes.
- Se conservan acciones corporativas en raw para inspección; no se ha construido
  un motor independiente de reconstrucción de dividendos/splits ni de fiscalidad.

## Features y unidades

`return_1d = P_t/P_previous - 1`.
`realized_volatility = sample_std(trailing_returns, n-1) * sqrt(periods_per_year)`.

Volatilidad usa el helper financiero ya probado en fase 1. El primer retorno
requiere dos precios; con poca historia la volatilidad es null, nunca cero por
falta de datos. La disponibilidad de una feature es el máximo de TODAS las
observaciones que intervienen, incluido el precio inicial de cada retorno.
Ejemplo: precios 100,110,99 -> retornos .10,-.10; con A=4, std anual=sqrt(.08).

Los retornos permanecen en la moneda y base de su instrumento. USD por EUR sigue
siendo USD por EUR. No se hacen conversiones implícitas a EUR, joins entre
activos con calendarios distintos, financiación FX ni agregaciones de cartera.
Eso evita introducir lógica financiera no solicitada en la capa de datos.

## Uso

Instalar en el entorno del proyecto (Python 3.12):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-data.lock
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Descargar un rango explícito: inicio incluido, fin excluido:

```powershell
.\.venv\Scripts\python.exe -m portfolio_data.cli download --start 2026-07-01 --end 2026-09-22
.\.venv\Scripts\python.exe -m portfolio_data.cli list
```

El comando devuelve un ID por instrumento y sale con error si alguno falla.
Para seleccionar uno se puede añadir `--instrument eurusd_reference`.
La configuración está en config/data.json y se puede indicar otra con `--config`
antes del subcomando. También se puede indicar `--root` para otro almacén local.

Para construir features, usar `features --snapshots ID1 ID2 ID3 --as-of INSTANTE`
con un instante ISO 8601 con zona. La configuración debe corresponder exactamente
al conjunto seleccionado; no se inventan filas para instrumentos ausentes.
Para reproducirlas: `replay FEATURE_ID`. Replay verifica dependencias e integridad,
recalcula con la misma configuración y exige la misma huella de código.

Los 22 documentos financieros permanecen en REFERENCES.md. Las fuentes y
condiciones específicas de datos están separadas en DATA_SOURCES.md.
