# Full ACD on SPX as OPTIONS (0DTE debit spreads), 3 years — results + per-trade anatomy

**Date:** 2026-07-02 · **Driver:** `bot/backtest_acd_spx_options.py` · **Data:** 746 days, real IVolatility 1-min NBBO for 1,785 leg-contracts (1,220 pulled today, 0 failures).

## Locked spec

Every intraday ACD setup (breakouts AND fades, `failed_c` included) → same-day 0DTE debit spread, long the strike nearest entry, short 25 pts further, entered at real NBBO at the first bar ≥ the setup's resolution time. One trade per day (earliest setup). Exits: hold-to-expiry (cash settle) vs active 50%-target/50%-stop. $10k start, XSP scale, 3% of equity per trade, compounding. Slippage per leg swept 0–20¢. Macro gate on/off.

## Headline — options make the full method WORSE

| Variant | Trades | Win | P&L | Final equity | MaxDD |
|---|---|---|---|---|---|
| gate / hold | 367 | 35% | −$6,471 | $3,529 | −74% |
| gate / active | 393 | 41% | −$5,988 | $4,012 | −61% |
| nogate / hold | 523 | 38% | −$4,875 | $5,125 | −68% |
| nogate / active | 523 | 45% | −$5,043 | $4,957 | −53% |

Slippage barely matters (−$4.8k frictionless → −$5.5k at 20¢/leg): **the loss is structural, not friction.** The underlying test lost to noise-around-zero; the options version pays theta on top of a zero-edge signal.

## THE finding: the corrected V5 cell is deeply negative

The gated-fades / active-exit subset of this run (n=340: `failed_a` + `failed_a_pivot`, macro-filtered, 50/50 exit) is, to close approximation, **V5's trade universe re-priced on the corrected engine** — same structure (ATM+25 0DTE debit spread), same entry convention, but with the fade look-ahead fixed (entry at the snap-back *resolution* bar, never the pierce extreme; fades no longer retroactively deleted).

**Result: −$4,852 over 340 trades, 41% win. 56% of fades expire worthless.**

V5's published +244% / 82%-win predates the 2026-07-02 audit fix whose own code comment says the bug "flattered every fade backtest (V5, crude)." This run is strong evidence that **V5's edge was the look-ahead artifact.** (Differences remain — V5's exact 9-variant config, sizing throttle — so a to-the-letter pre-registered re-run can still be done, but the burden of proof has flipped.)

## Per-trade WHY anatomy

**Why fades lose as bought options:** a fade fires *after* the snap-back — price is already back inside the range and, on mean-reverting SPX, mostly stalls there. A stalled underlying is death for a bought 0DTE spread: theta eats the debit all afternoon. 56% expired worthless; 59% of active-exit fades died at the stop. The fade signal isn't wrong about direction so much as **wrong about magnitude** — it predicts "no follow-through," and we paid for a structure that needs follow-through.

**Why breakouts (a_held) were the one bright spot (+$5,409 held, n=181):** an A that holds is the rare SPX day with real range extension; the debit spread's convexity pays 5–15× the median loss on those days (best trades: +$982, +$941, +$892 — all clean `A@time` events with no reversal). Median trade still *loses* $36 — the profit is pure right tail, exactly what options are for. **Counterfactual: holding beats the active exit for breakouts (+$1,707 vs −$92 per-contract)** — the mirror image of the fade lesson. Cutting winners at 50% decapitates the only payoff that carries the strategy.

**FOMC days: empirically confirmed poison for this bot.** 13 trades, −$1,374, 15% win (nogate/hold). Every recommendation below bans them.

**Entry timing:** first-hour entries (09:30–10:30) lost −$5,764 (n=298); late-morning (10:30–12:00) made +$1,196 (n=224). Early signals are opening noise. (Flagged as a *candidate* filter only — this is data-mined, not mechanism-derived, and needs out-of-sample confirmation.)

**Conviction (macro confluence) is uninformative:** win rates 37–43% across conviction 1–4, no monotonic pattern. Third independent strike against the macro layer on SPX.

## Best surviving configuration (not yet an edge)

`a_held` breakouts only, no macro gate, hold to expiry, FOMC banned: **+$5,665, n=178, 46% win** — but 2023 +$3,613, 2024 −$211, 2025 +$2,200, 2026 +$62. Two of four years carry everything. Plateau discipline: this is a *lead to validate*, not a strategy to deploy.

## What to change for SPX (evidence-ranked)

1. **Stop buying options on fades.** The signal says "stall" — the theta-positive expression is a **credit spread sold against the failed direction** (same two strikes, reversed). Testable immediately with today's cached legs. Highest-priority next test.
2. **Breakouts: hold, don't manage.** No 50% target on `a_held` — the right tail is the whole trade.
3. **Ban FOMC days** for signal trades (and always for condors).
4. **Drop the macro gate on SPX** (third consecutive strike: sweep, conviction table, state-P&L).
5. Candidate only: ignore first-hour signals (needs OOS validation).
6. The no-signal days (218) remain the condor opportunity — testable when the ladder pull lands.

## Files

- `results/spx/acd_options_day_ledger.csv` — every day, traded or why not.
- `results/spx/acd_options_trades.csv` — every trade with event chain, levels, macro state, conviction, both exit counterfactuals.
