# schwab_auth.py — Schwab OAuth in TWO non-interactive steps (the chat/CI-friendly way;
# an input() prompt dies with EOF when run via the chat's `!` runner).
#
#   Step 1:  .venv/bin/python bot/schwab_auth.py
#            -> prints the login link. Open it, log in (brokerage credentials), Allow.
#            The browser dead-ends on https://127.0.0.1/?code=... ("can't connect" is
#            EXPECTED). Copy the ENTIRE address-bar URL.
#   Step 2:  .venv/bin/python bot/schwab_auth.py 'PASTED_URL'
#            -> exchanges the code, writes the token, prints a live $SPX quote.
#
# The OAuth `state` from step 1 is persisted to .schwab_auth_state.json so step 2
# validates against the same context. Refresh tokens expire every 7 DAYS — redo both
# steps weekly. Always: set -a && source .env && set +a  first (keys live in .env).
import json
import os
import sys

CALLBACK_URL = "https://127.0.0.1"      # matches the registered app EXACTLY (no port)
ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN_PATH = os.path.join(ROOT, ".schwab_token.json")
STATE_PATH = os.path.join(ROOT, ".schwab_auth_state.json")


def _keys():
    key = os.environ.get("SCHWAB_APP_KEY")
    secret = os.environ.get("SCHWAB_APP_SECRET")
    if not key or not secret:
        raise SystemExit("Set SCHWAB_APP_KEY / SCHWAB_APP_SECRET in .env first "
                         "(see docs/schwab-setup.md)")
    return key, secret


def step1():
    from schwab.auth import get_auth_context
    key, _ = _keys()
    ctx = get_auth_context(key, CALLBACK_URL)
    with open(STATE_PATH, "w") as f:
        json.dump({"state": ctx.state}, f)
    print("1. Open this link in your browser and log in (BROKERAGE credentials):\n")
    print(f"   {ctx.authorization_url}\n")
    print('2. Click "Allow", pick your account.')
    print('3. The browser lands on https://127.0.0.1/?code=... showing "can\'t')
    print('   connect" — EXPECTED. Copy the ENTIRE address-bar URL.')
    print("4. Then run (quotes matter):\n")
    print("   ! set -a && source .env && set +a && "
          ".venv/bin/python bot/schwab_auth.py 'PASTED_URL'")


def step2(received_url):
    from schwab.auth import get_auth_context, client_from_received_url
    key, secret = _keys()
    if not os.path.exists(STATE_PATH):
        raise SystemExit("Run step 1 first (no saved auth state).")
    state = json.load(open(STATE_PATH))["state"]
    ctx = get_auth_context(key, CALLBACK_URL, state=state)

    def write_token(token, *_a, **_k):
        with open(TOKEN_PATH, "w") as f:
            json.dump(token, f)

    c = client_from_received_url(key, secret, ctx, received_url, write_token)
    os.remove(STATE_PATH)
    r = c.get_quote("$SPX")
    r.raise_for_status()
    q = list(r.json().values())[0].get("quote", {})
    print(f"AUTH OK — token written to {os.path.abspath(TOKEN_PATH)}")
    print(f"sanity quote: $SPX last={q.get('lastPrice')} (close={q.get('closePrice')})")
    print("Refresh token expires in 7 days — redo both steps weekly.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        step2(sys.argv[1])
    else:
        step1()
