# Susquehanna Predictions Cup — Quant Research

Systematic research and trading framework for the 2026 Susquehanna Predictions Cup.

## Live portfolio

- Michigan Senate D: **7,812 YES @ 0.640** — **Trade #6 LIVE**
- Rhode Island Senate D: 17,751 YES @ 0.845
- New Hampshire Senate D: 9,467 YES @ 0.845
- Georgia Senate R: 6,521 NO @ 0.920
- Delaware Senate R: 5,555 NO @ 0.900
- Texas Senate D: 5,042 YES @ 0.595

## Current objective
Move from discretionary one-market research to a high-throughput, portfolio-aware scanner that can rank many markets by executable expected value.

## Autonomous trading

The v1 autonomous engine is in `src/autopilot.py`. It matches live Susquehanna markets to Polling Forecast's public 2026 House/Senate/Governor forecast API, ranks executable edges, and can place guarded limit orders.

One scan (read-only):
`python src/autopilot.py`

One live cycle:
`python src/autopilot.py --live`

Continuous live mode:
`python src/autopilot.py --live --loop --interval 300`

Default guardrails are 10 percentage-point minimum edge, 1.5 percentage-point max spread, 3,000 SUSQies maximum per order and 3,000 SUSQies maximum per cycle. The probability signal is v1 and uses one external forecast source; this is not yet a calibrated institutional model.

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
Phase 3: **six positions live**. The Michigan position was filled at 0.640; current liquid balance shown by the account is ~58,019 SUSQies. Scanner foundation is in place; next step is historical calibration and official API ingestion.
