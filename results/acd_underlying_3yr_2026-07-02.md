# Full ACD on SPX underlying (as XSP), 3 years — results

**Date:** 2026-07-02 · **Driver:** `bot/backtest_acd_spx_underlying.py` · **Data:** 744 cached SPX days (2023-07-05 → 2026-06-26), 5 skipped for data, 826 invalid prints filtered (incl. a 0.0 print on 2024-01-19 that, unfiltered, fills a stop at zero and wipes the account — the first run died exactly that way).

## Locked spec (committed before the run)

Full ACD method — micro setups (breakouts AND fades) gated by the macro layer (chop filter, regime gate, conviction). **Not V5** (no fade-only filter, no options). Directional buy/sell of XSP = SPX/10, whole units. One position at a time; enter at the setup's price, exit at its stop (gap-through fills worse) or the session close; same-day only, no time stop. $10,000 start; risk 3% of current equity per trade, notional capped at 1× equity (cash, no leverage); compounding. Slippage per side swept {0, 0.05, 0.10} XSP pts; $0 commission (stated assumption). Setups with no stop (`failed_c`, `reversal_trade`, EOD `trt`/`sushi`) are logged, not traded — an underlying position can't be risk-sized without a stop distance.

## Headline

| Slippage/side | Trades | Win | P&L | Final equity | Max DD |
|---|---|---|---|---|---|
| 0.00 | 449 | 17% | **+$220** | $10,220 | −3.7% |
| 0.05 (baseline) | 449 | 17% | **−$529** | $9,471 | −8.4% |
| 0.10 | 449 | 17% | **−$1,240** | $8,760 | −14.4% |

**Frictionless, the full method is dead flat over 3 years (+2.2% total, less than T-bills). Any realistic friction makes it a slow bleed.** Evaluator: 55/100, Refine — HIGH flag: negative expectancy.

## Day-by-day accounting (744 days — full detail in `acd_underlying_day_ledger.csv`)

| What happened | Days |
|---|---|
| Traded (≥1 position) | 390 |
| No setup qualified at all (no A/C event — chop/drift day) | 216 |
| Setups fired but macro gate dropped them all | 130 |
| Only stop-less setups (`failed_c`) — unsizeable, logged | 8 |
| Skipped for bad data | 5 |

Macro-gate drops by cause: chop state 63, confused regime ~25 more, system_failure 19, regime gate (counter-trend breakout) the rest. Additionally 46 signals fired *while already holding a position* and were correctly skipped (one-position rule), 75 `sushi` and 29 `reversal_trade` macro setups were logged untraded, and `failed_c` appeared on 47 days.

Macro state on trade days vs P&L (slip 0): neutral n=188 −$73 · chop n=139 +$41 · trend_up n=76 −$378 · system_failure n=35 −$74 · trend_down n=11 −$45. **The macro layer's "best" conditions (trend_up) produced the worst P&L** — consistent with the number-line study on crude that found the states non-predictive.

## Why it loses (anatomy)

- **Exit split:** 351 stop-outs (avg −$11) vs 98 hold-to-close (avg +$34). Median stopped trade lasted **4 minutes**. ACD stops sit just beyond the A-level; SPX noise crosses them almost immediately after a fade entry.
- **Expectancy ≈ zero:** 17% × $47 − 83% × $11 ≈ $0/trade before costs. The classic tight-stop trap: high loss frequency at small size needs big winners, and SPX same-day moves don't deliver them often enough.
- **By setup (slip 0):** `failed_a` n=310 +$258 · `a_held` n=88 −$407 · `failed_a_pivot` n=44 −$88 · `c` n=7 +$457. Nothing has real edge; `c` is 7 trades of luck-grade sample.
- **By year:** 2023 +$153, 2024 −$130, 2025 +$67, 2026 +$130 (slip 0) — noise around zero every year, no regime dependence, no blow-up. It doesn't *break*; it just doesn't *make*.

## The 3%-risk caveat (important)

The user's spec asked 3% of equity risked per trade. With ACD's tight stops, 3% risk implies ~300 XSP units ≈ $140k notional on a $10k account — 14× leverage. The no-leverage cap bound on **448 of 449 trades**, so the *effective* risk per trade was ~0.1%, not 3%. Two honest readings:
1. As tested (cash account): results above — flat.
2. At true 3% risk (14× leverage): same per-trade returns × ~27 → the +$220 becomes ≈ +$6k frictionless, but the −$529 baseline becomes ≈ −$14k, i.e. **ruin**. Leverage amplifies a zero-edge system into a coin-flip death spiral; it cannot rescue it.

## What could be better / what this rules out

1. **Same-day underlying expression of full ACD on SPX has no edge.** This confirms the earlier per-signal diagnostic from the other direction (portfolio-level, sized, frictioned).
2. The **hold-to-close exits are where all the profit lives** (+$3.4k) and the stops are where it dies (−$3.9k). Any refinement should attack the exit/stop geometry (wider stops = fewer whipsaws but bigger losses — needs a sweep), not entries.
3. **The macro layer earns nothing here:** its gates removed 130 days of signals yet trade-day P&L is best in "chop" and worst in "trend_up". On SPX, as on crude, the number line looks non-predictive.
4. Options (V5's route) change the payoff shape — defined risk, convexity, no stop-whipsaw — which is exactly why the fade edge only appeared there. The next honest step for the ACD-on-underlying question is a **stop-width/exit sweep**; the next step for the project overall remains the **pre-registered V5 re-validation**.

## v2 — look-ahead audit + SPX parameter sweep (same day, later)

Audit of the v1 driver found and fixed three look-ahead exposures:
1. **Data hygiene used the full-day median** — the filter "knew" the afternoon at 10:00. Now causal: each print judged against the last kept print, seeded from the first 5 prints of the morning. (Same 826 bad prints dropped; results unchanged at the baseline config — the exposure was real but happened not to bite.)
2. **`late_day_c` label depends on the day's close** (overnight-carry test) — unknowable at entry. Overnight-horizon setups now excluded from trading (logged instead). No such trade had fired in v1, so numbers unchanged; the hole is closed.
3. **ATR path unused** — SPX ran on the %-of-price fallback. Added Fisher's faithful A/C = frac×ATR with ATR(14) from **prior days only**.

Parameter sweep at slip 0.05/side (OR minutes × A/C source × macro gate), seeking a plateau:

| Config | Trades | Win | P&L |
|---|---|---|---|
| OR15/pct/gate (baseline) | 449 | 17% | −$529 |
| OR15/pct/nogate | 814 | 32% | +$78 |
| OR15/atr18/gate | 433 | 15% | −$822 |
| OR15/atr18/nogate | 757 | 31% | **+$394** |
| OR15/atr25/gate | 338 | 15% | −$1,116 |
| OR15/atr25/nogate | 572 | 28% | −$1,286 |
| OR30/pct/gate | 385 | 15% | −$95 |
| OR30/pct/nogate | 629 | 27% | −$349 |
| OR30/atr18/gate | 357 | 14% | −$340 |
| OR30/atr18/nogate | 577 | 28% | −$417 |
| OR30/atr25/gate | 257 | 14% | −$621 |
| OR30/atr25/nogate | 415 | 27% | −$659 |

**Reading:** the whole surface is noise around zero (−1.3% to +0.4% per year). No plateau of profit exists to stand on; the best cell is a peak, not an edge. Two robust patterns: (a) **the macro gate hurts in every OR15 pairing and never helps much** — dropping it doubles the win rate; on SPX as on crude, the number line is not predictive; (b) wider A/C (atr25) is worse everywhere — fewer, later, more-exposed entries.

**Conclusion (v2):** the full ACD method has no edge on the SPX underlying under any tested parameterization. If ACD is worth anything on SPX, the value must come from the options payoff shape, not the directional signal. Next step unchanged: options overlay on this driver, and the pre-registered V5 re-validation.

## Files

- `results/spx/acd_underlying_day_ledger.csv` — one row per day: state, regime, raw setups, post-macro setups, trades, skip reasons, equity.
- `results/spx/acd_underlying_trades.csv` — one row per trade: entry/exit, reason, units, P&L, equity after.
- `results/spx/backtest_eval_2026-07-02_182252.md` — structured evaluator output (55/100, Refine).
