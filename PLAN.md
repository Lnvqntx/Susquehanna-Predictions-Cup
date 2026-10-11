# TOP 3 MISSION

## Objective
Finish the 2026 Midterm Elections Predictions Cup in the **top 3** by final SUSQie balance.

Today's leaderboard showed 3rd place around **742.9k SUSQies**; the benchmark will move, so the strategic target is **1,000,000+**.

## Operating rules
1. Prefer repeatable positive-EV situations.
2. Trade only at verified executable prices.
3. Use order-book-aware sizing.
4. Penalize portfolio-redundant trades.
5. Keep capital available for new mispricings.
6. Record every fill and probability.
7. Rotate capital when the edge disappears.

## Portfolio
- Rhode Island Senate D YES — LIVE
- New Hampshire Senate D YES — LIVE
- Georgia Senate R NO — LIVE
- Delaware Senate R NO — LIVE
- Texas Senate D YES — LIVE

## Progress
- [x] Build repository
- [x] Build probability scaffolding
- [x] Build market ranking/scoring
- [x] Execute 5 trades
- [x] Build order-book fill logic
- [x] Add portfolio-aware scoring
- [x] Reject Maine despite an initially attractive forecast discrepancy
- [ ] Build historical calibration layer
- [ ] Build live API adapter
- [ ] Reach 10+ validated markets
- [ ] Increase turnover only after calibration

## Current target
**Autonomous execution build**

- [x] Discover all 237 open markets
- [x] Bulk live-price scan
- [x] Exact order-book inspection
- [x] Authenticated trading key
- [x] Guarded limit-order client
- [x] Public forecast API adapter
- [x] Autonomous candidate ranking + order submission
- [ ] Add second independent forecast source
- [ ] Backtest live snapshots and calibrate thresholds
- [ ] Add realtime stream integration

## Current target
**Live scanner build**

The manual phase has produced six live positions. The next bottleneck is throughput, so the priority is authenticated API ingestion rather than another hand-screened market.

- [x] Build API transport scaffold
- [x] Build bulk-price reader
- [x] Build snapshot scanner
- [x] Build order-book fill simulator
- [ ] Verify authenticated API schema from the account's API Reference
- [ ] Populate exchange/market IDs
- [ ] Run first live 100-exchange scan
- [ ] Add 60–120 second refresh loop
- [ ] Connect probabilities + scoring to live prices
- [ ] Validate 10+ live candidates manually
- [ ] Only then enable any automated order path

The current Susquehanna API docs state that scripted strategies are permitted and that the v1 API supports bulk price reads for up to 100 exchange IDs; normal accounts have 100 reads/minute and 30 writes/minute. Realtime market channels require a realtime token and dropped delayed batches should trigger REST refreshes. citeturn822835search0turn314656search6

## Current target
**Live API scan — blocked only on API-key/schema verification.**

Michigan has a stronger and more coherent model cluster than Maine, but the live Susquehanna price is unknown. Obtain the live order book before acting.

**Rule:** research first, execute second.
