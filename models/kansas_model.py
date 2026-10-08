from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt


@dataclass(frozen=True)
class KansasInputs:
    market_price: float = 0.355
    structural_margin: float = -8.0  # Democratic minus Republican
    poll_margin: float = 0.6
    national_adjustment: float = 1.0
    poll_weight: float = 0.65
    margin_sd: float = 6.5


def normal_cdf(x: float, sd: float) -> float:
    if sd <= 0:
        raise ValueError('sd must be positive')
    return 0.5 * (1.0 + erf(x / (sd * sqrt(2.0))))


def estimate_probability(inputs: KansasInputs) -> tuple[float, float, float]:
    fundamental_weight = 1.0 - inputs.poll_weight
    blended_margin = (
        inputs.poll_weight * inputs.poll_margin
        + fundamental_weight * inputs.structural_margin
        + inputs.national_adjustment
    )
    probability = normal_cdf(blended_margin, inputs.margin_sd)
    edge = probability - inputs.market_price
    return blended_margin, probability, edge


if __name__ == '__main__':
    margin, probability, edge = estimate_probability(KansasInputs())
    print(f'Blended margin (D-R): {margin:.2f}')
    print(f'Estimated P(D win): {probability:.3f}')
    print(f'Market price: {KansasInputs().market_price:.3f}')
    print(f'Raw edge: {edge:+.3f}')
