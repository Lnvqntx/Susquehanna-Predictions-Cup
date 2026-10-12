# Autopilot execution observations — 2026-10-12

These are execution observations from the live autopilot output. They are not a substitute for the authoritative current portfolio endpoint.

## IA-01 House — Republican

Observed live event:

- exchange: 903
- requested contracts: 60,606
- initial committed notional: 9,999.99 SUSQies
- immediately filled: 2,691 contracts
- reported fill cost: 444.01 SUSQies
- resting remainder at the time: 57,915 contracts

Later position reconciliation showed the holding accumulated to roughly 4.8k contracts at an average cost near 0.162, so the first order response is not the final portfolio quantity.

## MT-01 House — Republican

Observed live event:

- exchange: 912
- requested contracts: 10,743
- filled: 2,693 contracts
- committed notional: 2,954.33 SUSQies
- reported fill cost: 740.58 SUSQies

The reconciled position showed approximately 2,693 contracts near a 0.275 average entry.

## Execution lesson

A single order response can be only a partial view of the resulting portfolio state. Current positions and open orders must be reconciled from the API before any subsequent action.
