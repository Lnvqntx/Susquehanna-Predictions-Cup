# Project Plan

## Phase 0 — Infrastructure ✅
- [x] Create repository
- [x] Create research/data/model directories
- [x] Record initial Alaska and Kansas market snapshots
- [x] Record initial Kansas polling dataset

## Phase 1 — Kansas Deep Dive 🚧
- [x] Collect current polling
- [x] Check independent forecast models
- [x] Check Kansas partisan baseline
- [x] Check incumbency/history
- [x] Check campaign-finance and spending signals
- [ ] Build a transparent probability model
- [ ] Stress-test assumptions
- [ ] Produce a final trade/no-trade decision
- [ ] Log the decision and rationale

## Phase 2 — General Election Model
Build reusable components for poll recency weighting, pollster weighting, fundamentals prior, national environment, margin uncertainty, win-probability conversion, and model ensemble.

## Phase 3 — Portfolio / Trading
- rank researched markets by edge
- account for correlations between races
- use conservative fractional Kelly
- cap exposure per race/theme
- maintain an append-only trade journal

## Phase 4 — Automation
Once the manual model works, add market snapshots, poll ingestion, probability refreshes, price-move detection, and meaningful-edge alerts.

## Decision rule
For a YES contract at price q: edge = P(YES) - q.

A position requires positive edge, sufficient confidence, robustness to reasonable model changes, and acceptable portfolio concentration. No trade is triggered by a single poll or headline.
