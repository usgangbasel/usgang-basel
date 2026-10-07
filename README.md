# usgang-basel

Ausgang Basel: events from Basel venues, with votes and "Ich gehe hin".

## Site (`site/`)
- Static page served by GitHub Pages: `https://usgangbasel.github.io/usgang-basel/`
- `site/data/events.json`, `site/data/venues.json`: event and venue data (written by the crawler)
- `site/backend.js`: Firebase (Firestore + anonymous sign-in) for votes, community events, venue requests and admin edits of venue info
- `firestore.rules`: the access rules to paste into Firestore → Rules
- Deployed by `.github/workflows/pages.yml` on every push to `site/`

## Nightly crawl (`crawler/run.py`, `.github/workflows/crawl.yml`)
- Runs every night at 03:17 (summer) / 02:17 (winter) and can be started by hand: Actions → nightly-crawl → Run workflow
- `crawler/sources.py`: what is read; every source has rules in `crawler/parsers.py` (no AI). Optional: with the repository secret `ANTHROPIC_API_KEY`, Claude reads pages whose rules find nothing (Sääli, venues added later)
- robots.txt is checked before every page (including AI crawler rules for AI-read pages)
- New events are merged into `site/data/events.json` without duplicates; details (end time, price, style) are filled in; events older than 2 days are removed
- Report: `crawler/last_run.json` and the run's summary page on GitHub; the site is redeployed automatically

## Crawler test (`crawler/`)
- `test_crawl4ai.py`: Crawl4AI test run (robots.txt check incl. AI crawlers, page load, schema.org events, rule-based parsers, optional AI extraction with secret `ANTHROPIC_API_KEY`)
- `parsers.py`: rule-based parsers for denkmal, Renée, Grenzwert, Nordstern
- Results on branch `test-results`
