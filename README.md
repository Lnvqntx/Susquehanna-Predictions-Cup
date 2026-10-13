# Susquehanna Predictions Cup — Quant Research

Systematic research, execution, and portfolio-management framework for the 2026 Susquehanna Predictions Cup.

## Mission

Finish the Midterm Elections tournament in the **top 3** by final SUSQie account value.

The strategic stretch target is **1,000,000+ SUSQies**. The real objective is relative leaderboard rank.

## Current snapshot — 2026-10-12

| Metric | Latest observed |
|---|---:|
| Starting bankroll | 100,000 SUSQies |
| Positions | 18 |
| Cash balance | ~0.085 SUSQies |
| Cost basis | 99,999.94 SUSQies |
| API-summed market value | 100,842.10 SUSQies |
| Portfolio-page account value | 100,769 SUSQies |
| Leaderboard rank | **365 / 1,403** |
| Leaderboard gain shown | **+824.21 SUSQies** |
| Portfolio-page daily P&L | **+382 SUSQies** |

The API position sum and signed-in portfolio value were read at slightly different moments, so they are not expected to match tick-for-tick.

## Current system

The project now has three working layers:

1. **Discovery:** scans all open tournament markets and fetches executable quotes.
2. **Forecast ranking:** compares an external forecast probability with the executable YES ask and ranks edge opportunities.
3. **Guarded autonomous entry:** places limit orders with live portfolio/open-order reconciliation, idempotency, duplicate-exchange protection, aggregate open-order limits, and safe transient-error behavior.

The current v1 forecast is still a **single-source signal**. It is not yet a calibrated institutional probability model.

## Autonomous entry

Read-only:

`python src/autopilot.py`

One live cycle:

`python src/autopilot.py --live`

Current competition profile:

`nohup caffeinate -i python -u src/autopilot.py --live --loop --interval 300 --min-edge 0.15 --max-order-cost 10000 --max-cycle-cost 10000 --max-open-cost 35000 > data/autopilot.log 2>&1 &`

Profile:

- refresh: 300 seconds
- minimum edge: 15 percentage points
- maximum order notional: 10,000 SUSQies
- maximum cycle notional: 10,000 SUSQies
- maximum aggregate resting-order notional: 35,000 SUSQies
- limit orders only

## Current bottleneck

The entry engine has already deployed essentially the full bankroll. Recent scans repeatedly found a top set of opportunities that were already represented in the portfolio.

The next performance upgrade is therefore **portfolio rotation**, not blindly increasing entry size.

Target architecture:

`live positions → revalue → recompute edge → rank weakest exposure → scan new opportunities → compare replacement EV → rotate only when improvement clears friction + uncertainty`

The rotation layer must remain dry-run until regression and historical tests pass.

## Repository layout

```text
.
├── data/
├── research/
├── models/
├── scripts/
├── src/
│   ├── rotator.py
├── trades/
├── docs/
└── tests/
```

## Safety

- Never commit `.env`.
- Never paste API keys into chat.
- Reconcile current positions and open orders before live writes.
- Never blindly retry an ambiguous order submission.
- Never enable live rotation before dry-run tests pass.

Run the suite with:

`python -m pytest -q`

## Portfolio rotation

The read-only rotation analyzer is now in `src/rotator.py`. It compares current holdings at executable exit prices with new opportunities and emits a dry-run SELL → BUY plan. Live rotation remains disabled until the two-leg sell/reconcile/buy/reconcile workflow is regression-tested.
