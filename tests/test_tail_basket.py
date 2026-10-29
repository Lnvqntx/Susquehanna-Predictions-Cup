from src.push_execute import walk
from src.tail_basket import Contract, build_races, sharpen, simulate


def test_sharpen_identity_and_tails():
    assert abs(sharpen(0.5, 1.3) - 0.5) < 1e-9
    assert abs(sharpen(0.1, 1.0) - 0.1) < 1e-9
    assert sharpen(0.1, 1.25) < 0.1 < 0.9 < sharpen(0.9, 1.25)


def test_three_way_race_drops_dem_and_independent():
    races = build_races([
        Contract("1", "Republican", "Nebraska Senate", 0.665),
        Contract("2", "Independent", "Nebraska Senate", 0.305),
        Contract("3", "Democratic", "Nebraska Senate", 0.065),
    ], rho=0.5)
    assert set(races["Nebraska Senate"].contracts) == {"Republican"}


def test_simulation_matches_market_marginals():
    races = build_races([
        Contract("1", "Republican", "X", 0.2), Contract("2", "Democratic", "X", 0.8),
        Contract("3", "Republican", "Y", 0.6), Contract("4", "Democratic", "Y", 0.4),
    ], rho=0.5)
    _, out = simulate(races, 20000, seed=1)
    px = sum(o["X"] for o in out) / len(out)
    py = sum(o["Y"] for o in out) / len(out)
    assert abs(px - 0.2) < 0.015 and abs(py - 0.6) < 0.015


def test_walk_respects_limit_and_budget():
    asks = [(0.10, 1000), (0.12, 1000), (0.20, 1000)]
    n, cost, worst = walk(asks, budget=150, limit=0.15)
    assert worst == 0.12 and n == 1000 + 416 and abs(cost - (100 + 416 * 0.12)) < 0.2
    bids = [(0.09, 500), (0.08, 500), (0.05, 500)]
    n, cash, worst = walk(bids, shares=800, limit=0.07, buying=False)
    assert n == 800 and worst == 0.08
