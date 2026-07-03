# FINAL BREAKDOWN — Hypothesis Campaign 2026-07-02

**Setup:** 7 research-derived hypotheses tested one by one on the BOT v2 baseline (a_held breakouts only, 0DTE 25-wide debit spread bought at real next-bar NBBO, held to official settle, FOMC banned, no macro gate, $10k @ 3% risk compounding, 0.05/leg slippage), then combinations. 746 days, 2023-07 → 2026-06. All engines carry the 2026-07-02 triple-audit fixes (no look-ahead; every trade replayable to the cent).

## Master scoreboard

| ID | What | Trades | Win | P&L | MaxDD | Yrs+ | Verdict |
|---|---|---|---|---|---|---|---|
| BASE | H1 fades cut | 416 | 43% | +$14,705 | −29% | 2/4 | adopted; regime-hostage |
| H2a | through-pivot days only | 127 | 46% | +$8,652 | −25% | 3/4 | combo ingredient |
| **H2b** | skip pivot-ahead | 308 | 43% | +$15,096 | −23% | 4/4 | **adopt** |
| H2c | pivot-flip only | 150 | 43% | +$1,359 | −24% | 2/4 | reject |
| H2d | anti-flip | 143 | 41% | +$2,518 | −19% | 2/4 | reject |
| H3a-d | OR20 / ATR10 A-C | 167-272 | 43-44% | +$5.4-13.9k | −21…−29% | 2-3/4 | not adopted |
| H4a | entry ≥10:30 | 252 | 42% | +$6,009 | −26% | 2/4 | reject (see H4c) |
| H4b | entry ≥11:15 | 91 | 42% | +$2,547 | −24% | 3/4 | reject |
| **H4c** | clean coil (no prior failed-A) | 178 | 48% | +$17,670 | −18% | 4/4 | **adopt — campaign star** |
| H5a | +NFP ban | 388 | 43% | +$12,461 | −29% | 2/4 | reject |
| **H5b** | +CPI ban | 393 | 43% | +$17,486 | −25% | 2/4 | adopt (provisional) |
| H6a/b | time stops 60/120min | 416 | 28-31% | +$1.6-5.8k | −31…−43% | — | **reject decisively** |
| H7 | volume/time filter | — | — | — | — | — | parked (no index volume data) |
| C1 | coil + pivot-not-ahead | 140 | 46% | +$9,985 | −19% | 3/4 | |
| C2 | C1 + CPI | 131 | 47% | +$10,960 | −15% | 3/4 | |
| C3 | C1 + CPI + NFP | 123 | 48% | +$13,792 | −15% | 4/4 | smoothest equity |
| **C4** | coil + CPI | 167 | 48% | **+$16,586** | −20% | 4/4 | **recommended: P&L champion** |
| **C5** | coil + through-pivot | 60 | **58%** | +$11,958 | **−12%** | 4/4 | **recommended: robustness champion** |
| C6 | C2 on ATR10 | 100 | 43% | +$2,271 | −28% | 3/4 | reject |

## The five things this campaign established

1. **The coil filter (H4c) is the discovery.** "Only trade the day's FIRST conviction move — skip any day that already printed a failed pierce." It improves every configuration it enters: win rate +5pts, drawdown −11pts, and it repairs both losing years. Mechanism was predicted by two independent sources before testing.
2. **Fisher's book rule about pivots-in-the-path (H2b) works as printed** (p.57, 2001). A 25-year-old rule, positive on 2026 data.
3. **Never manage a 0DTE debit spread intraday.** Time stops (H6) and profit targets (earlier grid) both amputate the right tail that IS the strategy. Third independent confirmation.
4. **Not everything from the research survived contact:** modern-Fisher parameters (H3) dilute; the webinar's pivot-flip (H2c) doesn't generalize; NFP days are good, not bad, for breakouts.
5. **The two recommended configs:**
   - **C4 "earner"** — coil + CPI ban: +$16,586 (+166%), 48% win, −20% DD, all years positive, ~1 trade/week.
   - **C5 "tank"** — coil + through-pivot: +$11,958 (+120%), 58% win, −12% DD, all years positive, 2025 only 40% of profit — but just 60 trades/3yr.

## Equity summary (recommended configs, $10k start)

| | 2023H2 | 2024 | 2025 | 2026H1 | Final |
|---|---|---|---|---|---|
| C4 | +$3,662 | +$488 | +$10,869 | +$1,567 | **$26,586** |
| C5 | +$3,450 | +$1,483 | +$4,816 | +$2,209 | **$21,958** |

## Honesty section (read before believing)

- **22 variants were scored on one 3-year dataset.** The best cells are optimistically biased by selection, full stop. Protections: the two core mechanisms (coil, pivot-ahead) were hypothesized from outside sources *before* testing; rejections (H3, H6, H2c) were accepted without rescue attempts; verdicts weighted stability over peak P&L.
- The CPI/NFP asymmetry (H5) was *discovered*, not predicted — least-trusted adoption; its date lists are approximate.
- C5's 60 trades = wide error bars on every stat.
- Structural idealizations remain: XSP = SPX/10 (strike grid doesn't fully exist), settle = EOD chain print (close to but not the official SPXW settle), 1-minute fill granularity.
- **Nothing here is validated.** The 2021-23 exam data (pending pull) is where C4 and C5 go to live or die — config frozen and committed before first contact. If they fail there, this whole document becomes a case study in disciplined overfitting.

## Artifacts

- Per-hypothesis logs: `H1-cut-fades.md` … `H6-time-stops.md`, `C-combinations.md`
- Raw run tables: `singles-raw.md`, `combos-raw.md`
- Recommended-config trade ledgers: `C4-trades.csv`, `C5-trades.csv`
- Harness: `bot/experiments_spx.py` (every variant reproducible)
