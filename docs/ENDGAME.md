# Endgame plan — 2026-10-29 (6 days left)

## Where we are
- Account value 94,565 SUSQies, rank **1,473**, -5.4k all time.
- Leaderboard: #1 +1.02M, #3 +890.8k (~990k account), #10 +272.9k, #70 +25.9k.
- The current book is a hedge: D and R tickets plus shorts. Simulated over 20k
  correlated elections it reaches ~126k (top ~70) **3%** of the time and never reaches top 10.

## Why change
Rank is the objective, not EV. Near the bottom of the table there is little to lose, so the
book should be one coherent, correlated scenario with a big payoff multiple.

The SUSQ crowd is pricing a strong Democratic year: D House 86.5%, D Senate 69%.
Real-money markets on Oct 29 are even more D for the House (~92%) and similar for the Senate (~67%).
The contrarian, high-multiple scenario is a **Republican polling miss** across competitive races.

## The plan (`data/tournament_push/basket_plan.json`, `trade_list.csv`)
1. **Stop `autopilot.py`.** It buys D edges and would fight this plan.
2. **Exit** the off-scenario tickets: D in RI/NH/MI/TX Senate, WI-01, PA-01, MT-01, ME-02.
   Also CO-04 R (only ~1.5x upside). Cover the DE and GA R shorts.
3. **Keep** the R longshots already held (WI-03, TX-15, PA-10, PA-08, IA-01, IA-03) and the WA-03 D short.
4. **Buy** R YES in 35 races priced 10–40%. Use equal shares, so roughly the same payout per race (~7.7k).
   This mixes competitive House seats, swing-state Senate/Governor races, and both chamber-control markets.

## Honest odds (model: rho=0.5 national swing share, longshot correction k=1.25)
| | >=126k (~top 70) | >=273k (~top 10) | >=990k (~top 3) | median |
|---|---|---|---|---|
| Hold current book | 3% | 0% | 0% | 71k |
| R basket 10–40% (recommended) | ~14% | ~1.5–2% | ~0% | 25k |
| R lottery 3–15% | ~10% | ~3% | ~0% | 8k |

**Top 3 is out of reach for any pre-election basket.** 95k can't be turned into ~1M on these
prices without R winning in places like Maryland and Oregon. The remaining edge is election night.

## Election night (US polls close ~05:30 IST Nov 4; settlement 22:30 IST Nov 4)
The platform reprices slower than results come in. When a trustworthy source calls a race,
buy the called winner below ~0.95. Once the price catches up, sell near 0.99 and recycle the cash.

```
python src/push_execute.py snipe --call "PA-08 House race=Republican" --spend 5000          # dry run
python src/push_execute.py snipe --call "PA-08 House race=Republican" --spend 5000 --live
```

Only act on actual calls (AP / Decision Desk). Never act on partial counts.

## Commands
```
python src/tail_basket.py --scenario Republican --band 0.10 0.40 --objective 126000   # rebuild plan
python src/push_execute.py plan                     # dry run with live order books
python src/push_execute.py plan --live              # place the exits + basket
```
Rebuild the plan right before executing; prices move.

## Execution log
- **2026-10-29 21:50 IST** — `push_execute.py plan --live` ran once. All 11 exits and 35 basket buys
  filled completely (no resting orders). Portfolio afterwards: 42 positions, value 78,329, cash 13,970,
  account 92,299. The roughly 2.3k drop from 94.6k is the bid/ask spread paid on the round trip.
  Covering the DE and GA shorts released collateral, so cash came in about 12k above plan. That
  ~14k is held back for election-night snipes.
