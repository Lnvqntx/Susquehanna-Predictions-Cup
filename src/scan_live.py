from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.susq_api import SusqAPI, SusqAPIError


def discover_midterm_tournament(api: SusqAPI) -> dict:
    explicit_slug = os.getenv("SUSQ_TOURNAMENT_SLUG")
    tournaments = api.list_tournaments(status="active", limit=100).get("data", [])

    if explicit_slug:
        for tournament in tournaments:
            if tournament.get("slug") == explicit_slug:
                return tournament
        return api.tournament(explicit_slug)

    candidates = [
        t for t in tournaments
        if "midterm" in (t.get("name") or "").lower()
        or "midterm" in (t.get("slug") or "").lower()
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        names = ", ".join(t.get("name", "<unnamed>") for t in tournaments)
        raise SusqAPIError(
            "Could not identify Midterm Elections tournament automatically. "
            f"Active tournaments: {names or '<none>'}"
        )

    names = ", ".join(t.get("name", "<unnamed>") for t in candidates)
    raise SusqAPIError(
        "Multiple Midterm-like tournaments found. "
        f"Set SUSQ_TOURNAMENT_SLUG in .env. Candidates: {names}"
    )


def build_rows(markets: list[dict], quotes: list[dict]) -> list[dict]:
    by_exchange = {str(q["exchangeId"]): q for q in quotes}
    rows: list[dict] = []

    for market in markets:
        exchanges = market.get("exchanges", [])
        for exchange in exchanges:
            q = by_exchange.get(str(exchange["id"]), {})
            latest = q.get("latestPrice")
            bid = q.get("bestBid")
            ask = q.get("bestAsk")
            buy_no = (1.0 - bid) if bid is not None else None

            row = {
                "market_id": str(market["id"]),
                "title": market["title"],
                "status": market.get("status"),
                "categories": "|".join(market.get("categories", [])),
                "exchange_id": str(exchange["id"]),
                "option": exchange.get("option"),
                "latest_price": latest,
                "buy_yes": ask,
                "best_bid_yes": bid,
                "buy_no": buy_no,
                "spread": q.get("spread"),
                "initial_price": exchange.get("initialPrice"),
                "settlement_date": market.get("settlementDate"),
            }
            if latest is not None and row["initial_price"] is not None:
                row["move_from_initial"] = latest - row["initial_price"]
            else:
                row["move_from_initial"] = None
            rows.append(row)

    return rows


def research_score(row: dict) -> float:
    """Priority only; NOT an edge estimate.

    Competitive prices and larger recent repricing get a higher research score.
    This tells us what to investigate, not what to buy.
    """
    p = row.get("latest_price")
    move = row.get("move_from_initial") or 0.0
    if p is None:
        return -1.0
    uncertainty = 1.0 - min(1.0, abs(p - 0.5) / 0.5)
    repricing = min(1.0, abs(move) / 0.20)
    spread = row.get("spread")
    liquidity_penalty = 0.0 if spread is None else min(1.0, spread / 0.03)
    return 0.65 * uncertainty + 0.35 * repricing - 0.15 * liquidity_penalty


def main() -> int:
    parser = argparse.ArgumentParser(description="Read the Midterm Elections tournament live market board.")
    parser.add_argument("--limit-markets", type=int, default=100)
    parser.add_argument("--out", default="data/live_scan.json")
    parser.add_argument("--csv", default="data/market_board.csv")
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    api = SusqAPI()

    try:
        tournament = discover_midterm_tournament(api)
        slug = tournament["slug"]
        tournament_id = tournament["id"]
        markets = api.list_all_tournament_markets(slug, status="open")
        if args.limit_markets > 0:
            markets = markets[:args.limit_markets]

        exchange_to_market: dict[str, dict] = {}
        for market in markets:
            for exchange in market.get("exchanges", []):
                exchange_to_market[str(exchange["id"])] = {
                    "market_id": str(market["id"]),
                    "title": market["title"],
                    "option": exchange.get("option"),
                }

        quotes = api.bulk_prices(list(exchange_to_market), tournament_id=tournament_id)
        rows = build_rows(markets, quotes)

        output = {
            "tournament": {
                "id": tournament_id,
                "slug": slug,
                "name": tournament.get("name"),
                "myBalance": tournament.get("myBalance"),
                "marketCount": tournament.get("marketCount"),
            },
            "markets_discovered": len(markets),
            "exchanges_quoted": len(quotes),
            "quotes": rows,
        }
        Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

        if rows:
            with Path(args.csv).open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["research_score"])
                writer.writeheader()
                for row in rows:
                    row = dict(row)
                    row["research_score"] = round(research_score(row), 6)
                    writer.writerow(row)

            ranked = sorted(rows, key=research_score, reverse=True)[: max(1, args.top)]
            print("\n🔎 RESEARCH QUEUE (priority only — not trade recommendations)")
            for i, row in enumerate(ranked, 1):
                print(
                    f"{i:2}. {row['market_id']:>4} | {row['title']} | "
                    f"{row['option']} | latest {row['latest_price']} | "
                    f"buyYES {row['buy_yes']} | buyNO {row['buy_no']} | "
                    f"priority {research_score(row):.3f}"
                )
    except SusqAPIError as exc:
        print(f"API error: {exc}")
        return 2

    print(f"\n✅ Tournament: {slug}")
    print(f"✅ Open markets scanned: {len(markets)}")
    print(f"✅ Exchange quotes fetched: {len(quotes)}")
    print(f"✅ JSON snapshot: {args.out}")
    print(f"✅ CSV board: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
