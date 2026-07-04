# pull_exam_databento.py — EXAM DATA VIA DATABENTO (~$1 of the $30 credit).
# The IVolatility plan couldn't reach pre-2023-07 minute data; Databento OPRA can.
# Pipeline (cost-estimated before every purchase, hard budget guard $25):
#   1. SPY 1-min bars 2021-06-28..2023-07-03 (XNAS.ITCH ohlcv-1m, ~$0.24) -> per-day
#      [(HH:MM ET, close*10)] paths (SPY*10 tracks SPX within ~0.05% intraday; the
#      documented underlying approximation for the exam).
#   2. Run the audited engine over those paths OFFLINE, collect every a_held signal
#      day, derive the exact legs the frozen configs price (ATM-5-grid + 25 further,
#      call for longs / put for shorts). NO P&L IS COMPUTED — signal enumeration only,
#      per the pre-registration.
#   3. Pull ONLY those legs' OPRA cbbo-1m (SPXW dailies; pennies), write them to
#      data_cache/ in the exact SPX_{d}_{d}_{K}_{T}_min.csv shape load_cached_minutes
#      expects — the exam runner then works unchanged.
#   4. Print data-quality stats (coverage, bar counts). The exam itself runs later,
#      once, per docs/exam-preregistration-2026-07-03.md.
# Run: cd bot && set -a && source ../.env && set +a && ../.venv/bin/python pull_exam_databento.py
import datetime as dt
import os

import pandas as pd

CACHE = os.path.join(os.path.dirname(__file__), "..", "data_cache")
START, END = "2021-06-28", "2023-07-04"          # end exclusive for databento
BUDGET = 25.0
SPY_PARQUET = os.path.join(CACHE, "SPY_1m_2021-06-28_2023-07-03.parquet")

_spent = 0.0


def _client():
    import databento as db
    return db.Historical(os.environ["DATABENTO_API_KEY"])


def _buy(c, **kw):
    """get_range with a running budget guard."""
    global _spent
    cost = c.metadata.get_cost(**{k: v for k, v in kw.items()})
    if _spent + cost > BUDGET:
        raise SystemExit(f"BUDGET GUARD: ${_spent:.2f} spent + ${cost:.2f} would exceed "
                         f"${BUDGET}")
    _spent += cost
    print(f"  buying: ${cost:.4f} (total ${_spent:.2f})", flush=True)
    return c.timeseries.get_range(**kw)


# ---------------------------------------------------------------- 1. SPY paths
def pull_spy(c):
    if os.path.exists(SPY_PARQUET):
        return pd.read_parquet(SPY_PARQUET)
    data = _buy(c, dataset="XNAS.ITCH", symbols=["SPY"], schema="ohlcv-1m",
                start=START, end=END)
    df = data.to_df()
    df.to_parquet(SPY_PARQUET)
    return df


# NYSE half days in/near the exam window (ex-ante public calendar). Audit D2 fix:
# without this, 2022-11-25 (290 bars) was dropped and 2021-11-26 kept 125 after-hours
# bars that moved its close ~20 pts into the next day's pivot.
HALF_DAYS = {"2021-11-26", "2022-11-25", "2023-07-03"}


def spy_to_paths(df):
    """{date: [(HH:MM ET, close*10)]} RTH-only; half days trimmed at the 13:00 close."""
    idx = df.index.tz_convert("America/New_York")
    out = {}
    for ts, row in zip(idx, df.itertuples()):
        d = ts.date().isoformat()
        hhmm = ts.strftime("%H:%M")
        end = "13:00" if d in HALF_DAYS else "16:00"
        if "09:30" <= hhmm <= end:
            out.setdefault(d, []).append((hhmm, float(row.close) * 10.0))
    return {d: bars for d, bars in out.items()
            if len(bars) >= (150 if d in HALF_DAYS else 300)}


# ---------------------------------------------------------------- 2. signal legs
def exam_legs(paths):
    from acd_micro import SPX
    from backtest_acd_spx_underlying import build_hist
    hist = build_hist(paths, SPX, use_atr=False)
    legs, sig_days = set(), 0
    for e in hist:
        sigs = [s for s in e.day_result.setups
                if s.horizon == "intraday" and s.name == "a_held"]
        if not sigs:
            continue
        sig_days += 1
        for s in sigs:
            typ = "C" if s.direction == "long" else "P"
            atm = round(s.entry_price / 5.0) * 5.0
            far = atm + 25.0 if s.direction == "long" else atm - 25.0
            for k in (atm, far):
                legs.add((e.date, k, typ))
    print(f"engine over {len(hist)} exam days: {sig_days} a_held signal days, "
          f"{len(legs)} unique legs")
    return sorted(legs)


def osi(date, strike, cp):
    ymd = date[2:4] + date[5:7] + date[8:10]
    return f"SPXW  {ymd}{cp}{int(round(strike * 1000)):08d}"


# ---------------------------------------------------------------- 3. buy legs
def pull_legs(c, legs):
    by_day = {}
    for d, k, cp in legs:
        by_day.setdefault(d, []).append((k, cp))
    ok = missing = 0
    for n, (d, ks) in enumerate(sorted(by_day.items()), 1):
        want = {osi(d, k, cp): (k, cp) for k, cp in ks}
        end = (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()
        try:
            data = _buy(c, dataset="OPRA.PILLAR", schema="cbbo-1m",
                        symbols=list(want), stype_in="raw_symbol", start=d, end=end)
            df = data.to_df()
        except Exception as e:
            print(f"  {d}: FAILED {str(e)[:80]}")
            missing += len(ks)
            continue
        if df.empty:
            missing += len(ks)
            continue
        idx = df.index.tz_convert("America/New_York")
        df = df.assign(time=[t.strftime("%H:%M") for t in idx])
        for sym, (k, cp) in want.items():
            sub = df[df["symbol"] == sym]
            if sub.empty:
                missing += 1
                continue
            out = pd.DataFrame({"time": sub["time"],
                                "bid": sub["bid_px_00"].astype(float),
                                "ask": sub["ask_px_00"].astype(float)})
            out = out[( "09:30" <= out["time"]) & (out["time"] <= "16:15")]
            out = out.drop_duplicates("time").sort_values("time")
            tag = f"SPX_{d}_{d}_{int(k)}_{cp}_min.csv"
            # write with a `timestamp` column shape normalize_minutes understands? No —
            # we write the NORMALIZED shape directly; load_cached_minutes will pass it
            # through normalize_minutes, which requires the RAW column names. Write raw:
            raw = pd.DataFrame({"timestamp": "2000-01-01 " + out["time"] + ":00",
                                "optionBidPrice": out["bid"],
                                "optionAskPrice": out["ask"],
                                "underlyingPrice": 0.0, "optionIv": 0.0})
            raw.to_csv(os.path.join(CACHE, tag), index=False)
            ok += 1
        if n % 25 == 0 or n == len(by_day):
            print(f"[{n}/{len(by_day)} days] legs ok={ok} missing={missing}", flush=True)
    print(f"legs done: ok={ok} missing={missing}  (missing = no SPXW 0DTE that day "
          f"-> the exam's no_expiry rule)")


if __name__ == "__main__":
    if not os.environ.get("DATABENTO_API_KEY"):
        raise SystemExit("DATABENTO_API_KEY missing (source .env)")
    c = _client()
    print("=== 1. SPY minute bars ===")
    spy = pull_spy(c)
    paths = spy_to_paths(spy)
    print(f"paths: {len(paths)} trading days ({min(paths)} -> {max(paths)})")
    print("=== 2. engine -> exact legs (no P&L) ===")
    legs = exam_legs(paths)
    print("=== 3. buy the legs ===")
    pull_legs(c, legs)
    print(f"=== DONE. total spend ${_spent:.2f} of ${BUDGET} guard ===")
