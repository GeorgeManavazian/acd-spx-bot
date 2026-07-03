# H2 — Pivot-confluence breakout filters

**Source:** *The Logical Trader* Ch.3 (A through pivot = "two signals in concert", p.55-56; pivot just beyond the A = wait, p.57) + Fisher's live webinar trade (pivot-flip precondition).

**Implementations** (`bot/experiments_spx.py::h2_variants`, all on BOT v2 baseline):
- (a) trade only days that also emitted `a_through_pivot` (A cleared the whole prior-day pivot band);
- (b) skip when the pivot band sits *ahead* of the trade (entirely beyond the OR in the trade direction) unless entry already cleared it — Fisher p.57;
- (c) pivot-flip only: OR opened one side of the pivot, A broke the other (the webinar trade shape; approximation — we use the prior-day pivot band, not his 3-day rolling pivot);
- (d) anti-flip control (breakout agrees with the open side).

| Variant | Trades | Win | P&L | MaxDD | Yrs+ |
|---|---|---|---|---|---|
| BASELINE | 416 | 43% | +$14,705 | −29% | 2/4 |
| a through-pivot only | 127 | 46% | +$8,652 | −25% | 3/4 |
| **b skip pivot-ahead** | 308 | 43% | **+$15,096** | **−23%** | **4/4** |
| c pivot-flip only | 150 | 43% | +$1,359 | −24% | 2/4 |
| d anti-flip | 143 | 41% | +$2,518 | −19% | 2/4 |

## Verdict

**(b) is a genuine improvement:** more P&L than baseline on 108 *fewer* trades, smaller drawdown, and flips 2024+2026 positive → 4/4 years. It's the book's own rule, mechanism-clear (don't buy a breakout with a known resistance band sitting in its path). **(a)** trades stability for P&L — useful ingredient in combos (see C5). **(c)/(d)** split the same coin weakly — the flip pattern that made Fisher's webinar trade special doesn't generalize as a standalone filter here. Adopt (b); carry (a) into combinations.
