# usgang-basel

Crawler and (later) hosting for the Ausgang Basel events page.

## Crawl4AI test
- `crawler/sites.py`: sites to test
- `crawler/test_crawl4ai.py`: checks robots.txt (incl. AI crawler rules), loads each page with Crawl4AI, saves HTML/markdown, extracts schema.org events, optionally lets an AI model extract events (needs repository secret `ANTHROPIC_API_KEY`)
- Runs on GitHub Actions (`.github/workflows/crawl4ai-test.yml`) on every push to `crawler/` or manually via Actions → crawl4ai-test → Run workflow
- Results land on the branch `test-results` in `results/` (`summary.md` first)
