# Current competition status

**Date:** 2026-10-12  
**Latest observed window:** approximately 18:15–18:30 IST

## Leaderboard

- Participants observed: **1,403**
- Rank: **365**
- Displayed gain: **+824.21 SUSQies**

## Portfolio

### Signed-in portfolio page

- Account value: **100,769 SUSQies**
- Daily P&L: **+382 SUSQies**
- Positions: **18**
- Available cash: **0**

### Authenticated position endpoint

- Cash: **0.085 SUSQies**
- Positions: **18**
- Cost basis: **99,999.94 SUSQies**
- Summed market value: **100,842.10 SUSQies**
- Summed unrealized P&L: **0.00 SUSQies at that read**

The two value figures came from separate reads, so continuous marking can create small differences.

## Autopilot

The live entry loop successfully:

- scanned the open market universe;
- ranked candidates by external forecast edge;
- submitted live limit orders;
- reconciled positions and open orders;
- avoided duplicate exchanges;
- handled partial fills;
- respected aggregate exposure controls.

The most recent observed scans found 12 ranked candidates and skipped all 12 because they were already represented in the portfolio.

## Interpretation

The entry engine has reached its current capital/deployment bottleneck.

The next performance task is **portfolio rotation**, not larger blind entries.

## Next phase

1. Read-only position revaluation.
2. Current-edge table for every holding.
3. New-opportunity table.
4. Dry-run sell→buy rotation logic.
5. Regression tests.
6. Explicit live-rotation flag.

Do not force liquidation merely to create trading activity.
