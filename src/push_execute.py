"""Execute the endgame plan written by src/tail_basket.py, or snipe called races.

Dry run by default: prints every order with a book-walked limit price. Add --live
to place limit orders through the same SusqAPI used by autopilot/trade.

  # 1) exits + basket from the plan
  python src/push_execute.py plan --plan data/tournament_push/basket_plan.json
  python src/push_execute.py plan --plan data/tournament_push/basket_plan.json --live

  # 2) election night: buy the winner of races already called by a reliable source
  python src/push_execute.py snipe --call "PA-08 House race=Republican" --spend 5000
  python src/push_execute.py snipe --call "PA-08 House race=Republican" --spend 5000 --live

Stop autopilot.py before running this; it would fight the plan.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scan_live import discover_midterm_tournament
from src.susq_api import SusqAPI, SusqAPIError


def _levels(book: dict[str, Any], key: str) -> list[tuple[float, float]]:
    out = []
    for lvl in book.get(key, []) or []:
        if isinstance(lvl, dict):
            p = lvl.get("price")
            q = lvl.get("quantity", lvl.get("size", lvl.get("qty")))
        else:
            p, q = lvl[0], lvl[1]
        if p is not None and q is not None:
            out.append((float(p), float(q)))
    return out


def walk(levels: list[tuple[float, float]], budget: float | None = None,
         shares: float | None = None, limit: float | None = None,
         buying: bool = True) -> tuple[int, float, float]:
    """Walk the book. Returns (shares, total cost/proceeds, worst price touched)."""
    got, money, worst = 0.0, 0.0, 0.0
    for p, q in levels:
        if limit is not None and ((buying and p > limit) or (not buying and p < limit)):
            break
        take = q
        if shares is not None:
            take = min(take, shares - got)
        if budget is not None:
            take = min(take, (budget - money) / p)
        if take <= 0:
            break
        got += take
        money += take * p
        worst = p
    return int(got), money, worst


def resolve_exchange(markets: list[dict[str, Any]], race: str, party: str) -> str | None:
    want = f"Will the {party} Party win the {race}?".lower()
    for m in markets:
        if m.get("title", "").strip().lower() == want:
            for ex in m.get("exchanges", []):
                if (ex.get("option") or ex.get("settlementOption") or "YES").upper() == "YES":
                    return str(ex["id"])
    return None


def place(api: SusqAPI, tid: str, exchange_id: str, action: str, qty: int, price: float,
          live: bool, label: str) -> None:
    price = round(price, 3)
    line = f"{action.upper():4s} {qty:>8,d} YES @ <= {price:.3f}  [{exchange_id}] {label}"
    if not live:
        print("DRY  " + line)
        return
    key = "push-" + secrets.token_urlsafe(20)
    try:
        res = api.place_order(exchange_id=exchange_id, side="yes", action=action,
                              quantity=qty, price=price, tournament_id=tid, idempotency_key=key)
        print(f"SENT {line} -> {res.get('status', res)}")
    except SusqAPIError as exc:
        # Never blind-retry: the order may have landed. Reconcile on the portfolio page.
        print(f"FAIL {line} -> {exc}  (check open orders before retrying)")
    time.sleep(0.4)


def cmd_plan(args: argparse.Namespace) -> int:
    plan = json.loads(Path(args.plan).read_text())["best"]
    api = SusqAPI()
    tour = discover_midterm_tournament(api)
    tid = str(tour["id"])
    markets = api.list_all_tournament_markets(tour["slug"], status="open")
    print(f"scenario={plan['scenario']} band={plan['band']} scheme={plan['scheme']} legs={len(plan['legs'])}")

    print("\n-- exits (raise cash first) --")
    if args.skip_exits:
        print("skipped (--skip-exits)")
    for e in ([] if args.skip_exits else plan["exits"]):
        ex = resolve_exchange(markets, e["race"], e["party"]) or e["exchange_id"]
        book = api.orderbook(ex, depth=50, tournament_id=tid)
        if e["action"].startswith("SELL"):
            floor = max(0.005, e["est_price"] - args.max_slip)
            n, cash, worst = walk(_levels(book, "bids"), shares=e["quantity"], limit=floor, buying=False)
            if n:
                place(api, tid, ex, "sell", n, worst, args.live, f"{e['party']} {e['race']} (~{cash:,.0f})")
            if n < e["quantity"]:
                print(f"     ! only {n:,}/{e['quantity']:,} sellable above {floor:.3f}; rest stays on")
        else:
            cap = min(0.99, e["est_price"] + args.max_slip)
            n, cost, worst = walk(_levels(book, "asks"), shares=e["quantity"], limit=cap)
            if n:
                place(api, tid, ex, "buy", n, worst, args.live, f"cover {e['party']} {e['race']} (~{cost:,.0f})")

    print("\n-- scenario basket --")
    total = 0.0
    for leg in plan["legs"]:
        ex = resolve_exchange(markets, leg["race"], leg["party"]) or leg["exchange_id"]
        book = api.orderbook(ex, depth=50, tournament_id=tid)
        cap = min(args.max_price, leg["last"] * (1 + args.max_markup) + 0.01)
        n, cost, worst = walk(_levels(book, "asks"), budget=leg["spend"], limit=cap)
        if n <= 0:
            print(f"SKIP {leg['party']} {leg['race']}: nothing offered <= {cap:.3f}")
            continue
        total += cost
        place(api, tid, ex, "buy", n, worst, args.live,
              f"{leg['party']} {leg['race']} avg {cost / n:.3f} pays {n:,}")
    print(f"\nbasket cost ~{total:,.0f} SUSQies")
    return 0


def cmd_snipe(args: argparse.Namespace) -> int:
    api = SusqAPI()
    tour = discover_midterm_tournament(api)
    tid = str(tour["id"])
    markets = api.list_all_tournament_markets(tour["slug"], status="open")
    for call in args.call:
        race, party = [x.strip() for x in call.split("=", 1)]
        ex = resolve_exchange(markets, race, party)
        if not ex:
            print(f"SKIP {call}: market not found")
            continue
        book = api.orderbook(ex, depth=50, tournament_id=tid)
        n, cost, worst = walk(_levels(book, "asks"), budget=args.spend, limit=args.max_price)
        if n <= 0:
            print(f"SKIP {call}: no asks <= {args.max_price}")
            continue
        place(api, tid, ex, "buy", n, worst, args.live,
              f"{party} {race} avg {cost / n:.3f} -> +{n - cost:,.0f} if it settles YES")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--plan", default="data/tournament_push/basket_plan.json")
    p.add_argument("--max-slip", type=float, default=0.03, help="exits: worst price move accepted")
    p.add_argument("--max-markup", type=float, default=0.35, help="basket: max limit vs snapshot price")
    p.add_argument("--max-price", type=float, default=0.45)
    p.add_argument("--live", action="store_true")
    p.add_argument("--skip-exits", action="store_true",
                   help="only place the basket buys (use if exits already went through)")
    s = sub.add_parser("snipe")
    s.add_argument("--call", action="append", required=True, help='"<race>=<Republican|Democratic>"')
    s.add_argument("--spend", type=float, default=5000)
    s.add_argument("--max-price", type=float, default=0.95)
    s.add_argument("--live", action="store_true")
    args = ap.parse_args()
    try:
        return cmd_plan(args) if args.cmd == "plan" else cmd_snipe(args)
    except SusqAPIError as exc:
        print(f"API error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
