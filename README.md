# ACD SPX Bot — an honest attempt at a trading edge

A systematic options-trading bot built on Mark Fisher's **ACD method** (*The Logical Trader*), backtested on three years of real S&P 500 option prices, stress-audited for the bugs that fool most backtests, and now running live paper trading against Schwab market data.

**The point of this project is not the return number. It's the process:** every strategy here had to survive hostile audits, pre-registered tests, and its own inventor's retractions — and most of them didn't. What's left is small, filtered, and honest about what it hasn't proven yet.

---

## The strategy, in depth

### The core idea (Fisher's ACD)

Every morning the market spends its first 15 minutes carving out an **opening range**. ACD draws a trigger line — the **A-level** — a calibrated distance beyond that range (~0.18% of price). Then one rule separates signal from noise: price must not just *touch* the line, it must **hold beyond it for half the opening-range duration** (7.5 minutes). Time confirms the move, not price alone.

- Price pushes past the A-level and **holds** → a real breakout (`a_held`). The market has picked a direction with enough conviction to sustain it.
- Price pokes past and **snaps back** → a failed breakout. Fisher's book said fade it; our data (and the modern Fisher himself) say that trade died with 24-hour markets. We don't take it — see the graveyard below.

### Why options, not stock

We tested the identical signals as pure directional buy/sell of the index: **dead flat over 3 years** (+2.2% before friction, negative after). The edge only exists in option form:

- **The trade:** a same-day (0DTE) debit spread — buy the strike nearest the breakout, sell one 25 points further in the breakout's direction. Defined risk (the debit), convex payoff.
- **Why it works when stock doesn't:** breakout trading is a right-tail business. Wins only ~45% of the time — but a real trend day pays 2-3× the debit while a dud costs 1×. Stops on stock got whipsawed to death in a median of **4 minutes**; the option's defined risk needs no stop at all.
- **The exit doctrine (tested three separate ways):** hold to expiry. Profit targets, time stops, and active management all amputate the exact tail the strategy lives on.

### The two production candidates

Both trade only `a_held` breakouts, only when the day is **clean** — no failed pierce earlier in the session (a prior fake-out marks the day as trap-prone; skipping those days improved every metric it touched):

| | **"The Earner"** | **"The Tank"** |
|---|---|---|
| Extra filter | skip CPI-release days | breakout must ALSO clear yesterday's pivot zone |
| Trades (3yr) | 167 (~1/week) | 60 (~1 per 2 weeks) |
| Win rate | 48% | **58%** |
| P&L ($10k, 3% risk compounding) | **+$16,586 (+166%)** | +$11,958 (+120%) |
| Max drawdown | −20% | **−12%** |
| Years positive | 4 of 4 | 4 of 4 |
| Profit from the one great year (2025) | 66% | **only 40%** |

The Tank's extra demand — two independent resistance structures broken in one move (Fisher: "two signals acting in concert") — trades frequency for robustness. At equal drawdown budgets it actually out-earns the Earner, because robustness converts into sizing headroom.

Both ban FOMC days (tested: 15% win rate on Fed days) and hold every position to cash settlement.

---

## Results across the whole project

| Test | Verdict |
|---|---|
| Full ACD, SPX underlying (buy/sell) | **flat** — no edge in any of 12 parameterizations |
| Full ACD as bought option spreads (all setups) | **loses** — theta on a zero-edge signal |
| Fades (failed breakouts), bought spreads | **−$10k** / 56% expire worthless |
| Fades as sold credit spreads | **−$5k** — better, still negative every year |
| Macro "number line" regime layer | **non-predictive** — 4 independent strikes |
| Breakouts, held, filtered (the campaign) | **the survivors** — table above |
| 7-hypothesis research campaign (22 variants) | 2 mechanisms adopted, both predicted before testing |

Full logs: [`results/hypotheses/`](results/hypotheses/) — one markdown log per hypothesis, every variant's numbers, and a [FINAL-BREAKDOWN](results/hypotheses/FINAL-BREAKDOWN.md) with an explicit multiple-testing honesty section.

---

## 🪦 The graveyard (strategies this project killed)

Honest quant work is mostly a cemetery. Residents so far:

1. **1DTE iron condors (Option Alpha style)** — ruled out in research: ~$20/trade edge, 27% win rate, brutal psychology. "Fool's gold."
2. **The crude-oil ACD bot** — graded 79/100 "Deploy" by its first backtest. Then a 7-auditor review found 5 engine bugs (a hidden filter dropping 82% of signals, Sunday bars deflating volatility 12%, a 46-minute "45-minute" opening range...). Rules were re-committed to git **before** the corrected rerun. Both pre-registered tests failed. +$8,650 became −$2,750. Abandoned.
3. **V5, the fade bot** — the project's former crown jewel: +244%, 82% win rate over 119 trades. An audit later found the fade entries used a look-ahead (entering at the pierce extreme — a price only hindsight can buy). Re-priced on the corrected engine, its trade universe lost $4,852. The edge was the bug.
4. **Fades in general** — killed three ways (bought, sold, filtered), then confirmed dead by Fisher himself in a post-book webinar: *"The reversals don't work anymore because nobody really panics anymore — 24-hour trading."*
5. **The number-line macro layer** — Fisher's multi-day regime score. Non-predictive on crude (dedicated study), non-predictive on SPX (four independent tests). Notably absent from Fisher's own modern process.

## 🐛 The bug museum (what almost fooled us)

- **The $9,594 phantom trade:** a single `0.0` price print in cached data filled a stop at zero and "lost" 96% of the test account in one row. Now caught by a causal hygiene filter.
- **The settle that wasn't:** option-feed spot freezes at ~16:01; settling there instead of the official close was wrong by a median 2.5 points — enough to flip 15% of trades' outcomes.
- **Time-scrambled files:** ~0.7% of cached CSVs had out-of-order rows; one day's "close" was actually its 2:32pm print, 73 points off.
- **The label that knew the future:** one setup's classification depended on the daily close — decided hours after its entry time. Never traded, defused anyway.
- **The lesson generalized:** look-ahead isn't one bug, it's a *class*. It lives in data cleaning (a filter that knows the day's median), in labels, in fills (same-bar quotes predate the signal), and — most dangerously — in *strategy selection itself* (tuning on the data you score on). This repo's defenses, in order: hostile multi-auditor reviews, cent-exact trade replays by independent re-implementation, pre-registered rule commits, and a held-out exam dataset the chosen configs have never touched.

---

## Where it stands now

- ✅ Backtest campaign complete (2023-2026, real NBBO minute data, audited engine)
- 🟢 **Live paper trading is on:** both bots launch automatically each market morning against live Schwab data, decide with the byte-identical engine, record fills at real XSP strikes/quotes, and publish an evening P&L report. No order code exists anywhere in this repo — by design.
- ⏳ **The exam:** 2021-2023 data (including the 2022 bear market) gets pulled next, configs frozen first, run once. That's where the Earner and the Tank live or die.
- ⏳ Quiet-day iron condor overlay: spec locked and committed *before* its data arrived; runs when the 75k-contract options-data pull completes.

## Repository map

| Path | Contents |
|---|---|
| `bot/acd_micro.py`, `acd_macro.py` | the signal engine (levels → events → setups), pure & self-tested |
| `bot/backtest_acd_spx_*.py` | the audited backtest drivers (underlying + options) |
| `bot/experiments_spx.py` | the hypothesis-campaign harness (every variant reproducible) |
| `bot/backtest_portfolio_condor.py` | the locked condor + combined-book spec |
| `bot/live_paper_engine.py`, `schwab_*.py` | live paper stack (data-only, no order code) |
| `results/` | every writeup, every hypothesis log, the recommended configs' trade ledgers |
| `docs/` | research synthesis, broker setup guide |

## Honesty footer

Backtests use vendor minute-NBBO data with known idealizations (XSP modeled as SPX÷10; official settlement approximated by the end-of-day chain print; 1-minute fill granularity). All results are **in-sample** until the frozen configs pass (a) the 2021-23 held-out test and (b) live paper months. If they fail, this repo becomes a well-documented case study in disciplined overfitting — which would also be worth reading.

*Built by George Manavazian with Claude (Anthropic) as pair programmer and adversarial auditor.*
