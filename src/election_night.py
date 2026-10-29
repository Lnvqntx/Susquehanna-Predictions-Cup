"""Election-night autopilot: trade SUSQ's lag behind Polymarket while you're busy.

Idea: once results come in, Polymarket reprices called races to ~0.97-1.00 within
minutes, but the SUSQ board lags. This loop watches both and:

  BUY   the SUSQ YES of a race's winner when Polymarket's best bid has been
        >= --win-bid on two polls at least --confirm-secs apart, and the SUSQ ask
        is still <= min(--max-buy, poly_bid - --min-gap).
  DUMP  a held SUSQ position whose Polymarket price has collapsed to <= --lose-bid
        while SUSQ still bids >= --min-dump-bid (sell the loser before SUSQ notices).
  CYCLE sell a position this bot bought once SUSQ bids >= --recycle-bid, freeing
        cash for the next race.

Only races that were genuinely open before results count: a race is eligible
only if its Polymarket price for the winner was below --baseline-max before
results (the 2026-10-29 snapshot in polymarket_map.csv).
That keeps the bot from buying already-safe seats pre-results.

Safety: dry run unless --live; per-race and total spend caps; each race is bought
at most once (state file survives restarts); stops at --stop; create a file named
STOP in the repo root to halt it.

Typical use (night of Nov 3, before ~04:30 IST):
    caffeinate -dimsu python3 -u src/election_night.py --live > data/election_night.log 2>&1 &
Dry-run check any time beforehand:
    python3 src/election_night.py --once
"""
from __future__ import annotations

import argparse
import csv
import json
import secrets
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import certifi

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.push_execute import _levels, walk
from src.scan_live import discover_midterm_tournament
from src.susq_api import SusqAPI, SusqAPIError

GAMMA = "https://gamma-api.polymarket.com"
MAP_CSV = ROOT / "data/tournament_push/polymarket_map.csv"
SUSQ_CSV = ROOT / "data/tournament_push/markets_2026-10-29.csv"
STATE = ROOT / "data/election_night_state.json"
STOP_FILE = ROOT / "STOP"


def now() -> datetime:
    return datetime.now(timezone.utc)


def log(msg: str) -> None:
    print(f"{datetime.now().strftime('%m-%d %H:%M:%S')}  {msg}", flush=True)


# ------------------------------------------------------------------ data

def load_map() -> list[dict[str, str]]:
    susq = {}
    with SUSQ_CSV.open() as f:
        for r in csv.DictReader(f):
            susq[(r["race"], r["party"])] = r["exchange_id"]
    rows = []
    with MAP_CSV.open() as f:
        for r in csv.DictReader(f):
            ex = susq.get((r["race"], r["party"]))
            if ex and r["party"] in ("Republican", "Democratic"):
                rows.append({**r, "susq_exchange": ex})
    return rows


def poly_quotes(ids: list[str]) -> dict[str, dict[str, Any]]:
    """market_id -> {bid, ask, last, closed, yes_won}. Batched gamma /markets calls.

    Markets that resolved may be filtered out of the default listing, so any id
    missing from the first pass is asked for again with closed=true.
    """
    out = _poly_fetch(ids, closed=None)
    missing = [i for i in ids if i not in out]
    if missing:
        out.update(_poly_fetch(missing, closed=True))
    return out


def _poly_fetch(ids: list[str], closed: bool | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    ctx = ssl.create_default_context(cafile=certifi.where())
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        params = [("id", x) for x in chunk] + [("limit", "100")]
        if closed is not None:
            params.append(("closed", "true" if closed else "false"))
        q = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{GAMMA}/markets?{q}",
                                     headers={"Accept": "application/json",
                                              "User-Agent": "susquehanna-predictions-cup/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network blips: skip this round, try next loop
            log(f"poly fetch error: {exc}")
            continue
        for m in data if isinstance(data, list) else []:
            try:
                prices = json.loads(m.get("outcomePrices") or "[]")
            except json.JSONDecodeError:
                prices = []
            yes = float(prices[0]) if prices else None
            closed = bool(m.get("closed"))
            out[str(m["id"])] = {
                "bid": _f(m.get("bestBid")), "ask": _f(m.get("bestAsk")),
                "last": _f(m.get("lastTradePrice")), "yes": yes, "closed": closed,
                "yes_won": closed and yes is not None and yes >= 0.99,
                "yes_lost": closed and yes is not None and yes <= 0.01,
            }
    return out


def _f(x: Any) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def poly_win_price(q: dict[str, Any]) -> float | None:
    if q.get("yes_won"):
        return 1.0
    return q.get("bid")


def poly_lose_price(q: dict[str, Any]) -> float | None:
    if q.get("yes_lost"):
        return 0.0
    return q.get("ask")


# ------------------------------------------------------------------ state

def load_state() -> dict[str, Any]:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"baseline": {}, "first_seen_win": {}, "bought": {}, "dumped": [], "recycled": [],
            "spent": 0.0}


def save_state(s: dict[str, Any]) -> None:
    STATE.write_text(json.dumps(s, indent=1))


# ------------------------------------------------------------------ SUSQ

def order(api: SusqAPI, tid: str, ex: str, action: str, qty: int, price: float, live: bool,
          label: str) -> bool:
    price = round(min(max(price, 0.001), 0.999), 3)
    line = f"{action.upper()} {qty:,} YES @ {price:.3f} [{ex}] {label}"
    if not live:
        log("DRY  " + line)
        return True
    try:
        res = api.place_order(exchange_id=ex, side="yes", action=action, quantity=qty, price=price,
                              tournament_id=tid, idempotency_key="night-" + secrets.token_urlsafe(18))
        log(f"SENT {line} -> traded={res.get('quantityTraded')} open={res.get('open')}")
        return True
    except SusqAPIError as exc:
        log(f"FAIL {line} -> {exc} (not retried)")
        return False


def positions_by_exchange(api: SusqAPI, slug: str) -> dict[str, int]:
    out = {}
    for p in api.tournament_positions(slug):
        try:
            out[str(p.get("exchangeId"))] = int(float(p.get("quantity") or 0))
        except (TypeError, ValueError):
            pass
    return out


def cash(api: SusqAPI, slug: str) -> float:
    try:
        return float(api.tournament(slug).get("myBalance") or 0)
    except (SusqAPIError, TypeError, ValueError):
        return 0.0


# ------------------------------------------------------------------ loop

def cycle(api: SusqAPI, tour: dict[str, Any], rows: list[dict[str, str]], st: dict[str, Any],
          a: argparse.Namespace) -> None:
    tid, slug = str(tour["id"]), tour["slug"]
    quotes = poly_quotes([r["poly_market_id"] for r in rows])
    if not quotes:
        return
    t = now().timestamp()

    # Baseline = pre-results price: the 2026-10-29 snapshot in the map file, else first sighting.
    for r in rows:
        q = quotes.get(r["poly_market_id"])
        key = f"{r['race']}|{r['party']}"
        if key in st["baseline"]:
            continue
        snap = _f(r.get("poly_yes_2026_10_29"))
        if snap is not None:
            st["baseline"][key] = snap
        elif q and q.get("yes") is not None and not q["closed"]:
            st["baseline"][key] = q["yes"]

    active = now() >= a.start_dt
    held = positions_by_exchange(api, slug)
    free = cash(api, slug)
    n_buy = n_dump = n_cyc = 0

    for r in rows:
        key = f"{r['race']}|{r['party']}"
        q = quotes.get(r["poly_market_id"])
        ex = r["susq_exchange"]
        if not q:
            continue
        base = st["baseline"].get(key)
        win_px = poly_win_price(q)
        lose_px = poly_lose_price(q)

        # --- BUY confirmed winners
        if (active and key not in st["bought"] and base is not None and base < a.baseline_max
                and win_px is not None and win_px >= a.win_bid
                and (q.get("yes_won") or (q.get("ask") or 1) - win_px <= a.max_poly_spread)):
            first = st["first_seen_win"].setdefault(key, t)
            if t - first >= a.confirm_secs or q.get("yes_won"):
                book = api.orderbook(ex, depth=50, tournament_id=tid)
                cap = min(a.max_buy, win_px - a.min_gap)
                budget = min(a.per_race, a.max_total - st["spent"], free - a.cash_floor)
                if budget >= 100:
                    n, cost, worst = walk(_levels(book, "asks"), budget=budget, limit=cap)
                    if n > 0 and order(api, tid, ex, "buy", n, worst, a.live,
                                       f"WIN {r['party']} {r['race']} poly={win_px:.3f} avg={cost / n:.3f} edge~{n - cost:,.0f}"):
                        st["bought"][key] = {"ex": ex, "qty": n, "cost": round(cost, 2), "t": t}
                        st["spent"] += cost
                        free -= cost
                        n_buy += 1
        elif key in st["first_seen_win"] and key not in st["bought"]:
            st["first_seen_win"].pop(key, None)  # signal faded; restart the confirmation clock

        # --- DUMP held losers before SUSQ reprices
        qty = held.get(ex, 0)
        if (active and qty > 0 and key not in st["dumped"] and base is not None and base > a.lose_bid
                and lose_px is not None and lose_px <= a.lose_bid):
            book = api.orderbook(ex, depth=50, tournament_id=tid)
            n, proceeds, worst = walk(_levels(book, "bids"), shares=qty, limit=a.min_dump_bid, buying=False)
            if n > 0 and order(api, tid, ex, "sell", n, worst, a.live,
                               f"LOSE {r['party']} {r['race']} poly={lose_px:.3f} ~{proceeds:,.0f}"):
                st["dumped"].append(key)
                n_dump += 1

        # --- RECYCLE our own snipes once SUSQ has caught up
        if key in st["bought"] and key not in st["recycled"] and qty > 0:
            book = api.orderbook(ex, depth=20, tournament_id=tid)
            bids = _levels(book, "bids")
            if bids and bids[0][0] >= a.recycle_bid:
                n, proceeds, worst = walk(bids, shares=min(qty, st["bought"][key]["qty"]),
                                          limit=a.recycle_bid, buying=False)
                if n > 0 and order(api, tid, ex, "sell", n, worst, a.live,
                                   f"CYCLE {r['party']} {r['race']} ~{proceeds:,.0f}"):
                    st["recycled"].append(key)
                    st["spent"] = max(0.0, st["spent"] - proceeds)
                    n_cyc += 1

    save_state(st)
    if n_buy or n_dump or n_cyc or int(t) % 300 < a.interval:
        log(f"cycle: active={active} cash={free:,.0f} spent={st['spent']:,.0f} "
            f"buys={n_buy} dumps={n_dump} recycles={n_cyc} tracked={len(st['baseline'])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--once", action="store_true", help="one dry pass with a report, then exit")
    ap.add_argument("--start", default="2026-11-03T23:00:00Z",
                    help="UTC time trading may begin (first polls close ~23:00Z = 04:30 IST)")
    ap.add_argument("--stop", default="2026-11-04T16:45:00Z", help="UTC stop (settlement is 17:00Z)")
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--win-bid", type=float, default=0.96)
    ap.add_argument("--max-poly-spread", type=float, default=0.03,
                    help="ignore Polymarket spikes with a wide bid/ask (thin books)")
    ap.add_argument("--confirm-secs", type=int, default=90)
    ap.add_argument("--baseline-max", type=float, default=0.90)
    ap.add_argument("--max-buy", type=float, default=0.93)
    ap.add_argument("--min-gap", type=float, default=0.04)
    ap.add_argument("--per-race", type=float, default=2500)
    ap.add_argument("--max-total", type=float, default=40000, help="cap on net snipe spend")
    ap.add_argument("--cash-floor", type=float, default=200)
    ap.add_argument("--lose-bid", type=float, default=0.03)
    ap.add_argument("--min-dump-bid", type=float, default=0.02)
    ap.add_argument("--recycle-bid", type=float, default=0.985)
    a = ap.parse_args()
    a.start_dt = datetime.fromisoformat(a.start.replace("Z", "+00:00"))
    stop_dt = datetime.fromisoformat(a.stop.replace("Z", "+00:00"))

    rows = load_map()
    api = SusqAPI()
    tour = discover_midterm_tournament(api)
    log(f"tracking {len(rows)} contracts | live={a.live} | start={a.start} stop={a.stop}")

    if a.once:
        quotes = poly_quotes([r["poly_market_id"] for r in rows])
        held = positions_by_exchange(api, tour["slug"])
        log(f"polymarket quotes: {len(quotes)}/{len(rows)}   SUSQ cash: {cash(api, tour['slug']):,.0f}")
        for r in rows:
            q = quotes.get(r["poly_market_id"], {})
            pr = api.price(r["susq_exchange"], tournament_id=tour["id"]) if held.get(r["susq_exchange"]) else {}
            if held.get(r["susq_exchange"]):
                log(f"held {held[r['susq_exchange']]:>7,}  {r['party'][:3]} {r['race']:24s} "
                    f"poly bid/ask {q.get('bid')}/{q.get('ask')}  susq bid/ask {pr.get('bestBid')}/{pr.get('bestAsk')}")
        missing = [r["race"] + " " + r["party"][:3] for r in rows if r["poly_market_id"] not in quotes]
        if missing:
            log(f"no polymarket quote for: {', '.join(missing)}")
        return 0

    st = load_state()
    while now() < stop_dt:
        if STOP_FILE.exists():
            log("STOP file found, exiting")
            break
        try:
            cycle(api, tour, rows, st, a)
        except SusqAPIError as exc:
            log(f"SUSQ error: {exc}")
        except Exception as exc:  # keep running through surprises; they get logged
            log(f"unexpected: {type(exc).__name__}: {exc}")
        time.sleep(a.interval)
    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
