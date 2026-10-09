from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    side: str
    probability: float
    price: float

    @property
    def edge(self) -> float:
        return self.probability - self.price

    @property
    def expected_return_on_cost(self) -> float:
        return self.edge / self.price


def rank_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """Rank by raw probability edge, highest first."""
    return sorted(candidates, key=lambda x: x.edge, reverse=True)


if __name__ == "__main__":
    candidates = [
        Candidate("Rhode Island Senate D", "YES", 0.97, 0.845),
        Candidate("New Hampshire Senate D", "YES", 0.89, 0.845),
        Candidate("Georgia Senate R", "NO", 0.96, 0.92),
        Candidate("Delaware Senate R", "NO", 0.975, 0.93),
        Candidate("Massachusetts Senate D", "YES", 0.98, 0.935),
    ]
    for c in rank_candidates(candidates):
        print(f"{c.name:32} {c.side:>3} edge={c.edge:+.3f} return={c.expected_return_on_cost:.2%}")
