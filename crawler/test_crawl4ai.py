"""Crawl4AI test run for Ausgang Basel.

For each site in sites.py:
  1. robots.txt check (our own bot name AND the AI crawler names, since the content may be read by an AI model).
  2. Load the page with Crawl4AI (real headless browser), save HTML + clean markdown.
  3. Extract schema.org Event data (JSON-LD) if the site publishes it -> no rules or AI needed.
  4. Optional: AI extraction of events with an Anthropic model, if ANTHROPIC_API_KEY is set.
Writes everything to results/ plus results/summary.md.
"""
import asyncio, json, os, re, sys, time, urllib.robotparser, urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from sites import SITES

OUT = Path("results"); OUT.mkdir(exist_ok=True)
BOT = "UsgangBaselBot/0.1 (+https://github.com/usgangbasel/usgang-basel)"
BOT_TOKEN = "UsgangBaselBot"
AI_AGENTS = ["ClaudeBot", "Claude-Web", "anthropic-ai"]
MODEL = os.getenv("LLM_MODEL", "anthropic/claude-haiku-4-5-20251001")


def robots_allows(url: str):
    """Return (allowed, reason). Blocks if robots.txt disallows us, '*' or an AI crawler."""
    m = re.match(r"(https?://[^/]+)", url)
    rp = urllib.robotparser.RobotFileParser()
    robots_url = m.group(1) + "/robots.txt"
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": BOT})
        with urllib.request.urlopen(req, timeout=20) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return True, "no robots.txt"
        return False, f"robots.txt error {e.code}"
    except Exception as e:  # network trouble: be conservative
        return False, f"robots.txt unreachable: {e}"
    for agent in [BOT_TOKEN, "*", *AI_AGENTS]:
        if not rp.can_fetch(agent, url):
            return False, f"disallowed for {agent}"
    return True, "allowed"


EVENT_TYPES = re.compile(r"Event$")

def jsonld_events(html: str):
    """All schema.org *Event objects found in JSON-LD blocks."""
    found = []
    soup = BeautifulSoup(html or "", "html.parser")
    def walk(x):
        if isinstance(x, list):
            for i in x: walk(i)
        elif isinstance(x, dict):
            t = x.get("@type")
            ts = t if isinstance(t, list) else [t]
            if any(isinstance(tt, str) and EVENT_TYPES.search(tt) for tt in ts):
                loc = x.get("location") or {}
                if isinstance(loc, list): loc = loc[0] if loc else {}
                offers = x.get("offers") or {}
                if isinstance(offers, list): offers = offers[0] if offers else {}
                found.append({
                    "title": x.get("name"), "start": x.get("startDate"), "end": x.get("endDate"),
                    "venue": loc.get("name") if isinstance(loc, dict) else loc,
                    "price": (offers.get("price") if isinstance(offers, dict) else None),
                    "currency": (offers.get("priceCurrency") if isinstance(offers, dict) else None),
                    "url": x.get("url"),
                })
            for v in x.values():
                if isinstance(v, (list, dict)): walk(v)
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try: walk(json.loads(s.string or s.get_text() or ""))
        except Exception: pass
    return found


EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "date": {"type": "string", "description": "YYYY-MM-DD"},
        "start": {"type": "string", "description": "start time HH:MM, empty if not stated"},
        "doors": {"type": "string", "description": "door time HH:MM, empty if not stated"},
        "end": {"type": "string", "description": "end time HH:MM, empty if not stated"},
        "price": {"type": "string", "description": "entry fee as written, empty if not stated"},
        "style": {"type": "string", "description": "music style / genre as written, empty if not stated"},
        "url": {"type": "string"},
    },
    "required": ["title", "date"],
}
INSTRUCTION = (
    "Extract every upcoming event (concert, club night, party, show) listed on this page of a venue in Basel. "
    "Today is {today}. Use the year that makes the date upcoming if the page omits it. "
    "Only use information that is on the page; never guess times, prices or genres - leave them empty."
)


async def main():
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    try:
        from crawl4ai import LLMConfig
        from crawl4ai.extraction_strategy import LLMExtractionStrategy
    except Exception:
        LLMConfig = LLMExtractionStrategy = None
    key = os.getenv("ANTHROPIC_API_KEY")
    today = time.strftime("%Y-%m-%d")
    rows = []
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, user_agent=BOT, verbose=False)) as crawler:
        for s in SITES:
            row = {"site": s["slug"], "url": s["url"]}
            ok, why = robots_allows(s["url"])
            row["robots"] = why
            if not ok or s.get("robots_only"):
                row["status"] = "skipped (robots)" if not ok else "robots ok (not crawled)"
                rows.append(row); print(row, flush=True); continue
            t0 = time.time()
            try:
                cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=60000,
                                       wait_until="networkidle" if s.get("js") else "domcontentloaded",
                                       delay_before_return_html=2.0 if s.get("js") else 0.0)
                r = await crawler.arun(url=s["url"], config=cfg)
            except Exception as e:
                row["status"] = f"error: {e}"[:200]; rows.append(row); print(row, flush=True); continue
            row["seconds"] = round(time.time() - t0, 1)
            row["http"] = getattr(r, "status_code", None)
            if not r.success:
                row["status"] = f"failed: {r.error_message}"[:200]; rows.append(row); print(row, flush=True); continue
            md = r.markdown.raw_markdown if hasattr(r.markdown, "raw_markdown") else str(r.markdown or "")
            (OUT / f"{s['slug']}.html").write_text(r.html or "", encoding="utf-8")
            (OUT / f"{s['slug']}.md").write_text(md, encoding="utf-8")
            row["html_kb"] = round(len(r.html or "") / 1024)
            row["markdown_chars"] = len(md)
            ev = jsonld_events(r.html)
            row["jsonld_events"] = len(ev)
            if ev: (OUT / f"{s['slug']}.jsonld.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")
            if s.get("llm") and key and LLMExtractionStrategy:
                try:
                    strat = LLMExtractionStrategy(
                        llm_config=LLMConfig(provider=MODEL, api_token=key),
                        schema={"type": "array", "items": EVENT_SCHEMA}, extraction_type="schema",
                        instruction=INSTRUCTION.format(today=today), input_format="markdown",
                        apply_chunking=False, extra_args={"temperature": 0, "max_tokens": 8000})
                    t1 = time.time()
                    r2 = await crawler.arun(url=s["url"], config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS, page_timeout=60000, extraction_strategy=strat,
                        wait_until="networkidle" if s.get("js") else "domcontentloaded",
                        delay_before_return_html=2.0 if s.get("js") else 0.0))
                    data = json.loads(r2.extracted_content or "[]")
                    data = [d for d in data if isinstance(d, dict) and not d.get("error")]
                    (OUT / f"{s['slug']}.llm.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                    row["llm_events"] = len(data); row["llm_seconds"] = round(time.time() - t1, 1)
                except Exception as e:
                    row["llm_events"] = f"error: {e}"[:160]
            elif s.get("llm"):
                row["llm_events"] = "no API key"
            row["status"] = "ok"
            rows.append(row); print(row, flush=True)
    (OUT / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["site", "status", "robots", "http", "seconds", "html_kb", "markdown_chars", "jsonld_events", "llm_events"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows: lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    (OUT / "summary.md").write_text(f"# Crawl4AI test {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    asyncio.run(main())
