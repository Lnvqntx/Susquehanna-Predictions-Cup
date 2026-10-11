# Trading

## Required setup
1. Create an API key with read + trade scope. The existing scanner key is read-only.
2. Keep the key in the repo-local .env as SUSQ_API_KEY. Never paste it into chat or commit it.
3. The client discovers the Midterm Elections tournament and routes orders with its tournament UUID.
4. Use src/trade.py for one reviewed limit order at a time.
5. Limit prices must use the 0.005 tick between 0.005 and 0.995.
6. Every order gets a client idempotency key.

## Dry run
python src/trade.py --exchange-id 927 --side yes --quantity 100 --price 0.300 --reason "PA-08 thesis"

## Live order
python src/trade.py --exchange-id 927 --side yes --quantity 100 --price 0.300 --reason "PA-08 thesis" --confirm

The CLI requires an explicit CONFIRM phrase before submission.

## Safety
The first live trading version supports limit orders only and requires explicit confirmation. Market orders are intentionally excluded. The API documents POST /orders as a write requiring an idempotencyKey. Standard accounts have a shared per-account write budget, so multiple keys do not increase capacity.
