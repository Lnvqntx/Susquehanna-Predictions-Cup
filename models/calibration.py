from __future__ import annotations

from math import erf, sqrt

def normal_cdf(x: float, sd: float) -> float:
    if sd <= 0:
        raise ValueError('sd must be positive')
    return 0.5 * (1.0 + erf(x / (sd * sqrt(2.0))))

def win_probability(projected_margin: float, margin_sd: float) -> float:
    return normal_cdf(projected_margin, margin_sd)

def uncertainty_haircut(probability: float, low_probability: float, high_probability: float, confidence: float = 0.5) -> float:
    if not 0.0 <= low_probability <= probability <= high_probability <= 1.0:
        raise ValueError('probability interval must be ordered inside [0, 1]')
    if not 0.0 <= confidence <= 1.0:
        raise ValueError('confidence must be in [0, 1]')
    midpoint = (low_probability + high_probability) / 2.0
    return confidence * probability + (1.0 - confidence) * midpoint
