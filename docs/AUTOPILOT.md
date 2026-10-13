# Autonomous trader

The project contains a forecast-driven autonomous **entry** loop.

## Pipeline

For each open market:

1. Read live market data.
2. Match the market to the external forecast.
3. Compute forecast-versus-executable-price edge.
4. Filter by edge and spread.
5. Rank candidates.
6. Reconcile current tournament positions and open orders.
7. Skip exchanges that are already occupied.
8. Size within configured budgets.
9. Submit a limit order with an idempotency key.
10. Reconcile ambiguous responses before any retry.

## Signal

The current v1 probability source is the public Polling Forecast 2026 US House/Senate/Governor forecast API.

The signal is useful for ranking, but it is **not yet calibrated** and uses one external source.

## Live execution profile

The competition run has used:

- `--interval 300`
- `--min-edge 0.15`
- `--max-order-cost 10000`
- `--max-cycle-cost 10000`
- `--max-open-cost 35000`

Exact command:

`nohup caffeinate -i python -u src/autopilot.py --live --loop --interval 300 --min-edge 0.15 --max-order-cost 10000 --max-cycle-cost 10000 --max-open-cost 35000 > data/autopilot.log 2>&1 &`

## Hard controls

- limit orders only
- minimum edge filter
- maximum spread filter
- per-order budget
- per-cycle budget
- aggregate open-order budget
- minimum refresh interval
- live position reconciliation
- live open-order reconciliation
- duplicate-exchange protection
- idempotent POST requests
- retry on transient HTTP/network failures
- stop on unsafe or ambiguous execution state

## Critical state distinction

`open_notional` measures **resting limit-order exposure only**.

It does not include filled positions.

Therefore a portfolio can have near-zero cash and zero open orders while still being fully invested.

## Current behavior

The last confirmed live scans found 12 ranked candidates and skipped all 12 because those exchanges were already represented in the current portfolio. This means the entry layer has reached the current portfolio-capacity bottleneck.

## Commands

Read-only:

`python src/autopilot.py`

One live cycle:

`python src/autopilot.py --live`

Continuous:

`python src/autopilot.py --live --loop --interval 300`

Log:

`tail -100 data/autopilot.log`

Stop:

`pkill -f "src/autopilot.py"`

## Next system

The portfolio rotator is now a separate execution path from the entry autopilot.

It compares current holdings against new opportunities and only recycles capital when the replacement is materially better.

Live rotation command:

`python src/rotator.py --live --confirm`

The entry loop and rotation loop should not be run concurrently unless their state coordination is explicitly verified.
