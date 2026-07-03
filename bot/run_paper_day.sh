#!/bin/zsh
# run_paper_day.sh — cron entrypoint: launch BOTH paper books (earner + tank) for the
# day. Each runs the audited engine on live data and exits on its own after the close.
# caffeinate keeps the Mac awake through the session. Logs to results/spx/paper/.
ROOT="/Users/georgiemanavazian/Documents/Options trading"
cd "$ROOT" || exit 1
set -a; source .env; set +a
mkdir -p results/spx/paper

# token freshness gate: Schwab refresh tokens die after 7 days; warn loudly at 6.
if [ -f .schwab_token.json ]; then
  AGE_DAYS=$(( ( $(date +%s) - $(stat -f %m .schwab_token.json) ) / 86400 ))
  if [ "$AGE_DAYS" -ge 6 ]; then
    osascript -e 'display notification "Schwab token expires within a day — redo the 2-step login" with title "ACD paper bot"' 2>/dev/null
  fi
  if [ "$AGE_DAYS" -ge 7 ]; then
    echo "$(date) SKIP: token expired (${AGE_DAYS}d old)" >> results/spx/paper/launch.log
    exit 0
  fi
else
  echo "$(date) SKIP: no token" >> results/spx/paper/launch.log
  exit 0
fi

echo "$(date) launching earner+tank paper engines" >> results/spx/paper/launch.log
/usr/bin/caffeinate -is .venv/bin/python bot/live_paper_engine.py --bot tank --live \
  >> results/spx/paper/engine_tank.log 2>&1 &
/usr/bin/caffeinate -is .venv/bin/python bot/live_paper_engine.py --bot earner --live \
  >> results/spx/paper/engine_earner.log 2>&1 &
wait
echo "$(date) engines exited" >> results/spx/paper/launch.log
