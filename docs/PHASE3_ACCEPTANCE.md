# Fase 3 — aceptación local

Fecha: 2026-09-24. Paquete: 0.5.0. Estado: **PASSED** para el núcleo diario
long-only y sus convenciones explícitas. La fase 4 no se ha iniciado.

## Evidencia

- 147 pruebas pasan sobre el paquete instalado: 119 anteriores y 28 nuevas.
- 45 casos sintéticos: 5 trayectorias x 3 políticas x 3 perfiles de ejecución.
- 45 reproducciones exactas de entradas, eventos, operaciones y resultados.
- Instalación por wheel, `pip check` correcto y fuentes instaladas idénticas.
- Replay guardado de EPPI/fase 1 sigue funcionando sin cambiar su motor.
- CI remoto no ejecutado; no se afirma una validación histórica de rentabilidad.

Artefactos: `reports/phase3-validation.json`, `reports/phase3-comparison.md`.
Bundles completos y copia de fuentes en `reports/runs/phase3-final-20260924/`
(locales, ignorados por Git; pueden regenerarse con la CLI).

## Criterios de aceptación

| Requisito | Evidencia |
|---|---|
| Contabilidad determinista reconciliada a mano | Compra con tres costes del 1%, venta, safe/carry, aportación, TWR, drawdown y hueco de precios |
| Impacto material de costes | Ida/vuelta con precios constantes: 1000 sin costes y menos de 960 con comisión del 1%; perfil de costes elevados en el informe |
| Mensual y emergencia | Aportación al primer cierre observado del mes, decisión posterior, ejecución siguiente apertura; emergencia entre meses tras caída |
| Capa vectorizada | Igualdad por periodo de NAV y costes con motor de eventos; ejemplo independiente 1000,1000,1100 |
| Stop, TP, tiempo y gaps | Stop en apertura adversa, stop primero en vela ambigua, TP respeta precio neto de impacto, salida por tiempo diferida |
| Órdenes límite | Sólo apertura siguiente; si no cumple, caduca; comprobación de bid/ask sintético |
| Disponibilidad temporal | Rechazo de velas tardías/obsoletas, prefijos invariantes, historial visible limitado al cierre, normalización UTC |
| Auditoría | Ledger, inputs/config/versiones/hash, checksum y rechazo de manipulación; replay exacto |

## Supuestos y límites aceptados

Ver BACKTESTING.md y MODELS.md para fórmulas y pruebas manuales. La SEC documenta
la semántica de órdenes; nuestras reglas de simulación se identifican como
convenciones del proyecto. No se ha inventado un modelo de predicción nuevo.

Una posición riesgosa y efectivo seguro en una moneda; sin apalancamiento ni
venta corta. Liquidez suficiente y unidades fraccionarias. La capacidad FX no
utilizada queda en efectivo. Spread y slippage son parámetros, no observaciones
reales. Remuneración y carry explícitos de cierre a apertura; intradía cero.
Anclas se reinician al aumentar posición. No se reconstruyen acciones
corporativas ni OHLC a partir del precio ajustado descargado en fase 2.

Los datos gratuitos descargados hoy no acreditan que fueran conocidos en una
fecha histórica: no se retrofecha su disponibilidad. Los resultados sintéticos
validan ingeniería, no una ventaja de inversión. El escenario de salto puede
romper el suelo de protección antes de ejecutar la emergencia; el motor no
oculta esa pérdida ni promete una garantía de capital.

Fases posteriores deberán ampliar el universo de activos y los detalles de
financiación/ejecución que requieran sus estrategias, con sus propias pruebas.
No hay órdenes reales, integración de broker ni estrategia FX implementada.
