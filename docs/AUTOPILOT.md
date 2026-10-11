# Autonomous trader

The project now has a forecast-driven autonomous loop.

## Data source

Polling Forecast publishes a public, read-only JSON API for the 2026 US House, Senate and governor forecasts. The API documents the fields used here, including race keys, forecast probabilities and `asOf`. The bot uses:
- `/api/us/house`
- `/api/us/senate`
- `/api/us/governors`

## Signal

For each open Susquehanna market:
1. Parse the state/district and party from the title.
2. Match it to the Polling Forecast race key.
3. Use the external party win probability.
4. Compare it with the current executable YES ask.
5. Require minimum edge and a tight spread.
6. Rank by edge.
7. In live mode, submit a limit order at the current ask.

This is deliberately simple. It is a v1 automated signal, not a calibrated institutional model.

## Hard controls

Defaults:
- minimum edge: 10 percentage points
- maximum spread: 1.5 percentage points
- maximum cost per order: 3,000 SUSQies
- maximum cost per scan cycle: 3,000 SUSQies
- refresh interval in loop mode: 300 seconds, never below 60 seconds
- limit orders only
- no duplicate exchange order while present in local state
- client-side idempotency key on every order

The live API key must have `read` and `trade` scopes and remain only in the local `.env`.

## Commands

Analyze only:

`python src/autopilot.py`

One live cycle:

`python src/autopilot.py --live`

Continuous autonomous mode:

`python src/autopilot.py --live --loop --interval 300`

The bot prints the candidates it considered before it submits anything.

## Important limitation

The v1 probability comes from one external model. It should not be interpreted as a guarantee of accuracy. Before reducing thresholds or increasing size, add a second independent forecast source and backtest the signal on saved snapshots.
