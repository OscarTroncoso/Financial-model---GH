# Fuentes documentales del proyecto

Fecha de consulta: 23 de septiembre de 2026. BibliografÃ­a inicial, ampliable por fase.

Las referencias se enlazan al editor, autor o instituciÃ³n cuando es posible. Se incluyen enlaces a documentos completos disponibles; no se redistribuyen copias de artÃ­culos de acceso restringido. Localizar un artÃ­culo no equivale a verificar su ecuaciÃ³n, reproducirlo ni validar su utilidad financiera.

El [registro de modelos](MODELS.md) indica quÃ© puede ejecutarse. [references.json](references.json) conserva los metadatos y [references.bib](references.bib) permite importarlos en un gestor bibliogrÃ¡fico.

## Referencias y estado de acceso

### black_perold_1992

**Black, Fischer and Perold, Andre F. (1992).** [Theory of constant proportion portfolio insurance](https://www.sciencedirect.com/science/article/pii/016518899290043E).

DOI: [10.1016/0165-1889(92)90043-E](https://doi.org/10.1016/0165-1889(92)90043-E).

Uso previsto: CPPI. Resumen editorial consultado; texto integral no verificado.

Define la exposiciÃ³n como mÃºltiplo del patrimonio sobre el suelo, con lÃ­mite de endeudamiento. Sustenta E=m*C, no nuestra convenciÃ³n de aportaciones.

### perold_sharpe_1988

**Perold, Andre F. and Sharpe, William F. (1988).** [Dynamic Strategies for Asset Allocation](https://rpc.cfainstitute.org/research/financial-analysts-journal/1988/dynamic-strategies-for-asset-allocation).

DOI: [10.2469/faj.v44.n1.16](https://doi.org/10.2469/faj.v44.n1.16).

Uso previsto: CPPI y benchmark. Resumen editorial y extracto del original consultados; apertura completa del PDF de Stanford fallÃ³.

Distingue buy-and-hold, constant mix y estrategias de seguro. La referencia estÃ¡tica del laboratorio es constant mix mensual.

### estep_kritzman_1988

**Estep, Tony and Kritzman, Mark (1988).** [TIPP: Insurance without complexity](https://doi.org/10.3905/jpm.1988.409172).

DOI: [10.3905/jpm.1988.409172](https://doi.org/10.3905/jpm.1988.409172).

Uso previsto: TIPP. Referencia y resumen identificados; texto original completo no accesible.

Referencia fundacional. La regla de suelo se contrasta con la exposiciÃ³n accesible de Dangl, Randl y Zechner, sin atribuirle una reproducciÃ³n integral del artÃ­culo de 1988.

### dangl_randl_zechner_2015

**Dangl, Thomas and Randl, Otto and Zechner, Josef (2015).** [Risk Control in Asset Management: Motives and Concepts](https://link.springer.com/chapter/10.1007/978-3-319-09114-3_14).

DOI: [10.1007/978-3-319-09114-3_14](https://doi.org/10.1007/978-3-319-09114-3_14).

Uso previsto: TIPP y control de riesgo. Texto del capÃ­tulo accesible; secciÃ³n 3.2.4 consultada. ExposiciÃ³n posterior, no original de TIPP.

Expone F_t=max(F_(t-1),k*V_t). Sin flujos y con inicializaciÃ³n coherente equivale a k*HWM. El ajuste por aportaciones se documenta por separado.

### lee_chiang_hsu_2008

**Lee, Huai I. and Chiang, Min Hsien and Hsu, Hsinan (2008).** [A new choice of dynamic asset management: the variable proportion portfolio insurance](https://researchoutput.ncku.edu.tw/zh/publications/a-new-choice-of-dynamic-asset-management-the-variable-proportion-/).

DOI: [10.1080/00036840600949280](https://doi.org/10.1080/00036840600949280).

Uso previsto: EPPI. Registro institucional de los autores y resumen consultados; ecuaciones originales pendientes de acceso.

El resumen identifica un mÃºltiplo que varÃ­a con el mercado. No respalda inventar una funciÃ³n exponencial del colchÃ³n.

### mancinelli_oliva_2023

**Mancinelli, Daniele and Oliva, Immacolata (2023).** [Constant or Variable? A Performance Analysis among Portfolio Insurance Strategies](https://www.mdpi.com/2227-9091/11/6/105).

DOI: [10.3390/risks11060105](https://doi.org/10.3390/risks11060105).

Uso previsto: CPPI, TIPP y EPPI. Texto extraÃ­do del artÃ­culo completo consultado en copia PDF; original MDPI limitÃ³ acceso. Estudio primario comparativo, exposiciÃ³n posterior de EPPI.

Se seleccionaron las ecuaciones discretas 8/11 del multiplicador; la contabilidad se mantiene autofinanciada. DecisiÃ³n y discrepancias en DYNAMIC_MODELS.md.

### benameur_prigent_2006

**Ben Ameur, Hachmi and Prigent, Jean-Luc (2006).** [Portfolio Insurance: determination of a dynamic CPPI multiple as function of state variables](https://www.cranberger.com/sites/default/files/libs/Portfolio%20insurance.pdf).

Uso previsto: Multiplicador dinÃ¡mico. Documento de trabajo original, versiÃ³n preliminar de diciembre de 2006; texto consultado. Copia en alojamiento de tercero.

SecciÃ³n 3: restricciones por cuantiles sobre el multiplicador a partir de rentabilidades y volatilidad pasadas. Cota implementada como conditional_cppi con un estimador gaussiano documentado por separado; no equivale a la fÃ³rmula conceptual de la especificaciÃ³n.

### cont_tankov_2009

**Cont, Rama and Tankov, Peter (2009).** [Constant Proportion Portfolio Insurance in the Presence of Jumps in Asset Prices](https://onlinelibrary.wiley.com/doi/pdf/10.1111/j.1467-9965.2009.00377.x).

DOI: [10.1111/j.1467-9965.2009.00377.x](https://doi.org/10.1111/j.1467-9965.2009.00377.x).

Uso previsto: Riesgo de saltos. Resumen editorial localizado; ecuaciones del texto completo pendientes.

Investiga saltos en precios y riesgo de CPPI. Referencia para la investigaciÃ³n de brechas; no convierte nuestro estrÃ©s sintÃ©tico en una calibraciÃ³n de saltos.

### gips_twr

**CFA Institute (documento en lÃ­nea).** [GIPS Standards Handbook for Firms, provision 2.A.24](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/).

Uso previsto: Contabilidad de rentabilidades. Documento oficial consultado, apartado de rentabilidad temporal y flujos.

Enlace geomÃ©trico de subperiodos para separar rentabilidad y aportaciones externas. El laboratorio no declara cumplimiento GIPS.

### std_sample

**The Book of Statistical Proofs (documento en lÃ­nea).** [Sample standard deviation](https://statproofbook.github.io/D/std-samp.html).

Uso previsto: EstadÃ­stica bÃ¡sica. DefiniciÃ³n publicada localizada y contrastada.

DesviaciÃ³n muestral con divisor n-1. La anualizaciÃ³n por raÃ­z del nÃºmero de periodos exige supuestos adicionales, documentados en el cÃ³digo.

### riskmetrics_1996

**J.P. Morgan and Reuters (1996).** [RiskMetrics Technical Document, Fourth Edition](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a).

Uso previsto: EWMA y riesgo. PDF original completo accesible en MSCI; referencia incorporada, auditorÃ­a de implementaciÃ³n pendiente.

Documento base para volatilidad y covarianza EWMA. No se incorpora un lambda universal ni se implementa un modelo por haber localizado el documento.

### bollerslev_1986

**Bollerslev, Tim (1986).** [Generalized autoregressive conditional heteroskedasticity](https://econ.duke.edu/~boller/Published_Papers/joe_86.pdf).

DOI: [10.1016/0304-4076(86)90063-1](https://doi.org/10.1016/0304-4076(86)90063-1).

Uso previsto: GARCH. ArtÃ­culo original en la web del autor; definiciÃ³n de secciÃ³n 2 y referencia a secciÃ³n 3 consultadas.

Modelo de varianza condicional. Su presencia en la bibliografÃ­a no permite saltar las fases del roadmap ni usarlo como predictor directo de direcciÃ³n.

### black_litterman_1992

**Black, Fischer and Litterman, Robert (1992).** [Global Portfolio Optimization](https://www.tandfonline.com/doi/abs/10.2469/faj.v48.n5.28).

DOI: [10.2469/faj.v48.n5.28](https://doi.org/10.2469/faj.v48.n5.28).

Uso previsto: Black-Litterman, fase 4. Metadatos editoriales comprobados; PDF escaneado localizado en Duke, ecuaciones aÃºn no auditadas.

Referencia fundacional para equilibrio y opiniones. Antes de programar se verificarÃ¡n las convenciones de retornos, tau, Omega y covarianza posterior.

### ledoit_wolf_2004

**Ledoit, Olivier and Wolf, Michael (2004).** [Honey, I Shrunk the Sample Covariance Matrix](https://www.pm-research.com/content/iijpormgmt/30/4/110).

Uso previsto: Covarianzas, fase 4. Datos editoriales localizados; extracto del preprint del autor de noviembre de 2003 consultado. Apertura completa del PDF fallÃ³.

Referencia para shrinkage de covarianzas. Debe distinguirse la versiÃ³n publicada de 2004 del preprint y precisarse el estimador antes de implementarlo.

### hyndman_athanasopoulos_2021

**Hyndman, Rob J. and Athanasopoulos, George (2021).** [Forecasting: Principles and Practice, third edition, section 5.10](https://otexts.com/fpp3/tscv.html).

Uso previsto: ValidaciÃ³n temporal. CapÃ­tulo en web de autores/editorial consultado.

ValidaciÃ³n con origen mÃ³vil y entrenamiento solo con observaciones anteriores. No sustituye controles adicionales de etiquetas solapadas en trading.

### bailey_etal_2015

**Bailey, David H. and Borwein, Jonathan M. and Lopez de Prado, Marcos and Zhu, Qiji Jim (2015).** [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

Uso previsto: SelecciÃ³n y sobreajuste. Preprint en web del autor, revisiÃ³n febrero de 2015; resumen e introducciÃ³n consultados.

Analiza el sesgo de seleccionar estrategias entre numerosos backtests. Registro de experimentos y pruebas fuera de muestra son necesarios; no implica implantar CSCV en esta fase.

### sortino_price_1994

**Sortino, Frank A. and Price, Lee N. (1994).** [Performance Measurement in a Downside Risk Framework](https://doi.org/10.3905/joi.3.3.59).

DOI: [10.3905/joi.3.3.59](https://doi.org/10.3905/joi.3.3.59).

Uso previsto: MÃ©tricas de riesgo bajista. Referencia editorial localizada; texto completo pendiente.

Referencia original del marco de downside risk. La implementaciÃ³n explicita objetivo cero, promedio de todos los periodos y anualizaciÃ³n; no declara reproducir todos los estimadores del artÃ­culo.

## Enlaces alternativos a documentos

- CPPI/constant mix: [copia del original de Perold y Sharpe en Stanford](https://web.stanford.edu/class/msande348/papers/PeroldSharpe.pdf). El buscador extrajo texto; la apertura directa fallÃ³ en esta sesiÃ³n.
- Comparativa CPPI/TIPP/EPPI: [PDF completo de Mancinelli y Oliva](https://pdfs.semanticscholar.org/93ef/d288ce43567f03d9289676712242d12b8627.pdf). Texto consultado; ecuaciones originales de EPPI aÃºn pendientes.
- Black-Litterman: [copia acadÃ©mica escaneada en Duke](https://people.duke.edu/~charvey/Teaching/BA453_2005/blacklitterman.pdf). No auditada ecuaciÃ³n por ecuaciÃ³n.
- Covarianzas: [preprint en web de Ledoit](https://ledoit.net/honey.pdf). Extracto localizado; apertura integral fallida.

## Trazabilidad de fÃ³rmulas del cÃ³digo actual

| CÃ¡lculo | Base documental o derivaciÃ³n | CÃ³digo / comprobaciÃ³n |
|---|---|---|
| ColchÃ³n y exposiciÃ³n CPPI | Blackâ€“Perold; lÃ­mite long-only de proyecto | rules.py; test_cppi_hand_example_and_cap |
| Suelo TIPP y drawdown | Regla publicada en Dangl et al., 3.2.4; identidad alpha=1-d | rules.py; test_floor_equivalence |
| HWM con aportaciones | ConvenciÃ³n explÃ­cita HWM anterior + aportaciÃ³n; no fÃ³rmula atribuida al TIPP original | rules.py; test_flow_adjusted_hwm |
| Rentabilidad temporal | GIPS 2.A.24 y valoraciÃ³n antes/despuÃ©s de cada flujo | engine.py; test_cost_return_split_on_deposit_date |
| Rendimiento defensivo ACT/365 | Identidad de capitalizaciÃ³n efectiva; convenciÃ³n temporal | rules.py; test_safe_effective_rate_and_negative_rate |
| Costes y pesos posteriores al coste | Resolver E=w*(V-k*abs(E-R)); identidad contable | accounting.py; pruebas de compra/venta y conciliaciÃ³n |
| Volatilidad muestral | DefiniciÃ³n n-1; escala anual declarada | rules.py; test_volatility_hand_example_and_warmup |
| MÃ©tricas diagnÃ³sticas | Definiciones explÃ­citas en metrics.py, incluida variante de Sortino | test_metrics_report.py |
| EPPI discreto, volatilidad y adaptativo V4 | Identidades, derivaciÃ³n y composiciÃ³n en DYNAMIC_MODELS.md | dynamic.py; test_dynamic.py |

## Alcance de la revisiÃ³n

El EPPI original de 2008 sigue sin acceso a sus ecuaciones; no se afirma su
reproducciÃ³n. El laboratorio selecciona la variante discreta de 2023. El
multiplicador inverso a volatilidad usa una normalizaciÃ³n explÃ­cita y el modelo
adaptativo V4 combina componentes documentados. El rÃ©gimen permanece neutral.
Las fases futuras requieren su propia auditorÃ­a de modelos y fuentes.
CorrecciÃ³n matemÃ¡tica, cÃ³digo y utilidad empÃ­rica son comprobaciones distintas.

El challenger conditional_cppi, aÃ±adido en 0.2.0, mantiene su identidad separada;
ver [CONDITIONAL_CPPI.md](CONDITIONAL_CPPI.md).

### mancinelli_thesis

**Mancinelli, Daniele.** [New Insights on Portfolio Insurance Strategies for Financial and Longevity Risk Management](https://iris.uniroma1.it/retrieve/24083cd0-80f8-44f9-9da4-3d9e043ab814/Tesi_dottorato_Mancinelli.pdf).

EcuaciÃ³n 1.51 localizada en extracto indexado del PDF institucional; pÃ¡ginas originales de Lee et al. no obtenidas.

DescripciÃ³n basada en precio relativo a una referencia inicial. No es idÃ©ntica a la recurrencia discreta seleccionada; se conserva como alternativa documental, no implementada.

### ardia_boudt_wauters_2016

**Ardia, David and Boudt, Kris and Wauters, Marjan.** [Smart beta and CPPI performance](https://libra.unine.ch/bitstreams/cd83e6b4-6948-43f9-860d-3d06269d7e90/download).

Texto del artÃ­culo consultado, secciÃ³n 3.3.

El overlay actÃºa sobre los pesos del activo subyacente e incluye una razÃ³n de volatilidades. No se confunde con una verificaciÃ³n literal de la fÃ³rmula de multiplicador del proyecto; sin implementaciÃ³n de este artÃ­culo.


## Cierre documental de fase 1 (0.3.0)

El catÃ¡logo contiene ahora 22 referencias. La selecciÃ³n precisa y las
limitaciones de acceso se registran en [DYNAMIC_MODELS.md](DYNAMIC_MODELS.md).
El original de EPPI de 2008 sigue sin verificarse; se seleccionÃ³ explÃ­citamente
la variante discreta publicada en 2023. La composiciÃ³n adaptativa pertenece al
proyecto y utiliza componentes documentados, sin atribuirla a un autor como
modelo canÃ³nico ni afirmar optimalidad.

| Fuente aÃ±adida | EcuaciÃ³n o definiciÃ³n | CÃ³digo/prueba |
|---|---|---|
| [Nystrup et al. 2019](https://doi.org/10.1007/s10479-018-2947-3) | Inversa de aversiÃ³n relativa, ec. 6 | dynamic.drawdown_modifier; test_drawdown_inverse_relative_aversion_by_hand |
| [Sharpe 1994](https://web.stanford.edu/~wfsharpe/art/sr/sr.htm) | Ratio de retornos diferenciales | metrics.sharpe_ratio; test_sharpe_differential_return_by_hand |
| [Rockafellar/Uryasev 2002](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf) | CVaR para distribuciÃ³n discreta | metrics.expected_shortfall; test_fractional_tail_mass_not_threshold_average |

La identidad inversa a volatilidad, su normalizaciÃ³n y sus supuestos se
explican separadamente; no se confunde con conditional_cppi. Ecuaciones EPPI
8/11 contrastadas con ejemplos +10%/-10%, estado acumulado y saturaciÃ³n.


## Phase 3 order semantics (accessed 2026-09-24)

- SEC: [Types of Orders](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders).
- SEC: [Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order).

Primary sources for market/limit/stop distinctions and gap execution risk.
OHLC ambiguity, proportional costs, overnight accrual and time stops are
explicit project conventions, not equations attributed to these sources.
See BACKTESTING.md and MODELS.md for equations and hand examples.


## Phase 4 source verification — 2026-09-24

- [Idzorek original paper](https://www.cis.upenn.edu/~mkearns/finread/idzorek.pdf): equations 1/2/3/8, Figure 1, and the eight-asset example in Tables 1/2/5/6. Numerical reproduction allows one basis point for rounded source inputs/outputs.
- [RiskMetrics original technical document](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a): covariance recursion, zero-mean convention and initialization example. Lambda is configurable.
- [Ledoit-Wolf well-conditioned estimator](https://www.sciencedirect.com/science/article/pii/S0047259X03000964): identity shrinkage target. Distinct from the previously listed constant-correlation Honey paper.
- [Original scikit-learn estimator source](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/covariance/_shrunk_covariance.py) and [official API](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html): centered finite-sample LW computation and numeric example. Full author-paper download was unavailable, so this exact verification scope is recorded rather than claiming a full paper replication.
- [Boyd and Vandenberghe](https://web.stanford.edu/~boyd/cvxbook/): convex optimization background; project projection and optimality certificate are derived in MODELS.md.

Single-view confidence interpolation, asset caps, drift bands and contribution/
execution rules are declared project choices. No factor-generated views or
forecasting model is attributed to these sources. See BLACK_LITTERMAN.md.

## Phase 5 primary sources

- [NIST/SEMATECH: Process Modeling: Least Squares](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm) (`nist_ols`). OLS coefficients and residual variance SSE/(n-p), p=2.
- [NIST/SEMATECH: How can I assess the uncertainty in a predicted response?](https://www.itl.nist.gov/div898/handbook/pmd/section5/pmd511.htm) (`nist_mean_response`). Conditional mean uncertainty differs from individual future outcome uncertainty.
- [Kenneth R. French: Detail for Daily Momentum Factor](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor_daily.html) (`french_daily_momentum`). Prior 2-12 month momentum background. Project session-count descriptor is a proxy, not the published portfolio factor.
- [MSCI: MSCI Quality Indexes Methodology, May 2022](https://www.msci.com/indexes/documents/methodology/2_MSCI_Quality_Indexes_Methodology_20220519.pdf) (`msci_quality_2022`). Section 2.2.2 normalization background. Project population scaling and post-score clipping do not replicate MSCI methodology.

## Phase 6 primary sources

- [Fidelity: Simple Moving Average](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma) (`fidelity_sma`). SMA arithmetic mean and moving-average trend background. Windows and thresholds are project conventions.
- [Fidelity: Rate of Change](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/roc) (`fidelity_roc`). Percentage price change; project reports the fractional return instead of multiplying by 100.
- [Fidelity: Bollinger Bands](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands) (`fidelity_bands`). SMA and standard-deviation envelope background only. Population z-score and contrarian rule are explicit project choices, not a guarantee of mean reversion.
- [Gagnon, Joseph E. and Chaboud, Alain P.: What Can the Data Tell Us about Carry Trades in Japanese Yen?](https://www.federalreserve.gov/pubs/ifdp/2007/899/ifdp899.htm) (`gagnon_chaboud_2007`). IFDP 899, July 2007. Carry definition and exchange-rate risk. Policy differential is a research proxy, not this paper replication or UIP forecast.
- [CME Group: Understanding FX Quote Conventions](https://www.cmegroup.com/education/courses/introduction-to-fx/understanding-fx-quote-conventions) (`cme_fx_quote`). Base/quote convention. USD per EUR gives USD P&L for signed EUR units.
- [yfinance authors: yfinance.download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) (`yfinance_intraday`). Official intraday interval and lookback restrictions. Live test uses pinned Ticker.history; provider limitations may change.
- [Federal Reserve Bank of St. Louis: Federal Funds Target Range - Upper Limit (DFEDTARU)](https://fred.stlouisfed.org/series/DFEDTARU) (`fred_fed_upper`). Daily percent policy target upper bound. No historical release-vintage claim.
- [Federal Reserve Bank of St. Louis: ECB Deposit Facility Rate for Euro Area (ECBDFR)](https://fred.stlouisfed.org/series/ECBDFR) (`fred_ecb_deposit`). Policy deposit rate percent. Not a matched-maturity bond yield; live endpoint failed in this session.

## Phase 7 verified equations and conventions

- [J.P. Morgan/Reuters, RiskMetrics 1996](https://faculty.runi.ac.il/kobi/riskmgt/rmtd.pdf), section 5.2 and scalar EWMA recurrence. Seed, 4H decay choice and risk policy are declared project conventions.
- [Bollerslev 1986, original author PDF](https://econ.duke.edu/~boller/Published_Papers/joe_86.pdf), equations 2/8, Theorem 1 and section 5. Finite-grid variance-targeted fitting is a restricted project estimator, not full MLE.
- [CME, Proper Position Size](https://www.cmegroup.com/education/courses/trade-and-risk-management/proper-position-size), risk amount divided by stop loss per unit. Costs/carry and post-cost constraints are explicit algebraic extensions.

## Phase 8 primary source

Rabiner (1989), [original HMM paper](https://web.mit.edu/6.435/www/Rabiner89.pdf), DOI 10.1109/5.18626. Full PDF verified 2026-09-25. Forward recursion and Gaussian EM support the HMM implementation; regime thresholds and financial interpretations are explicitly project conventions. See MODELS.md and FX_REGIMES.md.

## Phase 9 primary implementation sources

- [AutoReg: autoregressive AR-X conditional OLS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.ar_model.AutoReg.html): AR and lagged-exogenous ARX.
- [Vector Autoregressions](https://www.statsmodels.org/stable/vector_ar.html): VAR equations, fitting, one-step forecasting and stationarity assumption.
- [Implementing state space models for Statsmodels](https://www.chadfulton.com/topics/implementing_state_space.html): Author-provided Kalman filter implementation and covariance recursion.
- [MarkovRegression](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html): Gaussian switching regression; intercept-only specialization.

Sources accessed 2026-09-25. The original Kalman-1960 PDF could not be retrieved; verification instead uses the original implementation published by the statsmodels contributor. Financial policies and restricted model orders are explicit in MODELS.md. Rabiner (1989) remains the primary Gaussian-HMM estimation source.
