# Research synthesis — 5 documents, 5 agents (2026-07-02)

Sources: three YouTube ORB transcripts (research/), the ACD webinar+interview transcripts (`ACD strategy.docx`), and a targeted re-mine of *The Logical Trader* (scan note: book pp.24-25 missing — the early-vs-late-A discussion leaf).

## The headline: our backtest and post-book Fisher agree on everything

The webinar/interview transcripts are Fisher YEARS after the book we implemented. Point by point against our 3-year SPX results:

| Our finding (independent, data-first) | Fisher, post-book |
|---|---|
| Fades lose in every structure | "Reversals don't work anymore — nobody panics anymore, 24-hour trading." Only exception he grants: pre-weekend/holiday. |
| Number-line/macro layer non-predictive (4 strikes) | Number line never mentioned once in his current process. |
| FOMC days toxic (15% win) | "I trade data-free days. I stay away during all the report times." |
| Entries before 10:30 lost, later won | His equity-index window is ~2.5h before the close; his live morning trade carried a hard "half off by 11:15 without follow-through" time stop. |
| Unfiltered breakouts only marginally positive | "If you just trade A's and C's they don't work anymore — you have to be more selective" (volume/time filter). |
| SPX weakest instrument | "We don't really use indexes — drift factor, too many outside influences." Energies preferred. |
| Breakout longs 3× shorts on SPX (+$10.2k vs +$3.3k) | The drift factor: "hard to trade the S&P from the short side — money keeps filtering in." |

**Important precision on fades:** our `failed_a` IS the book's rubber-band trade (unconfirmed touch, stop at the A price) — implemented faithfully. The book (2001) celebrates it ("made 126 ticks, risked 4"); modern Fisher retracts it; our data sides with modern Fisher. The strategy didn't fail from mis-implementation — the market it worked in no longer exists.

## The three YouTube docs (graded)

- **"Why Most Traders Lose"** — flagship fix is the fade re-entry (our data falsifies it); fixed 1.5R target amputates the tail our profits live in; only crumb = higher-timeframe trend-alignment filter. Evidence: 8 hand-picked days on gold. Grade: D, one testable crumb.
- **"MAX way"** — one real idea: the 6-7-inside-candles coil rule (day that coils in the OR ~90 min then breaks tends to run — matches our 10:30–12:00 winners). No stops/targets/backtests, 40% ad. Grade: C-, one testable idea.
- **"3 Things"** — single-stock catalyst ORB, not index-applicable; volume-confirmation hand-wave; even its "reversal" play is a breakout, never a fade. Grade: D.

## Ranked testable hypotheses (playground = 2023-26 cache; exam = 2021-23 pull stays untouched)

1. **Cut fades from the bot.** Every source + our 4-years-every-structure data + the inventor's own retraction. In-sample effect known (+$14.7k breakouts-only but regime-concentrated); the question walk-forward must answer is robustness, not direction.
2. **Pivot-confluence breakout filter** (book Ch.3 + his live-trade checklist): A *through* the pivot range = double signal; pivot sitting just beyond the A = skip. Also the pivot-flip precondition (open one side of 3-day rolling pivot, break the other, then the A). Fully codeable from data we have.
3. **Modern-Fisher parameters:** 20-min OR for S&P (book's 15 is stale per the webinar) + A/C = 18-20% of ATR(10) benchmarked vs ATR(20). Cheap sweep.
4. **Coil-then-break filter:** require N bars inside the OR before the breakout (mechanism-grounded version of our empirical 10:30+ finding — the two independently point at the same structure).
5. **Data-free days:** extend the FOMC ban to CPI/NFP/PPI release dates (Fisher avoids all report days). Needs a release calendar.
6. **Time-stop exit for breakouts** (his "by 11:15, no new low → half off"): tension with our hold-to-expiry finding; test as a variant, expect it to hurt 0DTE convexity.
7. **Parked — volume/time Fisher-bar filter:** his #1 modern filter, but SPX index has no volume in our quote-derived bars. Revisit if we source index/ES volume.

## Discipline reminder

All 7 hypotheses formed from sources outside our dataset — the clean kind. Testing happens on 2023-26 (playground). The 2021-23 pull, when made, is the exam: config frozen and committed before first contact, run once, result stands.
