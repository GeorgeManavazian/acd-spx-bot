# backtest_portfolio_condor.py — THE COMBINED BOOK: breakout bot (Earner C4 or Tank C5)
# + iron condor on QUIET days, one shared compounding account. Locked spec (committed
# BEFORE the ladder data lands — the condor cells have never been seen):
#
#   Day routing (in order):
#     1. banned (FOMC always; +CPI for the Earner book, matching C4's own ban) -> cash.
#     2. breakout setup that passes the bot's filter (C4 coil / C5 coil+through-pivot)
#        -> the bot's normal trade: 0DTE 25-wide debit spread, next-bar NBBO, hold to settle.
#     3. QUIET day — NO A-family event all morning (no pierce, no fail; the A window
#        closes at 12:00, so this is live-knowable at noon) -> IRON CONDOR at the first
#        bar > 12:00: short call at first 5-strike >= or_high, short put at first
#        5-strike <= or_low, wings 25 further out. Real NBBO, 4 legs crossed at entry.
#     4. anything else (breakout attempted but filtered / unpriceable) -> cash. A day
#        that ATTEMPTED a breakout is not quiet; it never gets a condor.
#
#   Condor exits (the 4-way comparison, per user spec):
#     E1 hold      — cash-settle at the official close (4 entry fills only)
#     E2 bb50      — buy back when cost-to-close <= 50% of credit (8 fills)
#     E3 bb25      — buy back when cost-to-close <= 25% of credit (8 fills)
#     E4 flat1500  — close at the first bar >= 15:00 regardless (8 fills)
#   Exit walks use closeable values (short.ask - long.bid per side), bars strictly
#   after entry, never past 15:59.
#
#   Sizing: risk_pct of CURRENT equity on max loss/contract (condor: width - credit
#   + 4 legs slippage; debit spread: debit + 2 legs slippage). Compounding, shared.
#   Slippage 0.05/leg/fill baseline. XSP scale (/10).
#
# Run from bot/:  ../.venv/bin/python backtest_portfolio_condor.py [--probe]
#   --probe: report quiet-day leg coverage in the cache without running P&L.
import os
import sys
from collections import Counter

from acd_micro import SPX
from backtest_acd_spx_underlying import load_paths, build_hist, official_closes, \
    max_drawdown_pct
from backtest_acd_spx_options import price_day, legs_for, _next_min, SCALE, WIDTH
from acd_fade_pricing import spread_entry, expire_value
from load_ivol_intraday import load_cached_minutes
from filters import FOMC_DATES
from experiments_spx import CPI_DATES

START_EQUITY = 10_000.0
SLIP = 0.05
CONDOR_TIME = "12:00"
LAST_TRADEABLE = "15:59"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "spx", "hypotheses")

A_EVENTS = ("A_up", "A_down", "failed_A_up", "failed_A_down")


# ---------------------------------------------------------------- day classification
def coil(e, s):
    return not any(ev.type.startswith("failed_A") and ev.time < s.entry_time
                   for ev in e.day_result.events)


def through_pivot_day(e, s):
    return any(x.name == "a_through_pivot" for x in e.day_result.setups)


BOTS = {
    "earner": {"filter": coil, "ban": set(FOMC_DATES) | set(CPI_DATES)},
    "tank": {"filter": lambda e, s: coil(e, s) and through_pivot_day(e, s),
             "ban": set(FOMC_DATES)},
}


def is_quiet(e):
    """True when NO A-family event occurred all morning — nothing pierced either A level
    before the 12:00 cutoff. Live-knowable at noon."""
    return not any(ev.type in A_EVENTS for ev in e.day_result.events)


# ---------------------------------------------------------------- condor pricing
def _grid_up(x):
    return float(-(-x // 5) * 5)          # first 5-strike >= x


def _grid_dn(x):
    return float(x // 5 * 5)              # first 5-strike <= x


def condor_legs(e):
    sc = _grid_up(e.day_result.or_high)   # short call at/above the OR high
    sp = _grid_dn(e.day_result.or_low)    # short put at/below the OR low
    return sc, sc + WIDTH, sp, sp - WIDTH


def _series(bars):
    return {str(r["time"]): r for _, r in bars.iterrows()}


def price_condor(D, e, close):
    """Entry credit + per-bar cost-to-close + settle-owed for the day's condor.
    Returns (credit, owed_at_settle, walk[(t, cost_to_close)]) or (None, why)."""
    sc, lc, sp, lp = condor_legs(e)
    legs = {}
    for k, typ in ((sc, "call"), (lc, "call"), (sp, "put"), (lp, "put")):
        b = load_cached_minutes("SPX", D, D, k, typ)
        if b is None or b.empty:
            return None, "missing_leg_bars"
        legs[(k, typ)] = _series(b)
    fill_from = _next_min(CONDOR_TIME)
    times = sorted(set.intersection(*[set(s) for s in legs.values()]))
    entry_ts = [t for t in times if t >= fill_from]
    if not entry_ts:
        return None, "no_fillable_bar"
    t0 = entry_ts[0]
    credit = (float(legs[(sc, "call")][t0]["bid"]) - float(legs[(lc, "call")][t0]["ask"])
              + float(legs[(sp, "put")][t0]["bid"]) - float(legs[(lp, "put")][t0]["ask"]))
    if credit <= 0 or credit >= 2 * WIDTH:
        return None, "degenerate_credit"
    owed = (min(max(close - sc, 0.0), WIDTH) + min(max(sp - close, 0.0), WIDTH))
    walk = []
    for t in entry_ts[1:]:
        if t > LAST_TRADEABLE:
            break
        cost = (float(legs[(sc, "call")][t]["ask"]) - float(legs[(lc, "call")][t]["bid"])
                + float(legs[(sp, "put")][t]["ask"]) - float(legs[(lp, "put")][t]["bid"]))
        walk.append((t, cost))
    return (credit, owed, walk), ""


def condor_pnl_per_share(credit, owed, walk, exit_mode):
    """(pnl_per_share, n_fills). Buyback/flat exits pay the walked cost (8 fills);
    hold settles in cash (4 fills)."""
    if exit_mode == "hold":
        return credit - owed, 4
    if exit_mode in ("bb50", "bb25"):
        frac = 0.5 if exit_mode == "bb50" else 0.25
        for _t, cost in walk:
            if cost <= frac * credit:
                return credit - cost, 8
        return credit - owed, 4               # never triggered -> settle
    if exit_mode == "flat1500":
        for t, cost in walk:
            if t >= "15:00":
                return credit - cost, 8
        return credit - owed, 4               # no bar after 15:00 -> settle
    raise ValueError(exit_mode)


# ---------------------------------------------------------------- the combined runner
def run_portfolio(hist, closes, bot, exit_mode, risk_pct, slip=SLIP):
    cfg = BOTS[bot]
    equity, curve = START_EQUITY, []
    trades, day_reasons = [], Counter()
    for e in hist:
        if e.date in cfg["ban"]:
            day_reasons["banned"] += 1
            curve.append(equity)
            continue
        kept = [s for s in e.day_result.setups
                if s.horizon == "intraday" and s.name == "a_held" and cfg["filter"](e, s)]
        traded = False
        if kept:
            first = min(kept, key=lambda s: (s.entry_time, s.name))
            p, _why = price_day(e.date, first, closes[e.date], "debit")
            if p:
                per = p["debit"] / SCALE * 100.0 + 2 * slip
                n = int(risk_pct * equity / per) if per > 0 else 0
                if n > 0:
                    pnl = n * ((p["hold_val"] - p["debit"]) / SCALE * 100.0 - 2 * slip)
                    equity += pnl
                    trades.append({"date": e.date, "kind": "breakout", "pnl": round(pnl, 2)})
                    day_reasons["breakout"] += 1
                    traded = True
        elif is_quiet(e):
            pc, why = price_condor(e.date, e, closes[e.date])
            if pc is None:
                day_reasons[f"condor_{why}"] += 1
            else:
                credit, owed, walk = pc
                pps, fills = condor_pnl_per_share(credit, owed, walk, exit_mode)
                # max loss = width - credit (only ONE side can finish in the money)
                per = (WIDTH - credit) / SCALE * 100.0 + 4 * slip
                if per <= 0:
                    per = 4 * slip
                n = int(risk_pct * equity / per)
                if n > 0:
                    pnl = n * (pps / SCALE * 100.0 - fills * slip)
                    equity += pnl
                    trades.append({"date": e.date, "kind": "condor", "pnl": round(pnl, 2)})
                    day_reasons["condor"] += 1
                    traded = True
        if not traded and not kept and not is_quiet(e):
            day_reasons["attempted_not_taken"] += 1
        curve.append(equity)
    return _stats(trades, curve, day_reasons)


def _stats(trades, curve, reasons):
    def block(rows):
        w = [t for t in rows if t["pnl"] > 0]
        return {"n": len(rows), "win": len(w) / len(rows) if rows else 0.0,
                "pnl": round(sum(t["pnl"] for t in rows))}
    by_year = {}
    for t in trades:
        by_year.setdefault(t["date"][:4], []).append(t["pnl"])
    return {"all": block(trades),
            "breakout": block([t for t in trades if t["kind"] == "breakout"]),
            "condor": block([t for t in trades if t["kind"] == "condor"]),
            "final": round(curve[-1] if curve else START_EQUITY),
            "maxdd": max_drawdown_pct(curve),
            "by_year": {y: round(sum(v)) for y, v in sorted(by_year.items())},
            "pos_years": sum(1 for v in by_year.values() if sum(v) > 0),
            "reasons": dict(reasons)}


# ---------------------------------------------------------------- probe + main
def probe(hist):
    """How many quiet days can the current cache price? (Run before the real test.)"""
    n_quiet = n_ok = 0
    why = Counter()
    for e in hist:
        if not is_quiet(e):
            continue
        n_quiet += 1
        sc, lc, sp, lp = condor_legs(e)
        missing = [k for k, typ in ((sc, "call"), (lc, "call"), (sp, "put"), (lp, "put"))
                   if load_cached_minutes("SPX", e.date, e.date, k, typ) is None]
        if missing:
            why["missing_legs"] += 1
        else:
            n_ok += 1
    print(f"quiet days: {n_quiet}, fully priceable now: {n_ok} "
          f"({n_ok / max(n_quiet, 1):.0%}) — ladder pull fills the rest")
    return n_quiet, n_ok


if __name__ == "__main__":
    # ---- self-tests (synthetic; no cache) ----
    assert _grid_up(5003.2) == 5005.0 and _grid_up(5005.0) == 5005.0
    assert _grid_dn(4998.7) == 4995.0 and _grid_dn(4995.0) == 4995.0
    # condor pnl math: credit 8, settle owed 3 -> hold = +5 per share, 4 fills
    assert condor_pnl_per_share(8.0, 3.0, [], "hold") == (5.0, 4)
    # bb50: cost path drops to 3.9 (<= 4.0 = 50% of 8) -> pnl 8-3.9, 8 fills
    pnl, fills = condor_pnl_per_share(8.0, 25.0, [("13:00", 6.0), ("14:00", 3.9)], "bb50")
    assert abs(pnl - 4.1) < 1e-9 and fills == 8
    # bb25 not reached -> settles
    assert condor_pnl_per_share(8.0, 0.0, [("14:00", 3.0)], "bb25") == (8.0, 4)
    # flat1500 closes at the first 15:00+ bar
    pnl, fills = condor_pnl_per_share(8.0, 0.0, [("14:59", 5.0), ("15:01", 2.0)], "flat1500")
    assert abs(pnl - 6.0) < 1e-9 and fills == 8
    print("self-test OK: condor math (grid, hold/bb50/bb25/flat1500)")

    print("\nLoading history...")
    paths, _ = load_paths()
    hist = build_hist(paths, SPX, use_atr=False)
    closes = official_closes(paths)

    nq, nok = probe(hist)
    if "--probe" in sys.argv:
        sys.exit(0)
    if nok < 0.9 * nq:
        print(f"\nDATA NOT READY ({nok}/{nq} quiet days priceable) — wait for the ladder "
              f"pull, then rerun. Refusing a biased partial run.")
        sys.exit(1)

    print("\n=== THE GRID: 2 bots x 4 exits x 2 risks ===")
    rows = []
    for bot in ("earner", "tank"):
        for ex in ("hold", "bb50", "bb25", "flat1500"):
            for rp in (0.03, 0.05):
                st = run_portfolio(hist, closes, bot, ex, rp)
                rows.append((bot, ex, rp, st))
                yr = "  ".join(f"{y}:{p:+,}" for y, p in st["by_year"].items())
                print(f"{bot:<7} {ex:<9} {rp:.0%}: all n={st['all']['n']} "
                      f"${st['all']['pnl']:+,} (bo ${st['breakout']['pnl']:+,} / "
                      f"co ${st['condor']['pnl']:+,} win {st['condor']['win']:.0%}) "
                      f"final ${st['final']:,} maxDD {st['maxdd']:.0%} "
                      f"yrs+ {st['pos_years']}/4 | {yr}")

    print("\n=== HEADLINE: best condor exit per bot ===")
    for bot in ("earner", "tank"):
        for rp in (0.03, 0.05):
            best = max((r for r in rows if r[0] == bot and r[2] == rp),
                       key=lambda r: (r[3]["pos_years"], r[3]["final"]))
            st = best[3]
            print(f"{bot} @ {rp:.0%}: best exit = {best[1]}  final ${st['final']:,}  "
                  f"maxDD {st['maxdd']:.0%}  yrs+ {st['pos_years']}/4")
