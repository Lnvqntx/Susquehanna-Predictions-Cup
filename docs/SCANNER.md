Market Scanner

Purpose: turn a large market universe into a ranked shortlist instead of researching markets one by one.

Pipeline:
1. Normalize executable price and liquidity.
2. Convert independent research into a model probability for the traded side.
3. Compute raw edge = model probability - executable price.
4. Penalize low confidence, thin liquidity and redundant portfolio themes.
5. Rank candidates by a composite score.
6. Simulate the order-book fill before submitting a trade.

Current scanner command:
python scripts/scan_snapshot.py --input data/watchlist.csv

The snapshot scanner is intentionally offline. It does not pretend that stale data are live.

API phase: Susquehanna's documentation says participant API keys can be used for automated strategies. The October 2026 changelog says scripts should use the v1 API rather than scraping website endpoints, that /api/v1/exchanges/prices supports bulk reads for up to 100 exchange IDs, and that realtime market updates require a realtime token. Periodic REST refreshes are recommended because delayed realtime batches can be dropped. Source: Susquehanna docs and changelog.

Never commit an API key. Put it in a local environment variable or ignored .env file.

Next engineering step: add the official API adapter after confirming the exact API schemas in the account's API Reference. The model layer is deliberately independent of the data transport layer, so the scanner can be tested on snapshots first.
