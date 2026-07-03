# paper_report.py — the EVENING REPORT: one file you read with your coffee.
# Summarizes today's paper decisions + trades for both books (earner/tank), running
# equity and win rate since inception, token-expiry countdown, and pops a macOS
# notification with the headline. Cron runs it at 16:30 on market days; safe to run
# any time (graceful when there's no data yet).
# Run: .venv/bin/python bot/paper_report.py
import csv
import datetime as dt
import json
import os
import subprocess

ROOT = os.path.join(os.path.dirname(__file__), "..")
PAPER = os.path.join(ROOT, "results", "spx", "paper")
LEDGER = os.path.join(PAPER, "paper_ledger.csv")
START_EQUITY = 10_000.0
RISK_PCT = 0.03


def load_ledger():
    if not os.path.exists(LEDGER):
        return []
    return list(csv.DictReader(open(LEDGER)))


def book_stats(rows, bot):
    """Running equity for one book: each trade risks RISK_PCT of current equity on its
    per-share max loss; pnl_per_share scales by the implied contracts (XSP $100/pt)."""
    eq, trades = START_EQUITY, []
    for r in rows:
        if r.get("bot") != bot:
            continue
        pps = float(r.get("pnl_per_share") or 0)
        if r.get("kind") == "breakout":
            per_contract = float(r.get("debit") or 0) * 100.0
        else:
            width = abs(float(r.get("lc") or 0) - float(r.get("sc") or 0)) or 2.5
            per_contract = (width - float(r.get("credit") or 0)) * 100.0
        n = int(RISK_PCT * eq / per_contract) if per_contract > 0 else 0
        pnl = n * pps * 100.0
        eq += pnl
        trades.append({**r, "contracts": n, "pnl": round(pnl, 2)})
    wins = sum(1 for t in trades if t["pnl"] > 0)
    return {"trades": trades, "equity": round(eq, 2),
            "win": wins / len(trades) if trades else 0.0}


def today_decisions(bot, day):
    p = os.path.join(PAPER, f"decisions_{day}_{bot}.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def token_days_left():
    p = os.path.join(ROOT, ".schwab_token.json")
    if not os.path.exists(p):
        return -1
    age = (dt.datetime.now().timestamp() - os.path.getmtime(p)) / 86400
    return round(7 - age, 1)


def notify(msg):
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "ACD paper bot"'],
                       capture_output=True, timeout=10)
    except Exception:
        pass


def main():
    day = dt.date.today().isoformat()
    rows = load_ledger()
    lines = [f"# Paper report — {day}", ""]
    headline = []
    for bot in ("earner", "tank"):
        st = book_stats(rows, bot)
        todays = [t for t in st["trades"] if t.get("date") == day]
        dec = today_decisions(bot, day)
        n_scans = len(dec)
        lines.append(f"## {bot.upper()}  —  equity ${st['equity']:,}  "
                     f"({len(st['trades'])} trades, win {st['win']:.0%})")
        if todays:
            for t in todays:
                desc = (f"{t.get('setup', t.get('kind'))} {t.get('dir', '')} "
                        f"@{t.get('entry_t')} x{t['contracts']} -> ${t['pnl']:+,}")
                lines.append(f"- TODAY: {desc}")
                headline.append(f"{bot}: ${t['pnl']:+,}")
        else:
            why = dec[-1]["why"] if dec else "engine did not run"
            lines.append(f"- today: no trade ({n_scans} scans; last state: {why})")
            headline.append(f"{bot}: no trade")
        lines.append("")
    tdl = token_days_left()
    lines.append(f"---\nSchwab token: {'MISSING — run auth' if tdl < 0 else f'{tdl} days left'}"
                 f"{'  ⚠️ RE-AUTH NOW' if 0 <= tdl <= 1 else ''}")
    out = os.path.join(PAPER, f"report_{day}.md")
    os.makedirs(PAPER, exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    notify(" | ".join(headline) + (f" | token {tdl}d" if tdl <= 2 else ""))
    return out


if __name__ == "__main__":
    main()
