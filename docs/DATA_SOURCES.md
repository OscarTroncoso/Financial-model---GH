# Fuentes gratuitas de fase 2

Revisión: 23-09-2026. No se requieren cuentas, claves ni suscripciones para los
adaptadores implementados. La disponibilidad de un proveedor puede cambiar.

| Fuente | Uso implementado | Límites relevantes |
|---|---|---|
| Yahoo Finance mediante yfinance | Históricos diarios de precios y campos de ajustes/acciones corporativas | Herramienta no oficial; uso personal/investigación; datos revisables, ausencias y límites de servicio |
| API SDMX del BCE | EXR.D.USD.EUR.SP00.A, USD por EUR, frecuencia diaria | Tipo de referencia informativo; no bid/ask ni precio ejecutable |
| TradingView | Evaluado, no conectado | Su ayuda declara que no ofrece API pública de acceso a datos; su REST API se dirige a brokers |

Fuentes consultadas:

- [Proyecto yfinance](https://pypi.org/project/yfinance/): propósito y relación
  con Yahoo. La librería no convierte sus datos en un archivo histórico de
  versiones publicadas ni en un servicio con disponibilidad garantizada.
- [API de descarga](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
  y [Ticker.history](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html).
  La implementación usa el método history de la versión instalada 1.7.0 con
  parámetros explícitos; no depende de valores por defecto cambiantes.
- [Ejemplos oficiales de la API BCE](https://data.ecb.europa.eu/help/api/data-examples).
  Se solicita CSV, clave diaria fija, comienzo incluido y final convertido de
  exclusivo a inclusivo para la petición del BCE.
- [Tipos de referencia BCE](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).
  Su carácter informativo se mantiene en los metadatos y no se presenta como
  una serie de ejecución de la estrategia EUR/USD.
- [TradingView: acceso a su API](https://www.tradingview.com/support/solutions/43000474413-i-need-access-to-your-api-in-order-to-get-data-or-indicator-values/).
- [TradingView: exportación de gráficos](https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/).
  La exportación manual es una función separada. No se presupone disponibilidad
  gratuita de esa función ni se utiliza un scraper o un endpoint no documentado.
- [DuckDB y Parquet](https://duckdb.org/docs/stable/data/parquet/overview).

## Series de ejemplo

`config/data.json` incluye VWCE.DE, XEON.DE y el tipo de referencia EUR/USD del
BCE. Son muestras para probar la infraestructura; no se han convertido en una
asignación de cartera ni en recomendaciones de inversión. El fondo defensivo
es un activo cotizado, no efectivo legalmente garantizado ni un rendimiento
constante del 3%. Todos los identificadores son configurables.

No se sustituyen instrumentos entre proveedores cuando falla una descarga.
Tampoco se mezcla un tipo de referencia del BCE con una cotización ejecutable.
En una fase posterior, el trading intradía requerirá datos con resolución,
costes y condiciones de ejecución adecuados; estas descargas diarias no lo
resuelven. No se necesita contratar ese servicio para completar esta fase.

## Prueba real realizada

Se solicitaron inicialmente sesiones desde 01-07-2026 hasta 22-09-2026 inclusive.
Yahoo devolvió Close y Adj Close ausentes en la última sesión para ambos ETF.
El validador rechazó esas series y conservó las respuestas en la capa raw.
No se rellenaron los huecos, no se activó reparación automática y no se
publicaron esos lotes como limpios.

Una segunda petición, explícitamente acotada al 21-09-2026 inclusive, produjo
59 observaciones válidas por serie en los tres casos. Los identificadores y
marcas de tiempo reales figuran en reports/phase2-validation.json.
Las conexiones se verificaron con TLS; no se desactivó la verificación de
certificados. Todos los datos obtenidos y la caché del proveedor son locales y
están excluidos de Git.
