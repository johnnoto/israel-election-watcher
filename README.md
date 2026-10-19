# Israel Election Watcher

Live results, maps and coalition math for Israel's 26th Knesset election (October 27, 2026), built for [The Globe in Brief](https://substack.com/@theglobeinbrief).

## How It Works

- `index.html` is the page. It reads `config.json` and the files in `data/`, and checks `data/live.json` every 60 seconds for new results.
- The Elections Committee's site blocks cloud servers, including GitHub's. So on election night, **`election-night.command` runs on John's Mac**: every 90 seconds it downloads the Committee's results files (`expc.csv` by locality, `expb.csv` by ballot box) and uploads them to `raw/results.tgz` here.
- Each upload starts `.github/workflows/convert.yml` ("Publish results"), which converts the files, saves `data/live.json` and `data/boxes.json`, and republishes the site. The page updates about a minute after each upload.
- `.github/workflows/deploy.yml` republishes the site whenever anything else changes, such as `config.json`.
- Before polls close, the page shows the latest poll in `config.json`. Anything the Committee publishes before 22:00 Israel time, or while its site says "test environment", is treated as test data and never shown.

## Election Night Checklist

1. Around **3:45 PM ET (21:45 Israel time) on Tuesday, Oct 27**, plug in the Mac and double-click `election-night.command`. Leave the window open.
2. The first time, it asks for your GitHub token and saves it on the Mac.
3. Each line in the window says what happened. "Uploaded new results" means the page will update within a minute.
4. Keep it running until counting ends (usually by morning in Israel). The double-envelope votes come in a day or two later, so run it again on Oct 28 and 29 for an hour or so.

## Things You Can Edit On GitHub (Pencil Icon → Commit)

All of these are in `config.json`. The page picks up changes within about five minutes.

- **Add an exit poll** on election night: copy the poll block under `"polls"`, give it a new `id` and `label` (for example `"Channel 12 Exit Poll"`), and fill in `seats` using the ballot letters.
- **Recommendations after the President's consultations**: update `"camps"` and set `"recommendations_status": "actual"`.
- **Red lines**: edit `"pledges"`. Each one names the party (`a`), the party it rejects (`x`), and the wording shown on the page.
- **If the Committee leaves its "test environment" label up after polls close** and real results are hidden: set `"force_live": true`.

## Handy Buttons (Actions Tab)

- **Publish results**: reconverts the last uploaded files and republishes.
- **Deploy site**: republishes the page.
- **Check results source**: tests whether GitHub's servers can reach the Committee directly (they currently cannot). Writes a report to the `diagnostics` branch.

## Sources

Results: Central Elections Committee, votes26.bechirot.gov.il. Locality positions: Central Bureau of Statistics. Terrain: Mapzen/AWS Terrain Tiles. Oslo areas: OCHA via the Humanitarian Data Exchange. Borders: Natural Earth.
