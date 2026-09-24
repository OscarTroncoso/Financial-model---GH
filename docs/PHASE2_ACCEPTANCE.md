# Aceptación de fase 2 — 23-09-2026

**Resultado: APROBADA LOCALMENTE, paquete 0.4.0.**
Se completó Data Foundation con fuentes gratuitas comprobadas, conservando el
motor financiero 0.3.0 y las condiciones de aceptación de las fases posteriores.

## Evidencia

- 119 pruebas correctas: 88 financieras existentes y 31 nuevas de datos.
- Descarga real sin suscripción, claves ni cuentas: yfinance y API pública BCE.
- Tres series de ejemplo: VWCE.DE, XEON.DE y EUR/USD de referencia BCE.
- 59 observaciones por serie (177 en total), sesiones 01-07 a 21-09 de 2026.
- 174 filas de features: retornos y volatilidad móvil en la moneda/base de cada
  instrumento. La volatilidad inicial permanece null hasta completar el mínimo.
- Mismos snapshots/configuración/código -> mismo ID y contenido de features.
- Replay ejecutado por CLI; huellas de entradas, Parquet y contenido lógico
  comprobadas. Consulta anterior a la primera ingestión devuelve cero filas.
- `pip check` sin incompatibilidades; fuentes instaladas idénticas al workspace.
- Replay de un experimento aceptado de fase 1 sigue siendo exacto; sus fórmulas
  y sus archivos Python no se modificaron.
- `git diff --check` correcto. CI actualizado, ejecución remota no afirmada.

[Registro verificable](../reports/phase2-validation.json).
[Contrato y comandos](DATA_FOUNDATION.md).
[Fuentes gratuitas y TradingView](DATA_SOURCES.md).

Huella de pipeline: `fb86c9a4f11abed96bf5e4f994261474f710e88cafacc3ffc2ae9ac381245d46`.
ID de features: `61e8d7f7e2625f73979c9b737327d05751eedec4779c56a327eeaad35e91d724`.

## Puerta de aceptación de ROADMAP.md

| Criterio | Evidencia | Estado |
|---|---|---|
| Mismo snapshot produce las mismas features | test_same_snapshot_features_are_identical y replay real de 174 filas | PASS |
| Datos antiguos/futuros detectados | tests de antigüedad por periodo observado, fecha incompleta, publicación y revisión futuras | PASS |
| Ninguna publicación futura entra en una predicción histórica | filtro SQL de disponibilidad previo a selección de versiones; tests de revisión, disponibilidad y dependencias | PASS |
| Capas raw/clean/features | payload original del adaptador, Parquet tipado, manifiestos y publicación atómica | PASS |
| Normalización temporal | UTC, rechazo de timestamps sin zona, límites de sesión conservadores y pruebas DST | PASS |
| Parquet + DuckDB | lectura/escritura real, catálogo persistente y consultas as-of | PASS |
| Validación e historial | OHLC, moneda, unidades, duplicados, gaps, estados, hashes, snapshots sin sobrescritura | PASS |

## Incidencia real que validó el rechazo de datos

La primera solicitud incluyó el 22-09-2026. Yahoo devolvió Close y Adj Close
vacíos en esa sesión para ambos ETF. No se repararon ni rellenaron; el lote no
llegó a clean/catalog. El contenido recibido quedó en raw. La segunda solicitud
usó explícitamente fin exclusivo 22-09 y fue correcta. Esto es una reducción
registrada del rango de prueba, no una sustitución silenciosa de datos.

La conexión BCE se comprobó con verificación TLS activa. TradingView no se
utiliza: su documentación no ofrece una API pública para descargar esos datos.
No se añadieron scrapers ni dependencias de servicios de pago.

## Límites explícitos

El cierre acredita la infraestructura y sus invariantes, no que yfinance sea
una base histórica de versiones publicadas. Un histórico descargado hoy puede
estar revisado; no se retrofecha su disponibilidad. Sirve para análisis actual
con información histórica, pero no demuestra qué versión conocía el mercado
antes de la descarga. La ausencia de datos elegibles provoca un fallo, no una
excepción oculta a la regla temporal.

La tolerancia de huecos es por días naturales, no un calendario completo de
bolsas. Se conservan los ajustes del proveedor y los campos corporativos; no se
reconstruyen de forma independiente los ajustes históricos. Las tres series
son ejemplos técnicos y no una asignación de cartera.

No hay aún datos de ejecución bid/ask intradía, señales EUR/USD, descarga macro
con vintages certificados, ni backtest integrado de mercado real. Esos trabajos
pertenecen a fases posteriores. No se ha iniciado la fase 3.

## Reproducción local

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_data.cli list
.\.venv\Scripts\python.exe -m portfolio_data.cli replay 61e8d7f7e2625f73979c9b737327d05751eedec4779c56a327eeaad35e91d724
```

El replay usa archivos locales; no vuelve a pedir precios al proveedor. El raw,
Parquet y catálogo completos residen en data/ y están excluidos de Git. El
registro de aceptación, documentación, configuración y código se conservan en
el repositorio. Nuevas descargas tendrán IDs nuevos y pueden reflejar revisiones.
