# Israel Election Watcher

Live results, maps and coalition math for Israel's 26th Knesset election (October 27, 2026), built for [The Globe in Brief](https://substack.com/@theglobeinbrief).

## How It Works

- `index.html` is the page. It reads `config.json` and the files in `data/`, and checks `data/live.json` every 60 seconds for new results.
- `.github/workflows/live.yml` starts by itself on **Oct 27 at 21:40 Israel time**. It downloads the Central Elections Committee's results files (`expc.csv` by locality, `expb.csv` by ballot box) about every 90 seconds, converts them, commits them, and redeploys the site. It keeps going, one run after another, until `stop_checking_utc` in `config.json` (Nov 5).
- `.github/workflows/deploy.yml` publishes the site to GitHub Pages.
- Before polls close, the page shows the latest poll in `config.json`. Anything the Committee publishes before 22:00 is treated as test data and never shown.

## Things You Can Edit On GitHub (Pencil Icon → Commit)

All of these are in `config.json`. The page picks up changes within about five minutes.

- **Add an exit poll** on election night: copy the poll block under `"polls"`, give it a new `id` and `label` (for example `"Channel 12 Exit Poll"`), and fill in `seats` using the ballot letters.
- **Recommendations after the President's consultations**: update `"camps"` and set `"recommendations_status": "actual"`.
- **Red lines**: edit `"pledges"`. Each one names the party (`a`), the party it rejects (`x`), and the wording shown on the page.
- **If the Committee leaves its "test environment" label up after polls close** and real results are hidden: set `"force_live": true`.

## Handy Buttons (Actions Tab)

- **Check results source**: confirms GitHub can reach the Committee's site. Safe to run any time.
- **Live results → Run workflow**: starts checking right away. Use it if the automatic start is late.
- **Deploy site**: republishes the page.

## Sources

Results: Central Elections Committee, votes26.bechirot.gov.il. Locality positions: Central Bureau of Statistics. Terrain: Mapzen/AWS Terrain Tiles. Oslo areas: OCHA via the Humanitarian Data Exchange. Borders: Natural Earth.
