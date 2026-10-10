from __future__ import annotations

import argparse
import csv
from pathlib import Path

from models.scoring import Candidate, rank_candidates

def load_candidates(path: Path) -> list[Candidate]:
    candidates = []
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            candidates.append(Candidate(
                market=row['market'],
                side=row['side'],
                model_probability=float(row['model_probability']),
                executable_price=float(row['executable_price']),
                liquidity=float(row.get('liquidity', 0) or 0),
                confidence=float(row.get('confidence', 0.5) or 0.5),
                correlation_penalty=float(row.get('correlation_penalty', 0) or 0),
            ))
    return candidates

def main() -> None:
    parser = argparse.ArgumentParser(description='Rank prediction-market candidates.')
    parser.add_argument('--input', default='data/watchlist.csv')
    args = parser.parse_args()
    candidates = rank_candidates(load_candidates(Path(args.input)))
    print('RANK  MARKET                              SIDE  PRICE  MODEL  EDGE    SCORE')
    print('-' * 82)
    for i, c in enumerate(candidates, start=1):
        print(f'{i:>4}  {c.market[:34]:34} {c.side:>4}  {c.executable_price:5.1%}  {c.model_probability:5.1%}  {c.edge:+6.1%}  {c.score:+7.4f}')

if __name__ == '__main__':
    main()
