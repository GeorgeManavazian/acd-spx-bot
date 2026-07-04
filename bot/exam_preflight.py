# exam_preflight.py — QUADRUPLE-CHECK BEFORE THE EXAM. Verifies inputs and machinery
# WITHOUT computing any aggregate P&L (the pre-registration allows data-quality and
# mechanics verification; it forbids peeking at results). Checks:
#   1. DATA: SPY path coverage (days, bars/day, session completeness), leg-file
#      coverage vs signal days, option-quote sanity (bid<ask, nonzero, spread widths).
#   2. TRACKING: SPY*10 close vs the IVol EOD chain official print, distribution of
#      the error (the strike-anchoring risk, quantified).
#   3. MECHANICS: three sample days walked end-to-end with every number printed —
#      OR, levels, event chain, setup, chosen strikes, the entry quote at the fill
#      minute. Human-verifiable against the frozen spec. Sample days chosen by DATE
#      RULE (first signal day, one mid-2022, last signal day), not by outcome.
# Run: cd bot && ../.venv/bin/python exam_preflight.py
import os

import pandas as pd

from acd_micro import SPX, build_day
from backtest_acd_spx_underlying import build_hist
from load_ivol_intraday import load_cached_minutes, parse_0dte_chain
from pull_exam_databento import SPY_PARQUET, spy_to_paths
from exam_run import EXAM_START, EXAM_END, settle_closes, coil, through_pivot_day

CACHE = os.path.join(os.path.dirname(__file__), "..", "data_cache")


def main():
    print("=== 1. DATA COVERAGE ===")
    paths = {d: b for d, b in spy_to_paths(pd.read_parquet(SPY_PARQUET)).items()
             if d <= EXAM_END}
    exam_days = sorted(d for d in paths if d >= EXAM_START)
    bars = [len(paths[d]) for d in exam_days]
    print(f"SPY paths: {len(exam_days)} exam days ({exam_days[0]} -> {exam_days[-1]})")
    print(f"bars/day: min {min(bars)}, median {sorted(bars)[len(bars)//2]}, "
          f"max {max(bars)}; days <370 bars: {sum(1 for b in bars if b < 370)}")
    opens = [paths[d][0][0] for d in exam_days]
    print(f"first bar always 09:30? {set(opens) == {'09:30'}}")

    hist = [e for e in build_hist(paths, SPX, use_atr=False)
            if EXAM_START <= e.date <= EXAM_END]
    sig = [e for e in hist
           if any(s.name == "a_held" and s.horizon == "intraday"
                  for s in e.day_result.setups)]
    print(f"engine: {len(hist)} days, {len(sig)} a_held signal days")

    have = miss = bad_quote = 0
    spreads = []
    for e in sig:
        for s in e.day_result.setups:
            if s.name != "a_held":
                continue
            typ = "call" if s.direction == "long" else "put"
            atm = round(s.entry_price / 5.0) * 5.0
            far = atm + 25.0 if s.direction == "long" else atm - 25.0
            for k in (atm, far):
                df = load_cached_minutes("SPX", e.date, e.date, k, typ)
                if df is None or df.empty:
                    miss += 1
                    continue
                have += 1
                mid = df[(df["time"] >= "10:00") & (df["time"] <= "15:00")]
                if len(mid) and ((mid["bid"] > mid["ask"]).any()
                                 or (mid["ask"] <= 0).all()):
                    bad_quote += 1
                if len(mid):
                    spreads.append(float((mid["ask"] - mid["bid"]).median()))
    print(f"legs: {have} cached, {miss} missing (no-SPXW days -> no_expiry rule), "
          f"{bad_quote} files with crossed/zero quotes")
    if spreads:
        s_ = sorted(spreads)
        print(f"median NBBO spread per file: p50 {s_[len(s_)//2]:.2f}  "
              f"p90 {s_[int(len(s_)*0.9)]:.2f} (SPX pts)")

    print("\n=== 2. SPY*10 vs OFFICIAL CLOSE (tracking error) ===")
    closes, n_fb = settle_closes(paths)
    errs = []
    for d in exam_days:
        p = os.path.join(CACHE, f"SPX_{d}_0dte_m6.csv")
        try:
            _, official = parse_0dte_chain(pd.read_csv(p))
            errs.append(abs(paths[d][-1][1] - float(official)))
        except Exception:
            pass
    if errs:
        e_ = sorted(errs)
        print(f"n={len(e_)}  median {e_[len(e_)//2]:.2f} pts  "
              f"p90 {e_[int(len(e_)*0.9)]:.2f}  max {e_[-1]:.2f} "
              f"(settle uses the OFFICIAL print; SPY*10 fallback on {n_fb} days)")

    print("\n=== 3. SAMPLE-DAY WALKTHROUGHS (date-rule picks, no outcomes shown) ===")
    picks = [sig[0].date, next((e.date for e in sig if e.date >= "2022-06-01"),
                               sig[len(sig) // 2].date), sig[-1].date]
    for d in picks:
        e = next(x for x in hist if x.date == d)
        dr = e.day_result
        print(f"\n--- {d} ---")
        print(f"OR 09:30-09:45: high {dr.or_high:.2f} low {dr.or_low:.2f} "
              f"| pivot band {tuple(round(x, 2) for x in dr.pivot_band)} "
              f"| or_vs_pivot {dr.or_vs_pivot}")
        print(f"events: {' | '.join(f'{ev.type}@{ev.time}({ev.price:.2f})' for ev in dr.events)}")
        for s in dr.setups:
            if s.name != "a_held":
                continue
            print(f"setup: {s.name} {s.direction} entry {s.entry_time} @ {s.entry_price:.2f} "
                  f"| coil={coil(e, s)} through_pivot_day={through_pivot_day(e, s)}")
            typ = "call" if s.direction == "long" else "put"
            atm = round(s.entry_price / 5.0) * 5.0
            far = atm + 25.0 if s.direction == "long" else atm - 25.0
            for k in (atm, far):
                df = load_cached_minutes("SPX", d, d, k, typ)
                if df is None:
                    print(f"  leg {int(k)}{typ[0].upper()}: MISSING")
                    continue
                nxt = df[df["time"] > s.entry_time].head(1)
                if len(nxt):
                    r = nxt.iloc[0]
                    print(f"  leg {int(k)}{typ[0].upper()}: fill bar {r['time']} "
                          f"bid {r['bid']:.2f} ask {r['ask']:.2f}")
    print("\nPre-flight complete. NO aggregate P&L was computed.")


if __name__ == "__main__":
    main()
