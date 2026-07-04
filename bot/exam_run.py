# exam_run.py — THE PRE-REGISTERED EXAM, exactly per docs/exam-preregistration-2026-07-03.md.
# Runs ONCE on the 2021-06-28..2023-07-03 held-out window (Databento amendment: underlying
# = SPY*10; option quotes = OPRA cbbo-1m; settle = IVol EOD chain print, SPY*10 close as
# documented fallback). NOTHING here may be tuned; the configs are the frozen Earner (C4)
# and Tank (C5). Deviations from the registration text must be reported with the results.
#
#   Earner: a_held only + clean coil + FOMC ban + CPI ban, debit spread ATM/+25, hold.
#   Tank  : a_held only + clean coil + through-pivot day + FOMC ban, same structure.
#   $10k start, 3% of current equity on (debit + 2*slip), slip 0.05/leg (sweep 0/.10/.20
#   reported), XSP scale /10, one trade/day, settle at expiry.
#
# Run (the ceremony): cd bot && ../.venv/bin/python exam_run.py --confirm
import argparse
import csv
import os

import pandas as pd

from acd_micro import SPX
from backtest_acd_spx_underlying import build_hist, max_drawdown_pct
from backtest_acd_spx_options import price_day, size_contracts
from filters import FOMC_DATES
from pull_exam_databento import SPY_PARQUET, spy_to_paths

CACHE = os.path.join(os.path.dirname(__file__), "..", "data_cache")
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "spx", "exam")
EXAM_START, EXAM_END = "2021-07-06", "2023-07-03"
START_EQUITY, RISK_PCT, SLIP = 10_000.0, 0.03, 0.05

# frozen lists, verbatim from the pre-registration (2023 H1 FOMC from filters.py)
FOMC_EXAM = [
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22",
    "2021-11-03", "2021-12-15", "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
]
CPI_EXAM = [
    "2021-07-13", "2021-08-11", "2021-09-14", "2021-10-13", "2021-11-10", "2021-12-10",
    "2022-01-12", "2022-02-10", "2022-03-10", "2022-04-12", "2022-05-11", "2022-06-10",
    "2022-07-13", "2022-08-10", "2022-09-13", "2022-10-13", "2022-11-10", "2022-12-13",
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12", "2023-05-10", "2023-06-13",
]


def exam_paths():
    df = pd.read_parquet(SPY_PARQUET)
    return {d: b for d, b in spy_to_paths(df).items() if d <= EXAM_END}


def settle_closes(paths):
    """Official EOD chain print where the IVol 2021-23 chains have it; else SPY*10 close
    (fallback counted + reported)."""
    from load_ivol_intraday import parse_0dte_chain
    closes, fallback = {}, 0
    for d in paths:
        p = os.path.join(CACHE, f"SPX_{d}_0dte_m6.csv")
        try:
            _, anchor = parse_0dte_chain(pd.read_csv(p))
            closes[d] = float(anchor)
        except Exception:
            closes[d] = paths[d][-1][1]
            fallback += 1
    return closes, fallback


def coil(e, s):
    return not any(ev.type.startswith("failed_A") and ev.time < s.entry_time
                   for ev in e.day_result.events)


def through_pivot_day(e, s):
    return any(x.name == "a_through_pivot" for x in e.day_result.setups)


BOTS = {
    "earner": {"filter": coil,
               "ban": set(FOMC_DATES) | set(FOMC_EXAM) | set(CPI_EXAM)},
    "tank": {"filter": lambda e, s: coil(e, s) and through_pivot_day(e, s),
             "ban": set(FOMC_DATES) | set(FOMC_EXAM)},
}


def run_bot(hist, closes, bot, slip=SLIP):
    cfg = BOTS[bot]
    equity, curve = START_EQUITY, []
    trades, day_rows = [], []
    for e in hist:
        reason, taken = "", None
        if e.date in cfg["ban"]:
            reason = "banned"
        else:
            kept = [s for s in e.day_result.setups
                    if s.horizon == "intraday" and s.name == "a_held"
                    and cfg["filter"](e, s)]
            if not kept:
                reason = "no_qualifying_setup"
            else:
                first = min(kept, key=lambda s: (s.entry_time, s.name))
                p, why = price_day(e.date, first, closes[e.date], "debit")
                if p is None:
                    reason = f"no_expiry_or_data ({why})"
                else:
                    n = size_contracts(equity, p["debit"], slip)
                    if n <= 0:
                        reason = "size_zero"
                    else:
                        pnl = n * ((p["hold_val"] - p["debit"]) / 10.0 * 100.0 - 2 * slip)
                        equity += pnl
                        taken = {**{k: p[k] for k in ("date", "name", "direction",
                                                      "entry_time", "typ", "long",
                                                      "short", "debit", "hold_val")},
                                 "contracts": n, "pnl": round(pnl, 2),
                                 "equity_after": round(equity, 2),
                                 "or_high": round(e.day_result.or_high, 2),
                                 "or_low": round(e.day_result.or_low, 2),
                                 "events": "|".join(f"{ev.type}@{ev.time}"
                                                    for ev in e.day_result.events),
                                 "settle": closes[e.date]}
                        trades.append(taken)
        day_rows.append({"date": e.date, "trade": taken["name"] if taken else "",
                         "pnl": taken["pnl"] if taken else "", "reason": reason,
                         "equity": round(equity, 2)})
        curve.append(equity)
    return trades, day_rows, curve


def report(bot, trades, day_rows, curve, playground_dd):
    wins = [t for t in trades if t["pnl"] > 0]
    by_year, by_month_22 = {}, {}
    for t in trades:
        by_year.setdefault(t["date"][:4], []).append(t["pnl"])
        if t["date"].startswith("2022"):
            by_month_22.setdefault(t["date"][:7], []).append(t["pnl"])
    dd = max_drawdown_pct(curve)
    pnl = sum(t["pnl"] for t in trades)
    p1 = pnl > 0
    p2 = dd >= -playground_dd * 1.5
    lines = [f"## {bot.upper()}",
             f"- trades {len(trades)}  win {len(wins) / max(len(trades), 1):.0%}  "
             f"P&L ${pnl:+,.0f}  final ${curve[-1]:,.0f}  maxDD {dd:.1%}",
             "- by year: " + "  ".join(f"{y}: ${sum(v):+,.0f} (n={len(v)})"
                                       for y, v in sorted(by_year.items())),
             "- 2022 bear-market months: "
             + "  ".join(f"{m[5:]}: ${sum(v):+,.0f}"
                         for m, v in sorted(by_month_22.items())),
             f"- PASS bar 1 (P&L>0): {'PASS' if p1 else 'FAIL'}",
             f"- PASS bar 2 (maxDD <= {playground_dd * 1.5:.0%}): "
             f"{'PASS' if p2 else 'FAIL'} ({dd:.1%})",
             f"- **VERDICT: {'PASS' if (p1 and p2) else 'FAIL'}**"]
    return "\n".join(lines), (p1 and p2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="the exam runs ONCE; require explicit confirmation")
    a = ap.parse_args()
    if not a.confirm:
        raise SystemExit("This is the pre-registered exam. Run with --confirm to fire. "
                         "It runs ONCE.")
    if os.path.exists(os.path.join(OUT, "EXAM-RESULTS.md")):    # run-once, enforced
        raise SystemExit("EXAM ALREADY RAN — results exist. Re-running would violate "
                         "the pre-registration. (Audit item 9 sentinel.)")
    os.makedirs(OUT, exist_ok=True)
    paths = exam_paths()
    hist = [e for e in build_hist(paths, SPX, use_atr=False)
            if EXAM_START <= e.date <= EXAM_END]
    closes, n_fallback = settle_closes(paths)
    print(f"exam: {len(hist)} days ({hist[0].date} -> {hist[-1].date}), "
          f"settle fallbacks {n_fallback}")
    md = [f"# EXAM RESULTS — run {__import__('datetime').date.today().isoformat()}",
          f"{len(hist)} days; settle fallbacks {n_fallback}; slip {SLIP}/leg", ""]
    for bot, pdd in (("earner", 0.20), ("tank", 0.12)):
        trades, day_rows, curve = run_bot(hist, closes, bot)
        block, _ = report(bot, trades, day_rows, curve, pdd)
        print("\n" + block)
        md.append(block + "\n")
        for tag, rows in (("trades", trades), ("days", day_rows)):
            p = os.path.join(OUT, f"exam_{bot}_{tag}.csv")
            if rows:
                with open(p, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    w.writeheader()
                    w.writerows(rows)
        # slippage sensitivity (reported, not judged)
        for s in (0.0, 0.10, 0.20):
            tr, _dr, cv = run_bot(hist, closes, bot, slip=s)
            md.append(f"  - slip {s:.2f}: P&L ${sum(t['pnl'] for t in tr):+,.0f} "
                      f"maxDD {max_drawdown_pct(cv):.1%}")
        md.append("")
    with open(os.path.join(OUT, "EXAM-RESULTS.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"\nwritten: {os.path.join(OUT, 'EXAM-RESULTS.md')}")
