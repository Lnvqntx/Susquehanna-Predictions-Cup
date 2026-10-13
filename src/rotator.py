from __future__ import annotations

import argparse
import json
import math
import sys
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
            return float(bid) if bid is not None else None
        return (1.0 - float(ask)) if ask is not None else None
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
    min_edge: float,
    max_spread: float,
) -> list[Opportunity]:
    rows = build_rows(markets, quotes)
    out: list[Opportunity] = []

    for row in rows:
        exchange_id = str(row.get("exchange_id") or "")
        if not exchange_id or exchange_id in occupied_exchanges:
            continue

        title = str(row.get("title") or "")
        party = party_from_title(title)
        parsed = race_key(title)
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
    available = [o for o in opportunities if o.exchange_id != weakest.exchange_id]
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

    forecasts = fetch_forecasts()
    positions = load_positions(positions_raw, forecasts, quote_map)
    opportunities = build_opportunities(
        markets,
        quote_rows,
        forecasts,
        occupied,
        min_edge=min_edge,
        max_spread=max_spread,
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
        f"cash={report['cash']:,.2f} | positions={len(report['positions'])} | "
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Portfolio rotation analyzer. Live rotation is intentionally disabled pending dry-run validation."
    )
    parser.add_argument("--min-edge", type=float, default=0.05)
    parser.add_argument("--max-spread", type=float, default=0.02)
    parser.add_argument("--min-improvement", type=float, default=0.05)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Reserved for future live rotation; currently rejected for safety.",
    )
    args = parser.parse_args()

    if args.live:
        print("LIVE ROTATION DISABLED: run dry-run and regression tests first.")
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
