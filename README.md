# acd-spx-bot

Mark Fisher's ACD opening-range breakout, expressed as same-day (0DTE) SPX debit spreads and put through a pre-registered held-out test. The test said no. Registration, result, and every per-trade ledger are here.

## Thesis

Fisher's ACD method (*The Logical Trader*, 2001) says the opening range sets the day's reference levels, and a clean break of those levels with follow-through tends to carry. A 0DTE SPX debit spread is a capped-risk way to express that one-day directional view: the most I can lose is the debit, and the payoff is convex if the move runs. What has to be true is that breakouts continue often enough, and far enough, to cover the debit plus slippage. An in-sample search cannot answer that, because 22 variants scored on one 3-year dataset will always produce a winner. So the point of the project is the pre-registration: window, two frozen configurations, numeric pass bars, and an interpretation grid committed to git before any exam data existed, then one run.

## What I tested and what I learned

- The pre-registration is the product. `docs/exam-preregistration-2026-07-03.md` fixes the held-out window (2021-07-06 to 2023-07-03), the two configurations (the Earner and the Tank), the pass bars (P&L above zero at $0.05 per leg slippage; drawdown within 1.5x the in-sample figure), and what each outcome would mean. Registration committed 2026-07-03 at 01:48, results at 20:48 the same day; `bot/exam_run.py` refuses a second run once results exist. Takeaway: decide what counts as failure before you can see the data.
- Held-out result, 502 sessions: the Earner lost $599 on a $10,000 account (125 trades, 46% win, max drawdown 29.8%); the Tank lost $436 (38 trades, 42% win, max drawdown 17.2%). Both failed the P&L bar and both stayed inside their drawdown bars (30% and 18%), so the failure mode is no edge rather than a blow-up. Slippage at 0, 0.10 and 0.20 per leg was negative in every run. Takeaway: the in-sample edge did not survive out of sample, which is the question a held-out test exists to answer.
- The same configurations in-sample, 2023-07-05 to 2026-06-26 (746 sessions): the Earner made $16,586 (+166%, 167 trades, 48% win, 20% drawdown) and the Tank $11,958 (+120%, 60 trades, 58% win, 12% drawdown). They were the two survivors of 7 hypotheses and 22 variants. Takeaway: a good in-sample number is a candidate, not a result.
- One observation from the held-out run: the Earner was profitable through the 2022 bear market (+$1,534 over 70 trades) and lost $2,876 in the first half of 2023, the six months just before its training window. The Tank sat near breakeven throughout. Takeaway: the signal may have a regime it likes, but two years is not enough to say which.

## Graveyard

Every other expression of the idea also lost. On SPX at the one-day horizon, neither the breakout nor its failure was mispriced enough to pay for the spread.

| Idea | Number | Lesson |
|---|---|---|
| ACD on the SPX underlying, no options, 2023-07 to 2026-06 | +$220 (+2.2%) before friction, −$529 at $0.05 per side, 449 trades, 17% win | SPX noise crosses tight ACD stops within minutes |
| Fades (failed breakouts) bought as debit spreads | −$10.1k over 3 years | A fade predicts a stall; a bought spread needs a move, and theta ate it |
| Fades sold as credit spreads | −$5.0k, negative every year | Halves the loss without changing the sign |
| Fisher's number-line macro layer | non-predictive in four independent SPX tests; gated +$214 vs ungated +$8,512 | A multi-day regime score adds nothing to a one-day trade |
| Quiet-day iron condor overlay | condor leg negative in all 16 grid cells (−$486 to −$8,023) despite 58-73% win rates | The 30-40% of quiet mornings that break cost more than the rest pay |
| Time stops on the breakout spread | win rate 28-31%, +$1.6k to +$5.8k against +$14.7k held to expiry | The spread marks underwater most of the day even when it wins; an early check sells the low |
| Modern-Fisher parameters (20-minute range, ATR-scaled levels) | +$5.4k to +$13.9k against a +$14.7k baseline | Parameters tuned for futures pits do not transfer |
| 1DTE iron condors | ruled out in research at roughly $20 per trade, 27% win | Too little premium to survive one bad afternoon |

## How it was tested

- Data, in-sample: IVolatility 1-minute NBBO for SPX options, 746 sessions, 2023-07-05 to 2026-06-26, 1,785 option legs. Held-out: Databento OPRA 1-minute quotes plus SPY 1-minute bars, 2021-07-06 to 2023-07-03, 502 sessions. In-sample data is from IVolatility; the held-out window is from Databento because it reaches further back.
- Validation: 7 hypotheses and 22 variants scored in-sample, then two configurations frozen with numeric pass bars and FOMC/CPI calendars written before any exam data existed. Both failing meant no re-tuning on the exam data.
- Friction assumptions: $0.05 per leg slippage, $0 commissions, 3% of current equity risked per trade, hold to expiry, one trade per day.
- Known gaps: XSP modeled as SPX/10, so some modeled strikes do not exist. Exam underlying is SPY×10 (median 10.3-point basis to SPX), shifting strike anchoring by about two strikes; 78 of 502 exam days used the SPY×10 close as the settle. Settlement approximated by the end-of-day chain print. 1-minute fills. CPI dates approximate. The Tank's 60 in-sample and 38 exam trades give wide error bars. No 10-year confirmation.

## Where it stands

Paused since July 2026. Research is complete for the question I asked, and the answer was no. The pre-registration, both exam ledgers, and every hypothesis log are committed. A paper-trading stack (Schwab market data, no order code) was built but never run to a track record; there are no paper ledgers here. The registered question has its answer, so the next step is a new question. If I return to it: the same pre-registered design on 60-minute opening ranges, where the follow-through argument has more room, or the same test on a less efficient index.

## What this is not

Paper trading only. Not investment advice. Does not claim a live edge.

## How to run it

```
git clone https://github.com/GeorgeManavazian/acd-spx-bot
cd acd-spx-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python bot/acd_micro.py     # engine self-test, no data needed
python bot/acd_macro.py     # macro-layer self-test
```

The backtest drivers (`bot/backtest_acd_spx_*.py`, `bot/experiments_spx.py`) read cached minute data from `data_cache/`, not committed; rebuilding it needs `IVOL_API_KEY` for 2023-26 and `DATABENTO_API_KEY` for the exam window (`bot/pull_exam_databento.py`). Every result above is already under `results/exam/` and `results/hypotheses/`. `bot/exam_run.py --confirm` exits if `results/exam/EXAM-RESULTS.md` exists; that is deliberate.

## Built with

Python, pandas, IVolatility (in-sample minute NBBO), Databento (held-out window), schwab-py (paper data feed). Built with AI-assisted development (Claude Code); the research questions, hypotheses, validation choices, and conclusions are mine.
