# experiments_spx.py — THE HYPOTHESIS CAMPAIGN HARNESS (2026-07-02 autonomous session).
# Every experiment is a named variant of the BOT v2 baseline (a_held breakouts only,
# 0DTE 25-wide debit spread, hold to settle, FOMC ban, no macro gate, $10k @ 3%
# XSP-scale compounding, slip 0.05/leg). Variants plug in as:
#   - setup_filter(entry, setup) -> bool     (H2 pivot filters, H4 coil filters)
#   - spec/atr overrides                     (H3 modern parameters)
#   - extra banned dates                     (H5 data-free days)
#   - pricer override                        (H6 time-stop exit)
# NOTHING in the main driver changes per experiment. Logs -> results/spx/hypotheses/.
# PLAYGROUND ONLY: all of this is in-sample exploration on 2023-26. The 2021-23 pull
# is the exam and stays untouched.
#
# Run from bot/:  ../.venv/bin/python experiments_spx.py
import os
from datetime import date, timedelta
from dataclasses import replace

from acd_micro import SPX
from backtest_acd_spx_underlying import load_paths, build_hist, official_closes, \
    max_drawdown_pct
from backtest_acd_spx_options import price_day, size_contracts, legs_for, _next_min, \
    _value_series, SLIP_BASE, SCALE
from acd_fade_pricing import spread_entry, expire_value
from load_ivol_intraday import load_cached_minutes
from filters import FOMC_DATES

START_EQUITY = 10_000.0
HYP_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "spx", "hypotheses")


# ---------------------------------------------------------------- the one runner
def run_experiment(hist, closes, setup_filter=None, ban=None, pricer=None,
                   slip=SLIP_BASE):
    """BOT v2 loop with hooks. Returns stats dict. a_held only, hold-to-settle unless
    the pricer says otherwise, one trade per day (earliest surviving setup)."""
    banned = set(FOMC_DATES) | (set(ban) if ban else set())
    equity, curve, trades = START_EQUITY, [], []
    for i in range(len(hist)):
        e = hist[i]
        if e.date in banned:
            curve.append(equity)
            continue
        kept = [s for s in e.day_result.setups
                if s.horizon == "intraday" and s.name == "a_held"]
        if setup_filter:
            kept = [s for s in kept if setup_filter(e, s)]
        if not kept:
            curve.append(equity)
            continue
        first = min(kept, key=lambda s: (s.entry_time, s.name))
        if pricer:
            priced = pricer(e.date, first, closes[e.date])
        else:
            p, _why = price_day(e.date, first, closes[e.date], "debit")
            priced = (p["debit"], p["hold_val"], 2) if p else None
        if priced is None:
            curve.append(equity)
            continue
        debit, val, fills = priced
        n = size_contracts(equity, debit, slip)
        if n <= 0:
            curve.append(equity)
            continue
        pnl = n * ((val - debit) / SCALE * 100.0 - fills * slip)
        equity += pnl
        trades.append({"date": e.date, "dir": first.direction,
                       "entry_time": first.entry_time, "pnl": round(pnl, 2)})
        curve.append(equity)
    return _stats(trades, curve)


def _stats(trades, curve):
    wins = [t for t in trades if t["pnl"] > 0]
    by_year = {}
    for t in trades:
        by_year.setdefault(t["date"][:4], []).append(t["pnl"])
    yr = {y: (len(v), round(sum(v))) for y, v in sorted(by_year.items())}
    return {"trades": len(trades),
            "win": len(wins) / len(trades) if trades else 0.0,
            "pnl": round(sum(t["pnl"] for t in trades)),
            "final": round(curve[-1] if curve else START_EQUITY),
            "maxdd": max_drawdown_pct(curve),
            "by_year": yr, "pos_years": sum(1 for _, p in yr.values() if p > 0),
            "rows": trades}


def fmt(label, st):
    yrs = "  ".join(f"{y}:{p:+,}" for y, (_n, p) in st["by_year"].items())
    return (f"| {label} | {st['trades']} | {st['win']:.0%} | ${st['pnl']:+,} | "
            f"{st['maxdd']:.0%} | {st['pos_years']}/4 | {yrs} |")


HEADER = ("| Variant | Trades | Win | P&L | MaxDD | Yrs+ | By year |\n"
          "|---|---|---|---|---|---|---|")


# ---------------------------------------------------------------- H2: pivot confluence
def h2_variants(hist, closes):
    def through_pivot_day(e, s):
        return any(x.name == "a_through_pivot" for x in e.day_result.setups)

    def pivot_not_ahead(e, s):
        lo, hi = e.day_result.pivot_band
        if s.direction == "long":
            ahead = lo > e.day_result.or_high          # band entirely above the OR
            return (not ahead) or s.entry_price > hi   # ok if entry already cleared it
        ahead = hi < e.day_result.or_low
        return (not ahead) or s.entry_price < lo

    def pivot_flip(e, s):      # opened one side of the pivot, broke the other (his live trade)
        return ((e.day_result.or_vs_pivot == "above" and s.direction == "short")
                or (e.day_result.or_vs_pivot == "below" and s.direction == "long"))

    def pivot_side(e, s):      # breakout AGREES with the open side (anti-flip)
        return ((e.day_result.or_vs_pivot == "above" and s.direction == "long")
                or (e.day_result.or_vs_pivot == "below" and s.direction == "short"))

    return [("a: through-pivot days only", dict(setup_filter=through_pivot_day)),
            ("b: skip pivot-ahead (Fisher p.57)", dict(setup_filter=pivot_not_ahead)),
            ("c: pivot-flip only (webinar trade)", dict(setup_filter=pivot_flip)),
            ("d: pivot-side agree (anti-flip)", dict(setup_filter=pivot_side))]


# ---------------------------------------------------------------- H4: coil-then-break
def h4_variants(hist, closes):
    def entry_1030(e, s):
        return s.entry_time >= "10:30"

    def entry_1115(e, s):
        return s.entry_time >= "11:15"

    def clean_coil(e, s):      # no failed-A (either side) before this entry
        return not any(ev.type.startswith("failed_A") and ev.time < s.entry_time
                       for ev in e.day_result.events)

    return [("a: entry >= 10:30", dict(setup_filter=entry_1030)),
            ("b: entry >= 11:15", dict(setup_filter=entry_1115)),
            ("c: clean coil (no failed-A first)", dict(setup_filter=clean_coil))]


# ---------------------------------------------------------------- H5: data-free days
def first_fridays(y0="2023-07", y1="2026-06"):
    """NFP approximation: first Friday of each month (known-good for the window; the
    handful of holiday-shifted releases are accepted noise, logged in the H5 doc)."""
    out, d = [], date(2023, 7, 1)
    while d <= date(2026, 6, 30):
        f = date(d.year, d.month, 1)
        while f.weekday() != 4:
            f += timedelta(days=1)
        out.append(f.isoformat())
        d = (d.replace(day=28) + timedelta(days=5)).replace(day=1)
    return out


# CPI release dates (8:30 ET), from public BLS schedule; APPROXIMATE for a few 2026
# entries — flagged in the H5 log. Good enough for a playground direction check.
CPI_DATES = [
    "2023-07-12", "2023-08-10", "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15", "2024-06-12",
    "2024-07-11", "2024-08-14", "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13", "2025-06-11",
    "2025-07-15", "2025-08-12", "2025-09-11", "2025-10-15", "2025-11-13", "2025-12-10",
    "2026-01-13", "2026-02-11", "2026-03-11", "2026-04-10", "2026-05-12", "2026-06-10",
]


def h5_variants(hist, closes):
    nfp = first_fridays()
    return [("a: +NFP ban (first Fridays)", dict(ban=nfp)),
            ("b: +CPI ban", dict(ban=CPI_DATES)),
            ("c: +NFP +CPI ban", dict(ban=nfp + CPI_DATES))]


# ---------------------------------------------------------------- H6: time-stop exit
def make_timestop_pricer(minutes):
    def _to_min(t):
        return int(t[:2]) * 60 + int(t[3:])

    def pricer(D, setup, close):
        typ, atm, short = legs_for(setup)
        lb = load_cached_minutes("SPX", D, D, atm, typ)
        sb = load_cached_minutes("SPX", D, D, short, typ)
        if lb is None or lb.empty or sb is None or sb.empty:
            return None
        try:
            debit, entry_t = spread_entry(lb, sb, _next_min(setup.entry_time))
        except ValueError:
            return None
        if debit <= 0:
            return None
        struct = {"kind": "debit_spread", "opt_type": typ, "long_strike": atm,
                  "short_strike": short, "width": 25.0}
        hold_val = expire_value(struct, close)
        deadline = _to_min(entry_t) + minutes
        for t, v in _value_series(struct, lb, sb, entry_t):
            if _to_min(t) >= deadline:                 # one-shot check (Fisher time stop)
                if v <= debit:                         # not working by T -> get out
                    return (debit, v, 4)
                break                                  # working -> ride to settle
        return (debit, hold_val, 2)
    return pricer


def h6_variants(hist, closes):
    return [("a: time stop 60min", dict(pricer=make_timestop_pricer(60))),
            ("b: time stop 120min", dict(pricer=make_timestop_pricer(120)))]


# ---------------------------------------------------------------- campaign driver
def run_block(title, variants, hist, closes, baseline_line, log_lines):
    print(f"\n===== {title} =====")
    log_lines.append(f"\n## {title}\n\n{HEADER}")
    log_lines.append(baseline_line)
    for label, cfg in variants:
        st = run_experiment(hist, closes, **cfg)
        line = fmt(label, st)
        print(line)
        log_lines.append(line)
    return log_lines


if __name__ == "__main__":
    # self-tests
    ff = first_fridays()
    assert "2024-01-05" in ff and "2025-06-06" in ff and len(ff) == 36, (len(ff), ff[:3])
    assert len(CPI_DATES) == 36
    print("self-test OK: date lists")

    print("Loading paths + baseline history...")
    paths, _ = load_paths()
    hist = build_hist(paths, SPX, use_atr=False)
    closes = official_closes(paths)

    base = run_experiment(hist, closes)
    base_line = fmt("BASELINE (BOT v2)", base)
    print(base_line)

    lines = ["# Campaign run — singles", "", HEADER, base_line]

    lines = run_block("H2 pivot confluence", h2_variants(hist, closes), hist, closes,
                      base_line, lines)
    lines = run_block("H4 coil-then-break", h4_variants(hist, closes), hist, closes,
                      base_line, lines)
    lines = run_block("H5 data-free days", h5_variants(hist, closes), hist, closes,
                      base_line, lines)
    lines = run_block("H6 time-stop exits", h6_variants(hist, closes), hist, closes,
                      base_line, lines)

    # H3 needs different histories (spec/ATR changes) — separate loop
    print("\n===== H3 modern Fisher parameters =====")
    lines.append(f"\n## H3 modern Fisher parameters\n\n{HEADER}")
    lines.append(base_line)
    for label, spec, use_atr, atr_n in [
        ("a: OR20 / pct", replace(SPX, or_minutes=20), False, 14),
        ("b: OR20 / ATR10 18-22%", replace(SPX, or_minutes=20, a_atr_frac=0.18,
                                           c_atr_frac=0.22), True, 10),
        ("c: OR15 / ATR10 18-22%", replace(SPX, a_atr_frac=0.18, c_atr_frac=0.22),
         True, 10),
        ("d: OR20 / ATR10 20-25%", replace(SPX, or_minutes=20, a_atr_frac=0.20,
                                           c_atr_frac=0.25), True, 10),
    ]:
        h3_hist = build_hist(paths, spec, use_atr, atr_n=atr_n)
        st = run_experiment(h3_hist, closes)
        line = fmt(label, st)
        print(line)
        lines.append(line)

    os.makedirs(HYP_DIR, exist_ok=True)
    out = os.path.join(HYP_DIR, "singles-raw.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nraw results -> {out}")
