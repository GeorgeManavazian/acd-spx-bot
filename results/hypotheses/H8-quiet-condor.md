# H8 — Quiet-day iron condor (the combined book) — REJECTED

**Spec:** locked in `bot/backtest_portfolio_condor.py` and committed BEFORE the condor
data was pulled (the 218 quiet-day cells had never been priced by anyone until this
run). Condor at 12:01 on days with no A-family event all morning; shorts at the first
5-grid strikes beyond the OR edges, 25-wide wings, real 4-leg NBBO, exits {hold,
buyback-50%, buyback-25%, flat-15:00}, shared compounding equity with each bot's
breakout trades. Data: 615 legs pulled, 0 failures; 217/218 quiet days priceable.

## The grid (16 cells, all four condor exits × both bots × 3%/5%)

**The condor's own P&L is negative in every single cell** — from −$486 (tank/bb25/3%)
to −$8,023 (earner/hold/5%) — despite win rates of 58-73%. Full table in the run log;
representative rows at 3%:

| Book | Condor exit | Condor P&L | Condor win | Combined final | MaxDD | vs bot alone |
|---|---|---|---|---|---|---|
| Earner | hold | −$3,003 | 59% | $23,172 | −24% | worse (alone: $26,586 / −20%) |
| Earner | bb50 | −$2,157 | 73% | $26,930 | −18% | ≈ same money, ≈ same risk |
| Tank | bb25 | −$486 | 64% | $21,128 | −13% | worse (alone: $21,958 / −12%) |
| Tank | hold | −$1,994 | 59% | $18,862 | −13% | worse |

The "best exit per bot" question has an answer (buybacks beat holding — cutting the
tail loss is right for a SHORT-premium position, the exact mirror of the breakout
lesson), but it's optimizing the arrangement of deck chairs: no exit style gets the
condor above zero.

## Why it loses (same disease, third diagnosis)

A quiet morning does predict a quieter afternoon — the win rates prove it (58-73%
of condors finish profitable). But the payoff table is rigged the same way the credit
fades were: collect ~$70-90, lose up to ~$160-180 when an afternoon move blows a side.
The ~30-40% of quiet mornings that produce afternoon breaks (Fisher's own webinar:
6-7 inside candles → "a larger than expected move late in the afternoon or a choppy
day") cost more than the quiet majority pays. **Selling SPX premium at
opening-range-anchored strikes has now failed three independent tests** (credit fades,
quiet condors held, quiet condors managed) — this market prices its stillness fairly.

## Verdict

**Do not add the condor. The bots stay pure breakout.** The 218 quiet days remain
untraded — and that's a feature: the machine's edge is knowing when it has none.

Possible future variant (NOT tested, ladder data enables it): shorts further OTM
(wider berth for the afternoon drift) and/or VIX-conditioned credit floors. Any such
test is a new hypothesis with its own pre-commitment — the strikes-at-the-range
version is dead as specified.
