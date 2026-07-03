# H5 — Data-free days (extend the FOMC ban to NFP / CPI)

**Source:** webinar — "I like to trade what I call data-free days... I stay away during all the report times." FOMC ban already adopted and empirically confirmed.

**Date lists** (`bot/experiments_spx.py`): NFP = first Friday of each month (approximation; the few holiday-shifted releases are accepted noise). CPI = BLS release dates from public schedule (8:30 ET, pre-open; a few 2026 entries approximate). **Caveat logged:** these lists are close but not exchange-verified; a production version should use an official calendar.

| Variant | Trades | Win | P&L | MaxDD | Yrs+ | 2026 |
|---|---|---|---|---|---|---|
| BASELINE | 416 | 43% | +$14,705 | −29% | 2/4 | −3,757 |
| a +NFP ban | 388 | 43% | +$12,461 | −29% | 2/4 | −3,254 |
| b +CPI ban | 393 | 43% | **+$17,486** | −25% | 2/4 | **−894** |
| c +NFP+CPI | 365 | 43% | +$14,570 | −26% | 2/4 | −702 |

## Verdict

**CPI ban helps; NFP ban costs.** Interesting split: CPI releases at 8:30 leave a distorted opening range that produces bad breakouts (banning them added +$2.8k and repaired most of 2026's bleed); NFP days apparently contain some of the good trend days (banning them cut profit in 2023 and 2025). Mechanically sensible — CPI surprises re-price *levels* (gappy chop), NFP surprises often start *trends*. **Adopt (b) CPI-only** as a combo ingredient (it shines in C3/C4); leave NFP tradeable. Flag: this is the campaign's most data-mined adoption — CPI-vs-NFP asymmetry was discovered, not predicted. Treat as provisional until the 2021-23 exam.
