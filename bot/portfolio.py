# portfolio.py — the LIVE-FAITHFUL position manager. The signal engine emits many setups per
# day (often OPPOSING: an early failed_a short AND a later a_held long from the same move). A
# backtest that scores every setup independently and sums them is NOT tradeable — live you hold
# ONE position at a time, in time order, and an earlier trade must close before another opens.
# This walks a day's intraday path bar-by-bar, one position at a time, exiting on the setup's
# stop or at the session close (hold-to-horizon), and returns the REALIZED trades.
#
# Offline, pure. Run: .venv/bin/python bot/portfolio.py
from acd_rules import _to_min

POINT_VALUE = 1000.0        # CL: $1000 per 1.00 point (override per instrument)


def _bar_ohlc(bar):
    """(t, open, high, low, close) from a bar that is either (t, price) [o=h=l=c=price] or
    (t, open, high, low, close). Lets simulate_day check stops against the minute's true
    extreme and fill a gap-through at the bar's open (the realistic first print)."""
    if len(bar) == 2:
        t, p = bar
        return t, p, p, p, p
    t, op, hi, lo, cl = bar
    return t, op, hi, lo, cl


def simulate_day(bars, signals, point_value=POINT_VALUE, time_stop_minutes=None):
    """One position at a time, time-ordered.
      bars    : the day's intraday path; each element (("HH:MM"), price) OR (("HH:MM"), high, low, close).
                OHLC form lets stops fire on the intra-minute EXTREME (live-realistic), not just the close.
      signals : iterable of Setup-like objects with .entry_time .entry_price .direction .stop .name
      time_stop_minutes : Fisher's TIME stop ("more important than price stops"). At the first bar
                >= entry + this many minutes, if the trade is NOT in profit, exit there ("time"); a
                working (in-profit) trade is left to ride to its price stop / the close. None disables it.
    A signal is TAKEN only if we are flat at its entry_time (no overlapping/opposing double-count).
    Each taken position exits at the first bar AFTER entry whose extreme hits its stop (fill at the
    WORSE of the stop and the bar — gap-through can't fill better than the stop), else the time stop,
    else the session close. Enter at the signal's entry_price (a real level). Returns realized trades.
    """
    bars = sorted(bars)
    if not bars:
        return []
    close_t, _, _, _, close_p = _bar_ohlc(bars[-1])
    sigs = sorted(signals, key=lambda s: _to_min(s.entry_time))
    trades, free_from = [], -1                       # free_from = minute at/after which we can open
    close_m = _to_min(close_t)
    for s in sigs:
        et = _to_min(s.entry_time)
        if et < free_from or et > close_m:           # holding a prior position, or entry after the session -> skip
            continue
        exit_t, exit_p, reason = None, None, None
        time_checked = False                         # the time stop is a one-shot check at entry + T
        for bar in bars:
            t, op, hi, lo, cl = _bar_ohlc(bar)
            tm = _to_min(t)
            if tm <= et:                             # only bars strictly AFTER entry can exit it
                continue
            if s.stop is not None:
                if s.direction == "long" and lo <= s.stop:      # intra-bar low breaches the long stop
                    exit_t, exit_p, reason = t, min(s.stop, op), "stop"   # fill at stop, or the OPEN if it gapped through
                    break
                if s.direction == "short" and hi >= s.stop:     # intra-bar high breaches the short stop
                    exit_t, exit_p, reason = t, max(s.stop, op), "stop"
                    break
            if time_stop_minutes is not None and not time_checked and tm - et >= time_stop_minutes:
                time_checked = True                  # checked once; a working trade is then left to ride
                in_profit = (cl > s.entry_price) if s.direction == "long" else (cl < s.entry_price)
                if not in_profit:                    # not working by time T -> get out (Fisher's time stop)
                    exit_t, exit_p, reason = t, cl, "time"
                    break
        if exit_p is None:                           # no stop / time stop hit -> hold to session close
            exit_t, exit_p, reason = close_t, close_p, "close"
        sign = 1.0 if s.direction == "long" else -1.0
        ret = (exit_p / s.entry_price - 1.0) * sign if s.entry_price else 0.0
        trades.append({
            "name": s.name, "direction": s.direction,
            "entry_time": s.entry_time, "entry": s.entry_price,
            "exit_time": exit_t, "exit": exit_p, "reason": reason,
            "ret": ret, "usd": (exit_p - s.entry_price) * sign * point_value,
        })
        free_from = _to_min(exit_t)                  # blocked until this position's exit
    return trades


if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class Sig:
        name: str; direction: str; entry_time: str; entry_price: float; stop: float

    # Path: rises to 102, dips to 99, ends 101.
    bars = [("09:45", 100), ("10:00", 102), ("10:30", 99), ("11:00", 100), ("15:59", 101)]

    # 1) One position at a time: an early long AND an opposing short fire; only the FIRST (long) is
    #    taken; the 10:00 short is ignored because we're still holding the 09:45 long (held to close).
    sigs = [Sig("a_held", "long", "09:45", 100, 95),
            Sig("failed_a", "short", "10:00", 102, 103)]
    tr = simulate_day(bars, sigs)
    assert len(tr) == 1 and tr[0]["name"] == "a_held", tr
    assert tr[0]["reason"] == "close" and tr[0]["exit"] == 101, tr           # no stop hit -> close at 101
    assert abs(tr[0]["ret"] - (101/100 - 1)) < 1e-9, tr
    print("portfolio OK: opposing same-day signal ignored while in a position (no double-count)")

    # 2) Stop exit frees the book for a later, non-overlapping signal.
    sigs2 = [Sig("a_held", "long", "09:45", 100, 99.5),                       # stopped at 10:30 (price 99 <= 99.5)
             Sig("failed_a", "short", "11:00", 100, 102)]                     # taken after the stop -> holds to close 101 (stop 102 not hit)
    tr2 = simulate_day(bars, sigs2)
    assert len(tr2) == 2, tr2
    # long stopped at 10:30: stop 99.5 but the bar printed 99 (gap-through) -> fill at the WORSE price 99
    assert tr2[0]["reason"] == "stop" and tr2[0]["exit"] == 99, tr2
    assert tr2[0]["ret"] < 0, tr2
    assert tr2[1]["name"] == "failed_a" and tr2[1]["reason"] == "close", tr2  # later short taken, held to close
    assert tr2[1]["exit"] == 101 and tr2[1]["ret"] < 0, tr2                   # short into a higher close -> loss
    print("portfolio OK: stop exit frees the book; a later non-overlapping signal is then taken")

    # 3) A signal whose entry_time falls INSIDE an open position is skipped even if it would've won.
    sigs3 = [Sig("a_held", "long", "09:45", 100, 90),                         # held all day to close 101 (+)
             Sig("c", "long", "10:30", 99, 90)]                              # would profit, but we're in the 09:45 long
    tr3 = simulate_day(bars, sigs3)
    assert len(tr3) == 1 and tr3[0]["entry_time"] == "09:45", tr3
    print("portfolio OK: mid-position signal skipped (one position at a time)")

    # 4) Time stop: a long NOT in profit by entry+45min exits there ("time"); one that IS working
    #    at the checkpoint is left to ride to the close.
    ts_not = simulate_day(bars, [Sig("a_held", "long", "09:45", 100, 90)], time_stop_minutes=45)
    assert ts_not[0]["reason"] == "time" and ts_not[0]["exit"] == 99, ts_not   # first bar >=10:30: 99<100 -> out
    ts_win = simulate_day(bars, [Sig("a_held", "long", "09:45", 100, 90)], time_stop_minutes=15)
    assert ts_win[0]["reason"] == "close" and ts_win[0]["exit"] == 101, ts_win  # 10:00 in profit (102) -> rides
    print("portfolio OK: time stop exits a not-working trade, leaves a working one to ride")

    # 5) Empty bars / no signals are safe.
    assert simulate_day([], sigs) == [] and simulate_day(bars, []) == []
    print("portfolio OK: empty inputs")
    print("All portfolio self-tests passed.")
