"""What the nightly crawl reads. All sources use rules from crawler/parsers.py (no AI).
details: open each event's own page (only while its start time is unknown) to read times/price.
next/max_pages: follow "next page" links found in the HTML.
direct=True: the venue's own program; aggregator listings for that venue are then skipped.
ai_fallback=True: if the rules find nothing and the repository secret ANTHROPIC_API_KEY exists, Claude reads the page instead.
Venues added via the page (venues.json, crawl:true) without rules are read by Claude only if the key exists.
"""
SOURCES = [
    # aggregators
    {"id": "denkmal", "parser": "denkmal", "days": True, "direct": False},
    {"id": "eventfrog", "parser": "eventfrog", "url": "https://eventfrog.ch/de/events/basel.html", "pages": 3, "direct": False},
    # venue programs
    {"id": "renee", "parser": "renee", "url": "https://www.renee.ch", "venue": "Renée", "direct": True},
    {"id": "grenzwert", "parser": "grenzwert", "url": "https://grenzwert.ch/programm/", "venue": "Grenzwert", "direct": True},
    {"id": "nordstern", "parser": "nordstern", "url": "https://www.nordstern.com/events/", "venue": "Nordstern", "direct": True},
    {"id": "kaschemme", "parser": "kaschemme", "url": "https://www.kaschemme.ch/programm", "venue": "Kaschemme", "direct": True},
    {"id": "stadtcasino", "parser": "stadtcasino", "url": "https://www.stadtcasino-basel.ch/de/programm/veranstaltungen/", "venue": "Stadtcasino Basel", "direct": True, "details": "stadtcasino"},
    {"id": "viertel", "parser": "viertel", "url": "https://www.dasviertel.ch/programmklub", "venue": "Das Viertel", "direct": True,
     "next": r'href="(https://www\.dasviertel\.ch/programmklub\?comp-[a-z0-9]+_page=\d+)"', "max_pages": 4},
    {"id": "garedunord", "parser": "garedunord", "url": "https://www.garedunord.ch/", "venue": "Gare du Nord", "direct": True},
    {"id": "sommercasino", "parser": "sommercasino", "url": "https://sommercasino.ch/", "venue": "Sommercasino", "direct": True},
    {"id": "basso", "parser": "basso", "url": "https://www.bassoverse.space/beats", "venue": "Basso", "js": True, "direct": True, "details": "basso"},
    {"id": "saali", "parser": "saali", "url": "https://www.goldenes-fass.ch/saali/", "venue": "Sääli (Goldenes Fass)", "direct": True, "ai_fallback": True},
    # sites without a dated program: checked every night, flagged in the report if dates appear
    {"id": "hafenkran", "parser": "no_program", "url": "https://www.hafenkran.ch", "venue": "Hafenkran", "js": True, "direct": False},
    {"id": "nebel", "parser": "no_program", "url": "https://nebelbar.ch", "venue": "Nebel", "direct": False},
    {"id": "derriere", "parser": "no_program", "url": "https://derriere.ch", "venue": "Derrière", "direct": False},
]
# Never crawled: robots.txt disallows AI crawlers (ra.co).
EXCLUDED = ["ra.co"]

# Venues the page should never show (removed on request). Events from any source at these venues,
# or linking to these sites, are dropped and removed from events.json on every run.
BLOCKED_VENUES = ["Bird's Eye Jazz Club"]
BLOCKED_HOSTS = ["birdseye.ch"]
