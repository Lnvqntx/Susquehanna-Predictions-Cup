from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.susq_api import SusqAPI, SusqAPIError
from src.scan_live import discover_midterm_tournament


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect one tournament market and its live orderbooks.")
    parser.add_argument("--market-id", required=True)
    parser.add_argument("--depth", type=int, default=10)
    args = parser.parse_args()

    api = SusqAPI()
    try:
        tournament = discover_midterm_tournament(api)
        markets = api.list_all_tournament_markets(tournament["slug"], status="open")
        market = next((m for m in markets if str(m.get("id")) == args.market_id), None)
        if market is None:
            raise SusqAPIError(f"Market {args.market_id} not found in the open tournament board.")

        print(f"TOURNAMENT: {tournament.get('name')} [{tournament.get('id')}]")
        print(f"MARKET: {market['id']} | {market['title']}")
        print(f"STATUS: {market.get('status')} | SETTLEMENT: {market.get('settlementDate')}")

        for exchange in market.get("exchanges", []):
            exchange_id = str(exchange["id"])
            print(f"\nEXCHANGE {exchange_id} | option={exchange.get('option')} | latest={exchange.get('latestPrice')} | initial={exchange.get('initialPrice')}")
            price = api.price(exchange_id, tournament_id=tournament["id"])
            print(
                f"PRICE: latest={price.get('latestPrice')} "
                f"bid={price.get('bestBid')} ask={price.get('bestAsk')} spread={price.get('spread')}"
            )
            book = api.orderbook(exchange_id, depth=max(1, min(200, args.depth)), tournament_id=tournament["id"])
            print(f"ORDERBOOK: bestBid={book.get('bestBid')} bestAsk={book.get('bestAsk')} spread={book.get('spread')}")
            print("ASKS (best first):")
            for level in book.get("asks", [])[:args.depth]:
                print(f"  {level}")
            print("BIDS (best first):")
            for level in book.get("bids", [])[:args.depth]:
                print(f"  {level}")

    except SusqAPIError as exc:
        print(f"API error: {exc}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
