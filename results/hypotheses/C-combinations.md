# C — Combinations (winning singles stacked)

Ingredients: H4c clean-coil (star), H2b skip-pivot-ahead, H2a through-pivot, H5b CPI ban, H3c ATR10 spec.

| Combo | Trades | Win | P&L | MaxDD | Yrs+ | 2025 share | By year |
|---|---|---|---|---|---|---|---|
| BASELINE | 416 | 43% | +$14,705 | −29% | 2/4 | 110% | +3,620/−1,397/+16,238/−3,757 |
| H4c alone | 178 | 48% | +$17,670 | −18% | 4/4 | 68% | +3,469/+926/+11,987/+1,287 |
| C1 coil+pivot-not-ahead | 140 | 46% | +$9,985 | −19% | 3/4 | 65% | +2,163/−1,008/+6,531/+2,300 |
| C2 C1+CPI | 131 | 47% | +$10,960 | −15% | 3/4 | 54% | +2,315/−174/+5,925/+2,894 |
| C3 C1+CPI+NFP | 123 | 48% | +$13,792 | −15% | 4/4 | 48% | +2,315/+552/+6,610/+4,314 |
| **C4 coil+CPI** | 167 | 48% | **+$16,586** | −20% | **4/4** | 66% | +3,662/+488/+10,869/+1,567 |
| **C5 coil+through-pivot** | 60 | **58%** | +$11,958 | **−12%** | **4/4** | **40%** | +3,450/+1,483/+4,816/+2,209 |
| C6 C2 on ATR10 spec | 100 | 43% | +$2,271 | −28% | 3/4 | 93% | |

## Reading

- **The coil filter is the load-bearing ingredient** — it appears in every 4/4-year row and every sub-−20% drawdown row.
- **C5 is the most *robust* profile in the campaign:** 58% win, −12% max drawdown, and the only config where 2025 supplies less than half the profit — the closest thing to regime-independence we've produced. Cost: only 60 trades in 3 years (~1 every 2 weeks), so each number carries wide error bars, and compounding a small trade count caps total P&L.
- **C4 is the best P&L-per-robustness:** nearly baseline profit, all years positive, one simple extra rule.
- Stacking beyond two filters (C3) trades P&L for smoothness honestly, but every added condition shrinks n and grows the overfitting debt.
- C6 confirms H3: the ATR10 re-parameterization dilutes everything it touches.

## Interaction note (multiple-testing honesty)

22 variants were evaluated on one dataset. The two adopted mechanisms (coil, pivot-ahead) were *predicted* by outside sources before testing, which protects them somewhat; the CPI/NFP asymmetry and the exact combo rankings were discovered in-sample and deserve the least trust. All of it faces the 2021-23 exam before anything trades.
