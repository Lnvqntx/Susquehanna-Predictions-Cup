# Susquehanna Predictions Cup — Quant Research

Systematic research and trading framework for the 2026 Susquehanna Predictions Cup.

## Live portfolio
- Rhode Island Senate D: 17,751 YES @ 0.845
- New Hampshire Senate D: 9,467 YES @ 0.845
- Georgia Senate R: 6,521 NO @ 0.920
- Delaware Senate R: 5,555 NO @ 0.900
- Texas Senate D: 5,042 YES @ 0.595

## Current objective
Move from discretionary one-market research to a high-throughput, portfolio-aware scanner that can rank many markets by executable expected value.

## Scanner
Run from the repository root:
python scripts/scan_snapshot.py --input data/watchlist.csv

The scanner ranks candidates using model probability, executable price, liquidity, confidence and portfolio redundancy. It is currently snapshot-based; it does not yet submit orders automatically.

## Repository layout
```text
.
├── data/
│   ├── markets.csv
│   ├── polls.csv
│   ├── model_inputs.csv
│   ├── watchlist.csv
│   └── portfolio.csv
├── research/
├── models/
│   ├── probability.py
│   ├── poll_weighting.py
│   ├── calibration.py
│   ├── scoring.py
│   ├── orderbook.py
│   └── portfolio.py
├── scripts/
│   └── scan_snapshot.py
├── trades/
├── docs/
│   └── SCANNER.md
└── PLAN.md
```

## Status
Phase 3: five positions live. Scanner foundation is in place; next step is historical calibration and official API ingestion.
