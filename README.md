# usgang-basel

Ausgang Basel: events from Basel venues, with votes and "Ich gehe hin".

## Site (`site/`)
- Static page served by GitHub Pages: `https://usgangbasel.github.io/usgang-basel/`
- `site/data/events.json`, `site/data/venues.json`: event and venue data (written by the crawler)
- `site/backend.js`: Firebase (Firestore + anonymous sign-in) for votes, community events, venue requests and admin edits of venue info
- `firestore.rules`: the access rules to paste into Firestore → Rules
- Deployed by `.github/workflows/pages.yml` on every push to `site/`

## Crawler (`crawler/`)
- `test_crawl4ai.py`: Crawl4AI test run (robots.txt check incl. AI crawlers, page load, schema.org events, rule-based parsers, optional AI extraction with secret `ANTHROPIC_API_KEY`)
- `parsers.py`: rule-based parsers for denkmal, Renée, Grenzwert, Nordstern
- Results on branch `test-results`
