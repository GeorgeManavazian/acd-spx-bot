# H6 — Time-stop exits (Fisher: "time is more important than price")

**Source:** book pp.19, 61, 72, 147 + the webinar's live "half off by 11:15 without a new low." Tension going in: our data said hold-to-expiry beats managing, because 0DTE debit-spread profit is all right tail.

**Implementation** (`bot/experiments_spx.py::make_timestop_pricer`): one-shot check at entry+T on real closeable values (long.bid − short.ask); not working (value ≤ entry debit) → exit there, crossing 4 legs; working → ride to settle.

| Variant | Trades | Win | P&L | MaxDD | Yrs+ |
|---|---|---|---|---|---|
| BASELINE (hold) | 416 | 43% | +$14,705 | −29% | 2/4 |
| a T=60min | 416 | 28% | +$1,609 | −43% | 3/4 |
| b T=120min | 416 | 31% | +$5,796 | −31% | 2/4* |

## Verdict

**Rejected, decisively.** Time stops gut the win rate (43%→28%) and the P&L. The mechanism is clear: a 0DTE ATM debit spread marks *underwater* for most of its life even on eventual winner days (theta + spread), so a "not working yet?" check at T=60/120 amputates winners at their low. Fisher's time stops are for linear futures, where an un-moving position has zero carry; an option position has *negative* carry priced in and needs its whole runway. Third confirmation of the hold doctrine (after the 50%-target test and the grid). Do not manage 0DTE debit spreads intraday.
