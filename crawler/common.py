"""Shared helpers: robots.txt, ids, duplicate detection, categories."""
import re, unicodedata, urllib.robotparser, urllib.request, urllib.error

BOT = "UsgangBaselBot/1.0 (+https://github.com/usgangbasel/usgang-basel)"
BOT_TOKEN = "UsgangBaselBot"
AI_AGENTS = ["ClaudeBot", "Claude-Web", "anthropic-ai"]
_robots = {}

def robots_allows(url, ai=True):
    """(allowed, reason). Disallowed for us, for '*', or (if the page is read by AI) for an AI crawler -> skip."""
    host = re.match(r"(https?://[^/]+)", url).group(1)
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(host + "/robots.txt", headers={"User-Agent": BOT})
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
            _robots[host] = rp
        except urllib.error.HTTPError as e:
            _robots[host] = "none" if e.code in (404, 410) else f"error {e.code}"
        except Exception as e:
            _robots[host] = f"unreachable: {e}"
    rp = _robots[host]
    if rp == "none": return True, "no robots.txt"
    if isinstance(rp, str): return False, f"robots.txt {rp}"
    for agent in [BOT_TOKEN, "*"] + (AI_AGENTS if ai else []):
        if not rp.can_fetch(agent, url):
            return False, f"disallowed for {agent}"
    return True, "allowed"


def fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", fold(s)).strip("-")

def event_id(e):
    return f"{e['date']}-{slug(e['venue'])[:12]}-{slug(e['title'])[:40]}"


# Venue names as other sources spell them -> the name used on the page
VENUE_ALIASES = {
    "sudhaus": "Sud", "gannet": "The Gannet", "basso": "Basso", "nebel bar": "Nebel", "nebelbar": "Nebel",
    "derriere": "Derrière", "renee": "Renée", "bird's eye": "Bird's Eye Jazz Club", "birds eye": "Bird's Eye Jazz Club",
    "viertel klub": "Das Viertel", "das viertel klub": "Das Viertel", "stadtcasino": "Stadtcasino Basel",
    "kaserne": "Kaserne Basel", "goldenes fass": "Sääli (Goldenes Fass)", "zum goldenen fass": "Sääli (Goldenes Fass)",
}
def canon_venue(v):
    v = (v or "").strip()
    return VENUE_ALIASES.get(fold(v), v)


# ---- duplicate detection (same rules as the page) ----
STOP = set("the der die das and und mit live in im at de la le feat ft presents pres x vs konzert concert party dj djs b2b tour 2025 2026 2027".split())
def _nv(v): return re.sub(r"[^a-z0-9]", "", re.sub(r"^the\s+", "", fold(v)))
def _tw(t): return {w for w in re.split(r"[^a-z0-9]+", fold(t)) if len(w) > 1 and w not in STOP}
def same_venue(a, b):
    x, y = _nv(a), _nv(b)
    return bool(x and y and (x == y or (min(len(x), len(y)) >= 4 and (x.startswith(y) or y.startswith(x)))))
def similar_title(a, b):
    if _nv(a) and _nv(a) == _nv(b): return True
    na, nb = _nv(a), _nv(b)
    if min(len(na), len(nb)) >= 4 and (na.startswith(nb) or nb.startswith(na)):
        return True  # "RE:BACK" vs "RE:BACK: Annie, ..." (one title is the other plus a line-up)
    # "Festival: Film A" vs "Festival: Film B" -> compare only what follows the shared prefix
    if ":" in a and ":" in b:
        pa, ra = a.split(":", 1); pb, rb = b.split(":", 1)
        if _nv(pa) == _nv(pb) and ra.strip() and rb.strip():
            return similar_title(ra, rb)
    A, B = _tw(a), _tw(b)
    if not A or not B: return False
    n, m = len(A & B), min(len(A), len(B))
    return n / m >= 0.6 if m >= 2 else (n >= 1 and max(len(A), len(B)) <= 2)
def _mins(t):
    m = re.match(r"^(\d{1,2}):(\d{2})", t or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None
def far_apart(a, b):
    x, y = _mins(a.get("time")), _mins(b.get("time"))
    return x is not None and y is not None and abs(x - y) >= 90
def is_dup(a, b):
    return a["date"] == b["date"] and same_venue(a["venue"], b["venue"]) and not far_apart(a, b) and similar_title(a["title"], b["title"])


# ---- categories in the page's German style ----
GROUPS = [
    (r"klassik|classical|oper|opera|kammermusik|orchester", "Konzert / Klassik"),
    (r"jazz", "Konzert / Jazz"),
    (r"techno|house|trance|drum|dnb|bass|electro|edm|minimal|psy", "Club / {}"),
    (r"disco|italo|funk|soul|afro|hip ?hop|dancehall|reggae|amapiano|open format|80s|90s|latin|salsa", "Party / {}"),
    (r"rock|metal|punk|pop|folk|blues|indie|hardcore|screamo|singer|chanson|tango", "Konzert / {}"),
    (r"theater|drag|comedy|lesung|reading|performance|tanz", "Bühne / {}"),
    (r"film|kino|cinema", "Film"),
]
def category_from(style, default="Anderes"):
    s = (style or "").strip()
    if not s: return default
    for pat, cat in GROUPS:
        if re.search(pat, s, re.I):
            first = re.split(r"[,/]", s)[0].strip()
            return cat.format(first[:1].upper() + first[1:]) if "{}" in cat else cat
    return default
