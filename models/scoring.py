from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Candidate:
    market: str
    side: str
    model_probability: float
    executable_price: float
    liquidity: float = 0.0
    confidence: float = 0.5
    correlation_penalty: float = 0.0

    @property
    def edge(self) -> float:
        return self.model_probability - self.executable_price

    @property
    def return_on_cost(self) -> float:
        if self.executable_price <= 0:
            return 0.0
        return self.edge / self.executable_price

    @property
    def score(self) -> float:
        liquidity_factor = min(1.0, max(0.0, self.liquidity / 10000.0))
        confidence_factor = 0.5 + 0.5 * min(1.0, max(0.0, self.confidence))
        redundancy = min(1.0, max(0.0, self.correlation_penalty))
        return self.edge * confidence_factor * (0.5 + 0.5 * liquidity_factor) * (1.0 - 0.5 * redundancy)

def rank_candidates(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(candidates, key=lambda c: c.score, reverse=True)
