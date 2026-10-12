# Live API Bootstrap

## Current implementation status

The authenticated v1 API layer is operational for the competition entry workflow.

- [x] v1 transport client
- [x] local secret handling
- [x] bulk price reads
- [x] tournament discovery
- [x] tournament positions
- [x] open-order reads
- [x] order-book reads
- [x] limit-order submission
- [x] idempotent writes
- [x] transient retry behavior
- [x] live position/open-order reconciliation
- [x] autonomous entry execution

The project no longer treats authenticated order submission as a blocked phase.

## Setup

Create an API key from the Susquehanna profile with:

- `read`
- `trade`

Store it locally as `SUSQ_API_KEY` in the ignored `.env` file.

Never commit `.env`.

## Validation

API smoke test:

`python src/api_smoke_test.py`

Live-market scan:

`python src/scan_live.py --limit-markets 0 --top 40`

Read-only autopilot:

`python src/autopilot.py`

## Execution model

Live entry uses:

- tournament-scoped routing
- limit prices on the supported tick
- client idempotency keys
- current position reconciliation
- current open-order reconciliation
- duplicate-exchange protection
- aggregate resting-order exposure limits
- safe transient retry behavior

## Current boundary

Authentication and basic trading are complete.

The next engineering work is portfolio-state management:

1. revalue existing positions;
2. calculate current edge decay;
3. compare existing positions against new opportunities;
4. dry-run capital rotations;
5. only then enable live rotation.

Realtime streaming and a multi-source calibrated probability model remain later upgrades.
