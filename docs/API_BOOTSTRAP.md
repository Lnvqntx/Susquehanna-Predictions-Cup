# Live API Bootstrap

Official October 2026 changelog notes:
- Scripts and bots should use the v1 API rather than website endpoints.
- Normal accounts have an account-level budget of 100 reads/minute and 30 writes/minute.
- The bulk prices endpoint accepts up to 100 exchange IDs per call.
- Realtime channels require a realtime token from POST /api/v1/realtime/token.
- Delayed realtime batches can be dropped, so clients should periodically refresh REST state.

Implementation status:
- transport client: added
- secret handling: added
- bulk-price method: added
- snapshot writer: added
- exchange-ID manifest: waiting for verified mapping
- exact response schema: waiting for API Reference verification
- automated order submission: intentionally disabled

Setup:
1. Create an API key in the Susquehanna profile.
2. Keep it local as SUSQ_API_KEY. Do not paste it into chat or commit it.
3. Verify the exact API Reference query/response schema.
4. Populate data/exchange_ids.txt.
5. Run: python src/scan_live.py

Source: Susquehanna official changelog, October 2026.
