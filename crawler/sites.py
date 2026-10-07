"""Test targets. expect: what the test should show for this site."""
SITES = [
    # Fixed venue sites with their own program
    {"slug": "grenzwert", "venue": "Grenzwert", "url": "https://grenzwert.ch/programm/", "llm": True},
    {"slug": "renee", "venue": "Renée", "url": "https://www.renee.ch", "llm": True},
    {"slug": "saali", "venue": "Sääli (Goldenes Fass)", "url": "https://www.goldenes-fass.ch/saali/", "llm": False},
    {"slug": "nordstern", "venue": "Nordstern", "url": "https://www.nordstern.com/events/", "llm": False},
    {"slug": "birdseye", "venue": "Bird's Eye Jazz Club", "url": "https://www.birdseye.ch/", "llm": False},
    # Wix sites: content is built with JavaScript, needs the real browser
    {"slug": "basso", "venue": "Basso", "url": "https://www.bassoverse.space/beats", "llm": True, "js": True},
    {"slug": "hafenkran", "venue": "Hafenkran", "url": "https://www.hafenkran.ch", "llm": False, "js": True},
    # Aggregators
    {"slug": "denkmal", "venue": None, "url": "https://denkmal.org/de/basel/2026-10-09", "llm": False, "js": True},
    {"slug": "eventfrog", "venue": None, "url": "https://eventfrog.ch/de/events/basel.html", "llm": False},
    # robots.txt test: these must be refused before any page is loaded
    {"slug": "ra", "venue": None, "url": "https://ra.co/events/ch/basel", "robots_only": True},
    {"slug": "sudhaus", "venue": "Sud", "url": "https://www.sudhaus.ch/", "robots_only": True},
]
