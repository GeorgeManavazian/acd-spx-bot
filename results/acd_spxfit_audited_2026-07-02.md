# SPX-fit ACD options, 3-year results (2026-07-02)

**Date:** 2026-07-02 (evening) · **Driver:** `bot/backtest_acd_spx_options.py`

## Results (slip 0.05/leg, $10k, 3% risk compounding, FOMC banned in SPX-fit)

| Config | Trades | Win | P&L | MaxDD | By year |
|---|---|---|---|---|---|
| all-debit grid (4 variants) | 393–523 | 39–44% | **−$2.3k to −$5.9k** | −59…−66% | red everywhere |
| **SPX-fit, gate** (fades=credit, breakouts held) | 383 | 58% | **+$214** | −31% | mixed |
| **SPX-fit, no gate** | 510 | 55% | **+$8,512** | −29% | +2,569 / −293 / +5,952 / +283 |
| breakouts-only (a_held debit, hold, FOMC ban) | 416 | 43% | **+$14,705** | −29% | +3,620 / **−1,397** / +16,238 / **−3,757** |

Slippage sweep 0→20¢/leg moves SPX-fit by <$500 — result is friction-robust.

## Honest reading

1. **The credit flip worked as designed but didn't flip the sign:** fade losses halved (−$10.1k debit → −$5.0k credit). Fades on SPX remain a losing trade in every expression tested. Their only defense now is diversification optics, and they don't earn it.
2. **Breakouts (a_held) as held debit spreads are the real signal** — positive in the combined config (+$13.5k of its P&L) and +$14.7k standalone. BUT standalone is **regime-concentrated: 2025 supplies more than 100% of the profit; 2024 and 2026 both lose.** Not deployable on this evidence.
3. The macro gate subtracts again (+$214 gated vs +$8,512 ungated) — fourth consecutive strike.
4. FOMC ban: 24 days sat out, empirically justified (banned days were 15%-win days pre-ban).

## What would make this trustworthy

- **Walk-forward:** tune nothing, split by year, demand positive expectancy in most years — breakouts-only already fails this (2 of 4 negative).
- **More regimes:** only 3 years of SPX intraday exists in cache (the vendor window we have); the 5-year policy can't be met on this instrument yet.
- **Real XSP strikes** once ladder data lands (integer grid, 2-3 wide) — kills the /10 idealization.
- The **condor-on-quiet-days** test (218 no-signal days) — data arrives with the ladder pull (~21h).

## Files
- `results/spx/acd_options_day_ledger_spxfit.csv`, `acd_options_trades_spxfit.csv` — SPX-fit no-gate ledgers (every day, every trade, WHY columns, counterfactuals).
