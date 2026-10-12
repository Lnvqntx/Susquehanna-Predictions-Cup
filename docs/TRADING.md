# Trading

## Setup

1. Create an API key with `read` + `trade` scope.
2. Store it only in the ignored repo-local `.env` as `SUSQ_API_KEY`.
3. Never commit or paste the key.
4. The API client discovers the Midterm Elections tournament and routes orders with the tournament UUID.
5. Use limit orders only.
6. Use the exchange price tick of 0.005.
7. Give each write an idempotency key.

## Reviewed single order

Dry run:

`python src/trade.py --exchange-id 927 --side yes --quantity 100 --price 0.300 --reason "PA-08 thesis"`

Live:

`python src/trade.py --exchange-id 927 --side yes --quantity 100 --price 0.300 --reason "PA-08 thesis" --confirm`

## Autonomous entry

Current competition profile:

`nohup caffeinate -i python -u src/autopilot.py --live --loop --interval 300 --min-edge 0.15 --max-order-cost 10000 --max-cycle-cost 10000 --max-open-cost 35000 > data/autopilot.log 2>&1 &`

Run only one live instance.

## Current portfolio

Latest confirmed read:

- 18 positions
- ~0.085 cash
- 99,999.94 cost basis
- 100,842.10 summed position market value
- rank 365 / 1,403

Because cash is effectively exhausted, the next useful capability is portfolio rotation.

## Safety

- No market orders.
- No duplicate exchange exposure.
- Reconcile positions and open orders before autonomous entry.
- Reconcile ambiguous submissions before any retry.
- Do not enable live rotation until dry-run tests pass.
