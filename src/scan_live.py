from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.susq_api import SusqAPI, SusqAPIError


def discover_midterm_tournament(api: SusqAPI) -> dict:
    explicit_slug = os.getenv('SUSQ_TOURNAMENT_SLUG')
    tournaments = api.list_tournaments(status='active', limit=100).get('data', [])
    if explicit_slug:
        for tournament in tournaments:
            if tournament.get('slug') == explicit_slug:
                return tournament
        return api.tournament(explicit_slug)
    candidates = [t for t in tournaments if 'midterm' in (t.get('name') or '').lower() or 'midterm' in (t.get('slug') or '').lower()]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        names = ', '.join(t.get('name', '<unnamed>') for t in tournaments)
        raise SusqAPIError(f'Could not identify Midterm Elections tournament automatically. Active tournaments: {names or "<none>"}')
    names = ', '.join(t.get('name', '<unnamed>') for t in candidates)
    raise SusqAPIError(f'Multiple Midterm-like tournaments found. Set SUSQ_TOURNAMENT_SLUG in .env. Candidates: {names}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Read the Midterm Elections tournament and print live market quotes.')
    parser.add_argument('--limit-markets', type=int, default=100)
    parser.add_argument('--out', default='data/live_scan.json')
    args = parser.parse_args()
    api = SusqAPI()
    try:
        tournament = discover_midterm_tournament(api)
        slug = tournament['slug']
        tournament_id = tournament['id']
        markets = api.list_all_tournament_markets(slug, status='open')[:max(1, args.limit_markets)]
        exchange_to_market: dict[str, dict] = {}
        for market in markets:
            for exchange in market.get('exchanges', []):
                exchange_to_market[str(exchange['id'])] = {'market_id': str(market['id']), 'title': market['title'], 'option': exchange.get('option')}
        quotes = api.bulk_prices(list(exchange_to_market), tournament_id=tournament_id)
        output = {'tournament': {'id': tournament_id, 'slug': slug, 'name': tournament.get('name'), 'myBalance': tournament.get('myBalance'), 'marketCount': tournament.get('marketCount')}, 'markets_discovered': len(markets), 'exchanges_quoted': len(quotes), 'quotes': [{**exchange_to_market.get(str(q['exchangeId']), {}), **q} for q in quotes]}
        Path(args.out).write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    except SusqAPIError as exc:
        print(f'API error: {exc}')
        return 2
    print(f'✅ Tournament: {slug}')
    print(f'✅ Open markets discovered: {len(markets)}')
    print(f'✅ Exchange quotes fetched: {len(quotes)}')
    print(f'✅ Snapshot written to {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())