# SPX-fit ACD options — post-audit results (3 auditors, 9 fixes, full re-run)

**Date:** 2026-07-02 (evening) · **Driver:** `bot/backtest_acd_spx_options.py` (audited v2)

## The audit (user-demanded live-fidelity pass, 3 independent auditors)

**Auditor 1 — signal knowability:** no critical look-ahead in any traded path; the V5-era fade bug confirmed dead. Fixed: hygiene seed peeked at first-5-minute median (now seeds from prior day's close); `late_day_c`/`c_through_pivot` label was close-contaminated (now time-only — defused before it could bite); 61-minute "first hour" (now exclusive). Known limitation documented: the day's bar series comes from an option anchored off the day's EOD spot (minute-coverage hazard; post-ladder fix = merge spots across all strikes).

**Auditor 2 — execution fidelity:** 2 CRITICALs fixed: (1) bar files weren't time-sorted (~0.7% scrambled; one settle was a 2:32pm print, 73 pts off); (2) settlement used the frozen ~16:01 feed spot, median 2.5 / p90 8.3 pts off official — 15% of trades settle within 2.5 pts of a strike, so this flipped outcomes. Now settles on the EOD chain's official print. Also fixed: same-minute fills (optimistic both directions → now fill the NEXT bar), active-exit walk ran into non-tradeable post-16:00 bars (now capped 15:59), phantom exit slippage on cash-settled trades, sizing now includes entry slippage, truncated days dropped. Documented, unfixable with current data: XSP = SPX/10 idealization (real XSP strikes are integer-gridded; some modeled strikes don't exist).

**Auditor 3 — red-team replay:** 6/6 sampled trades reproduced to the cent by an independent re-implementation (event chains, entry NBBO, settles, sizing, P&L); the full 367-row ledger regenerates with 0 mismatches.

## Post-audit results (slip 0.05/leg, $10k, 3% risk compounding, FOMC banned in SPX-fit)

| Config | Trades | Win | P&L | MaxDD | By year |
|---|---|---|---|---|---|
| all-debit grid (4 variants) | 393–523 | 39–44% | **−$2.3k to −$5.9k** | −59…−66% | red everywhere |
| **SPX-fit, gate** (fades=credit, breakouts held) | 383 | 58% | **+$214** | −31% | mixed |
| **SPX-fit, no gate** | 510 | 55% | **+$8,512** | −29% | +2,569 / −293 / +5,952 / +283 |
| breakouts-only (a_held debit, hold, FOMC ban) | 416 | 43% | **+$14,705** | −29% | +3,620 / **−1,397** / +16,238 / **−3,757** |

Slippage sweep 0→20¢/leg moves SPX-fit by <$500 — result is friction-robust.

## Honest reading

1. **The credit flip worked as designed but didn't flip the sign:** fade losses halved (−$10.1k debit → −$5.0k credit). Fades on SPX remain a losing trade in every expression tested. Their only defense now is diversification optics, and they don't earn it.
2. **Breakouts (a_held) as held debit spreads are the real signal** — positive in the combined config (+$13.5k of its P&L) and +$14.7k standalone. BUT standalone is **regime-concentrated: 2025 supplies more than 100% of the profit; 2024 and 2026 both lose.** The skill's failure-pattern list calls this "relies on 1–2 exceptional periods." Not deployable on this evidence.
3. The macro gate subtracts again (+$214 gated vs +$8,512 ungated) — fourth consecutive strike.
4. FOMC ban: 24 days sat out, empirically justified (banned days were 15%-win days pre-ban).

## What would make this trustworthy

- **Walk-forward:** tune nothing, split by year, demand positive expectancy in most years — breakouts-only already fails this (2 of 4 negative).
- **More regimes:** only 3 years of SPX intraday exists in cache (the vendor window we have); the 5-year policy can't be met on this instrument yet.
- **Real XSP strikes** once ladder data lands (integer grid, 2-3 wide) — kills the /10 idealization.
- The **condor-on-quiet-days** test (218 no-signal days) — data arrives with the ladder pull (~21h).

## Files
- `results/spx/acd_options_day_ledger_spxfit.csv`, `acd_options_trades_spxfit.csv` — SPX-fit no-gate ledgers (every day, every trade, WHY columns, counterfactuals).
- Prior epoch (pre-audit) writeup: `acd_options_3yr_2026-07-02.md` — numbers superseded by this doc.
