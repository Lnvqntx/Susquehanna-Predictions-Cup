from __future__ import annotations


def fractional_kelly(probability: float, price: float, bankroll: float, fraction: float = 0.25) -> float:
    """Return conservative fractional-Kelly bankroll allocation for a YES contract."""
    if not 0 < probability < 1:
        raise ValueError("probability must be in (0, 1)")
    if not 0 < price < 1:
        raise ValueError("price must be in (0, 1)")
    if bankroll < 0:
        raise ValueError("bankroll must be non-negative")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    full_kelly = max(0.0, (probability - price) / (1.0 - price))
    return bankroll * fraction * full_kelly
