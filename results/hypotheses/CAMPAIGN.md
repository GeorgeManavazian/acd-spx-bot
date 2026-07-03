# Hypothesis Campaign — 2026-07-02 (autonomous session)

**Mission:** implement + test the 7 research-derived hypotheses one by one, then combinations.
**Discipline:** everything here runs on the 2023-26 PLAYGROUND data. The 2021-23 pull remains the untouched exam. Verdicts weigh year-by-year stability and drawdown over headline P&L — plateaus, not peaks.

## Organization

- One log per hypothesis: `results/spx/hypotheses/H<n>-<slug>.md` — spec, variants, results table, verdict.
- Code: `bot/experiments_spx.py` — every experiment is a named config (setup-filter predicate + engine spec + exit); NO edits to the main driver per experiment.
- **Baseline for all comparisons = BOT v2** (H1 adopted): a_held breakouts only, 0DTE 25-wide debit spread, hold to settle, FOMC ban, no macro gate, $10k @ 3% XSP-scale compounding, slip 0.05/leg.
- Combinations get `C<n>-<slug>.md` logs, same format.
- Final synthesis: `FINAL-BREAKDOWN.md` in this directory.

## Scoreboard — CAMPAIGN COMPLETE (see FINAL-BREAKDOWN.md)

| ID | Hypothesis | Status | Best variant | P&L | Yrs+ | Verdict |
|---|---|---|---|---|---|---|
| BASE | BOT v2 (H1: fades cut) | DONE | — | +$14,705 | 2/4 | adopted baseline |
| H2 | Pivot-confluence filter | DONE | b: skip pivot-ahead | +$15,096 | 4/4 | **adopt (b)** |
| H3 | Modern Fisher params | DONE | c: OR15/ATR10 | +$13,906 | 3/4 | not adopted |
| H4 | Coil-then-break | DONE | c: clean coil ⭐ | +$17,670 | 4/4 | **adopt (c) — star** |
| H5 | Data-free days | DONE | b: CPI ban | +$17,486 | 2/4 | adopt (b), provisional |
| H6 | Time-stop exit | DONE | — | +$5,796 | — | **reject** (guts convexity) |
| H7 | Volume/time filter | PARKED | — | — | — | no index volume in our data |
| C4 | coil + CPI | DONE | earner | **+$16,586** | 4/4 | **recommended** |
| C5 | coil + through-pivot | DONE | tank | +$11,958 (58% win, −12% DD) | 4/4 | **recommended** |

## Baseline year-by-year (the bar every hypothesis must clear)

2023 +$3,620 (49% win) · 2024 **−$1,397** (39%) · 2025 +$16,238 (50%) · 2026 **−$3,757** (32%)

The problem to solve is not "more P&L" — it's **2024 and 2026**. A filter that keeps most of 2025 while cutting the losing years is the win condition.
