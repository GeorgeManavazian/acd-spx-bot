# acd-spx-bot

Mark Fisher's ACD opening-range breakout, traded as same-day (0DTE) SPX debit spreads. I pre-registered a held-out test, ran it once, and it failed. The registration and the result are both in this repo, along with every per-trade ledger.

## Thesis

Fisher's ACD method (*The Logical Trader*, 2001) says the opening range sets the day's reference levels, and that a clean break of those levels with follow-through tends to keep going. I traded that view as a 0DTE SPX debit spread because the most I can lose is the debit and the payoff grows if the move runs. For it to work, breakouts have to keep going often enough and far enough to pay back the debit plus slippage, and honestly I couldn't answer that in-sample. Score 22 variants on one 3-year dataset and one of them wins by chance. So I fixed a window, froze two configurations, wrote numeric pass bars and an interpretation grid, committed all of it to git before any exam data existed, and then ran the exam once.

## What I tested and what I learned

- `docs/exam-preregistration-2026-07-03.md` is the core of the repo. It fixes the held-out window (2021-07-06 to 2023-07-03), the two configurations (the Earner and the Tank), the pass bars (P&L above zero at $0.05 per leg slippage; drawdown within 1.5x the in-sample figure), and what each outcome would mean. I committed it 2026-07-03 at 01:48, before I had any exam data, and the results at 20:48 the same day. `bot/exam_run.py` refuses a second run once results exist, which I built in so I couldn't talk myself into a second try.
- Held-out result, 502 sessions: the Earner lost $599 on a $10,000 account (125 trades, 46% win, max drawdown 29.8%), and the Tank lost $436 (38 trades, 42% win, max drawdown 17.2%). Both failed the P&L bar. Both stayed inside their drawdown bars (30% and 18%), so nothing blew up, the edge just wasn't there. Every slippage setting I ran, 0, 0.10 and 0.20 per leg, came out negative.
- In-sample, same two configurations, 2023-07-05 to 2026-06-26 (746 sessions): the Earner made $16,586 (+166%, 167 trades, 48% win, 20% drawdown) and the Tank $11,958 (+120%, 60 trades, 58% win, 12% drawdown). I picked them as the two survivors of 7 hypotheses and 22 variants, and watching them go from that to a loss was genuinely frustrating.
- One thing I noticed in the held-out run, and I didn't expect it. The Earner made money through the 2022 bear market (+$1,534 over 70 trades) and then lost $2,876 in the first half of 2023, the six months right before its training window. The Tank sat near breakeven the whole time. The signal might like one regime, but I can't tell which from two years.

## Graveyard

Every other way I tried the idea lost too. Over one day on SPX, the spread cost more than the breakout paid, and the same held for the fade.

| Idea | Number | Lesson |
|---|---|---|
| ACD on the SPX underlying, no options, 2023-07 to 2026-06 | +$220 (+2.2%) before friction, −$529 at $0.05 per side, 449 trades, 17% win | SPX noise hit the tight ACD stops within minutes of the open |
| Fades (failed breakouts) bought as debit spreads | −$10.1k over 3 years | A stall doesn't pay a bought spread, theta ate it |
| Fades sold as credit spreads | −$5.0k, negative every year | Lost half as much, but it still lost |
| Fisher's number-line macro layer | non-predictive in four independent SPX tests; gated +$214 vs ungated +$8,512 | The macro gate didn't help a one-day trade at all |
| Quiet-day iron condor overlay | condor leg negative in all 16 grid cells (−$486 to −$8,023) despite 58-73% win rates | The 30-40% of quiet mornings that broke out anyway cost more than all the others paid |
| Time stops on the breakout spread | win rate 28-31%, +$1.6k to +$5.8k against +$14.7k held to expiry | Winning spreads sit underwater most of the day, so checking early just sold the low |
| Modern-Fisher parameters (20-minute range, ATR-scaled levels) | +$5.4k to +$13.9k against a +$14.7k baseline | The pit-tuned parameters did worse here, every version of them |
| 1DTE iron condors | ruled out in research at about $20 per trade, 27% win | Not enough premium to cover one bad afternoon |

## How it was tested

- Data, in-sample: IVolatility 1-minute NBBO for SPX options, 746 sessions, 2023-07-05 to 2026-06-26, 1,785 option legs. Held-out: Databento OPRA 1-minute quotes plus SPY 1-minute bars, 2021-07-06 to 2023-07-03, 502 sessions. I went with Databento for the held-out window because it reaches further back.
- Validation: I scored 7 hypotheses and 22 variants in-sample, then froze two configurations with numeric pass bars and FOMC/CPI calendars before any exam data existed. Both failed, and I did no re-tuning on the exam data afterward.
- Friction: $0.05 per leg slippage, $0 commissions, 3% of current equity risked per trade, hold to expiry, one trade per day.
- Known gaps: I modeled XSP as SPX/10, so some modeled strikes do not exist. The exam underlying is SPY×10 (median 10.3-point basis to SPX), which shifts strike anchoring by about two strikes, and 78 of 502 exam days used the SPY×10 close as the settle. I approximated settlement with the end-of-day chain print. 1-minute fills. CPI dates approximate. The Tank's 60 in-sample and 38 exam trades give wide error bars. No 10-year confirmation.

## Where it stands

Paused since July 2026. I asked one question and the answer was no, and I'm okay with that. The pre-registration, both exam ledgers and every hypothesis log are committed. I built a paper-trading stack (Schwab market data, no order code) but never ran it long enough for a track record, so there are no paper ledgers here. If I come back to it, I'd run the same pre-registered design on 60-minute opening ranges, where follow-through has more room to work, or the same test on a less efficient index.

## What this is not

Paper trading only. Not investment advice. I'm not claiming a live edge.

## How to run it

```
git clone https://github.com/GeorgeManavazian/acd-spx-bot
cd acd-spx-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python bot/acd_micro.py     # engine self-test, no data needed
python bot/acd_macro.py     # macro-layer self-test
```

The backtest drivers (`bot/backtest_acd_spx_*.py`, `bot/experiments_spx.py`) read cached minute data from `data_cache/`, which I don't commit. Rebuilding it needs `IVOL_API_KEY` for 2023-26 and `DATABENTO_API_KEY` for the exam window (`bot/pull_exam_databento.py`). Every result above is under `results/exam/` and `results/hypotheses/`. `bot/exam_run.py --confirm` exits if `results/exam/EXAM-RESULTS.md` exists. I built it that way on purpose.

## Built with

Python, pandas, IVolatility (in-sample minute NBBO), Databento (held-out window), schwab-py (paper data feed). Built with AI-assisted development (Claude Code); the research questions, hypotheses, validation choices, and conclusions are mine.
