"""Tournament-endgame basket builder.

Leaderboard rank, not expected value, is the objective. With ~6 days left and the
book near the bottom of the table, the only path to the top is a large, correlated
bet that pays many times over if one national scenario happens.

This module:
  1. turns market prices into a correlated election simulation
     (one shared national swing + independent race noise),
  2. scores candidate baskets by P(final account value >= leaderboard targets),
  3. emits a dry-run order plan (sells of off-scenario positions, buys of
     scenario contracts) that can be executed with the existing guarded API code.

Pure stdlib so it runs anywhere the rest of the repo runs.

Offline (snapshot CSV, no API key needed):
    python src/tail_basket.py --markets data/tournament_push/markets_2026-10-29.csv \
        --holdings data/tournament_push/holdings_2026-10-29.csv

Live prices/positions via the tournament API (dry run, no orders):
    python src/tail_basket.py --live-data
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

N = NormalDist()
CHAMBERS = {"U.S. House", "U.S. Senate"}


@dataclass
class Contract:
    exchange_id: str
    party: str          # Republican / Democratic / Independent
    race: str
    price: float        # last trade (or best ask when live)


@dataclass
class Race:
    race: str
    p_rep: float                    # two-party probability the Republican wins
    contracts: dict[str, Contract] = field(default_factory=dict)
    loading: float = 0.0            # weight on the national swing


@dataclass
class Holding:
    race: str
    party: str
    quantity: int                   # negative = short YES
    avg_price: float


# ---------------------------------------------------------------- loading

TITLE_RE = re.compile(r"Will the (\w+) Party win the (.+?)\??$")


def load_markets_csv(path: Path) -> list[Contract]:
    out = []
    with path.open() as f:
        for r in csv.DictReader(f):
            out.append(Contract(r["exchange_id"], r["party"], r["race"], float(r["last_price"])))
    return out


def load_holdings_csv(path: Path) -> list[Holding]:
    out = []
    with path.open() as f:
        for r in csv.DictReader(f):
            m = TITLE_RE.match(r["Market"].strip())
            if not m:
                continue
            out.append(Holding(m.group(2), m.group(1), int(r["Quantity"]), float(r["Avg Price"])))
    return out


def sharpen(p: float, k: float) -> float:
    """Favorite-longshot correction: logit(p_true) = k * logit(p_market).

    Contest crowds overpay for longshots. On 2026-10-29 SUSQ priced R-House at
    14.5% vs ~8% on Kalshi/Polymarket and IA-01 R at 9.5% vs ~7.5%; k~1.25
    roughly reconciles those gaps. k=1 trusts SUSQ prices as-is.
    """
    import math
    l = math.log(p / (1 - p)) * k
    return 1 / (1 + math.exp(-l))


def build_races(contracts: list[Contract], rho: float, sharpen_k: float = 1.0) -> dict[str, Race]:
    by_race: dict[str, dict[str, Contract]] = {}
    for c in contracts:
        by_race.setdefault(c.race, {})[c.party] = c
    races: dict[str, Race] = {}
    for name, cs in by_race.items():
        if "Independent" in cs:
            # Three-way race: "not Republican" is not "Democrat wins", so only the R
            # contract can be simulated honestly. Drop the D/I tickets.
            cs = {k: v for k, v in cs.items() if k == "Republican"}
        r = cs.get("Republican")
        d = cs.get("Democratic")
        if r and d:
            p = r.price / (r.price + d.price)
        elif r:
            p = r.price
        elif d:
            p = 1.0 - d.price
        else:
            continue
        p = sharpen(min(max(p, 0.01), 0.99), sharpen_k)
        # Chamber control is almost entirely the national swing.
        loading = 0.95 if name in CHAMBERS else rho
        races[name] = Race(name, p, cs, loading)
    return races


# ---------------------------------------------------------------- simulation

def simulate(races: dict[str, Race], n_sims: int, seed: int,
             swing_shift: float = 0.0) -> tuple[list[float], list[dict[str, bool]]]:
    """Return national swings and R-win outcomes per sim.

    X_race = mu + sqrt(l) * S + sqrt(1-l) * e, R wins iff X > 0, so the marginal
    P(R wins) equals the market price when swing_shift == 0.
    """
    rng = random.Random(seed)
    mus = {k: N.inv_cdf(r.p_rep) for k, r in races.items()}
    swings, outcomes = [], []
    for _ in range(n_sims):
        s = rng.gauss(swing_shift, 1.0)
        res = {}
        for k, r in races.items():
            x = mus[k] + (r.loading ** 0.5) * s + ((1 - r.loading) ** 0.5) * rng.gauss(0, 1)
            res[k] = x > 0
        swings.append(s)
        outcomes.append(res)
    return swings, outcomes


def contract_pays(outcome: dict[str, bool], race: str, party: str) -> bool:
    rep = outcome[race]
    if party == "Republican":
        return rep
    if party == "Democratic":
        return not rep
    return False  # independents treated as losing in the two-party sim


# ---------------------------------------------------------------- baskets

def fill_price(last: float, spend: float, impact_per_10k: float) -> float:
    """Crude average fill: ask ~= last + half a tick, plus linear impact."""
    ask = last + 0.005
    return min(0.99, ask * (1 + impact_per_10k * spend / 10_000))


def scenario_candidates(races: dict[str, Race], party: str, lo: float, hi: float) -> list[Contract]:
    out = []
    for r in races.values():
        c = r.contracts.get(party)
        if c and lo <= c.price <= hi:
            out.append(c)
    return sorted(out, key=lambda c: c.price)


def build_basket(cands: list[Contract], budget: float, scheme: str,
                 max_per_contract: float, impact: float) -> list[dict]:
    if not cands or budget <= 0:
        return []
    if scheme == "equal_shares":       # same payout per race -> stake proportional to price
        weights = [c.price for c in cands]
    elif scheme == "equal_stake":
        weights = [1.0 for _ in cands]
    elif scheme == "cheap_tilt":       # more money on cheaper, higher-multiple tickets
        weights = [1.0 / c.price ** 0.5 for c in cands]
    else:
        raise ValueError(scheme)
    tot = sum(weights)
    spend = [min(max_per_contract, budget * w / tot) for w in weights]
    # redistribute any capped remainder once
    left = budget - sum(spend)
    free = [i for i, s in enumerate(spend) if s < max_per_contract]
    if left > 1 and free:
        ftot = sum(weights[i] for i in free)
        for i in free:
            spend[i] = min(max_per_contract, spend[i] + left * weights[i] / ftot)
    legs = []
    for c, s in zip(cands, spend):
        px = fill_price(c.price, s, impact)
        legs.append({"race": c.race, "party": c.party, "exchange_id": c.exchange_id,
                     "last": c.price, "est_fill": round(px, 4), "spend": round(s, 2),
                     "shares": int(s / px)})
    return legs


def evaluate(legs: list[dict], kept: list[Holding], cash_left: float,
             outcomes: list[dict[str, bool]], targets: list[float]) -> dict:
    finals = []
    for o in outcomes:
        v = cash_left
        for l in legs:
            if contract_pays(o, l["race"], l["party"]):
                v += l["shares"]
        for h in kept:
            if h.race in o and contract_pays(o, h.race, h.party):
                v += h.quantity     # short positions lose |q| when YES pays
        finals.append(v)
    finals.sort()
    n = len(finals)
    return {
        "p": {t: sum(1 for f in finals if f >= t) / n for t in targets},
        "median": finals[n // 2],
        "p90": finals[int(n * 0.9)],
        "p99": finals[int(n * 0.99)],
        "max": finals[-1],
    }


# ---------------------------------------------------------------- holdings

def split_holdings(holdings: list[Holding], races: dict[str, Race], scenario_party: str,
                   keep_min_multiple: float) -> tuple[list[Holding], list[dict], float]:
    """Keep positions that pay in the scenario at a high multiple; plan to exit the rest.

    Returns (kept, exit_plan, estimated cash raised by exits).
    """
    kept, exits, cash = [], [], 0.0
    for h in holdings:
        race = races.get(h.race)
        c = race.contracts.get(h.party) if race else None
        if not c:
            continue
        price = c.price
        long_scenario = h.quantity > 0 and h.party == scenario_party
        short_against = h.quantity < 0 and h.party != scenario_party   # short of the other side
        multiple = (1 / price) if long_scenario else 0
        if (long_scenario and multiple >= keep_min_multiple) or short_against:
            kept.append(h)
            continue
        if h.quantity > 0:
            proceeds = h.quantity * max(price - 0.01, 0.0) * 0.97      # sell into the bid
            exits.append({"action": "SELL YES", "race": h.race, "party": h.party,
                          "exchange_id": c.exchange_id, "quantity": h.quantity,
                          "est_price": round(price - 0.01, 3), "est_cash": round(proceeds, 2)})
            cash += proceeds
        else:
            cost = -h.quantity * min(price + 0.01, 0.99) * 1.03         # buy back the short
            exits.append({"action": "BUY YES (cover short)", "race": h.race, "party": h.party,
                          "exchange_id": c.exchange_id, "quantity": -h.quantity,
                          "est_price": round(price + 0.01, 3), "est_cash": round(-cost, 2)})
            cash -= cost
    return kept, exits, cash


# ---------------------------------------------------------------- main

def run(args: argparse.Namespace) -> dict:
    contracts = load_markets_csv(Path(args.markets))
    holdings = load_holdings_csv(Path(args.holdings)) if args.holdings else []
    races = build_races(contracts, args.rho, args.sharpen)
    _, outcomes = simulate(races, args.sims, args.seed)

    targets = args.targets
    base = evaluate([], [h for h in holdings if h.race in races], args.cash, outcomes, targets)
    results = []
    for party in ([args.scenario] if args.scenario else ["Republican", "Democratic"]):
        for keep_mult in (2.0, 1.4):
            kept, exits, raised = split_holdings(holdings, races, party, keep_mult)
            budget = args.cash + raised
            # don't double up on races we already hold for the scenario
            held = {(h.race, h.party) for h in kept}
            for lo, hi in args.bands:
                cands = [c for c in scenario_candidates(races, party, lo, hi)
                         if (c.race, c.party) not in held]
                for scheme in ("equal_shares", "equal_stake", "cheap_tilt"):
                    legs = build_basket(cands, budget, scheme, args.max_per_contract, args.impact)
                    left = budget - sum(l["spend"] for l in legs)
                    ev = evaluate(legs, kept, left, outcomes, targets)
                    results.append({"scenario": party, "keep_min_multiple": keep_mult,
                                    "band": [lo, hi], "scheme": scheme, "n_legs": len(legs),
                                    "budget": round(budget, 2), "eval": ev,
                                    "exits": exits, "kept": [h.__dict__ for h in kept],
                                    "legs": legs})
    key_t = args.objective
    results.sort(key=lambda r: (r["eval"]["p"][key_t], r["eval"]["p"][targets[-1]]), reverse=True)
    return {"baseline_hold_everything": base, "rho": args.rho, "sims": args.sims, "objective": key_t, "targets": targets,
            "n_races": len(races), "best": results[0], "table": [
                {k: r[k] for k in ("scenario", "keep_min_multiple", "band", "scheme", "n_legs", "budget")}
                | {"p": r["eval"]["p"], "median": round(r["eval"]["median"]),
                   "p99": round(r["eval"]["p99"])} for r in results[:15]]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markets", default="data/tournament_push/markets_2026-10-29.csv")
    ap.add_argument("--holdings", default="data/tournament_push/holdings_2026-10-29.csv")
    ap.add_argument("--cash", type=float, default=2196.0, help="free SUSQies before exits")
    ap.add_argument("--rho", type=float, default=0.5, help="share of race variance from the national swing")
    ap.add_argument("--sharpen", type=float, default=1.25, help="longshot-bias correction k (1 = trust prices)")
    ap.add_argument("--sims", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--impact", type=float, default=0.25, help="fractional price impact per 10k spent")
    ap.add_argument("--max-per-contract", type=float, default=8000)
    ap.add_argument("--targets", type=float, nargs="+", default=[126_000, 273_000, 500_000, 990_000],
                    help="account values: ~top70, ~top10, ~top5ish, ~top3 on 2026-10-29")
    ap.add_argument("--band", dest="bands", type=float, nargs=2, action="append",
                    help="price band(s) for scenario tickets; default tries 4 bands")
    ap.add_argument("--scenario", choices=["Republican", "Democratic"], default=None)
    ap.add_argument("--objective", type=float, default=273_000)
    ap.add_argument("--out", default="data/tournament_push/basket_plan.json")
    args = ap.parse_args()
    if not args.bands:
        args.bands = [(0.03, 0.15), (0.05, 0.25), (0.08, 0.40), (0.10, 0.60)]

    report = run(args)
    Path(args.out).write_text(json.dumps(report, indent=2))
    t = report["targets"]
    print(f"races={report['n_races']} sims={report['sims']} rho={report['rho']} sharpen={args.sharpen}  objective=P(>= {report['objective']:,.0f})")
    b = report["baseline_hold_everything"]
    print("HOLD CURRENT BOOK               " + "  ".join(f"{b['p'][x]*100:5.1f}%" for x in t) + f"  {round(b['median']):8,d}  {round(b['p99']):8,d}")
    print("scenario  keep  band         scheme        legs  " + "  ".join(f">={x/1000:.0f}k" for x in t) + "   median     p99")
    for r in report["table"]:
        ps = "  ".join(f"{r['p'][x]*100:5.1f}%" for x in t)
        print(f"{r['scenario'][:3]:8s}  {r['keep_min_multiple']:.1f}  {str(r['band']):11s}  {r['scheme']:12s}  {r['n_legs']:4d}  {ps}  {r['median']:8,d}  {r['p99']:8,d}")
    print(f"\nplan written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
