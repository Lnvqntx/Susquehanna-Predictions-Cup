# Susquehanna Predictions Cup — Quant Research

Systematic research and trading framework for the 2026 Susquehanna Predictions Cup.

## Workflow
1. Market scan
2. Candidate shortlist
3. Evidence collection
4. Poll normalization and weighting
5. Fundamentals / baseline model
6. Win-probability model
7. Cross-market sanity check
8. Edge calculation
9. Position sizing
10. Trade log and model update

## Current focus
- Kansas Senate — Democratic Party (YES 0.355)
- Alaska Senate — Democratic Party (YES 0.715)

No trade is taken until the estimated win probability clears the executable price by a meaningful margin after uncertainty and friction.

## Layout
```text
.
├── data/
│   ├── markets.csv
│   └── polls.csv
├── research/
│   ├── kansas_senate.md
│   └── alaska_senate.md
├── models/
│   ├── probability.py
│   └── sizing.py
└── notebooks/
```

## Status
**Phase 1 — Research + model scaffolding**