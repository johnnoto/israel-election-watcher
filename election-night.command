#!/bin/bash
# Israel Election Watcher: election-night relay.
#
# The Elections Committee's site blocks cloud servers, so this runs on your Mac.
# It downloads the Committee's results files every 90 seconds and uploads them
# to GitHub, which converts them and republishes the page.
#
# Double-click to start. Leave the window open and the Mac plugged in and online.
# Press Control-C (or close the window) to stop.
#
#   ./election-night.command --once     check once and stop (for a test run)

REPO="johnnoto/israel-election-watcher"
SITE="${SITE:-https://votes26.bechirot.gov.il/}"
MEDIA="${MEDIA:-https://media26.bechirot.gov.il/files/}"
API="${API:-https://api.github.com}"
INTERVAL="${INTERVAL:-90}"
TOKEN_FILE="$HOME/.election-watcher-token"
WORK="$HOME/.election-watcher"
ONCE=0; [ "$1" = "--once" ] && ONCE=1

mkdir -p "$WORK/raw"
cd "$WORK" || exit 1

say() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*"; }

ask_token() {
  while :; do
    echo
    echo "Paste your GitHub token (it starts with github_pat_) and press Return."
    echo "Nothing appears while you paste. That is normal."
    read -rs TOKEN; echo
    TOKEN=$(printf '%s' "$TOKEN" | tr -d ' \t\r\n')
    if [ -z "$TOKEN" ]; then echo "Nothing was pasted. Copy the token on the GitHub page again, then try once more."; continue; fi
    case "$TOKEN" in
      github_pat_*|ghp_*) ;;
      *) echo "That doesn't look like a GitHub token (it should start with github_pat_). It began with: ${TOKEN:0:6}…"; continue ;;
    esac
    printf '%s' "$TOKEN" > "$TOKEN_FILE"; chmod 600 "$TOKEN_FILE"
    return
  done
}
[ -s "$TOKEN_FILE" ] || ask_token
TOKEN=$(cat "$TOKEN_FILE")
gh() { curl -sS -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "$@"; }

while :; do
  code=$(gh -o "$WORK/repo.json" -w '%{http_code}' "$API/repos/$REPO")
  if [ "$code" = "200" ]; then break; fi
  if [ "$code" = "401" ]; then
    say "GitHub did not accept that token. It may have been copied incompletely, or it has expired."
  elif [ "$code" = "404" ] || [ "$code" = "403" ]; then
    say "The token works but cannot see $REPO. On the token page, give it access to israel-election-watcher with Contents: Read and write."
  else
    say "Could not reach GitHub (HTTP $code). Check the internet connection."
  fi
  rm -f "$TOKEN_FILE"
  ask_token
  TOKEN=$(cat "$TOKEN_FILE")
done
say "Connected to GitHub as the owner of $REPO."

# Keep the Mac awake while this window is open.
caffeinate -dimsu -w $$ 2>/dev/null &

last=""
while :; do
  ok=1
  curl -sSf -m 60 --retry 3 -A "Mozilla/5.0" -o raw/page.html "$SITE" || ok=0
  curl -sSf -m 90 --retry 3 -A "Mozilla/5.0" -o raw/expc.csv "${MEDIA}expc.csv?t=$(date +%s)" || ok=0
  curl -sSf -m 120 --retry 3 -A "Mozilla/5.0" -o raw/expb.csv "${MEDIA}expb.csv?t=$(date +%s)" || ok=0
  if [ $ok = 1 ] && grep -q 'סמל ישוב' raw/expc.csv && grep -q 'סמל ישוב' raw/expb.csv; then
    sum=$(cat raw/expc.csv raw/expb.csv | shasum | cut -c1-16)
    if [ "$sum" != "$last" ]; then
      tar -czf results.tgz -C raw expc.csv expb.csv page.html
      sha=$(gh "$API/repos/$REPO/contents/raw/results.tgz?ref=main" | grep -o '"sha": *"[0-9a-f]\{40\}"' | head -1 | grep -o '[0-9a-f]\{40\}')
      { printf '{"message":"Results files %s","branch":"main","content":"' "$(date -u +%H:%M:%S)"
        base64 < results.tgz | tr -d '\n'
        if [ -n "$sha" ]; then printf '","sha":"%s"}' "$sha"; else printf '"}'; fi; } > body.json
      code=$(gh -X PUT --data-binary @body.json -o put.json -w '%{http_code}' "$API/repos/$REPO/contents/raw/results.tgz")
      if [ "$code" = "200" ] || [ "$code" = "201" ]; then
        last="$sum"
        boxes=$(($(wc -l < raw/expb.csv) - 1))
        say "Uploaded new results ($boxes ballot-box rows). The page updates in about a minute."
      else
        say "Upload failed (HTTP $code). Will try again."
      fi
    else
      say "No change since the last upload."
    fi
  else
    say "Could not download the Committee's files this time. Will try again."
  fi
  [ $ONCE = 1 ] && break
  sleep "$INTERVAL"
done
say "Done."
