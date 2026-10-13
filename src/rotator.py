from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.autopilot import party_from_title, race_key
from src.pollingforecast import PollingForecastError, fetch_forecasts, party_probability
from src.scan_live import build_rows, discover_midterm_tournament
from src.susq_api import SusqAPI, SusqAPIError


@dataclass(frozen=True)
class PositionView:
    exchange_id: str
    market_id: str
    title: str
    side: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    model_probability: float | None
    executable_exit_price: float | None
    hold_return: float | None


@dataclass(frozen=True)
class Opportunity:
    exchange_id: str
    market_id: str
    title: str
    side: str
    model_probability: float
    executable_buy_price: float
    edge: float
    expected_return: float
    spread: float | None
    forecast_asof: str | None


@dataclass(frozen=True)
class RotationPlan:
    sell_exchange_id: str
    sell_title: str
    sell_side: str
    sell_quantity: int
    sell_price: float
    sell_proceeds: float
    old_hold_return: float
    buy_exchange_id: str
    buy_title: str
    buy_side: str
    buy_price: float
    buy_quantity: int
    new_expected_return: float
    improvement: float


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _position_side(position: dict[str, Any]) -> str:
    side = str(position.get("option") or position.get("side") or "YES").upper()
    return "NO" if side == "NO" else "YES"


def _sell_price(side: str, quote: dict[str, Any]) -> float | None:
    bid = quote.get("bestBid")
    ask = quote.get("bestAsk")
    try:
        if side == "YES":
            return round(float(bid), 3) if bid is not None else None
        return round(1.0 - float(ask), 3) if ask is not None else None
    except (TypeError, ValueError):
        return None


def _buy_price(side: str, row: dict[str, Any]) -> float | None:
    raw = row.get("buy_yes") if side == "YES" else row.get("buy_no")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _side_probability(party_probability_value: float, side: str) -> float:
    return party_probability_value if side == "YES" else 1.0 - party_probability_value


def _expected_return(probability: float, price: float) -> float | None:
    if price <= 0.0:
        return None
    return probability / price - 1.0


def load_positions(
    positions: list[dict[str, Any]],
    forecasts: dict[str, dict[str, Any]],
    quotes: dict[str, dict[str, Any]],
) -> list[PositionView]:
    out: list[PositionView] = []

    for p in positions:
        quantity = int(_number(p.get("quantity")))
        if quantity <= 0:
            continue

        title = str(p.get("marketTitle") or "")
        parsed = race_key(title)
        party = party_from_title(title)
        exchange_id = str(p.get("exchangeId") or "")
        if not parsed or not party or not exchange_id:
            continue

        _, forecast_key, _ = parsed
        forecast = forecasts.get(forecast_key)
        model_p = None
        if forecast:
            raw_p = party_probability(forecast, party)
            model_p = _side_probability(raw_p, _position_side(p))

        side = _position_side(p)
        sell_price = _sell_price(side, quotes.get(exchange_id, {}))
        hold_return = (
            _expected_return(model_p, sell_price)
            if model_p is not None and sell_price is not None
            else None
        )

        out.append(
            PositionView(
                exchange_id=exchange_id,
                market_id=str(p.get("marketId") or ""),
                title=title,
                side=side,
                quantity=quantity,
                avg_cost=_number(p.get("avgCost")),
                current_price=_number(p.get("currentPrice")),
                market_value=_number(p.get("marketValue")),
                cost_basis=_number(p.get("costBasis")),
                model_probability=model_p,
                executable_exit_price=sell_price,
                hold_return=hold_return,
            )
        )

    return out


def build_opportunities(
    markets: list[dict[str, Any]],
    quotes: list[dict[str, Any]],
    forecasts: dict[str, dict[str, Any]],
    occupied_exchanges: set[str],
    occupied_markets: set[str],
    min_edge: float = 0.05,
    max_spread: float = 0.02,
    occupied_races: set[tuple[str, str]] | None = None,
) -> list[Opportunity]:
    rows = build_rows(markets, quotes)
    occupied_races = occupied_races or set()
    out: list[Opportunity] = []

    for row in rows:
        exchange_id = str(row.get("exchange_id") or "")
        market_id = str(row.get("market_id") or "")
        if (
            not exchange_id
            or exchange_id in occupied_exchanges
            or market_id in occupied_markets
        ):
            continue

        title = str(row.get("title") or "")
        party = party_from_title(title)
        parsed = race_key(title)
        if parsed and (parsed[0], parsed[1]) in occupied_races:
            continue
        if not party or not parsed:
            continue

        _, forecast_key, _ = parsed
        forecast = forecasts.get(forecast_key)
        if not forecast:
            continue

        spread = row.get("spread")
        try:
            spread_value = float(spread) if spread is not None else None
        except (TypeError, ValueError):
            spread_value = None

        if spread_value is not None and spread_value > max_spread:
            continue

        raw_p = party_probability(forecast, party)
        for side in ("YES", "NO"):
            price = _buy_price(side, row)
            if price is None or not 0.005 <= price <= 0.995:
                continue

            p = _side_probability(raw_p, side)
            edge = p - price
            expected_return = _expected_return(p, price)
            if expected_return is None or edge < min_edge:
                continue

            out.append(
                Opportunity(
                    exchange_id=exchange_id,
                    market_id=str(row.get("market_id") or ""),
                    title=title,
                    side=side,
                    model_probability=p,
                    executable_buy_price=price,
                    edge=edge,
                    expected_return=expected_return,
                    spread=spread_value,
                    forecast_asof=forecast.get("asOf"),
                )
            )

    return sorted(out, key=lambda x: (x.expected_return, x.edge), reverse=True)


def make_rotation_plan(
    positions: list[PositionView],
    opportunities: list[Opportunity],
    min_improvement: float,
    max_sell_quantity: int | None = None,
) -> RotationPlan | None:
    eligible = [
        p
        for p in positions
        if p.hold_return is not None
        and p.executable_exit_price is not None
        and p.executable_exit_price > 0
        and p.quantity > 0
    ]
    if not eligible or not opportunities:
        return None

    weakest = min(eligible, key=lambda p: p.hold_return)

    # A candidate must not already exist anywhere in the current portfolio.
    # This is deliberately enforced again here (in addition to scan-time
    # filtering) so a malformed/stale candidate list can never create a
    # same-exchange or same-market rotation.
    occupied_exchanges = {p.exchange_id for p in positions}
    occupied_markets = {p.market_id for p in positions if p.market_id}
    available = [
        o
        for o in opportunities
        if o.exchange_id not in occupied_exchanges
        and (not o.market_id or o.market_id not in occupied_markets)
    ]
    if not available:
        return None

    best = available[0]
    improvement = best.expected_return - weakest.hold_return
    if improvement < min_improvement:
        return None

    sell_price = float(weakest.executable_exit_price)
    sell_qty = weakest.quantity
    if max_sell_quantity is not None:
        sell_qty = min(sell_qty, max_sell_quantity)
    proceeds = sell_qty * sell_price
    buy_qty = math.floor(proceeds / best.executable_buy_price)
    if sell_qty <= 0 or buy_qty <= 0:
        return None

    return RotationPlan(
        sell_exchange_id=weakest.exchange_id,
        sell_title=weakest.title,
        sell_side=weakest.side,
        sell_quantity=sell_qty,
        sell_price=sell_price,
        sell_proceeds=proceeds,
        old_hold_return=weakest.hold_return,
        buy_exchange_id=best.exchange_id,
        buy_title=best.title,
        buy_side=best.side,
        buy_price=best.executable_buy_price,
        buy_quantity=buy_qty,
        new_expected_return=best.expected_return,
        improvement=improvement,
    )


def run_scan(
    api: SusqAPI,
    min_edge: float,
    max_spread: float,
    min_improvement: float,
) -> dict[str, Any]:
    tournament = discover_midterm_tournament(api)
    markets = api.list_all_tournament_markets(tournament["slug"], status="open")

    exchange_ids = [
        str(ex["id"])
        for market in markets
        for ex in market.get("exchanges", [])
    ]
    quote_rows = api.bulk_prices(exchange_ids, tournament_id=tournament["id"])
    quote_map = {str(q["exchangeId"]): q for q in quote_rows}

    positions_raw = api.tournament_positions(tournament["slug"])
    open_orders = api.list_orders(
        status="open",
        tournament_id=str(tournament["id"]),
        limit=200,
    )

    occupied = {
        str(p.get("exchangeId"))
        for p in positions_raw
        if _number(p.get("quantity")) != 0
    }
    occupied.update(
        str(o.get("exchangeId"))
        for o in open_orders
        if o.get("exchangeId") is not None
    )
    occupied_markets = {
        str(p.get("marketId"))
        for p in positions_raw
        if p.get("marketId") is not None and _number(p.get("quantity")) != 0
    }
    occupied_races: set[tuple[str, str]] = set()
    for p in positions_raw:
        if _number(p.get("quantity")) == 0:
            continue
        parsed = race_key(str(p.get("marketTitle") or ""))
        if parsed:
            occupied_races.add((parsed[0], parsed[1]))

    forecasts = fetch_forecasts()
    positions = load_positions(positions_raw, forecasts, quote_map)
    opportunities = build_opportunities(
        markets,
        quote_rows,
        forecasts,
        occupied,
        occupied_markets,
        min_edge=min_edge,
        max_spread=max_spread,
        occupied_races=occupied_races,
    )
    plan = make_rotation_plan(
        positions,
        opportunities,
        min_improvement=min_improvement,
    )

    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "tournament": tournament,
        "cash": _number(tournament.get("myBalance")),
        "positions": positions,
        "open_orders": len(open_orders),
        "opportunities": opportunities,
        "plan": plan,
    }


def print_report(report: dict[str, Any], top: int) -> None:
    print(f"ROTATOR | {report['observed_at']}")
    print(
        f"cash={report['cash']:,.2f} | analyzed_positions={len(report['positions'])} | "
        f"open_orders={report['open_orders']}"
    )

    print("\nCURRENT POSITIONS")
    ranked_positions = sorted(
        report["positions"],
        key=lambda p: p.hold_return if p.hold_return is not None else float("-inf"),
    )
    for p in ranked_positions:
        hold = "NA" if p.hold_return is None else f"{p.hold_return:+.1%}"
        prob = "NA" if p.model_probability is None else f"{p.model_probability:.1%}"
        exit_px = "NA" if p.executable_exit_price is None else f"{p.executable_exit_price:.3f}"
        print(
            f"- {p.title} | {p.side} | qty={p.quantity} | "
            f"model={prob} | sell={exit_px} | hold_return={hold}"
        )

    print("\nNEW OPPORTUNITIES")
    for i, o in enumerate(report["opportunities"][:top], 1):
        print(
            f"{i:2}. {o.title} | {o.side} | buy={o.executable_buy_price:.3f} | "
            f"model={o.model_probability:.1%} | edge={o.edge:+.1%} | "
            f"return={o.expected_return:+.1%}"
        )

    plan = report["plan"]
    print("\nROTATION")
    if plan is None:
        print("NO ROTATION: no replacement clears the configured improvement threshold.")
        return

    print(
        f"SELL {plan.sell_quantity} {plan.sell_side} | {plan.sell_title} "
        f"@ {plan.sell_price:.3f} -> ~{plan.sell_proceeds:,.2f} SUSQies"
    )
    print(
        f"BUY  {plan.buy_quantity} {plan.buy_side} | {plan.buy_title} "
        f"@ {plan.buy_price:.3f}"
    )
    print(
        f"expected-return improvement={plan.improvement:+.1%} "
        f"({plan.old_hold_return:+.1%} -> {plan.new_expected_return:+.1%})"
    )


def _fresh_tournament_state(api: SusqAPI) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    tournament = discover_midterm_tournament(api)
    positions = api.tournament_positions(tournament["slug"])
    orders = api.list_orders(
        status="open",
        tournament_id=str(tournament["id"]),
        limit=200,
    )
    return tournament, positions, orders


def _position_for_exchange(positions: list[dict[str, Any]], exchange_id: str) -> dict[str, Any] | None:
    for position in positions:
        if str(position.get("exchangeId")) == str(exchange_id) and _number(position.get("quantity")) > 0:
            return position
    return None


def _account_cash(api: SusqAPI, tournament_slug: str) -> float:
    tournament = api.tournament(tournament_slug)
    return _number(tournament.get("myBalance"))


def _reconcile_sell(
    api: SusqAPI,
    tournament_slug: str,
    exchange_id: str,
    starting_quantity: int,
    starting_cash: float,
    timeout_seconds: float = 20.0,
) -> tuple[int, float]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        positions = api.tournament_positions(tournament_slug)
        remaining_position = _position_for_exchange(positions, exchange_id)
        remaining_quantity = int(_number(remaining_position.get("quantity"))) if remaining_position else 0
        cash = _account_cash(api, tournament_slug)
        filled = max(0, starting_quantity - remaining_quantity)
        if filled > 0 or cash > starting_cash + 1e-9:
            return filled, max(0.0, cash - starting_cash)
        time.sleep(2.0)
    positions = api.tournament_positions(tournament_slug)
    remaining_position = _position_for_exchange(positions, exchange_id)
    remaining_quantity = int(_number(remaining_position.get("quantity"))) if remaining_position else 0
    cash = _account_cash(api, tournament_slug)
    return max(0, starting_quantity - remaining_quantity), max(0.0, cash - starting_cash)


def _execute_rotation(
    api: SusqAPI,
    plan: RotationPlan,
    tournament: dict[str, Any],
    positions: list[dict[str, Any]],
    open_orders: list[dict[str, Any]],
) -> int:
    tournament_id = str(tournament["id"])
    slug = str(tournament["slug"])

    # Revalidate the exact position before submitting the sell.
    position = _position_for_exchange(positions, plan.sell_exchange_id)
    if position is None:
        print("🛑 LIVE ABORT: sell position no longer exists.")
        return 2
    current_qty = int(_number(position.get("quantity")))
    if current_qty < plan.sell_quantity:
        print(
            f"🛑 LIVE ABORT: position shrank from planned {plan.sell_quantity:,} "
            f"to {current_qty:,} contracts."
        )
        return 2

    if any(str(o.get("exchangeId")) == plan.buy_exchange_id for o in open_orders):
        print("🛑 LIVE ABORT: replacement exchange has an open order.")
        return 2

    # Re-read both legs immediately before writing anything.
    sell_quote = api.price(plan.sell_exchange_id, tournament_id=tournament_id)
    buy_quote = api.price(plan.buy_exchange_id, tournament_id=tournament_id)
    sell_px = _sell_price(plan.sell_side, sell_quote)
    if sell_px is None or sell_px <= 0:
        print("🛑 LIVE ABORT: no executable sell price.")
        return 2

    # For a YES/NO binary contract, a side-specific executable price is valid
    # on the 0.005 tick. Re-normalize before submission.
    sell_px = round(sell_px / 0.005) * 0.005
    sell_px = round(sell_px, 3)

    starting_cash = _account_cash(api, slug)
    if starting_cash < -1e-9:
        print("🛑 LIVE ABORT: invalid negative tournament cash.")
        return 2

    sell_key = "rot-sell-" + __import__("secrets").token_urlsafe(24)
    try:
        sell_result = api.place_order(
            exchange_id=plan.sell_exchange_id,
            side=plan.sell_side.lower(),
            action="sell",
            quantity=plan.sell_quantity,
            price=sell_px,
            tournament_id=tournament_id,
            idempotency_key=sell_key,
        )
    except SusqAPIError as exc:
        print(f"🛑 LIVE SELL FAILED: {exc}")
        return 2

    if not isinstance(sell_result, dict):
        print("🛑 LIVE ABORT: sell response was not a JSON object.")
        return 2

    print("\n✅ SELL SUBMITTED")
    print(f"   exchange={plan.sell_exchange_id} side={plan.sell_side} qty={plan.sell_quantity:,} limit={sell_px:.3f}")
    print(
        f"   orderId={sell_result.get('orderId')} "
        f"filled={sell_result.get('quantityTraded')} "
        f"remaining={sell_result.get('remainingQuantity')}"
    )

    filled, cash_released = _reconcile_sell(
        api,
        slug,
        plan.sell_exchange_id,
        plan.sell_quantity,
        starting_cash,
    )
    print(f"   reconciled_filled={filled:,} cash_released={cash_released:,.2f}")

    if filled <= 0 or cash_released <= 0:
        print("🛑 LIVE ABORT: sell produced no verified usable cash; BUY not submitted.")
        return 2

    # Re-read the replacement quote after the sell. Do not use the stale report
    # price to fund the buy.
    buy_quote = api.price(plan.buy_exchange_id, tournament_id=tournament_id)
    buy_yes_bid = buy_quote.get("bestBid")
    buy_yes_ask = buy_quote.get("bestAsk")
    if plan.buy_side == "YES":
        raw_buy_px = buy_yes_ask
    else:
        raw_buy_px = (1.0 - float(buy_yes_bid)) if buy_yes_bid is not None else None

    if raw_buy_px is None:
        print("🛑 LIVE ABORT: no executable replacement buy price.")
        return 2

    buy_px = round(float(raw_buy_px) / 0.005) * 0.005
    buy_px = round(buy_px, 3)
    if buy_px <= 0 or buy_px >= 1:
        print("🛑 LIVE ABORT: invalid replacement buy price.")
        return 2

    buy_qty = math.floor(cash_released / buy_px)
    if buy_qty <= 0:
        print("🛑 LIVE ABORT: released cash cannot purchase one replacement contract.")
        return 2

    # Reconcile once more immediately before the buy to ensure no one else (or
    # another local process) has occupied the exchange.
    _, latest_positions, latest_open_orders = _fresh_tournament_state(api)
    if _position_for_exchange(latest_positions, plan.buy_exchange_id) is not None:
        print("🛑 LIVE ABORT: replacement exchange became occupied before BUY.")
        return 2
    if any(str(o.get("exchangeId")) == plan.buy_exchange_id for o in latest_open_orders):
        print("🛑 LIVE ABORT: replacement exchange now has an open order.")
        return 2

    buy_key = "rot-buy-" + __import__("secrets").token_urlsafe(24)
    try:
        buy_result = api.place_order(
            exchange_id=plan.buy_exchange_id,
            side=plan.buy_side.lower(),
            action="buy",
            quantity=buy_qty,
            price=buy_px,
            tournament_id=tournament_id,
            idempotency_key=buy_key,
        )
    except SusqAPIError as exc:
        print(f"🛑 LIVE BUY FAILED: {exc}")
        return 2

    if not isinstance(buy_result, dict):
        print("🛑 LIVE ABORT: buy response was not a JSON object.")
        return 2

    print("\n✅ BUY SUBMITTED")
    print(f"   exchange={plan.buy_exchange_id} side={plan.buy_side} qty={buy_qty:,} limit={buy_px:.3f}")
    print(
        f"   orderId={buy_result.get('orderId')} "
        f"filled={buy_result.get('quantityTraded')} "
        f"remaining={buy_result.get('remainingQuantity')}"
    )
    print("\n✅ ROTATION COMPLETE: sell was reconciled before replacement buy.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Portfolio rotation analyzer. Live rotation is intentionally disabled pending dry-run validation."
    )
    parser.add_argument("--min-edge", type=float, default=0.05)
    parser.add_argument("--max-spread", type=float, default=0.02)
    parser.add_argument("--min-improvement", type=float, default=0.05)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Required with --live to authorize the exact freshly recomputed plan.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Reserved for future live rotation; currently rejected for safety.",
    )
    args = parser.parse_args()

    if args.confirm and not args.live:
        print("--confirm requires --live.")
        return 3

    api = SusqAPI()
    try:
        report = run_scan(
            api,
            min_edge=args.min_edge,
            max_spread=args.max_spread,
            min_improvement=args.min_improvement,
        )
    except (SusqAPIError, PollingForecastError, OSError, ValueError) as exc:
        print(f"ROTATOR ERROR: {exc}")
        return 2

    serializable = {
        "observed_at": report["observed_at"],
        "tournament": {
            "id": report["tournament"].get("id"),
            "slug": report["tournament"].get("slug"),
            "name": report["tournament"].get("name"),
        },
        "cash": report["cash"],
        "open_orders": report["open_orders"],
        "positions": [asdict(p) for p in report["positions"]],
        "opportunities": [asdict(o) for o in report["opportunities"]],
        "plan": asdict(report["plan"]) if report["plan"] else None,
    }

    print_report(report, top=max(1, args.top))

    if args.write:
        out = ROOT / "data" / "rotation_report.json"
        out.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")
        print(f"\nreport_written={out}")

    if args.live:
        if report["plan"] is None:
            print("\nLIVE ABORT: no qualifying rotation plan.")
            return 4
        if not args.confirm:
            print("\nDRY RUN ONLY: add --confirm together with --live to authorize this freshly computed plan.")
            return 0

        plan = report["plan"]
        print("\nLIVE ROTATION REVIEW")
        print(f"SELL {plan.sell_quantity:,} {plan.sell_side} | {plan.sell_title} @ ~{plan.sell_price:.3f}")
        print(f"BUY  replacement | {plan.buy_side} | {plan.buy_title} @ ~{plan.buy_price:.3f}")
        print(f"expected-return improvement: {plan.improvement:+.1%}")
        if input("\nType ROTATE to submit the freshly recomputed two-leg order: ").strip() != "ROTATE":
            print("Cancelled.")
            return 1

        live_tournament, live_positions, live_orders = _fresh_tournament_state(api)
        try:
            return _execute_rotation(
                api,
                plan,
                live_tournament,
                live_positions,
                live_orders,
            )
        except (SusqAPIError, OSError, ValueError) as exc:
            print(f"🛑 LIVE ROTATION ERROR: {exc}")
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
