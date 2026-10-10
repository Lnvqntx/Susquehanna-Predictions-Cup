from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    market: str
    side: str
    cost: float
    theme: str

def theme_exposure(positions: list[Position]) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in positions:
        out[p.theme] = out.get(p.theme, 0.0) + p.cost
    return out

def correlation_penalty(theme: str, positions: list[Position], bankroll: float) -> float:
    if bankroll <= 0:
        return 0.0
    exposure = theme_exposure(positions).get(theme, 0.0) / bankroll
    return min(1.0, max(0.0, exposure * 2.0))
