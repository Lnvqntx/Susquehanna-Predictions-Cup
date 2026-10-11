from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pollingforecast import PollingForecastError, fetch_forecasts, party_probability
from src.scan_live import build_rows, discover_midterm_tournament
from src.susq_api import SusqAPI, SusqAPIError

STATE_PATH = ROOT / "data" / "autopilot_state.json"
PORTFOLIO_PATH = ROOT / "data" / "portfolio.csv"
TRADE_LOG_PATH = ROOT / "trades" / "trade_log.csv"
STATE_ABSENT = {"orders": {}, "spent": {}}

STATE_ABBREV = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA","colorado":"CO",
    "connecticut":"CT","delaware":"DE","florida":"FL","georgia":"GA","hawaii":"HI","idaho":"ID",
    "illinois":"IL","indiana":"IN","iowa":"IA","kansas":"KS","kentucky":"KY","louisiana":"LA",
    "maine":"ME","maryland":"MD","massachusetts":"MA","michigan":"MI","minnesota":"MN","mississippi":"MS",
    "missouri":"MO","montana":"MT","nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ",
    "new mexico":"NM","new york":"NY","north carolina":"NC","north dakota":"ND","ohio":"OH","oklahoma":"OK",
    "oregon":"OR","pennsylvania":"PA","rhode island":"RI","south carolina":"SC","south dakota":"SD",
    "tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT","virginia":"VA","washington":"WA",
    "west virginia":"WV","wisconsin":"WI","wyoming":"WY","district of columbia":"DC",
}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return json.loads(json.dumps(STATE_ABSENT))
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.loads(json.dumps(STATE_ABSENT))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def race_key(title: str) -> tuple[str, str, str] | None:
    m = re.search(r"([A-Z]{2}-\d{1,2})\s+House", title)
    if m:
        return "house", m.group(1), ""
    m = re.search(r"the\s+([A-Za-z ]+)\s+Senate", title)
    if m:
        state = STATE_ABBREV.get(m.group(1).strip().lower())
        return ("senate", state, "") if state else None
    m = re.search(r"the\s+([A-Za-z ]+)\s+Governor", title)
    if m:
        state = STATE_ABBREV.get(m.group(1).strip().lower())
        return ("governor", f"G-{state}", "") if state else None
    return None


def party_from_title(title: str) -> str | None:
    t = title.lower()
    if "democratic party" in t:
        return "democratic"
    if "republican party" in t:
        return "republican"
    return None


def executable_price(row: dict[str, Any]) -> float | None:
    value = row.get("buy_yes")
    if value is None:
        return None
    return float(value)



def market_signature(title: str) -> tuple[str, str] | None:
    party = party_from_title(title)
    if not party:
        t = title.lower()
        if "republican party" in t:
            party = "republican"
        elif "democratic party" in t:
            party = "democratic"
    if not party:
        return None
    m = re.search(r"([A-Z]{2}-\\d{1,2})", title)
    if m:
        return m.group(1), party
    lower = title.lower()
    for state_name, abbr in STATE_ABBREV.items():
        if state_name in lower and ("senate" in lower or "governor" in lower):
            office = "SENATE" if "senate" in lower else "GOVERNOR"
            return f"{abbr}-{office}", party
    return None


def existing_manual_market_signatures() -> set[tuple[str, str]]:
    signatures: set[tuple[str, str]] = set()
    for path in (PORTFOLIO_PATH, TRADE_LOG_PATH):
        if not path.exists():
            continue
        try:
            import csv
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    market = (row.get("market") or "").strip()
                    signature = market_signature(market)
                    if signature:
                        signatures.add(signature)
        except OSError:
            continue
    return signatures


def choose_candidates(rows: list[dict[str, Any]], forecasts: dict[str, dict[str, Any]],
                      min_edge: float, max_spread: float, min_forecast: float = 0.05,
                      max_forecast: float = 0.95) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        party = party_from_title(row["title"])
        if not party:
            continue
        parsed = race_key(row["title"])
        if not parsed:
            continue
        _, key, _ = parsed
        forecast = forecasts.get(key)
        if not forecast:
            continue
        p = party_probability(forecast, party)
        price = executable_price(row)
        if p is None or price is None:
            continue
        if not (min_forecast <= p <= max_forecast):
            continue
        spread = float(row.get("spread") or 1.0)
        if spread > max_spread:
            continue
        edge = p - price
        if edge < min_edge:
            continue
        # Conservative score: large edge, but downweight very low external certainty.
        confidence = min(1.0, max(0.0, abs(p - 0.5) * 2.0))
        score = edge * (0.75 + 0.25 * confidence)
        candidates.append({
            **row,
            "forecast_key": key,
            "forecast_probability": p,
            "edge": edge,
            "score": score,
            "forecast_asof": forecast.get("asOf"),
            "forecast_rating": forecast.get("rating"),
        })
    return sorted(candidates, key=lambda x: x["score"], reverse=True)


def submit_candidate(api: SusqAPI, tournament: dict[str, Any], candidate: dict[str, Any],
                     max_cost: float, min_edge: float) -> dict[str, Any]:
    price = float(candidate["buy_yes"])
    quantity = int(max_cost // price)
    if quantity <= 0:
        raise ValueError("No affordable contracts at current price.")
    key = "auto-" + secrets.token_urlsafe(24)
    result = api.place_order(
        exchange_id=str(candidate["exchange_id"]),
        side="yes",
        action="buy",
        quantity=quantity,
        price=price,
        tournament_id=str(tournament["id"]),
        idempotency_key=key,
    )
    return result


def scan_once(api: SusqAPI, min_edge: float, max_spread: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tournament = discover_midterm_tournament(api)
    markets = api.list_all_tournament_markets(tournament["slug"], status="open")
    exchange_to_market = {
        str(ex["id"]): market
        for market in markets
        for ex in market.get("exchanges", [])
    }
    quotes = api.bulk_prices(list(exchange_to_market), tournament_id=tournament["id"])
    rows = build_rows(markets, quotes)
    forecasts = fetch_forecasts()
    candidates = choose_candidates(rows, forecasts, min_edge=min_edge, max_spread=max_spread)
    return tournament, candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous forecast-vs-market trader.")
    parser.add_argument("--live", action="store_true", help="Submit orders instead of only printing.")
    parser.add_argument("--loop", action="store_true", help="Repeat every --interval seconds.")
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--min-edge", type=float, default=0.10)
    parser.add_argument("--max-spread", type=float, default=0.015)
    parser.add_argument("--max-order-cost", type=float, default=3000.0)
    parser.add_argument("--max-cycle-cost", type=float, default=3000.0)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    api = SusqAPI()
    state = load_state()
    manual_signatures = existing_manual_market_signatures()

    while True:
        try:
            tournament, candidates = scan_once(api, args.min_edge, args.max_spread)
            balance = float(tournament.get("myBalance") or 0)
            print(f"\nAUTOPILOT | {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
            print(f"balance={balance:,.2f} | candidates={len(candidates)}")

            for i, c in enumerate(candidates[:args.top], 1):
                print(
                    f"{i:2}. {c['title']} | exchange={c['exchange_id']} | "
                    f"market={c['market_id']} | external={c['forecast_probability']:.1%} | "
                    f"ask={float(c['buy_yes']):.1%} | edge={c['edge']:+.1%} | "
                    f"score={c['score']:.3f}"
                )

            if args.live and candidates:
                spent = 0.0
                traded = 0
                skipped_existing = 0
                for c in candidates:
                    signature = market_signature(c["title"])
                    if signature and signature in manual_signatures:
                        skipped_existing += 1
                        continue
                    if spent >= args.max_cycle_cost:
                        break
                    exchange_id = str(c["exchange_id"])
                    if exchange_id in state["orders"]:
                        continue
                    cost_cap = min(args.max_order_cost, args.max_cycle_cost - spent, balance - spent)
                    if cost_cap <= 0:
                        break
                    try:
                        result = submit_candidate(api, tournament, c, cost_cap, args.min_edge)
                    except (SusqAPIError, ValueError) as exc:
                        print(f"❌ {c['title']}: {exc}")
                        continue
                    cost = float(result.get("totalCost") or 0)
                    order_id = str(result.get("orderId") or "")
                    state["orders"][exchange_id] = {
                        "orderId": order_id,
                        "market": c["title"],
                        "submittedPrice": c["buy_yes"],
                        "forecastProbability": c["forecast_probability"],
                        "edge": c["edge"],
                        "submittedAt": datetime.now(timezone.utc).isoformat(),
                    }
                    spent += cost
                    traded += 1
                    print(
                        f"✅ AUTO TRADE | {c['title']} | order={order_id} | "
                        f"filled={result.get('quantityTraded')} | remaining={result.get('remainingQuantity')} | "
                        f"cost={cost:.2f}"
                    )
                state["lastCycleAt"] = datetime.now(timezone.utc).isoformat()
                state["lastCycleSpent"] = spent
                state["lastCycleTrades"] = traded
                state["lastCycleSkippedExisting"] = skipped_existing
                save_state(state)
                print(f"skipped_existing={skipped_existing}")

            if not args.loop:
                return 0
            time.sleep(max(60, args.interval))
        except (SusqAPIError, PollingForecastError, OSError, ValueError) as exc:
            print(f"❌ AUTOPILOT ERROR: {exc}")
            if not args.loop:
                return 2
            time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
