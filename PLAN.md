# TOP 3 MISSION — EXECUTION PLAN

## Objective

Finish the 2026 Midterm Elections Predictions Cup in the **top 3** by final SUSQie account value.

## Current state — 2026-10-12

- Leaderboard: **365 / 1,403**
- Displayed leaderboard gain: **+824.21 SUSQies**
- Positions: **18**
- Cash: **~0.085 SUSQies**
- Cost basis: **99,999.94 SUSQies**
- API-summed market value: **100,842.10 SUSQies**
- Entry autopilot: **live-tested**
- Portfolio: **effectively fully deployed**
- Next bottleneck: **portfolio rotation + model calibration**

## Completed

- [x] Repository and research structure
- [x] Probability/model scaffolding
- [x] Market ranking/scoring
- [x] Manual research workflow
- [x] Order-book fill simulation
- [x] Authenticated API client
- [x] Bulk live market scan
- [x] Exact order-book inspection
- [x] Guarded limit-order submission
- [x] Idempotent writes
- [x] Position/open-order reconciliation
- [x] Duplicate-exchange protection
- [x] Aggregate resting-order cap
- [x] Transient API retry handling
- [x] Autonomous entry ranking + execution
- [x] Regression tests for execution guards

## Phase 4 — Portfolio rotation

### Goal

Recycle capital from weaker positions into materially stronger opportunities.

Required sequence:

1. Read every current position.
2. Revalue each position at an executable price.
3. Recompute current model probability and edge.
4. Score existing positions for edge decay, concentration, and uncertainty.
5. Scan all open markets for new opportunities.
6. Compare each new opportunity against the weakest eligible holding.
7. Rotate only when expected improvement clears execution friction and an uncertainty buffer.
8. Log and dry-run the complete sell→buy sequence.
9. Enable live rotation only after tests pass.

### Non-negotiable rules

- Never sell simply because price fell.
- Never rotate into a weaker expected-value trade.
- Never trade from stale prices.
- Never create duplicate exchange exposure.
- Never retry an ambiguous write without live reconciliation.

## Modeling upgrades

### Calibration
- [ ] Timestamp probability/price snapshots
- [ ] Historical calibration
- [ ] Brier score and log loss
- [ ] Uncertainty by race type
- [ ] Out-of-sample threshold tuning

### Forecast ensemble
- [ ] Add a second independent forecast source
- [ ] Add pollster/recency weighting
- [ ] Add structural state/district baseline
- [ ] Blend forecasts transparently
- [ ] Penalize source disagreement

### Execution
- [x] Limit-order execution
- [x] Partial-fill handling
- [x] Position reconciliation
- [x] Open-order reconciliation
- [x] Idempotent writes
- [x] Aggregate open-order budget
- [x] Duplicate-exchange guard
- [ ] Portfolio rotation
- [ ] Stale-order management
- [ ] Realtime market stream

## Operating rule

**Research first. Execute second. Rotate only when the replacement is demonstrably better.**
