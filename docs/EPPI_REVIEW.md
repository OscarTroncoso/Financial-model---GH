# EPPI formulation decision — 2026-09-23

Version 0.3.0 enables the specifically identified **discrete Mancinelli-Oliva
2023 multiplier** under model ID `eppi`. Exact equations, worked examples,
policy differences and limitations are in [DYNAMIC_MODELS.md](DYNAMIC_MODELS.md).

The prior block was justified: the original Lee, Chiang and Hsu (2008) equation
pages remain inaccessible, and the original project description of an
exponential cushion function was not supported. We resolve the implementation
choice by selecting the accessible 2023 publication's own discrete rule, not by
asserting that the unavailable 2008 original has been verified.

The fixed-reference level rule described in Mancinelli's doctoral thesis and
the additive discrete recurrence are not algebraically interchangeable. Both
were found, but only the latter is selected. No reference-price reset is invented.
The source's apparent wealth-accounting discrepancy remains documented; only
the multiplier is reproduced and our tested self-financing accounting is used.

This is a transparent research-specification correction, not evidence that EPPI
performs better or that any empirical results from either article were replicated.
