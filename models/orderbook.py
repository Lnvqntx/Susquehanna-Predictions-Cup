from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Ask:
    price: float
    quantity: int

@dataclass(frozen=True)
class FillEstimate:
    contracts: int
    cost: float
    average_price: float
    worst_price: float

def fill_budget(asks: list[Ask], budget: float, max_price: float) -> FillEstimate:
    if budget <= 0 or max_price <= 0 or max_price > 1:
        raise ValueError('invalid budget or max_price')
    contracts = 0
    cost = 0.0
    worst = 0.0
    for ask in sorted(asks, key=lambda a: a.price):
        if ask.price > max_price:
            break
        affordable = int((budget - cost) / ask.price)
        take = min(ask.quantity, max(0, affordable))
        if take == 0:
            break
        contracts += take
        cost += take * ask.price
        worst = ask.price
        if cost >= budget:
            break
    avg = cost / contracts if contracts else 0.0
    return FillEstimate(contracts, cost, avg, worst)
