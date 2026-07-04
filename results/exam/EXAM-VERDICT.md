# The Exam Verdict — both configurations FAIL (2026-07-03)

Per the pre-registration (`docs/exam-preregistration-2026-07-03.md`, publicly timestamped
before any exam data existed): **the frozen Earner and Tank were run ONCE on 2021-07-06 →
2023-07-03 held-out data. Both fail pass-bar 1 (total P&L > 0). The result stands. No
re-tuning on this data, ever.**

| | Trades | Win | P&L | MaxDD (bar) | Verdict |
|---|---|---|---|---|---|
| Earner | 125 | 46% | **−$599** | −29.8% (≤30% ✓) | **FAIL** |
| Tank | 38 | 42% | **−$436** | −17.2% (≤18% ✓) | **FAIL** |

## What the failure does and does not say

**It says:** the playground's headline returns (+166% / +120%) were substantially
curve-fit to 2023-2026. On data the configs never met, the measured edge is ~zero. The
pre-agreed interpretation applies: the campaign becomes a disciplined-overfitting case
study, and live paper trading is the project's only remaining validation path.

**It does not say the bots blew up:** −6% and −4.4% over two years, with drawdowns
*inside* their allowed bounds (both passed bar 2). The failure mode is "no edge on new
data," not "hidden catastrophic risk." The risk framework — defined-risk spreads, 3%
sizing, FOMC bans — behaved as designed through a bear market.

**Texture (reported, not argued):** the Earner was actually *profitable through 2022*
(+$1,534 across the bear year, including +$858/+$717/+$969 in Oct-Dec) and died in
2023-H1 (−$2,876) — the half-year immediately adjacent to its training window. The Tank
took only 38 trades in two years and hovered at breakeven. Make of that what you will;
the bars were chosen in advance precisely so this paragraph can't move the verdict.

## Disclosed deviations (all decided/documented before the run)

1. **Underlying = SPY×10** (Databento amendment): tracks the official close with a
   median 10.3-pt basis (dividend drift) — shifts strike anchoring ~2 strikes (longs
   slightly ITM, shorts slightly OTM vs true-ATM intent). Debits and settles are real
   quotes/prints for the strikes actually chosen, so P&L is internally consistent.
2. **Settle fallbacks:** 78 of 502 days had no cached official EOD print; SPY×10 close
   used (documented fallback).
3. **`no_expiry` by data presence** rather than an ex-ante listing calendar — 126
   signal-day legs missing; red-team verified the missing-day pattern matches the real
   SPXW Tue/Thu listing history (dailies launched Apr 2022).
4. NYSE half days trimmed at 13:00 via an ex-ante calendar (audit fix, committed
   pre-run).

## Process record

- Registration frozen + pushed to the public repo before data acquisition.
- Data acquired post-freeze (Databento OPRA + SPY; total spend $0.52).
- Pre-flight: compliance audit (frozen lists verified 16/16 + 24/24 exact), data-quality
  pass (0 crossed quotes), 3 sample-day walkthroughs, independent red-team re-derivation
  (zero divergence) — all without computing P&L.
- One run, sentinel-enforced. Artifacts: `EXAM-RESULTS.md`, `exam_{earner,tank}_{trades,days}.csv`.

## What happens now

Per the registration's interpretation grid: **no rescue, no re-tune.** The live paper
test (started 2026-07-06, same frozen configs) continues — the future is the one dataset
that can't be overfit. If the paper months also read flat, the honest conclusion is that
this signal family has no deployable edge on SPX, and the project's value is the
process itself.
