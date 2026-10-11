# PA-08 House — Republican Party

## Live snapshot — 2026-10-11

- Susquehanna Republican YES latest: **0.295**
- Best ask: **0.300**
- Best bid: **0.295**
- Best ask quantity: **29,020**
- Next asks: 0.305 (26,289), 0.310 (9,607), 0.315 (65,290)
- Democratic YES latest: **0.705**
- Democratic best ask: **0.710**
- Resolution: **2026-11-04**

## Market structure

The Republican and Democratic contracts are the two party-winner contracts for PA-08. The live books are internally consistent: Republican ask 30.0% and Democratic ask 71.0%. No obvious technical pricing anomaly is visible; the opportunity is therefore a probability disagreement, not an order-book glitch.

## External evidence

The latest public polling record is stale: Lake Research Partners, fielded Jun 18–23, had Cognetti 47%, Bresnahan 45%. Election.org and USPollingData both show this as the latest qualifying public poll. citeturn275768search0turn275768search3

The Hill/DDHQ's Oct. 9 forecast gives Cognetti a 53% win chance and Bresnahan 47%. citeturn623073search1

PollingForecast currently gives Bresnahan a 56% win chance and projects R+1.0. citeturn275768search4

Scrutinel, updated Oct. 3, gives Bresnahan 63%, with R+2.3 and an 80% range from R+11.4 to D+6.8. It uses 90% fundamentals and only 10% polls, and its poll input is still from June. citeturn275768search1

Crosstab, updated Oct. 10, gives Democrats a 57% win chance and projects D+1.3. citeturn623073search5

RealClearPolling reports the current Polymarket probability for Cognetti at 73%, implying roughly 27% for Bresnahan. citeturn623073search2

The district is a true toss-up by multiple expert race ratings, and Bresnahan's 2024 margin was only R+1.6 despite Trump carrying the district by R+8.4. citeturn623073search2turn623073search7

## Working probability

Because the forecast models disagree sharply and the public polling is stale, use a **conservative working probability of 50% for Bresnahan**.

This is intentionally below Scrutinel's 63% and PollingForecast's 56%, and above the DDHQ/Crosstab Democratic-leaning forecasts.

## Edge

At a 0.300 executable ask:
- Working P(R): **50%**
- Price: **30%**
- Raw edge: **+20 percentage points**
- EV per contract: **+0.20 SUSQies**

This is a large statistical edge but **low/medium confidence**, because the 27–29% prediction-market cluster is a meaningful counter-signal.

## Execution decision

**TRADE #7 — BUY REPUBLICAN YES**

Target:
- Capital: **5,000 SUSQies**
- Limit: **30.0%**
- Contracts: approximately **16,666**
- Maximum acceptable price without refreshed analysis: **32.0%**

At 0.30, the displayed 29,020-contract ask is sufficient for the intended size.

Do not chase above 32%. If the 30–32% liquidity disappears, re-run the market inspector and re-evaluate rather than paying up.

**Status: READY TO EXECUTE**
