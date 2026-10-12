# Market Scanner

Purpose: turn the full tournament market universe into a ranked shortlist instead of researching markets one by one.

## Pipeline

1. Read the live market universe.
2. Normalize executable prices and liquidity.
3. Match markets to probability estimates.
4. Compute raw edge.
5. Penalize weak confidence, thin liquidity, and redundant portfolio themes.
6. Rank candidates.
7. Pass qualified candidates to the guarded execution engine.

## Current live capability

The authenticated scanner can:

- discover the Midterm Elections tournament;
- scan the open market universe;
- fetch live exchange quotes;
- save JSON/CSV snapshots;
- feed candidates to the autonomous entry engine.

Read-only scan:

`python src/scan_live.py --limit-markets 0 --top 40`

Autonomous entry:

`python src/autopilot.py`

## Current limitation

The probability signal is still v1 and comes from one external forecast source. It is not historically calibrated.

Model roadmap:

- second independent forecast source;
- pollster/recency weighting;
- structural state/district baseline;
- historical calibration;
- out-of-sample edge-threshold testing.

## Portfolio awareness

Execution already reconciles current positions and open orders and skips occupied exchanges.

The next scanner upgrade is to expose current-position edge decay so the portfolio rotator can compare new opportunities against capital already deployed.

Never commit API credentials.
