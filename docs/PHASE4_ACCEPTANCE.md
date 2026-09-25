# Fase 4 — aceptación local

Fecha: 2026-09-24. Paquete: 0.6.0. Estado: **PASSED** para el baseline de
Black-Litterman y el adaptador de rebalanceo documentados en BLACK_LITTERMAN.md.
La fase 5 no está implementada.

## Evidencia verificable

- **184 pruebas** pasan sobre el paquete instalado: 147 anteriores + 37 nuevas.
- **12 comparaciones**: tres estimadores de covarianza y cuatro escenarios de opiniones.
- **3 decisiones mensuales** adicionales con aportaciones, costes y ejecución posterior.
- **15 bundles reproducidos exactamente**, con inputs/config/versiones y auditoría.
- Wheel instalado, `pip check` correcto y fuentes instaladas idénticas al repositorio.
- Replays guardados de las fases 1 y 3 siguen verificándose.
- No se ha ejecutado CI remoto ni validado una rentabilidad de mercado.

Artefactos: `reports/phase4-validation.json`, `reports/phase4-comparison.md`.
Bundles y copia de fuentes: `reports/runs/phase4-accepted-20260924/` (local,
ignorado por Git, regenerable mediante CLI).

## Criterios del roadmap

| Criterio | Resultado |
|---|---|
| Reproducir ejemplo conocido de BL | Ejemplo de ocho activos de Idzorek, tablas 5/6; error máximo 0.0000635143 frente a salidas publicadas, inferior al margen de 0.0001 por redondeo |
| Reacción a opiniones y confianza | Pruebas de opiniones absolutas/relativas, cambio de signo, confianza creciente, confianza cero y total, y neutralidad sin opiniones |
| Pesos sujetos a restricciones | Sólo posiciones largas, suma uno dentro de la cartera de acciones, máximo por activo y certificado de optimalidad; configuraciones imposibles se rechazan |
| Rebalanceo mensual con costes | Aportación previa al cálculo de desvío, compras netas sin ventas innecesarias en el caso manual, bandas, ejecución posterior y presupuesto CPPI/TIPP después de costes |

También se comprueban covarianzas manuales y ejemplo oficial de Ledoit-Wolf,
rechazo de datos/opiniones no disponibles, invariancia de prefijos, rechazo de
matrices inválidas, sensibilidad a costes, conservación de dinero, cambios de
moneda no resueltos, límites tras gaps y detección de manipulación de bundles.

## Identidad de modelos y supuestos

Las fórmulas y fuentes están en MODELS.md, REFERENCES.md y references.json/bib.
El posterior se verifica contra el artículo accesible de Idzorek. Para LW se
identifica el objetivo esférico y se contrasta el algoritmo centrado con el
código original de scikit-learn y su ejemplo; no se atribuye la fórmula al
estimador de correlación constante de otro artículo. El acceso al PDF íntegro
del autor falló y ese alcance documental queda registrado.

Las opiniones son entradas explícitas con fecha/fuente; no se generan señales
sistemáticas. La conversión de confianza es una convención analítica de una
opinión, documentada como tal. Las restricciones pertenecen al proyecto. El
presupuesto de acciones procede de CPPI/TIPP y la capacidad FX no usada sigue
segura. La matriz de riesgo elegida es Sigma; no la incertidumbre de la media.

Los ejemplos usan etiquetas y retornos sintéticos. El ejemplo académico de ocho
activos comprueba matemáticas; no define el universo invertible del usuario.
La secuencia mensual usa marcas de ejecución planas para aislar contabilidad y
no es un backtest histórico. En la comparación, el límite del 60% en el primer
activo se vuelve vinculante: opiniones más alcistas cambian la media posterior
sin permitir que su peso exceda ese límite.

La integración de datos se ofrece mediante `returns_from_prices` sobre los
contratos de fase 2. No se inventan precios OHLC ni se retrofecha una descarga
actual. El adaptador de ejecución opera valores monetarios ya marcados por el
motor que lo utilice; no sustituye la simulación OHLC ni las órdenes del broker.
La validación walk-forward de opiniones generadas y la elección de un universo
real requieren el trabajo posterior correspondiente.
