from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scan_live import discover_midterm_tournament
from src.susq_api import SusqAPI, SusqAPIError

def parse_price(raw: str) -> float:
    p = float(raw)
    if not 0.005 <= p <= 0.995:
        raise ValueError("Limit price must be between 0.005 and 0.995.")
    units = round(p / 0.005)
    if abs(p - units * 0.005) > 1e-9:
        raise ValueError("Limit price must be on the 0.005 tick.")
    return round(p, 3)

def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded tournament limit-order client.")
    parser.add_argument("--exchange-id", required=True)
    parser.add_argument("--side", choices=["yes", "no"], required=True)
    parser.add_argument("--quantity", type=int, required=True)
    parser.add_argument("--price", type=parse_price, required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    if args.quantity <= 0:
        parser.error("--quantity must be positive")
    api = SusqAPI()
    tournament = discover_midterm_tournament(api)
    tournament_id = str(tournament["id"])
    cost = args.quantity * args.price

    print("\nTRADE REVIEW")
    print(f"  tournament: {tournament.get('name')} [{tournament_id}]")
    print(f"  exchange:   {args.exchange_id}")
    print(f"  side:       {args.side.upper()}")
    print("  action:     BUY")
    print(f"  quantity:   {args.quantity:,}")
    print(f"  limit:      {args.price:.3f}")
    print(f"  max cost:   {cost:,.2f} SUSQies")
    print(f"  reason:     {args.reason}")

    if not args.confirm:
        print("  mode:       DRY RUN")
        print("\nDry run only. Re-run with --confirm to submit.")
        return 0

    print("  mode:       LIVE")
    if input("\nType CONFIRM to submit this exact order: ").strip() != "CONFIRM":
        print("Cancelled.")
        return 1
    key = "cup-" + secrets.token_urlsafe(24)
    try:
        result = api.place_order(exchange_id=args.exchange_id, side=args.side, action="buy", quantity=args.quantity, price=args.price, tournament_id=tournament_id, idempotency_key=key)
    except SusqAPIError as exc:
        print(f"❌ Order failed: {exc}")
        return 2
    print("\n✅ Order submitted")
    print(f"  orderId:         {result.get('orderId')}")
    print(f"  open:            {result.get('open')}")
    print(f"  quantityTraded:  {result.get('quantityTraded')}")
    print(f"  remaining:       {result.get('remainingQuantity')}")
    print(f"  totalCost:       {result.get('totalCost')}")
    print(f"  canonical side:  {result.get('side')}")
    print(f"  canonical price: {result.get('price')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
