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

**Disabled for now.**

Live rotation requires a two-step, reconciled sequence:

1. submit SELL;
2. reconcile the resulting position/cash state;
3. compute the actually available proceeds;
4. submit BUY;
5. reconcile again.

There is deliberately no `--live` execution path until that sequence has regression coverage.

## Important

- Holding loss/gain is not a reason by itself to sell.
- Only current expected return matters.
- Never replace a position with a weaker expected return.
- Never rotate into an exchange already represented in the live portfolio/open orders.
- Use executable prices, not last-trade prices.
- Respect uncertainty and forecast disagreement.
