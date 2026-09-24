# Aceptación de fase 1 — 23 de septiembre de 2026

**Resultado: APROBADA LOCALMENTE, versión 0.3.0.**
Se completa el laboratorio de seguros de cartera definido en ROADMAP.md.
Este cierre acredita mecánica financiera y reproducibilidad sobre escenarios
sintéticos; no acredita utilidad inversora, calibración ni resultados históricos.

## Evidencia ejecutada

- 88 pruebas unitarias y de integración correctas con el paquete instalado.
- 10 escenarios x 8 modelos = 80 comparaciones por configuración.
- 9 configuraciones predefinidas = 720 simulaciones, todas guardadas y
  reproducidas exactamente desde sus entradas. Sin búsqueda de parámetros.
- Las 50 ejecuciones anteriores (0.2.0) mantienen sus eventos financieros y
  métricas existentes; solo se añaden campos de auditoría y métricas nuevas.
- Fuentes Python instaladas idénticas a las del repositorio; instalación offline
  desde wheel en el entorno aislado. `git diff --check` correcto.
- 22 referencias documentales con identidad, enlaces y limitaciones de acceso.
- No se afirma ejecución remota de GitHub Actions.

Huella del código: `2060253c256302aad5cf8658fb8808b1d98c1f77d4384c4ca4f8a7c0fd3bcaf3`.

[Registro de reproducción](../reports/phase1-validation.json).
[Comparación completa](../reports/phase1-final-comparison.md).
[Sensibilidad](../reports/phase1-final-sensitivity.md).
Paquetes completos locales: `reports/runs/phase1-accepted-20260923/`.
Los paquetes completos están excluidos de Git; los resúmenes y el código que
permite regenerarlos permanecen en el repositorio.

## Criterios de ROADMAP.md

| Criterio | Comprobación | Estado |
|---|---|---|
| Fórmulas concuerdan con cálculos manuales | tests de colchón, suelos, HWM, exposición, costes, volatilidad, multiplicadores y métricas | PASS |
| Estimadores sin información futura | disponibilidad temporal validada; cambios en sufijos no alteran prefijos de eventos | PASS |
| Aportaciones y rebalanceos reproducibles | aportación antes del objetivo, retornos neutrales a flujos, calendario mensual y replay | PASS |
| Escenarios de estrés ejecutables | caídas, gaps, recuperación, volatilidad, tipos negativos y grandes aportaciones | PASS |
| Informe comparativo generado | 80 comparaciones base y 720 con sensibilidad | PASS |
| Todos los benchmarks obligatorios | static, cppi, tipp, volatility_adaptive, adaptive y eppi; además drawdown y conditional_cppi | PASS |

## Entregables e identidad de modelos

El núcleo contiene contabilidad con aportaciones, retornos defensivos explícitos,
suelo nominal CPPI, HWM, TIPP/drawdown, estimación de volatilidad, multiplicadores,
rebalanceo mensual, control diario, salidas de emergencia y registro de decisiones.
Incluye CAGR, volatilidad, drawdown, downside deviation, Sharpe, Sortino, Calmar,
expected shortfall, protección, cash lock, capturas, recuperación, costes y rotación.

La selección concreta está en [DYNAMIC_MODELS.md](DYNAMIC_MODELS.md):

- CPPI inverso a volatilidad normalizado; elasticidad verificada 1.
- Adaptativo V4: composición explícita del proyecto con respuesta de drawdown
  documentada. No se atribuye el conjunto a un modelo canónico publicado ni se
  replica el optimizador de la fuente. Régimen neutral; V5 sigue la secuencia
  posterior de investigación, sin estimador inventado.
- EPPI: multiplicador discreto de la publicación de 2023. Se corrigió de forma
  explícita PROJECT_SPEC 4.7. El original de 2008 continúa inaccesible y no se
  afirma su reproducción. La contabilidad autofinanciada está verificada aparte.

Se implementan las variantes seleccionadas, con sus convenciones declaradas;
no se sustituyen unas por otras para rellenar la tabla. Las formulaciones no
verificadas y los parámetros de régimen no implementados siguen rechazándose.

## Lectura de los resultados

El gap de -50% de la comparación base provoca 104 observaciones bajo el suelo
para CPPI, TIPP y EPPI; el drawdown ronda el 29.92%. Esto es compatible con el
retardo de ejecución y demuestra que el suelo no es una garantía.

Algunos modelos dinámicos evitan ese gap porque la entrada todavía estaba
pendiente y fue vetada. Una prueba específica sitúa el gap DESPUÉS de adquirir
exposición y confirma roturas de suelo también para esos modelos. No se presenta
la ausencia de brechas en una tabla como evidencia de superioridad.

EPPI permanece defensivo en algunas sendas bajistas porque cada compra pendiente
encuentra un presupuesto reducido y es cancelada. Es un efecto explícito del
protocolo de ejecución, no una predicción acertada del mercado.

Desactivar emergencias opcionales produce brechas también en modelos dinámicos;
la política de ejecución importa tanto como la fórmula. Los perfiles de costes
son 0, 5 y 20 puntos básicos por euro negociado. Los cambios pueden alterar las
operaciones posteriores, por lo que no se impone una relación monótona entre
costes y rentabilidad a lo largo de trayectorias endógenamente diferentes.
No se selecciona un ganador ni se optimizan parámetros con estos escenarios.

## Comandos de reproducción

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_lab.cli --config config/lab.json --suite reports/runs/new-phase1-validation
.\.venv\Scripts\python.exe -m portfolio_lab.cli --replay reports/runs/phase1-accepted-20260923/baseline/overnight_gap--eppi.json
```

El directorio de una nueva ejecución debe estar vacío/no existir. La reproducción
requiere la misma versión exacta de código; no ejecuta código de snapshots.

## Límite del cierre

Sin datos históricos/OOS, FX real, Black-Litterman, GARCH, modelo de régimen,
aprendizaje automático ni conexión a broker. Esos trabajos conservan sus fases
y puertas de aceptación. Las pruebas sintéticas no permiten aprobar dinero real.
La siguiente fase es Data Foundation (fase 2); no se ha iniciado.
