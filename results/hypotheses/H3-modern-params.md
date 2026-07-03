# H3 — Modern Fisher parameters (OR 20-min, A/C from ATR(10))

**Source:** the webinar — "we don't use 5-minute opening ranges anymore... S&P = 20 minutes"; A/C = 18-20% of the 10-day average true range (vs the book's stale values). Our engine previously used the book's 15-min OR with %-of-price A/C.

| Variant | Trades | Win | P&L | MaxDD | Yrs+ |
|---|---|---|---|---|---|
| BASELINE (OR15/pct) | 416 | 43% | +$14,705 | −29% | 2/4 |
| a OR20 / pct | 205 | 43% | +$6,708 | −22% | 3/4 |
| b OR20 / ATR10 18-22% | 184 | 43% | +$5,397 | −27% | 2/4 |
| c OR15 / ATR10 18-22% | 272 | 44% | +$13,906 | −29% | 3/4 |
| d OR20 / ATR10 20-25% | 167 | 44% | +$5,977 | −21% | 2/4 |

## Verdict

**Not adopted.** The 20-minute OR halves the trade count and the P&L without buying stability; ATR-based A/C at 15-min OR (c) roughly matches baseline (slightly better year-spread, slightly less profit) — a wash. Fisher's modern parameters were tuned for *futures pits and energies*, and on SPX 0DTE options the book-era 15-min/pct combination sits on at least as good a plateau. Kept as reference; C6 (combo on ATR10 spec) also underperformed. The lesson from his own book survives: consistency of parameters beats the specific choice.
