# Connecting the bot to Schwab / ThinkorSwim — setup guide

The paper engine reads live market data through the **Schwab Trader API** (the official API behind ThinkorSwim's data). Paper phase sends **no orders** — it records what the bot *would* do, with real XSP strikes and real bid/ask, into an auditable ledger.

## One-time setup (your part, ~15 min + a waiting period)

1. **Create a developer account** at https://developer.schwab.com (separate from your brokerage login; then link your brokerage account when prompted).
2. **Create an app**: Dashboard → Apps → Create App.
   - API product: **Trader API — Individual**
   - Callback URL: `https://127.0.0.1` (what our app registered; the auth script's
     CALLBACK_URL constant must match it EXACTLY)
   - App name/description: anything (e.g. "ACD paper bot").
3. **Wait for approval.** Status must say **"Ready For Use"** — typically 1-3 business days. "Approved - Pending" will NOT work.
4. **Copy credentials into `.env`** (repo root, already gitignored):
   ```
   SCHWAB_APP_KEY=your-app-key
   SCHWAB_APP_SECRET=your-secret
   ```
5. **Authorize** (interactive — browser opens, log in with your *brokerage* credentials):
   ```
   ! set -a && source .env && set +a && .venv/bin/python bot/schwab_auth.py
   ```
   The script prints a Schwab login link / opens the browser. Log in, approve the app —
   the browser then lands on `https://127.0.0.1` and shows a **"can't connect" error
   page. That is expected and correct.** Copy the FULL URL from the address bar (it
   carries the `?code=...`) and paste it into the terminal prompt. Success prints a
   live $SPX quote. **Refresh tokens expire every 7 days** — rerun this weekly
   (schwab-py silently refreshes the 30-minute access tokens in between).

## What's already built (my part, done)

| File | Job |
|---|---|
| `bot/schwab_auth.py` | one-time OAuth; writes `.schwab_token.json` (gitignored) |
| `bot/schwab_client.py` | data wrapper: $SPX minute bars, quotes, XSP chain NBBO |
| `bot/live_paper_engine.py` | the paper loop — same audited brain as the backtest |

## How the paper engine keeps backtest fidelity (the thing we care about)

- Signals come from `acd_micro.build_day` — the **identical audited engine** the backtest uses, run on bars-so-far each minute. No reimplementation, no drift.
- Routing = the campaign configs verbatim: Earner (coil + CPI ban) or Tank (coil + through-pivot), FOMC ban, quiet-day condor at 12:01.
- Fills recorded at the **next minute's real NBBO** — the backtest's fill convention — but on **real XSP strikes** (this finally kills the SPX÷10 idealization).
- Every minute's decision is logged to `results/spx/paper/decisions_<date>_<bot>.jsonl`; settled trades append to `results/spx/paper/paper_ledger.csv`.
- The decision core is a pure function, so each evening it can be replayed from the recorded bars and diffed against what the live loop actually did — any mismatch is a fidelity bug, found the cheap way.

## Running it (market days, after auth)

```
set -a && source .env && set +a
.venv/bin/python bot/live_paper_engine.py --bot tank --live      # full day loop
.venv/bin/python bot/live_paper_engine.py --bot earner --once    # single scan (testing)
```

## Not built yet, on purpose

- **Order placement** — nothing here can move money. When paper results earn it, real-order code gets its own module, its own review, and its own kill switches.
- ToS's paperMoney simulator is NOT connected — the Trader API only talks to real accounts, so our paper layer is our own (and better: it logs *why* for every minute).
