# backtest_acd_spx_options.py — the FULL ACD method on SPX expressed as OPTIONS:
# every intraday setup (breakouts AND fades, failed_c included — options give it the
# defined risk its missing stop denied the underlying test) becomes a same-day (0DTE)
# ATM debit spread in the signal's direction. The underlying test (same driver family)
# proved the directional signal alone is flat; this asks whether the options payoff
# shape — capped loss, no stop-whipsaw, convex win — turns the same signals into money.
#
# LOCKED SPEC (zero discretion):
#   Signals    : acd_micro setups, intraday horizon only, gate variants {macro gate ON, OFF}.
#   Structure  : 0DTE debit spread — long the strike nearest entry (SPX 5-pt grid), short
#                25 pts further in the direction. Entry = long.ask - short.bid at the first
#                bar >= the setup's entry_time (real NBBO). Degenerate (debit<=0) skipped.
#   Portfolio  : ONE trade per day — the EARLIEST tradeable setup (a hold-to-expiry position
#                occupies the book to the close, so later same-day signals are untakeable).
#   Exits      : primary = hold to expiry, cash-settle at intrinsic vs the day's close.
#                comparison = active 50%-target / 50%-stop walk on real close-value bars
#                (V5's lesson: the exit, not the entry, carried that strategy).
#   Account    : $10,000 start; XSP scale (all SPX premiums/strikes /10; one XSP contract =
#                $100/point exactly = SPX/10 assumption). Risk 3% of CURRENT equity per
#                trade; contracts = floor(3% * equity / (debit*100/10)); max loss = debit.
#                Compounding. size_zero days logged.
#   Friction   : slippage swept {0, 5, 10, 20}c per leg per fill, XSP terms (= SPX cents/10
#                is NOT applied — cents are quoted on the XSP contract directly, punishing).
#                Entry crosses 2 legs; expiry cash settlement has no exit friction; the
#                active exit crosses 2 legs again.
#   Ledger     : one row per day (traded / why not) + one row per trade, both CSVs.
#
# LOOK-AHEAD GUARDS: signals and macro context inherit the audited v2 underlying driver
# (causal hygiene, prior-day pivot/ATR/context). Entry debit is read at the first bar at or
# AFTER the setup's resolution time; settle uses only the day's close; the active-exit walk
# only sees bars after entry.
#
# Offline once data is pulled (pull_acd_options_spx.py). Run from bot/:
#   ../.venv/bin/python backtest_acd_spx_options.py
import csv
import os
from collections import Counter

from acd_micro import SPX
from acd_macro import macro_context, apply_macro, FADES
from acd_fade_pricing import spread_entry, expire_value, close_value
from backtest_acd_spx_underlying import load_paths, build_hist, max_drawdown_pct, \
    official_closes
from filters import FOMC_DATES
from load_ivol_intraday import load_cached_minutes
from run_acd_signal import hlc_from_path

START_EQUITY = 10_000.0
RISK_PCT = 0.03
SCALE = 10.0                       # XSP = SPX/10; premiums and strikes divide by 10
WIDTH = 25.0                       # SPX points (2.5 XSP points)
SLIP_SWEEP = (0.0, 0.05, 0.10, 0.20)   # per leg per fill, XSP dollars
SLIP_BASE = 0.05
TARGET, STOP = 0.5, 0.5
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "spx")


def legs_for(setup):
    typ = "call" if setup.direction == "long" else "put"
    atm = round(setup.entry_price / 5.0) * 5.0
    short = atm + WIDTH if setup.direction == "long" else atm - WIDTH
    return typ, atm, short


def size_contracts(equity, debit_spx, slip=0.0):
    """XSP contracts at 3%-of-equity risk. Per-contract max loss = debit_spx/10 * 100 plus
    the 2 entry legs' slippage (audit #8: real max loss includes what you paid to get in)."""
    per_contract = debit_spx / SCALE * 100.0 + 2.0 * slip
    if per_contract <= 0 or equity <= 0:
        return 0
    return int((RISK_PCT * equity) / per_contract)


def _next_min(hhmm):
    h, m = int(hhmm[:2]), int(hhmm[3:])
    m += 1
    return f"{h + m // 60:02d}:{m % 60:02d}"


LAST_TRADEABLE = "15:59"           # 0DTE SPX/XSP options stop trading at 16:00


def _value_series(struct, long_bars, short_bars, entry_t):
    """Closeable value bars STRICTLY after entry and only while the option still trades —
    the feed freezes ~16:01-16:19 and blows the spread at 16:00 (audit #4: the walk was
    'filling' on non-tradeable bars)."""
    Lb = {str(r["time"]): r for _, r in long_bars.iterrows()}
    Sb = {str(r["time"]): r for _, r in short_bars.iterrows()}
    return [(t, close_value(struct, Lb[t], Sb[t]))
            for t in sorted(Lb) if entry_t < t <= LAST_TRADEABLE and t in Sb]


def _walk_target_stop(debit, series, settle_value, target=TARGET, stop=STOP):
    """exit_target_stop + a triggered flag, so the caller charges exit-leg slippage only
    when legs were actually crossed (audit #5: cash settles were paying phantom fills)."""
    for t, v in sorted(series):
        if v - debit >= target * debit or debit - v >= stop * debit:
            return v, True
    return settle_value, False


def credit_legs_for(setup):
    """SPX-fit fade expression: SELL the 25-wide vertical against the failed direction.
    Bearish fade -> call credit spread (short ATM, long ATM+25); bullish -> put credit
    (short ATM, long ATM-25). Profits from the stall the fade signal actually predicts."""
    atm = round(setup.entry_price / 5.0) * 5.0
    if setup.direction == "short":
        return "call", atm, atm + WIDTH
    return "put", atm, atm - WIDTH


def _vertical_intrinsic(typ, short_k, width, settle):
    """What the SOLD vertical is worth at expiry (what the seller owes), capped at width."""
    if typ == "call":
        return min(max(settle - short_k, 0.0), width)
    return min(max(short_k - settle, 0.0), width)


def price_day(date, setup, close, structure="debit"):
    """The day's trade. structure='debit' (buy vertical WITH the signal) or 'credit'
    (sell vertical AGAINST a fade). Both return per-share entry/settle numbers where
    pnl_per_share = hold_val - debit for debit, and credit - hold_owed for credit —
    normalized here so pnl fields read the same: entry cost basis + settle value.
    Returns dict or (None, why)."""
    fill_from = _next_min(setup.entry_time)            # audit #3: same-bar quotes predate the
    if structure == "credit":                          # signal print -> fill the NEXT bar
        typ, short_k, wing_k = credit_legs_for(setup)
        short_bars = load_cached_minutes("SPX", date, date, short_k, typ)
        wing_bars = load_cached_minutes("SPX", date, date, wing_k, typ)
        if short_bars is None or short_bars.empty or wing_bars is None or wing_bars.empty:
            return None, "missing_leg_bars"
        try:
            # sell short_k (collect bid), buy wing (pay ask), first bar > entry time
            neg, entry_t = spread_entry(wing_bars, short_bars, fill_from)
            credit = -neg                              # wing.ask - short.bid = -(credit)
        except ValueError:
            return None, "no_fillable_bar"
        if credit <= 0 or credit >= WIDTH:
            return None, "degenerate_credit"
        owed = _vertical_intrinsic(typ, short_k, WIDTH, close)
        return {"date": date, "name": setup.name, "direction": setup.direction,
                "entry_time": entry_t, "typ": typ, "long": wing_k, "short": short_k,
                "kind": "credit", "debit": WIDTH - credit,   # cost basis = max loss
                "hold_val": WIDTH - owed,                    # value kept at settle
                "ts_val": WIDTH - owed, "ts_triggered": False}, ""   # no active exit (credit v1)
    typ, atm, short = legs_for(setup)
    long_bars = load_cached_minutes("SPX", date, date, atm, typ)
    short_bars = load_cached_minutes("SPX", date, date, short, typ)
    if long_bars is None or long_bars.empty or short_bars is None or short_bars.empty:
        return None, "missing_leg_bars"
    try:
        debit, entry_t = spread_entry(long_bars, short_bars, fill_from)
    except ValueError:
        return None, "no_fillable_bar"
    if debit <= 0:
        return None, "degenerate_debit"
    struct = {"kind": "debit_spread", "opt_type": typ, "long_strike": atm,
              "short_strike": short, "width": WIDTH}
    hold_val = expire_value(struct, close)
    ts_val, triggered = _walk_target_stop(
        debit, _value_series(struct, long_bars, short_bars, entry_t), hold_val)
    return {"date": date, "name": setup.name, "direction": setup.direction,
            "entry_time": entry_t, "typ": typ, "long": atm, "short": short,
            "kind": "debit", "debit": debit, "hold_val": hold_val, "ts_val": ts_val,
            "ts_triggered": triggered}, ""


def run(hist, closes, use_macro, exit_mode="hold", slip=SLIP_BASE, write_files=False,
        tag="", spx_fit=False, fomc_ban=False, no_fades=False):
    """exit_mode: 'hold' (expiry settle, entry friction only) or 'ts' (active 50/50,
    entry + exit friction). spx_fit: fades SELL credit spreads (stall-aligned), breakouts
    buy debit spreads and always HOLD (exit_mode ignored). fomc_ban: no trades on FOMC
    announcement dates (filters.FOMC_DATES). no_fades: fades removed from the tradeable
    set entirely (hypothesis #1, 2026-07-02: our data — losers in every structure, all
    four years — plus post-book Fisher's own retraction: 'reversals don't work anymore')."""
    equity = START_EQUITY
    day_rows, trade_rows, curve = [], [], []
    fomc = set(FOMC_DATES)
    for i in range(len(hist)):
        e = hist[i]
        ctx = macro_context(i, hist)
        raw = [s for s in e.day_result.setups if s.horizon == "intraday"]
        kept = apply_macro(raw, ctx) if use_macro else list(raw)
        kept = [s for s in kept if s.horizon == "intraday"]
        if no_fades:
            kept = [s for s in kept if s.name not in FADES]
        reason, taken = "", None
        if fomc_ban and e.date in fomc:
            reason = "fomc_ban"
        elif not raw:
            reason = "no_setups"
        elif not kept:
            reason = ("no_breakout_setups (fades cut)"
                      if no_fades and all(s.name in FADES for s in raw)
                      else f"macro_dropped_all ({ctx.trend_state}/{ctx.regime})")
        else:
            first = min(kept, key=lambda s: (s.entry_time, s.name))   # earliest -> the book
            structure = "credit" if (spx_fit and first.name in FADES) else "debit"
            priced, why = price_day(e.date, first, closes[e.date], structure)
            if priced is None:
                reason = f"{why} ({first.name} @ {first.entry_time})"
            else:
                hold_this = exit_mode == "hold" or spx_fit      # spx_fit: always hold
                val = priced["hold_val"] if hold_this else priced["ts_val"]
                # expiry = cash settle, no exit legs; charge 4 fills only on a real exit
                fills = 2 if (hold_this or not priced["ts_triggered"]) else 4
                n = size_contracts(equity, priced["debit"], slip)
                if n <= 0:
                    reason = f"size_zero (debit ${priced['debit'] / SCALE * 100:.0f}/contract)"
                else:
                    pnl = n * ((val - priced["debit"]) / SCALE * 100.0 - fills * slip)
                    equity += pnl
                    dr = e.day_result
                    taken = {**priced, "contracts": n, "pnl": round(pnl, 2),
                             "equity_after": round(equity, 2),
                             "skipped_same_day": len(kept) - 1,
                             # --- the WHY columns ---
                             "conviction": first.conviction,
                             "trend_state": ctx.trend_state, "regime": ctx.regime,
                             "or_high": round(dr.or_high, 2), "or_low": round(dr.or_low, 2),
                             "or_vs_pivot": dr.or_vs_pivot,
                             "events": "|".join(f"{ev.type}@{ev.time}" for ev in dr.events),
                             "refs": str(first.refs),
                             "close": closes[e.date],
                             # both exits, always, so every trade carries its counterfactual
                             "hold_pnl_1x": round((priced["hold_val"] - priced["debit"])
                                                  / SCALE * 100.0, 2),
                             "ts_pnl_1x": round((priced["ts_val"] - priced["debit"])
                                                / SCALE * 100.0, 2)}
                    trade_rows.append(taken)
        day_rows.append({
            "date": e.date, "trend_state": ctx.trend_state, "regime": ctx.regime,
            "raw_setups": "|".join(f"{s.name}:{s.direction}" for s in raw),
            "after_macro": "|".join(f"{s.name}:{s.direction}" for s in kept),
            "trade": taken["name"] if taken else "",
            "pnl": taken["pnl"] if taken else "",
            "no_trade_reason": reason,
            "equity_close": round(equity, 2),
        })
        curve.append(equity)
    st = summarize(trade_rows, day_rows, curve, slip, use_macro, exit_mode)
    if write_files:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        _write_csv(os.path.join(RESULTS_DIR, f"acd_options_day_ledger{tag}.csv"), day_rows)
        _write_csv(os.path.join(RESULTS_DIR, f"acd_options_trades{tag}.csv"), trade_rows)
    return st, day_rows, trade_rows


def summarize(trades, days, curve, slip, use_macro, exit_mode):
    wins = [t for t in trades if t["pnl"] > 0]
    by_name, by_year = {}, {}
    for t in trades:
        by_name.setdefault(t["name"], []).append(t["pnl"])
        by_year.setdefault(t["date"][:4], []).append(t["pnl"])
    reasons = Counter(d["no_trade_reason"].split(" (")[0] for d in days
                      if d["no_trade_reason"])
    return {
        "gate": use_macro, "exit": exit_mode, "slip": slip,
        "days": len(days), "trades": len(trades),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "total_pnl": sum(t["pnl"] for t in trades),
        "final_equity": curve[-1] if curve else START_EQUITY,
        "max_drawdown": max_drawdown_pct(curve),
        "no_trade": dict(reasons),
        "by_setup": {k: (len(v), sum(v)) for k, v in sorted(by_name.items())},
        "by_year": {k: (len(v), sum(v)) for k, v in sorted(by_year.items())},
    }


def _write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def print_stats(st):
    lab = f"{'gate' if st['gate'] else 'nogate'}/{st['exit']}"
    print(f"=== {lab:<14} slip {st['slip']:.2f} ===  trades {st['trades']}  "
          f"win {st['win_rate']:.0%}  P&L ${st['total_pnl']:+,.0f}  "
          f"final ${st['final_equity']:,.0f}  maxDD {st['max_drawdown']:.1%}")
    print(f"    no-trade: {st['no_trade']}")
    print("    by setup: " + "  ".join(f"{k}:n{n}/${p:+,.0f}"
                                       for k, (n, p) in st["by_setup"].items()))
    print("    by year : " + "  ".join(f"{k}:n{n}/${p:+,.0f}"
                                       for k, (n, p) in st["by_year"].items()))


if __name__ == "__main__":
    # ---- self-tests (offline, monkeypatched bars) ----
    import pandas as pd
    from acd_micro import Setup
    import backtest_acd_spx_options as me

    assert size_contracts(10_000.0, 12.5) == 2       # $125/contract, 3% = $300 -> 2
    assert size_contracts(10_000.0, 40.0) == 0       # $400/contract > $300 -> size_zero
    assert size_contracts(0.0, 12.5) == 0
    print("self-test OK: XSP sizing")

    def fake_cache(sym, date, exp, strike, typ):
        px = {5000.0: [(("10:00"), 30, 32), (("10:30"), 36, 38), (("16:00"), 39, 41)],
              5025.0: [(("10:00"), 18, 20), (("10:30"), 19, 21), (("16:00"), 20, 22)]}
        rows = px.get(float(strike))
        if rows is None:
            return None
        return pd.DataFrame({"time": [r[0] for r in rows], "bid": [r[1] for r in rows],
                             "ask": [r[2] for r in rows]})
    real = me.load_cached_minutes
    me.load_cached_minutes = fake_cache
    globals()["load_cached_minutes"] = fake_cache

    # fills are strictly AFTER the signal minute (audit #3): signal 10:00 -> next bar 10:30
    s = Setup("a_held", "long", "10:00", 5002.0, 4990.0, 1, "intraday", {})
    tr, why = price_day("2024-06-03", s, 5040.0)
    # long 5000C ask@10:30 38, short 5025C bid@10:30 19 -> debit 19; settle 5040 -> 25
    assert tr and abs(tr["debit"] - 19.0) < 1e-9 and tr["hold_val"] == 25.0, (tr, why)
    # walk: no tradeable bars after 10:30 before 16:00 -> settles, not triggered
    assert tr["ts_val"] == 25.0 and tr["ts_triggered"] is False, tr
    print("self-test OK: price_day (next-bar fill, debit 19, settle 25, no phantom exit)")

    s2 = Setup("failed_a", "short", "10:00", 5002.0, None, 1, "intraday", {})
    tr2, why2 = price_day("2024-06-03", s2, 5040.0)
    assert tr2 is None and why2 == "missing_leg_bars", (tr2, why2)   # no put bars in fake
    print("self-test OK: missing legs skipped with reason")

    # credit fade @10:30 bar: short 5000C bid 36, wing 5025C ask 21 -> credit 15.
    # basis = 25-15 = 10; settle 5040 -> owed 25 -> hold_val 0 (max loss);
    # settle 4990 -> owed 0 -> hold_val 25, pnl/share = 25-10 = +15 (the credit).
    trc, whyc = price_day("2024-06-03", s2, 5040.0, structure="credit")
    assert trc and trc["kind"] == "credit", (trc, whyc)
    assert abs(trc["debit"] - 10.0) < 1e-9 and trc["hold_val"] == 0.0, trc
    trc2, _ = price_day("2024-06-03", s2, 4990.0, structure="credit")
    assert trc2["hold_val"] == 25.0 and abs(trc2["hold_val"] - trc2["debit"] - 15.0) < 1e-9
    print("self-test OK: credit fade math (next-bar fill, both settle sides)")
    assert size_contracts(10_000.0, 12.5, slip=0.05) == 2       # 125.10/contract
    assert _next_min("09:59") == "10:00" and _next_min("15:59") == "16:00"
    print("self-test OK: slip-inclusive sizing + minute math")

    me.load_cached_minutes = real
    globals()["load_cached_minutes"] = real

    # ---- real run ----
    print("\nLoading 3yr SPX history...")
    paths, _ = load_paths()
    hist = build_hist(paths, SPX, use_atr=False)
    closes = official_closes(paths)     # audit #2: settle on the EOD chain's official print,
    print(f"history: {len(hist)} days\n")   # not the option feed's frozen ~16:01 spot

    print(f"--- gate x exit grid (slip {SLIP_BASE}/leg) ---")
    for gate in (True, False):
        for exit_mode in ("hold", "ts"):
            st, *_ = run(hist, closes, use_macro=gate, exit_mode=exit_mode,
                         slip=SLIP_BASE,
                         write_files=(gate and exit_mode == "hold"), tag="")
            print_stats(st)

    print(f"\n--- SPX-FIT (fades=credit, breakouts=debit+hold, FOMC ban) ---")
    for gate in (True, False):
        st, *_ = run(hist, closes, use_macro=gate, spx_fit=True, fomc_ban=True,
                     slip=SLIP_BASE, write_files=False, tag="_spxfit")
        print_stats(st)

    # THE BOT (hypothesis #1 adopted 2026-07-02): breakouts only, fades cut.
    print(f"\n--- BOT v2: breakouts only (fades CUT), debit+hold, FOMC ban, no gate ---")
    st, *_ = run(hist, closes, use_macro=False, spx_fit=True, fomc_ban=True,
                 no_fades=True, slip=SLIP_BASE, write_files=True, tag="_botv2")
    print_stats(st)
    print(f"\n--- BOT v2 slippage sweep ---")
    for slip in SLIP_SWEEP:
        st, *_ = run(hist, closes, use_macro=False, spx_fit=True, fomc_ban=True,
                     no_fades=True, slip=slip)
        print(f"  slip {slip:.2f}: trades {st['trades']}  win {st['win_rate']:.0%}  "
              f"P&L ${st['total_pnl']:+,.0f}  final ${st['final_equity']:,.0f}  "
              f"maxDD {st['max_drawdown']:.1%}")
    print(f"\nLedgers written to {os.path.abspath(RESULTS_DIR)}/")
