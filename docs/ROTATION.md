# Portfolio rotation

## Purpose

The entry autopilot deploys capital into high-edge markets. Once the portfolio is fully invested, the next source of improvement is capital rotation.

The rotation analyzer compares:

- current positions at executable exit prices;
- current model probability for the held side;
- expected return of continuing to hold;
- new opportunities at executable buy prices;
- the improvement from replacing the weakest eligible position.

## Decision rule

For a binary outcome bought at price (q) with model probability (p):

`expected_return = p / q - 1`

For an existing holding, (q) is the executable exit price. This treats existing cost as sunk and evaluates the capital at today's liquidation value.

A proposed rotation requires:

`new_expected_return - old_hold_return >= min_improvement`

The threshold is intentionally separate from the entry edge threshold to prevent needless churn.

## Execution phases

### Phase 1 — read-only

`python src/rotator.py --write`

This produces a report in `data/rotation_report.json`.

### Phase 2 — dry-run

The report itself contains the exact proposed SELL and BUY quantities/prices.

### Phase 3 — live

Live rotation is now implemented behind an explicit confirmation gate:

`python src/rotator.py --live --confirm`

The CLI will recompute the current report first, show the proposed SELL → BUY, then require typing:

`ROTATE`

before submitting anything.

The live sequence is:

1. revalidate the exact position and replacement availability;
2. re-read the sell quote;
3. submit the SELL limit order with an idempotency key;
4. reconcile the actual position decrease and released tournament cash;
5. re-read the replacement BUY quote;
6. revalidate that the replacement exchange is still unoccupied;
7. submit the BUY only from **actually released cash**;
8. report the resulting order IDs/fills.

A sell that produces no verified usable cash causes the BUY leg to be skipped.

## Important

- Holding loss/gain is not a reason by itself to sell.
- Only current expected return matters.
- Never replace a position with a weaker expected return.
- Do not rotate into another exchange inside an underlying market already held; this avoids correlated same-race churn.
- Never rotate into an exchange already represented in the live portfolio/open orders.
- Use executable prices, not last-trade prices.
- Respect uncertainty and forecast disagreement.
