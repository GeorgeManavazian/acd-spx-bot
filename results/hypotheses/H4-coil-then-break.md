# H4 — Coil-then-break filters ⭐ (campaign star)

**Source:** "MAX way" video's 6-7-inside-candles heuristic + our own empirical finding (entries before 10:30 lost). Two independent pointers at the same structure: a breakout that comes out of a *clean coil* beats one that comes out of noise.

**Implementations** (`bot/experiments_spx.py::h4_variants`, BOT v2 baseline):
- (a) entry ≥ 10:30 (blunt time floor);
- (b) entry ≥ 11:15 (his literal ~6-7 bars);
- (c) **clean coil: no failed-A event (either side) before the entry** — the market's first serious push past an A-level is the one that holds, with no prior fake-outs.

| Variant | Trades | Win | P&L | MaxDD | Yrs+ | By year |
|---|---|---|---|---|---|---|
| BASELINE | 416 | 43% | +$14,705 | −29% | 2/4 | +3,620 / −1,397 / +16,238 / −3,757 |
| a ≥10:30 | 252 | 42% | +$6,009 | −26% | 2/4 | |
| b ≥11:15 | 91 | 42% | +$2,547 | −24% | 3/4 | |
| **c clean coil** | 178 | **48%** | **+$17,670** | **−18%** | **4/4** | +3,469 / +926 / +11,987 / +1,287 |

## Verdict

**(c) dominates the baseline on every axis** — more profit on 43% as many trades, 11 points less drawdown, and all four years positive including the two the baseline lost. The blunt time floors (a/b) *lose* money vs baseline, which is the interesting part: the edge isn't "trade later," it's "trade the day's FIRST conviction move." A failed pierce earlier in the day marks the session as trap-prone, and skipping those days is worth more than any clock rule. **Adopt (c).** Interpretation guard: 48% win on 178 trades is still tail-driven; this filter concentrates, it does not transform.
