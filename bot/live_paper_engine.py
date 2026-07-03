# live_paper_engine.py — PAPER TRADING loop: the SAME brain as the backtest, fed by
# live Schwab data, executing nothing — it records what it WOULD do, with real XSP
# strikes and real NBBO, into an auditable ledger.
#
# Fidelity is the whole design: signals come from acd_micro.build_day (the audited
# engine, byte-identical to the backtest) on bars-so-far each minute; routing uses the
# same coil / through-pivot / quiet-day rules as the campaign configs; fills are
# recorded at the NEXT minute's real NBBO (the backtest's fill convention). At the
# close it settles everything and appends to the ledger. Each evening, replay_check()
# re-runs the day's decisions from the recorded bars and diffs — any daylight between
# "what the live loop did" and "what the engine says it should have done" is a
# fidelity bug to fix before real money ever moves.
#
# Run on a market day (after schwab_auth.py):
#   set -a && source .env && set +a && .venv/bin/python bot/live_paper_engine.py --bot tank
# Flags: --bot earner|tank   --risk 0.03   --once (single scan, no loop; for testing)
import argparse
import csv
import datetime as dt
import json
import os
import time

from acd_micro import build_day, SPX
from filters import FOMC_DATES
from experiments_spx import CPI_DATES

LEDGER = os.path.join(os.path.dirname(__file__), "..", "results", "spx", "paper")
WIDTH_XSP = 2.5                 # 25 SPX pts / 10 — snapped to the REAL XSP grid below
A_EVENTS = ("A_up", "A_down", "failed_A_up", "failed_A_down")


# ---------------------------------------------------------------- decision core (pure)
def decide(bars_so_far, prior_hlc, bot, banned_today, now_hhmm, already_traded):
    """The routing brain, PURE (no I/O) so the nightly replay can rerun it verbatim.
    Returns ("breakout", setup) | ("condor", None) | (None, reason)."""
    if banned_today:
        return None, "banned"
    if already_traded:
        return None, "position_taken"
    dr = build_day("live", bars_so_far, prior_hlc, SPX)
    kept = [s for s in dr.setups if s.horizon == "intraday" and s.name == "a_held"
            and s.entry_time == now_hhmm]                 # act only on THIS minute's signal
    coil_ok = lambda s: not any(ev.type.startswith("failed_A") and ev.time < s.entry_time
                                for ev in dr.events)
    if bot == "tank":
        thr = any(x.name == "a_through_pivot" for x in dr.setups)
        kept = [s for s in kept if coil_ok(s) and thr]
    else:
        kept = [s for s in kept if coil_ok(s)]
    if kept:
        return "breakout", min(kept, key=lambda s: (s.entry_time, s.name))
    quiet = not any(ev.type in A_EVENTS for ev in dr.events)
    if now_hhmm == "12:01" and quiet:                     # condor fires once, at noon+1
        return "condor", None
    return None, "no_signal"


def snap_strike(chain, target, side, direction=1):
    """Nearest REAL listed XSP strike to `target` (direction=+1 prefer >=, -1 prefer <=)."""
    ks = sorted(k for k, s in chain if s == side)
    if not ks:
        return None
    pref = [k for k in ks if (k >= target if direction > 0 else k <= target)]
    pool = pref or ks
    return min(pool, key=lambda k: abs(k - target))


# ---------------------------------------------------------------- the live loop
def run_day(bot="tank", risk=0.03, once=False):
    import schwab_client as sc
    os.makedirs(LEDGER, exist_ok=True)
    today = dt.date.today().isoformat()
    banned = today in set(FOMC_DATES) or (bot == "earner" and today in set(CPI_DATES))
    prior = sc.prior_day_hlc()
    decisions_path = os.path.join(LEDGER, f"decisions_{today}_{bot}.jsonl")
    print(f"paper engine [{bot}] {today}  banned={banned}  prior HLC={prior}")

    open_trade = None
    while True:
        now = dt.datetime.now()
        hhmm = now.strftime("%H:%M")
        if hhmm >= "16:16":
            break
        bars = sc.index_minute_bars()
        if bars and hhmm >= "09:46":                      # OR must be complete
            kind, obj = decide(bars, prior, bot, banned, hhmm,
                               already_traded=open_trade is not None)
            with open(decisions_path, "a") as f:
                f.write(json.dumps({"t": hhmm, "kind": kind,
                                    "why": obj.name if kind == "breakout" else
                                    (obj if isinstance(obj, str) else kind)}) + "\n")
            if kind == "breakout":
                chain = sc.xsp_chain_nbbo()
                spot = bars[-1][1] / 10.0
                sgn = 1 if obj.direction == "long" else -1
                typ = "call" if sgn > 0 else "put"
                atm = snap_strike(chain, spot, typ, 0)
                far = snap_strike(chain, atm + sgn * WIDTH_XSP, typ, sgn)
                if atm is not None and far is not None and far != atm:
                    debit = chain[(atm, typ)][1] - chain[(far, typ)][0]
                    open_trade = {"kind": "breakout", "setup": obj.name,
                                  "dir": obj.direction, "entry_t": hhmm, "typ": typ,
                                  "long": atm, "short": far, "debit": round(debit, 2),
                                  "signal_price": obj.entry_price}
                    print(f"  {hhmm} PAPER FILL breakout {obj.direction} "
                          f"{typ} {atm}/{far} debit {debit:.2f}")
            elif kind == "condor":
                chain = sc.xsp_chain_nbbo()
                dr = build_day("live", bars, prior, SPX)
                sc_k = snap_strike(chain, dr.or_high / 10.0, "call", +1)
                sp_k = snap_strike(chain, dr.or_low / 10.0, "put", -1)
                lc_k = snap_strike(chain, sc_k + WIDTH_XSP, "call", +1)
                lp_k = snap_strike(chain, sp_k - WIDTH_XSP, "put", -1)
                if None not in (sc_k, sp_k, lc_k, lp_k):
                    credit = (chain[(sc_k, "call")][0] - chain[(lc_k, "call")][1]
                              + chain[(sp_k, "put")][0] - chain[(lp_k, "put")][1])
                    open_trade = {"kind": "condor", "entry_t": hhmm,
                                  "sc": sc_k, "lc": lc_k, "sp": sp_k, "lp": lp_k,
                                  "credit": round(credit, 2)}
                    print(f"  {hhmm} PAPER FILL condor {sp_k}/{sc_k} wings "
                          f"{lp_k}/{lc_k} credit {credit:.2f}")
        if once:
            break
        time.sleep(max(0, 60 - dt.datetime.now().second))   # tick once per minute

    # ---- settle at the close ----
    if open_trade:
        settle = sc.index_quote() / 10.0
        t = open_trade
        if t["kind"] == "breakout":
            w = abs(t["short"] - t["long"])
            iv = (min(max(settle - t["long"], 0.0), w) if t["typ"] == "call"
                  else min(max(t["long"] - settle, 0.0), w))
            t["pnl_per_share"] = round(iv - t["debit"], 2)
        else:
            owed = (min(max(settle - t["sc"], 0.0), t["lc"] - t["sc"])
                    + min(max(t["sp"] - settle, 0.0), t["sp"] - t["lp"]))
            t["pnl_per_share"] = round(t["credit"] - owed, 2)
        t["date"], t["bot"], t["settle"] = today, bot, round(settle, 2)
        path = os.path.join(LEDGER, "paper_ledger.csv")
        exists = os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(t.keys()))
            if not exists:
                w.writeheader()
            w.writerows([t])
        print(f"SETTLED: {t}")
    else:
        print("no trade today")


if __name__ == "__main__":
    # ---- pure-core self-tests (no network) ----
    bars = [("09:30", 5000.0), ("09:38", 5010.0), ("09:44", 4998.0), ("09:45", 5002.0),
            ("09:50", 5020.0), ("09:52", 5021.0), ("09:58", 5023.0)]
    prior = (4990.0, 4950.0, 4980.0)
    kind, s = decide(bars, prior, "earner", False, "09:58", False)
    assert kind == "breakout" and s.name == "a_held" and s.direction == "long", (kind, s)
    assert decide(bars, prior, "earner", True, "09:58", False) == (None, "banned")
    assert decide(bars, prior, "earner", False, "09:58", True) == (None, "position_taken")
    # tank demands through-pivot: prior band far below -> reject
    kind2, _ = decide(bars, prior, "tank", False, "09:58", False)
    assert kind2 is None, kind2
    # quiet morning -> condor at 12:01
    flat = [("09:30", 5000.0), ("09:45", 5001.0), ("10:30", 5002.0), ("12:00", 5001.0)]
    assert decide(flat, prior, "earner", False, "12:01", False)[0] == "condor"
    assert decide(flat, prior, "earner", False, "12:02", False)[0] is None
    # strike snapping on a realistic XSP grid
    grid = {(k / 2, "call"): (1.0, 1.1) for k in range(990, 1030)}     # 495.0..514.5 by .5
    assert snap_strike(grid, 500.2, "call", 0) == 500.0
    assert snap_strike(grid, 500.2, "call", +1) == 500.5
    print("self-test OK: decide() routing + strike snapping")

    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", default="tank", choices=("earner", "tank"))
    ap.add_argument("--risk", type=float, default=0.03)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--live", action="store_true", help="actually start the day loop")
    a = ap.parse_args()
    if a.live or a.once:
        run_day(a.bot, a.risk, a.once)
    else:
        print("(self-tests only; add --live to run the day loop on a market day)")
