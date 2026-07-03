# PRE-REGISTERED EXAM — Earner (C4) & Tank (C5) on 2021-2023 held-out data

**Committed 2026-07-03, BEFORE any 2021-2023 SPX intraday/options data exists in this
repository.** The git timestamp of this file is the proof. After the exam data is
pulled, NOTHING in this document may change; the configured runs execute once and the
results stand. Any deviation must be reported as a deviation.

## Exam window

**2021-07-06 → 2023-07-03** (the two years immediately preceding the playground, per
the trailing-5-year data policy). No overlap with the 2023-07-05 → 2026-06-26
playground on which every parameter below was chosen.

## Frozen configurations (identical code paths to the playground: `bot/experiments_spx.py`)

Common to both: SPX InstrumentSpec defaults (15-min opening range 09:30–09:45 ET,
A = 0.18% / C = 0.21% of OR midpoint, hold = 7.5 min, 12:00 A-cutoff); trade only
`a_held` intraday setups; **clean-coil filter** (skip any setup preceded by a failed-A
event either side, same day); one trade per day (earliest surviving setup); 0DTE debit
spread — long the 5-grid strike nearest entry, short 25 SPX pts further in trade
direction; entry at the first bar STRICTLY after the signal minute, debit = long.ask −
short.bid; hold to expiry; settle vs the EOD chain underlying print; $10,000 start;
risk 3% of current equity on (debit + 2×slip); slippage 0.05/leg (report 0/0.10/0.20
as sensitivity); FOMC days banned; no macro gate.

- **EARNER (C4):** + CPI-release days banned.
- **TANK (C5):** + the day must also emit `a_through_pivot` (A cleared the entire
  prior-day pivot band), per `through_pivot_day` in `bot/backtest_portfolio_condor.py`.
  No CPI ban.

**0DTE availability rule:** trade only days where a same-day SPX/SPXW expiration
existed (before Apr/May 2022, dailies were Mon/Wed/Fri only; Tue/Thu were added then).
Determination is ex-ante (listing calendars are known in advance). Days without a 0DTE
expiry are recorded as `no_expiry`, not traded, not counted against the bots.

## Frozen event calendars for the exam window

FOMC decision days (2021-2022; 2023 H1 already in `bot/filters.py`):
2021-01-27, 2021-03-17, 2021-04-28, 2021-06-16, 2021-07-28, 2021-09-22, 2021-11-03,
2021-12-15, 2022-01-26, 2022-03-16, 2022-05-04, 2022-06-15, 2022-07-27, 2022-09-21,
2022-11-02, 2022-12-14.

CPI release days (Earner ban only):
2021-07-13, 2021-08-11, 2021-09-14, 2021-10-13, 2021-11-10, 2021-12-10,
2022-01-12, 2022-02-10, 2022-03-10, 2022-04-12, 2022-05-11, 2022-06-10, 2022-07-13,
2022-08-10, 2022-09-13, 2022-10-13, 2022-11-10, 2022-12-13,
2023-01-12, 2023-02-14, 2023-03-14, 2023-04-12, 2023-05-10, 2023-06-13.

(These lists were written from public schedules without consulting any price data. If
a date is later found to be clerically wrong, the correction and its P&L impact must
both be reported.)

## Pass / fail criteria (chosen now, argued never)

A configuration **PASSES** the exam iff, at 0.05/leg slippage over the full window:
1. Total P&L > 0;
2. Max drawdown does not exceed 1.5× its playground value (Earner: ≤30%; Tank: ≤18%);
3. No look-ahead or engine defect is discovered during the run (any fix voids and
   restarts the exam with a fresh pre-registration).

Reported regardless of outcome: trades, win rate, P&L, max DD, by-year table, slippage
sensitivity, and the same numbers for the 2022 bear-market months specifically.

**Interpretation grid (agreed in advance):**
- Both pass → proceed to sizing decisions and extended paper trading with real weight.
- One passes → the survivor advances; the failure is written up, not rescued.
- Both fail → the campaign's edges were curve-fit; the public repo gets the
  "disciplined overfitting case study" writeup. No re-tuning on exam data, ever.

## Execution plan (after the ladder pull frees the API lane)

1. Pull 2021-07-06 → 2023-07-03: daily 0DTE chains (strike grids + EOD spot), the
   per-day near-ATM anchor contract (underlying path), and the signal-day legs the two
   configs request. Estimated ~4-6k requests.
2. Extend `filters.FOMC_DATES` and the CPI list with the frozen dates above (code
   change committed before the run).
3. Run both configs ONCE via `bot/experiments_spx.py` machinery. Publish results to
   `results/spx/exam/` and the public repo — pass or fail.
