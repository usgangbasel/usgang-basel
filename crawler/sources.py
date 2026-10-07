"""What the nightly crawl reads.
kind 'rules': parsed with crawler/parsers.py (no AI).
kind 'ai':    page text is read by Claude (only if the repository secret ANTHROPIC_API_KEY is set).
direct=True:  the venue's own program; aggregator listings for that venue are then skipped.
"""
SOURCES = [
    {"id": "denkmal", "kind": "rules", "parser": "denkmal", "days": True, "direct": False},
    {"id": "renee", "kind": "rules", "parser": "renee", "url": "https://www.renee.ch", "venue": "Renée", "direct": True},
    {"id": "grenzwert", "kind": "rules", "parser": "grenzwert", "url": "https://grenzwert.ch/programm/", "venue": "Grenzwert", "direct": True},
    {"id": "nordstern", "kind": "rules", "parser": "nordstern", "url": "https://www.nordstern.com/events/", "venue": "Nordstern", "direct": True},

    {"id": "birdseye", "kind": "ai", "url": "https://www.birdseye.ch/", "venue": "Bird's Eye Jazz Club", "direct": True},
    {"id": "kaschemme", "kind": "ai", "url": "https://www.kaschemme.ch/programm", "venue": "Kaschemme", "direct": True},
    {"id": "stadtcasino", "kind": "ai", "url": "https://www.stadtcasino-basel.ch/de/programm/veranstaltungen/", "venue": "Stadtcasino Basel", "direct": True},
    {"id": "viertel", "kind": "ai", "url": "https://www.dasviertel.ch/programmklub", "venue": "Das Viertel", "direct": True},
    {"id": "garedunord", "kind": "ai", "url": "https://www.garedunord.ch/", "venue": "Gare du Nord", "direct": True},
    {"id": "sommercasino", "kind": "ai", "url": "https://sommercasino.ch/", "venue": "Sommercasino", "direct": True},
    {"id": "basso", "kind": "ai", "url": "https://www.bassoverse.space/beats", "venue": "Basso", "js": True, "direct": True},
    {"id": "saali", "kind": "ai", "url": "https://www.goldenes-fass.ch/saali/", "venue": "Sääli (Goldenes Fass)", "direct": True},
    {"id": "hafenkran", "kind": "ai", "url": "https://www.hafenkran.ch", "venue": "Hafenkran", "js": True, "direct": False},
    {"id": "eventfrog", "kind": "ai", "url": "https://eventfrog.ch/de/events/basel.html", "pages": 3, "direct": False},
]
# Never crawled: robots.txt disallows AI crawlers (ra.co) - kept here as a reminder.
EXCLUDED = ["ra.co"]
