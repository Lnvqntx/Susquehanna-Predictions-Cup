# Susquehanna Predictions Cup — Quant Research

Systematic research and trading framework for the 2026 Susquehanna Predictions Cup.

## Workflow
1. Market scan
2. Candidate shortlist
3. Evidence collection
4. Poll normalization and weighting
5. Fundamentals / baseline model
6. Win-probability model
7. Cross-model sanity check
8. Edge calculation
9. Position sizing
10. Trade log and model update

## Current focus
- Kansas Senate — Democratic Party (YES 0.355)
- Alaska Senate — Democratic Party (YES 0.715)

## Kansas status — 2026-10-08
The first-pass model produces ~39.7%, but the broader forecast cross-check is lower and model disagreement is material. After combining the transparent model with independent forecasts, the current working probability is **~37%**.

At a 35.5% executable price, that is only **~+1.5 percentage points of raw edge**. We therefore have **NO TRADE YET**.

## Layout
```
.
├── data/
│   ├── markets.csv
│   ├── polls.csv
│   └── model_inputs.csv
├── research/
│   ├── kansas_senate.md
│   ├── kansas_model_v0.md
│   └── kansas_model_v1.md
├── models/
│   ├── probability.py
│   ├── kansas_model.py
│   └── sizing.py
├── trades/
│   └── trade_log.csv
├── notebooks/
└── PLAN.md
```

## Core principle
A market is attractive only when the estimated probability is meaningfully above the executable price and the edge survives reasonable model perturbations. A close polling margin is not itself a trade signal.

## Status
**Phase 1 — Kansas model v1 in progress; no position opened.**
