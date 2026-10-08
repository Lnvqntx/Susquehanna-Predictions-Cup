from __future__ import annotations

from dataclasses import dataclass
from math import exp, log


@dataclass(frozen=True)
class Poll:
    pollster: str
    days_old: float
    sample_size: int
    dem: float
    rep: float


def poll_weight(days_old: float, sample_size: int, half_life_days: float = 10.0) -> float:
    """Recency × sqrt(sample-size) weight. This is scaffolding, not calibration."""
    if days_old < 0:
        raise ValueError('days_old must be non-negative')
    if sample_size <= 0:
        raise ValueError('sample_size must be positive')
    if half_life_days <= 0:
        raise ValueError('half_life_days must be positive')
    recency = exp(-log(2.0) * days_old / half_life_days)
    return recency * sample_size ** 0.5


def weighted_margin(polls: list[Poll]) -> float:
    if not polls:
        raise ValueError('poll list cannot be empty')
    weights = [poll_weight(p.days_old, p.sample_size) for p in polls]
    total = sum(weights)
    return sum(w * (p.dem - p.rep) for w, p in zip(weights, polls)) / total


if __name__ == '__main__':
    polls = [
        Poll('YouGov', 4, 2255, 48, 45),
        Poll('NYT/Siena', 7, 605, 46, 47),
        Poll('Trafalgar', 7, 1095, 44, 44),
        Poll('Wedgewood', 14, 500, 50, 48),
        Poll('Emerson', 22, 750, 45, 43),
        Poll('GSG', 22, 800, 49, 47),
        Poll('co/efficient', 28, 915, 44, 49),
        Poll('GBAO', 4, 600, 46, 41),
    ]
    print(f'Weighted poll margin: D+{weighted_margin(polls):.2f}')
