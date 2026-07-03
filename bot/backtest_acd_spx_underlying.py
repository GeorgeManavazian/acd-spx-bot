# backtest_acd_spx_underlying.py — the FULL ACD method (micro + macro, breakouts AND fades)
# on the SPX underlying, traded directionally as XSP (= SPX/10), NO options. This is NOT V5:
# no fade-only filter, no skip-failed_c, no option structures. The question it answers:
# "does Fisher's full method, as written, make money just buying/selling the index?"
#
# LOCKED SPEC (zero discretion; v2 after the 2026-07-02 look-ahead audit of v1):
#   Universe   : every cached SPX day (~3yr, Jul 2023 -> Jun 2026), day paths from the cache.
#   Signals    : acd_micro.build_day setups, optionally gated by acd_macro.apply_macro.
#                Only INTRADAY-horizon setups with a price stop are traded. Excluded + logged:
#                stop=None (failed_c, reversal_trade), EOD entries (trt/sushi), and overnight
#                setups (late_day_c — its overnight label is decided by the CLOSE, which is
#                unknowable at its entry time; trading it same-day was a look-ahead exposure).
#   Execution  : one position at a time (portfolio.simulate_day), enter at the setup's
#                entry_price, exit on its stop (gap-through fills at the WORSE price) or the
#                session close. Same-day only; no time stop. Bars are per-minute spots.
#   Account    : $10,000 start. Risk per trade = 3% of CURRENT equity (compounding).
#                units = floor(risk$ / (|entry-stop|/10)); notional capped at 1x equity
#                (cash account, no leverage). Gap-through can lose more than 3% — reported.
#   Friction   : slippage per side in XSP points; baseline 0.05, swept {0, 0.05, 0.10}.
#                Commission $0 (index-ETF assumption; stated, not hidden).
#   Ledger     : one row per DAY (traded or not, with the reason) + one row per TRADE.
#
# LOOK-AHEAD GUARDS (audit 2026-07-02, v2):
#   - data hygiene is CAUSAL: a print is judged against the last KEPT print (seeded from the
#     first 5 positive prints of the morning), never against the full-day median (v1 bug —
#     the day's median isn't knowable at 10:00).
#   - ATR for Fisher's A/C = frac*ATR formula is computed from PRIOR days only (true range
#     over completed days; today's H/L never enters today's levels).
#   - pivot = PRIOR day's H/L/C; macro context = day i-1 (acd_macro contract).
#   - entries at the setup's own resolution bar; exits only on bars strictly after entry
#     (portfolio.py contract); overnight/EOD/close-labeled setups not traded (above).
#
# Offline (cached data only). Run from bot/:  ../.venv/bin/python backtest_acd_spx_underlying.py
import csv
import os
from collections import Counter
from dataclasses import replace

from acd_micro import build_day, SPX, InstrumentSpec
from acd_macro import DayEntry, macro_context, apply_macro
from portfolio import simulate_day
from run_acd_signal import cached_days, day_path, hlc_from_path

START_EQUITY = 10_000.0
RISK_PCT = 0.03
SCALE = 10.0                      # XSP = SPX / 10
SLIP_BASE = 0.05                  # XSP points per side
SLIP_SWEEP = (0.0, 0.05, 0.10)
ATR_N = 14
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "spx")


# ---------------------------------------------------------------- data (load once, causal clean)
def _clean_path_causal(path, seed_ref=None):
    """Causal hygiene: judge each print against the LAST KEPT print, seeded from the PRIOR
    day's close (known at 09:30; audit 2026-07-02 v3 — the v2 seed used the median of the
    first 5 prints, i.e. future prints judged bar 1, inside the OR window). First day ever
    falls back to the first positive print. Returns (bars, n_dropped)."""
    if seed_ref is None:
        pos = [s for _, s in path if s > 0]
        if not pos:
            return [], len(path)
        seed_ref = pos[0]
    ref, kept = seed_ref, []
    for t, s in path:
        if s > 0 and abs(s / ref - 1.0) <= 0.15:
            kept.append((t, s))
            ref = s
    return kept, len(path) - len(kept)


def _complete_day(path):
    """A day's path must reach the close: last bar >= 15:55, or a half-day close
    (12:55-13:20). Truncated files made 'the close' a mid-day print (audit finding #9)."""
    last = path[-1][0]
    return last >= "15:55" or ("12:55" <= last <= "13:20")


def load_paths():
    """{date: clean bars} for every cached day with enough data. Loaded ONCE; every sweep
    config rebuilds its history from these paths (pure, fast)."""
    paths, skipped, n_bad, prev_close = {}, [], 0, None
    for D in cached_days():
        try:
            path = day_path(D)
        except Exception:
            skipped.append(D)
            continue
        path, dropped = _clean_path_causal(path, prev_close)
        n_bad += dropped
        if len(path) < 30 or not _complete_day(path):
            skipped.append(D)
            continue
        paths[D] = path
        prev_close = path[-1][1]
    if n_bad:
        print(f"  data hygiene (causal): dropped {n_bad} invalid prints")
    return paths, skipped


def official_closes(paths):
    """{date: official closing spot} from the cached EOD 0DTE chain snapshots (the chain's
    underlying_price is the end-of-day print — far closer to the real PM settle than the
    option feed's frozen ~16:01 spot, which was median 2.5 / p90 8.3 pts off). Falls back
    to the path's last print when a chain file is missing."""
    from load_ivol_intraday import fetch_0dte_chain
    out = {}
    for D in paths:
        try:
            _, anchor = fetch_0dte_chain("SPX", D)
            out[D] = float(anchor)
        except Exception:
            out[D] = paths[D][-1][1]
    return out


def true_range(hlc, prev_close):
    h, l, _ = hlc
    return max(h - l, abs(h - prev_close), abs(l - prev_close))


def build_hist(paths, spec, use_atr, atr_n=ATR_N):
    """DayEntry history under `spec`. ATR (if used) is Fisher's A/C basis, computed strictly
    from PRIOR days' H/L/C (true range, atr_n-day mean); None until enough history -> the
    engine falls back to %-of-price for those warmup days. A calendar gap in the cache does
    NOT reset the pivot (the prior TRADING day is the correct pivot source)."""
    hist, trs, prev_hlc = [], [], None
    for D in sorted(paths):
        bars = paths[D]
        hlc = hlc_from_path(bars)
        if prev_hlc is None:
            prev_hlc = hlc
            continue
        atr = (sum(trs[-atr_n:]) / atr_n) if (use_atr and len(trs) >= atr_n) else None
        try:
            dr = build_day(D, bars, prev_hlc, spec, atr=atr)
            hist.append(DayEntry(D, hlc, dr))
        except Exception:
            pass
        trs.append(true_range(hlc, prev_hlc[2]))
        prev_hlc = hlc
    return hist


# ---------------------------------------------------------------- sizing
def size_units(equity, entry_spx, stop_spx):
    """Whole XSP units for a 3%-of-equity risk, notional capped at 1x equity (no leverage).
    Returns (units, capped?)."""
    risk_per_unit = abs(entry_spx - stop_spx) / SCALE
    if risk_per_unit <= 0 or equity <= 0:
        return 0, False
    units = int((RISK_PCT * equity) / risk_per_unit)
    max_units = int(equity / (entry_spx / SCALE))
    return min(units, max_units), units > max_units


# ---------------------------------------------------------------- the run
def tradeable_setups(kept):
    """Intraday-horizon setups with a price stop. late_day_c (overnight; label decided by the
    close) and stop-less setups (failed_c) are excluded — logged by the caller."""
    return [s for s in kept if s.stop is not None and s.horizon == "intraday"]


def run(paths, hist, slip=SLIP_BASE, use_macro=True, write_files=False):
    equity = START_EQUITY
    day_rows, trade_rows, curve = [], [], []
    n_capped = 0

    for i in range(len(hist)):
        e = hist[i]
        ctx = macro_context(i, hist)
        raw = e.day_result.setups
        kept = apply_macro(raw, ctx) if use_macro else list(raw)
        tradeable = tradeable_setups(kept)
        excluded = [s for s in kept if s not in tradeable]

        if not raw:
            reason = "no_setups (no A/C event qualified — chop or drift day)"
        elif not kept:
            reason = f"macro_dropped_all (state={ctx.trend_state}, regime={ctx.regime})"
        elif not tradeable:
            reason = "only_excluded_setups (stopless/overnight — not tradeable on underlying)"
        else:
            reason = ""

        day_trades = []
        if tradeable:
            for t in simulate_day(paths[e.date], tradeable, point_value=0.0):
                sig_sign = 1.0 if t["direction"] == "long" else -1.0
                stop = next(s.stop for s in tradeable
                            if s.entry_time == t["entry_time"] and s.name == t["name"]
                            and s.direction == t["direction"])
                units, capped = size_units(equity, t["entry"], stop)
                if units <= 0:
                    trade_rows.append({**t, "date": e.date, "units": 0, "pnl": 0.0,
                                       "equity_after": round(equity, 2),
                                       "note": "size_zero (stop too far for equity)"})
                    continue
                n_capped += int(capped)
                move_xsp = (t["exit"] - t["entry"]) * sig_sign / SCALE
                pnl = units * (move_xsp - 2.0 * slip)
                equity += pnl
                day_trades.append(t["name"])
                trade_rows.append({**t, "date": e.date, "units": units,
                                   "pnl": round(pnl, 2), "equity_after": round(equity, 2),
                                   "note": "capped_at_1x_equity" if capped else ""})
        n_busy_skipped = len(tradeable) - len(day_trades) if tradeable else 0

        day_rows.append({
            "date": e.date, "trend_state": ctx.trend_state, "regime": ctx.regime,
            "cum_number_line": ctx.cum,
            "raw_setups": "|".join(f"{s.name}:{s.direction}" for s in raw),
            "after_macro": "|".join(f"{s.name}:{s.direction}(c{s.conviction})" for s in kept),
            "excluded_logged": "|".join(s.name for s in excluded),
            "macro_setups_logged": "|".join(s.name for s in ctx.macro_setups),
            "trades_taken": "|".join(day_trades),
            "skipped_while_holding": n_busy_skipped,
            "no_trade_reason": reason,
            "equity_close": round(equity, 2),
        })
        curve.append(equity)

    stats = summarize(trade_rows, day_rows, curve, n_capped, slip)
    if write_files:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        _write_csv(os.path.join(RESULTS_DIR, "acd_underlying_day_ledger.csv"), day_rows)
        _write_csv(os.path.join(RESULTS_DIR, "acd_underlying_trades.csv"), trade_rows)
    return stats, day_rows, trade_rows


def max_drawdown_pct(curve):
    peak, worst = -1e18, 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst


def summarize(trades, days, curve, n_capped, slip):
    done = [t for t in trades if t["units"] > 0]
    wins = [t for t in done if t["pnl"] > 0]
    by_name, by_year = {}, {}
    for t in done:
        by_name.setdefault(t["name"], []).append(t["pnl"])
        by_year.setdefault(t["date"][:4], []).append(t["pnl"])
    return {
        "slip": slip,
        "days_evaluated": len(days),
        "trades": len(done),
        "win_rate": len(wins) / len(done) if done else 0.0,
        "total_pnl": sum(t["pnl"] for t in done),
        "final_equity": curve[-1] if curve else START_EQUITY,
        "max_drawdown": max_drawdown_pct(curve),
        "exit_reasons": dict(Counter(t["reason"] for t in done)),
        "capped_trades": n_capped,
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


def print_stats(st, label=""):
    print(f"=== {label}  slip {st['slip']:.2f} ===  "
          f"trades {st['trades']}  win {st['win_rate']:.0%}  "
          f"P&L ${st['total_pnl']:+,.0f}  final ${st['final_equity']:,.0f}  "
          f"maxDD {st['max_drawdown']:.1%}")


# ---------------------------------------------------------------- sweep configs
def sweep_configs():
    """(label, spec, use_atr, use_macro). ATR variants use Fisher's stated ~18-20%-of-ATR
    formula (c > a); the pct variant is the original %-of-price fallback. OR length 15 vs 30
    minutes. Macro gate on/off (the number-line study found its states non-predictive)."""
    out = []
    for orm in (15, 30):
        base = replace(SPX, or_minutes=orm)
        for a_lab, spec, use_atr in (
            ("pct", base, False),
            ("atr18", replace(base, a_atr_frac=0.18, c_atr_frac=0.22), True),
            ("atr25", replace(base, a_atr_frac=0.25, c_atr_frac=0.30), True),
        ):
            for gate in (True, False):
                out.append((f"OR{orm}/{a_lab}/{'gate' if gate else 'nogate'}",
                            spec, use_atr, gate))
    return out


if __name__ == "__main__":
    # ---- self-tests (no cache needed) ----
    from acd_micro import Setup
    eq = 10_000.0
    assert size_units(eq, 5000.0, 4990.0) == (20, True)     # notional cap binds
    assert size_units(eq, 5000.0, 4550.0) == (6, False)     # risk-based, cap slack
    assert size_units(eq, 5000.0, 5000.0) == (0, False)
    assert size_units(0.0, 5000.0, 4990.0) == (0, False)    # bankrupt -> no trade
    print("self-test OK: sizing")

    # causal clean: a 0.0 print and a 10x glitch die; a normal drift survives
    p = [("09:30", 5000), ("09:31", 5002), ("09:32", 0.0), ("09:33", 50000.0),
         ("09:34", 5004), ("09:35", 5001)]
    kept, dropped = _clean_path_causal(p)
    assert dropped == 2 and all(s > 0 and s < 6000 for _, s in kept), (kept, dropped)
    print("self-test OK: causal hygiene (0.0 and 10x prints dropped, no full-day peek)")

    # ATR is prior-days-only: history of 20 flat days -> ATR exists from day 15 on
    fake = {f"2024-01-{d:02d}": [("09:30", 5000.0), ("10:00", 5010.0), ("15:59", 5005.0)]
            for d in range(1, 22)}
    h = build_hist(fake, replace(SPX, a_atr_frac=0.18, c_atr_frac=0.22), use_atr=True)
    assert len(h) == 20, len(h)
    print("self-test OK: build_hist with prior-days ATR")

    # overnight/stopless exclusion
    s_ok = Setup("a_held", "long", "10:00", 5000.0, 4990.0, 1, "intraday", {})
    s_on = Setup("late_day_c", "long", "14:44", 5000.0, 4990.0, 3, "overnight", {})
    s_ns = Setup("failed_c", "long", "10:20", 5000.0, None, 1, "intraday", {})
    assert tradeable_setups([s_ok, s_on, s_ns]) == [s_ok]
    print("self-test OK: overnight + stopless setups excluded")

    # ---- real 3-year sweep ----
    print("\nLoading 3yr SPX paths from cache (one pass)...")
    paths, skipped = load_paths()
    print(f"paths: {len(paths)} days ({min(paths)} -> {max(paths)}), "
          f"{len(skipped)} skipped for data\n")

    print(f"--- SWEEP (slip {SLIP_BASE}/side) ---")
    results = []
    for label, spec, use_atr, gate in sweep_configs():
        hist = build_hist(paths, spec, use_atr)
        st, *_ = run(paths, hist, slip=SLIP_BASE, use_macro=gate)
        results.append((label, st))
        print_stats(st, label)

    best = max(results, key=lambda r: r[1]["total_pnl"])
    print(f"\nbest by P&L: {best[0]}  (see plateau discussion in the results doc — "
          f"pick stability, not the peak)")

    # baseline-config ledgers (original locked spec: OR15/pct/gate) at all slippages
    print("\n--- BASELINE CONFIG (OR15/pct/gate) slippage sweep + ledgers ---")
    hist = build_hist(paths, SPX, use_atr=False)
    for s in SLIP_SWEEP:
        st, *_ = run(paths, hist, slip=s, use_macro=True, write_files=(s == SLIP_BASE))
        print_stats(st, "OR15/pct/gate")
    print(f"\nLedgers written to {os.path.abspath(RESULTS_DIR)}/")
