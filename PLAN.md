# Project Plan

## Phase 0 — Infrastructure ✅
- [x] Create repository
- [x] Create research/data/model directories
- [x] Record initial Alaska and Kansas market snapshots
- [x] Record Kansas polling dataset
- [x] Create trade journal

## Phase 1 — Kansas Deep Dive ✅ / calibration next
- [x] Collect current polling
- [x] Check independent forecast models
- [x] Check Kansas partisan baseline
- [x] Check incumbency/history
- [x] Check campaign-finance and spending signals
- [x] Build transparent first-pass probability model
- [x] Produce model v1 working probability
- [ ] Stress-test assumptions systematically
- [ ] Add historical calibration layer
- [ ] Produce final trade/no-trade decision

**Current Kansas v1:** ~36.8% Democratic win probability vs 35.5% executable YES. Raw edge ~+1.3 pts. Decision: **NO TRADE YET**.

## Phase 2 — General Election Model
- [ ] Recency-weighted polls
- [ ] Pollster reliability weights
- [ ] Fundamentals prior
- [ ] National environment factor
- [ ] Correlated election error
- [ ] Margin → win-probability calibration
- [ ] Forecast ensemble

## Phase 3 — Market Selection ✅
- [x] Build snapshot market scanner
- [x] Add probability/price/liquidity/confidence scoring
- [x] Add portfolio correlation inputs

## Phase 3 — Market Selection
- [x] Execute Trade #4 after live order-book refresh


- [ ] Scan all open markets
- [ ] Rank by price vs model discrepancy
- [ ] Research top candidates deeply
- [ ] Track market momentum and liquidity

## Phase 4 — Portfolio / Trading
- [ ] Conservative fractional Kelly
- [ ] Position caps
- [ ] Cross-race correlation controls
- [ ] Entry/exit rules
- [ ] Append-only trade journal

## Phase 5 — Automation
- [x] Define API integration boundary

- [ ] Market snapshot ingestion
- [ ] Poll ingestion
- [ ] Probability refresh
- [ ] Edge scanner
- [ ] Alerting for robust opportunities
