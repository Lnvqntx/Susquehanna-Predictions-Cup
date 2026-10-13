from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scan_live import discover_midterm_tournament
from src.susq_api import SusqAPI, SusqAPIError


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a concise live tournament portfolio snapshot.")
    parser.add_argument("--write", action="store_true", help="Also write data/latest_portfolio_snapshot.json.")
    args = parser.parse_args()

    api = SusqAPI()
    tournament = discover_midterm_tournament(api)
    account = api.account()
    positions = api.tournament_positions(tournament["slug"])
    orders = api.list_orders(
        status="open",
        tournament_id=str(tournament["id"]),
        limit=200,
    )

    market_value = sum(float(p.get("marketValue") or 0) for p in positions)
    cost_basis = sum(float(p.get("costBasis") or 0) for p in positions)
    unrealized = sum(float(p.get("unrealizedPnL") or 0) for p in positions)

    open_notional = 0.0
    for order in orders:
        quantity = float(order.get("quantity") or 0)
        price = float(
            order.get("priceLimit")
            if order.get("priceLimit") is not None
            else order.get("price")
            or 0
        )
        open_notional += max(quantity, 0.0) * max(price, 0.0)

    snapshot = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "tournament": tournament.get("slug"),
        "cash": float(account.get("balance") or 0),
        "positions": len(positions),
        "market_value": round(market_value, 2),
        "cost_basis": round(cost_basis, 2),
        "unrealized_pnl": round(unrealized, 2),
        "open_orders": len(orders),
        "open_notional": round(open_notional, 2),
    }

    for key, value in snapshot.items():
        print(f"{key}={value}")

    if args.write:
        out = Path("data/latest_portfolio_snapshot.json")
        out.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        print(f"snapshot_written={out}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SusqAPIError as exc:
        print(f"PORTFOLIO SNAPSHOT ERROR: {exc}")
        raise SystemExit(1)
