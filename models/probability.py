from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt


@dataclass
class ProbabilityEstimate:
    probability: float
    low: float
    high: float
    explanation: str


def normal_cdf(x: float, mean: float = 0.0, sd: float = 1.0) -> float:
    if sd <= 0:
        raise ValueError("sd must be positive")
    return 0.5 * (1.0 + erf((x - mean) / (sd * sqrt(2.0))))


def win_probability_from_margin(projected_margin: float, margin_sd: float) -> float:
    return normal_cdf(projected_margin, 0.0, margin_sd)


def edge(probability: float, executable_price: float) -> float:
    return probability - executable_price
