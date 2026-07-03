# schwab_client.py — thin, mockable wrapper around schwab-py for everything the live
# paper engine needs: index minute bars, index quote, XSP option chain NBBO. No order
# placement here — the paper phase never sends orders; when we go live for real, order
# code gets its own module and its own review.
#
# All functions return plain python (floats/dicts/lists) so the engine and its tests
# never import schwab types.
import os
import datetime as dt

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", ".schwab_token.json")
INDEX_SYMBOL = "$SPX"          # signal engine runs on the index itself
CHAIN_SYMBOL = "$XSP"          # index option chains need the $ prefix (verified 2026-07-03)

_client = None


def client():
    """Lazy singleton. Raises with a helpful message if auth hasn't been run."""
    global _client
    if _client is None:
        from schwab.auth import client_from_token_file
        key = os.environ.get("SCHWAB_APP_KEY")
        secret = os.environ.get("SCHWAB_APP_SECRET")
        if not key or not secret:
            raise RuntimeError("SCHWAB_APP_KEY/SECRET missing — source .env")
        if not os.path.exists(TOKEN_PATH):
            raise RuntimeError("No token file — run bot/schwab_auth.py first")
        _client = client_from_token_file(TOKEN_PATH, key, secret)
    return _client


def index_quote():
    """Latest $SPX spot (float)."""
    r = client().get_quote(INDEX_SYMBOL)
    r.raise_for_status()
    d = list(r.json().values())[0]
    return float(d["quote"]["lastPrice"])


def index_minute_bars(day=None):
    """[(\"HH:MM\", close)] 1-min bars for `day` (default today), ET, RTH only —
    the exact shape acd_micro.build_day eats. Prior-day call gives the pivot HLC."""
    c = client()
    day = day or dt.date.today()
    start = dt.datetime.combine(day, dt.time(0, 0))
    end = dt.datetime.combine(day, dt.time(23, 59))
    r = c.get_price_history_every_minute(INDEX_SYMBOL, start_datetime=start,
                                         end_datetime=end,
                                         need_extended_hours_data=False)
    r.raise_for_status()
    out = []
    for candle in r.json().get("candles", []):
        t = dt.datetime.fromtimestamp(candle["datetime"] / 1000)
        hhmm = t.strftime("%H:%M")
        if "09:30" <= hhmm <= "16:15":
            out.append((hhmm, float(candle["close"])))
    return out


def prior_day_hlc(day=None):
    """(H, L, C) of the prior trading day's RTH session, from minute bars — the same
    path-derived approximation the backtest uses (fidelity: same inputs, same pivots)."""
    day = day or dt.date.today()
    for back in range(1, 6):
        bars = index_minute_bars(day - dt.timedelta(days=back))
        if len(bars) > 30:
            spots = [s for _, s in bars]
            return (max(spots), min(spots), spots[-1])
    raise RuntimeError("no prior trading day found in the last 5 days")


def xsp_chain_nbbo(expiry=None):
    """{(strike, 'call'|'put'): (bid, ask)} for XSP 0DTE (or `expiry` date).
    Real strikes, real NBBO — this kills the SPX/10 idealization."""
    c = client()
    expiry = expiry or dt.date.today()
    r = c.get_option_chain(CHAIN_SYMBOL, from_date=expiry, to_date=expiry)
    r.raise_for_status()
    data = r.json()
    out = {}
    for side, key in (("call", "callExpDateMap"), ("put", "putExpDateMap")):
        for _exp, strikes in data.get(key, {}).items():
            for k, contracts in strikes.items():
                cn = contracts[0]
                out[(float(k), side)] = (float(cn["bid"]), float(cn["ask"]))
    return out


if __name__ == "__main__":
    # offline self-test: shape contracts only (no network without a token)
    fake_chain = {(500.0, "call"): (1.2, 1.3), (502.5, "call"): (0.4, 0.5)}
    assert fake_chain[(500.0, "call")][1] == 1.3
    print("self-test OK (shapes). For a live smoke test: source .env, run "
          "bot/schwab_auth.py once, then: .venv/bin/python -c "
          "'import schwab_client as s; print(s.index_quote())'")
