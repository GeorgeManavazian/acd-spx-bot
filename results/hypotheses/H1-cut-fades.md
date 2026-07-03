# H1 — Cut fades entirely

**Source:** our 4-years-every-structure data + post-book Fisher ("reversals don't work anymore — nobody panics anymore, 24-hour trading") + all three YouTube docs (none advocate fading a break, even the hype ones).

**Implementation:** `no_fades=True` in `bot/backtest_acd_spx_options.py::run` — fades removed from the tradeable set before selection (not merely re-structured). Days whose only setups were fades are logged `no_breakout_setups (fades cut)` (95 days).

## Result (BOT v2 = baseline going forward)

| Config | Trades | Win | P&L | Final | MaxDD |
|---|---|---|---|---|---|
| SPX-fit WITH credit fades | 510 | 55% | +$8,512 | $18,512 | −28.8% |
| **BOT v2 (fades cut)** | 416 | 43% | **+$14,705** | $24,705 | −28.6% |

Slippage sweep 0→20¢/leg: P&L moves <$650. By year: 2023 +$3,620 · 2024 −$1,397 · 2025 +$16,238 · 2026 −$3,757.

## Verdict: **ADOPTED**

Cutting fades adds +$6.2k and simplifies the bot to one setup (`a_held`). Honest cost: win rate drops to 43% (fades were frequent small winners masking their net loss), and the remaining bot is fully exposed to breakout-regime concentration — 2025 supplies more than all of the profit. That concentration is now THE problem for H2-H6 to attack.

Trade count check: 416 breakout trades vs 178 in the combined config — fades used to occupy the one-trade-per-day slot on 238 days where a breakout also fired later. Cutting fades doesn't just remove losers; it unblocks breakouts.
