#!/bin/bash
# Election-night feed: reads the Elections Committee's official results files
# (expc.csv by locality, expb.csv by ballot box) from the unaltered copy that
# israel.weinbren.me republishes, because the Committee blocks GitHub's servers.
# Downloads only when the copy's version changes, converts with fetch_results.py,
# commits the data and redeploys the site. Runs for up to RUN_MINUTES.
set -u
BASE="${MIRROR_BASE:-https://israel.weinbren.me/live}"
UA='Mozilla/5.0 (compatible; GlobeInBriefElectionWatcher/1.0; +https://johnnoto.github.io/israel-election-watcher/)'
INTERVAL="${INTERVAL:-120}"
END=$(( $(date +%s) + ${RUN_MINUTES:-345} * 60 ))
RAW=/tmp/raw; mkdir -p "$RAW"
last=""
say() { echo "$(date -u +%H:%M:%S) $*"; }

while [ "$(date +%s)" -lt "$END" ]; do
  if curl -sSf -m 30 -A "$UA" -o /tmp/status.json "$BASE/status.json?_=$(date +%s)"; then
    read -r vc vb updated < <(python3 -c "
import json; s = json.load(open('/tmp/status.json')); f = s.get('files', {})
print(f.get('expc.csv', '-'), f.get('expb.csv', '-'), s.get('updated', '-'))")
    key="$vc/$vb"
    if [ "$vc" != "-" ] && [ "$vb" != "-" ] && [ "$key" != "$last" ]; then
      rm -f "$RAW"/*
      if curl -sSf -m 120 -A "$UA" -o "$RAW/expc.csv" "$BASE/expc.csv?v=$vc" \
         && curl -sSf -m 180 -A "$UA" -o "$RAW/expb.csv" "$BASE/expb.csv?v=$vb" \
         && grep -q 'סמל ישוב' "$RAW/expc.csv" && grep -q 'סמל ישוב' "$RAW/expb.csv"; then
        python3 -c "
from datetime import datetime; from zoneinfo import ZoneInfo
u = '$updated'
print(datetime.fromisoformat(u).astimezone(ZoneInfo('Asia/Jerusalem')).strftime('%d/%m/%Y %H:%M') if u != '-' else '')" > "$RAW/cec_time.txt"
        git fetch -q origin main && git reset -q --hard origin/main
        out=$(python3 scripts/fetch_results.py --local "$RAW" --guard 2>&1); say "$out"
        if echo "$out" | grep -q '^CHANGED'; then
          git add data/live.json data/boxes.json
          if git commit -qm "Results via mirror, Committee data as of $(cat "$RAW/cec_time.txt")"; then
            if git push -q origin HEAD:main; then
              last="$key"
              curl -sS -o /dev/null -w "deploy dispatch %{http_code}\n" -X POST \
                -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" \
                "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/workflows/deploy.yml/dispatches" \
                -d '{"ref":"main"}'
            else
              say "push failed; will retry"
            fi
          fi
        else
          last="$key"
        fi
      else
        say "download failed; will retry"
      fi
    else
      say "no new files (expc $vc, updated $updated)"
    fi
  else
    say "status not reachable; will retry"
  fi
  sleep "$INTERVAL"
done
say "run window over; the next scheduled run takes over"
