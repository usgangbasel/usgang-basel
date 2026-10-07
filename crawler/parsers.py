"""Rule-based parsers (no AI). Each takes the Crawl4AI markdown of a page and returns a list of events:
{title, venue, date (YYYY-MM-DD), start, end, style, url}. Unknown fields are "".
"""
import re
from datetime import date, datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    ZH = ZoneInfo("Europe/Zurich")
except Exception:
    ZH = None

MON_EN = {m: i for i, m in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], 1)}

def _year_for(month: int, day: int, today: date) -> int:
    """Pages often omit the year: pick the one that makes the date upcoming (allowing ~2 months in the past)."""
    y = today.year
    return y + 1 if (month, day) < (today.month, today.day) and today.month - month > 2 else y

def _lines(md):
    return [l.strip() for l in md.splitlines() if l.strip()]

def _hhmm(h):
    if not h: return ""
    h = h.replace(".", ":")
    if ":" not in h: h += ":00"
    hh, mm = h.split(":")[:2]
    return f"{int(hh):02d}:{int(mm):02d}"


def denkmal(md, today, html=""):
    """[ Venue 21 - 23h, 21 Uhr bis 23 Uhr. Title. genre,genre ](url)  on a page headed '# Freitag, 9. Oktober 2026'."""
    mons = ["januar","februar","märz","april","mai","juni","juli","august","september","oktober","november","dezember"]
    m = re.search(r"#\s*\w+,\s*(\d{1,2})\.\s*(\w+)\s+(\d{4})", md)
    if not m: return []
    d = date(int(m.group(3)), mons.index(m.group(2).lower()) + 1, int(m.group(1))).isoformat()
    out = []
    for vm in re.finditer(r"\[\s*(.+?)\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?h,[^.]*\.\s*(.+?)\s*\]\((https://denkmal\.org/[^)]+)\)", md):
        venue, start, end, rest, url = vm.groups()
        parts = rest.rsplit(". ", 1)
        title, style = (parts[0], parts[1].rstrip(".")) if len(parts) == 2 else (rest.rstrip("."), "")
        out.append(dict(title=title.strip(), venue=venue.strip(), date=d, start=_hhmm(start), end=_hhmm(end),
                        style=style.replace(",", ", "), url=url))
    return out


def renee(md, today, html=""):
    """* Th, 8 Oct 23:00 / DJs: Name / Genres"""
    L = _lines(md); out = []
    for i, l in enumerate(L):
        m = re.match(r"\*\s*\w{2},\s*(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{1,2}:\d{2})", l)
        if not m: continue
        day, mon, t = int(m.group(1)), MON_EN[m.group(2).lower()], m.group(3)
        block = []
        for nxt in L[i+1:i+5]:
            if nxt.startswith("*") or nxt.startswith("["): break
            block.append(nxt)
        if not block: continue
        # optional event name line before the "DJ(s):" line
        title_parts = [b for b in block if not re.match(r"DJs?:", b)][:1] if not block[0].startswith("DJ") else []
        dj = next((re.sub(r"^DJs?:\s*", "", b) for b in block if re.match(r"DJs?:", b)), "")
        style = block[-1] if len(block) >= 2 and not block[-1].startswith("DJ") else ""
        title = (title_parts[0] + ": " + dj) if title_parts and dj else (dj or (title_parts[0] if title_parts else ""))
        out.append(dict(title=title, venue="Renée", date=date(_year_for(mon, day, today), mon, day).isoformat(),
                        start=t, end="", style=style, url="https://www.renee.ch"))
    return out


def grenzwert(md, today, html=""):
    """#### 09.10.2026 / ###### 22:00 / Title / Genre   (the page also contains template placeholders from 2025: dropped as past)"""
    L = _lines(md); out = []
    for i, l in enumerate(L):
        m = re.match(r"#+\s*(\d{2})\.(\d{2})\.(\d{4})$", l)
        if not m or i + 3 >= len(L): continue
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if d < today: continue
        tm = re.match(r"#+\s*(\d{1,2}[:.]\d{2})", L[i+1])
        title, style = L[i+2], L[i+3]
        if style.startswith("#"): style = ""
        out.append(dict(title=title, venue="Grenzwert", date=d.isoformat(), start=_hhmm(tm.group(1)) if tm else "",
                        end="", style=style, url="https://grenzwert.ch/programm/"))
    return out


def nordstern(md, today, html=""):
    """* ## Fr, 16.10 / 23:00 / # Blackworks: / # Fatima Hajji / * support ... / [ TICKETS ](url)"""
    L = _lines(md); out = []
    for i, l in enumerate(L):
        m = re.match(r"\*?\s*#+\s*\w{2},\s*(\d{1,2})\.(\d{1,2})\s*/\s*(\d{1,2}:\d{2})", l)
        if not m: continue
        day, mon, t = int(m.group(1)), int(m.group(2)), m.group(3)
        heads, acts, url = [], [], ""
        for nxt in L[i+1:i+25]:
            if re.match(r"\*?\s*#+\s*\w{2},\s*\d", nxt): break
            if nxt.startswith("# "): heads.append(nxt[2:].strip())
            elif nxt.startswith("* "): acts.append(nxt[2:].strip())
            u = re.search(r"\[\s*TICKETS\s*\]\((https?://[^)]+)\)", nxt)
            if u: url = u.group(1); break
        if not heads: continue
        if re.search(r"bernexpo|titlis|mountain|zürich|zurich", " ".join(heads), re.I):
            continue  # Nordstern also lists events it organises elsewhere
        if heads[-1].endswith(":") and acts:  # "Club Futura:" followed by the line-up as a list
            heads = heads + [", ".join(acts)]
        title = " ".join(h if h.endswith(":") else h + "," for h in heads).rstrip(",").rstrip(":")
        out.append(dict(title=title, venue="Nordstern", date=date(_year_for(mon, day, today), mon, day).isoformat(),
                        start=t, end="", style="", url=url or "https://www.nordstern.com/events/"))
    return out




MON_DE = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "mrz": 3, "apr": 4, "mai": 5, "may": 5, "jun": 6, "jul": 7, "aug": 8,
          "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dez": 12, "dec": 12}
def _mon(name):
    n = name.lower().strip(". ")[:4]
    for k, v in MON_DE.items():
        if n.startswith(k): return v
    return None

LOWER = {"w/", "und", "mit", "the", "of", "and", "feat.", "x", "vs", "in", "im", "am", "de", "la", "le"}
def _smart_case(t):
    """'STUDENTENFUTTER XXL' -> 'Studentenfutter XXL', 'NEWSTARS PRODUCTION W/ DJ GREGORY' -> 'Newstars Production w/ DJ Gregory'."""
    if not t.isupper(): return t
    out = []
    for w in t.split():
        lw = w.lower()
        if lw in LOWER: out.append(lw)
        elif len(w.strip("()/.,")) <= 3 and w.isalpha(): out.append(w)  # XXL, DJ, MC, 90S stay as they are
        else: out.append(w[:1] + w[1:].lower())
    return " ".join(out)

def _mk(title, venue, d, start="", url="", **kw):
    e = dict(title=re.sub(r"\s+", " ", title).strip(" -|:"), venue=venue, date=d.isoformat(), start=start, end=kw.pop("end", ""), url=url)
    e.update({k: v for k, v in kw.items() if v})
    return e


def birdseye(md, today, html=""):
    """Each event appears as a summary block that starts with its date heading ('# **16+17** ❘ 10'), then time
    ('Fr, 20:30 Uhr', optionally '❘ Museum Tinguely' for events elsewhere), title(s) '## **…**', price and reservation ID.
    The repeated detail block (title before the heading) carries no title after its heading and is ignored."""
    md = re.sub(r"\+\s*\n\s*", "+", md)
    heads = list(re.finditer(r"^#\s+\*\*([\d+ ]+)\*\*\s*❘\s*(\d{1,2})", md, re.M))
    out, seen = [], set()
    for k, m in enumerate(heads):
        seg = md[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(md)]
        part = seg.split("\nDetails\n")[0]
        titles = []
        for t in re.findall(r"^## \*\*(.+?)\*\*\s*$", part, re.M):
            if t not in titles: titles.append(t)
        if not titles: continue
        title = re.sub(r"^\d\.\s*Set:\s*", "", titles[0])  # double bills have one heading (and time) per set
        t = re.search(r"(\d{1,2}:\d{2})\s*Uhr", part)
        loc = re.search(r"Uhr\s*(?:❘|\n)\s*([^*\n❘]+?)\s*\*\*", part)
        venue = loc.group(1).strip() if loc and "bird" not in loc.group(1).lower() else "Bird's Eye Jazz Club"
        price = re.search(r"Eintritt\s+([^\n]+)", part)
        oid = re.search(r"ObjID=(\d+)", part)
        mon = int(m.group(2))
        for day in [int(x) for x in m.group(1).replace(" ", "").split("+") if x]:
            d = date(_year_for(mon, day, today), mon, day)
            if d < today or (d, title, venue) in seen: continue
            seen.add((d, title, venue))
            url = f"https://www.birdseye.ch/index.php?EventID={oid.group(1)}&l=de" if oid else "https://www.birdseye.ch/"
            out.append(_mk(title, venue, d, t.group(1) if t else "", url,
                           price=price.group(1).strip().replace("–", "-") if price else "", style="Jazz", category="Konzert / Jazz"))
    return out


def kaschemme(md, today, html=""):
    """Squarespace list: '# [Title](url)' followed by a Google Calendar link with exact UTC start/end."""
    out = []
    for m in re.finditer(r"^# \[(.+?)\]\((https://www\.kaschemme\.ch/programm/[^)]+)\)", md, re.M):
        title, url = m.group(1), m.group(2)
        block = md[m.end():m.end() + 1500]
        before = md[max(0, m.start() - 600):m.start()]
        g = re.search(r"dates=(\d{8})T(\d{4})\d{2}Z/(\d{8})T(\d{4})\d{2}Z", block)
        if not g: continue
        def local(dd, hm):
            dt = datetime.strptime(dd + hm, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            return dt.astimezone(ZH) if ZH else dt + timedelta(hours=2)
        st, en = local(g.group(1), g.group(2)), local(g.group(3), g.group(4))
        if st.date() < today: continue
        cats = re.findall(r"\?category=([^)]+)\)", before.split("](https://www.kaschemme.ch/programm/")[-1] if before else "")
        cats = [c.replace("+", " ") for c in cats]
        style = re.search(r"\[(.+?)\]", title)
        out.append(_mk(re.sub(r"\s*\\?\[.*?\\?\]\s*", " ", title).replace("\\", ""), "Kaschemme", st.date(), st.strftime("%H:%M"), url,
                       end=en.strftime("%H:%M"), price="frei" if "Freier Eintritt" in cats else "",
                       style=(style.group(1).replace("&amp;", "&").replace("\\", "") if style else "")))
    return out


def stadtcasino(md, today, html=""):
    """'… 10  Okt' line followed by '## [Title](url)'. No times on the list page."""
    out = []
    for m in re.finditer(r"(\d{1,2})\s+([A-Za-zä]{3})\w*\s*\n+\s*## \[(.+?)\s*\]\((https://www\.stadtcasino-basel\.ch/[^)]+)\)", md):
        day, mon = int(m.group(1)), _mon(m.group(2))
        if not mon: continue
        title = m.group(3)
        if re.search(r"wanderung|führung|workshop", title, re.I): continue
        d = date(_year_for(mon, day, today), mon, day)
        if d < today: continue
        cat = "Konzert / Klassik" if re.search(r"sinfonie|orchest|kammer|quart|quatuor|philharm|requiem|barock|ensemble|solisten|chor|gesangverein", title, re.I) else ("Bühne" if re.search(r"comedy|hypnose|lesung", title, re.I) else "Konzert")
        out.append(_mk(title, "Stadtcasino Basel", d, "", m.group(4), category=cat))
    return out


def viertel(md, today, html=""):
    """Wix list: '18+FREE ENTRY' / '## TITLE' / 'GENRE / GENRE' / '## 09' / '## OKT.'"""
    L = _lines(md); out = []
    for i, l in enumerate(L):
        m = re.match(r"^(\d{2})\+\s*(.*)$", l)
        if not m or i + 4 >= len(L): continue
        t, g, dd, mm = L[i+1], L[i+2], L[i+3], L[i+4]
        if not (t.startswith("## ") and re.match(r"## \d{1,2}$", dd) and re.match(r"## [A-ZÄ]{3}", mm)): continue
        day, mon = int(dd[3:]), _mon(mm[3:])
        if not mon: continue
        d = date(_year_for(mon, day, today), mon, day)
        if d < today: continue
        title = _smart_case(t[3:].strip())
        out.append(_mk(title, "Das Viertel", d, "", "https://www.dasviertel.ch/programmklub",
                       style=_smart_case(g), price="frei" if "FREE" in m.group(2).upper() else ""))
    return out


def garedunord(md, today, html=""):
    """HTML event cards: day-time 'Do 19:30', series, date '15.10.26', title + ensemble."""
    from bs4 import BeautifulSoup
    out = []
    for a in BeautifulSoup(html or "", "html.parser").select("a.event-card"):
        g = lambda c: (a.select_one(c).get_text(" ", strip=True) if a.select_one(c) else "")
        dm = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{2})", g(".event-card__date"))
        if not dm: continue
        d = date(2000 + int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
        series = g(".event-card__series")
        if d < today or re.search(r"workshop|vortrag", series, re.I): continue
        tm = re.search(r"(\d{1,2}:\d{2})", g(".event-card__day-time"))
        title, ens = g(".event-card__title"), g(".event-card__ensemble")
        href = a.get("href", "")
        out.append(_mk(f"{title}: {ens}" if ens else title, "Gare du Nord", d, tm.group(1) if tm else "",
                       ("https://www.garedunord.ch" + href) if href.startswith("/") else href, style=series,
                       category=("Bühne / Musiktheater" if "musiktheater" in series.lower() else "Konzert / Neue Musik")))
    return out


def sommercasino(md, today, html=""):
    """'Freitag, 16. Oktober 2026 [Infos](url)' / '## [Title](url)' / '### Konzerte | Club' / '#### Doors: 20 Uhr'"""
    mons = ["januar","februar","märz","april","mai","juni","juli","august","september","oktober","november","dezember"]
    L = _lines(md); out = []
    for i, l in enumerate(L):
        m = re.match(r"^\w+,\s*(\d{1,2})\.\s*(\w+)\s+(\d{4})\s*\[Infos\]\((https://sommercasino\.ch/events/[^)]+)\)", l)
        if not m or i + 1 >= len(L) or m.group(2).lower() not in mons: continue
        d = date(int(m.group(3)), mons.index(m.group(2).lower()) + 1, int(m.group(1)))
        if d < today: continue
        tm = re.match(r"##\s*\[(.+?)\s*\]", L[i+1])
        if not tm: continue
        cat = re.sub(r"^#+\s*", "", L[i+2]) if i + 2 < len(L) and L[i+2].startswith("###") else ""
        tl = L[i+3] if i + 3 < len(L) else ""
        doors = re.search(r"Doors:?\s*(\d{1,2}(?:[:.]\d{2})?)", tl)
        start = re.match(r"#+\s*(\d{1,2}[:.]\d{2})", tl)
        kind = cat.split("|")[0].strip()
        out.append(_mk(tm.group(1), "Sommercasino", d, _hhmm(start.group(1)) if start else (_hhmm(doors.group(1)) if doors else ""),
                       m.group(4), doors=_hhmm(doors.group(1)) if doors else "",
                       category={"Konzerte": "Konzert", "Konzert": "Konzert", "Party": "Party", "Literatur": "Lesung"}.get(kind, kind or "Anderes")))
    return out


def basso(md, today, html=""):
    """Wix list: room / genres / line-up / title / weekday / '9.10.26' / [](url)"""
    L = _lines(md); out = []
    for i, l in enumerate(L):
        m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2})$", l)
        if not m or i < 4 or not re.match(r"^(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)$", L[i-1]): continue
        d = date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if d < today: continue
        title, lineup, genres = L[i-2], L[i-3], L[i-4]
        u = re.search(r"\((https://www\.bassoverse\.space/programm/[^)]+)\)", L[i+1] if i + 1 < len(L) else "")
        full = f"{title}: {lineup.replace(' • ', ', ')}" if lineup and lineup.upper() != "TBA" and len(lineup) < 140 else title
        out.append(_mk(full, "Basso", d, "", u.group(1) if u else "https://www.bassoverse.space/beats",
                       style=genres.replace(" • ", ", ").strip()))
    return out


EF_KEEP = re.compile(r"/de/p/(konzerte|partys|theater-buehne|festivals|comedy|kino)/")
def eventfrog(md, today, html=""):
    """'[ ![Event-Image …](img) [Tickets] Okt 8 Title Donnerstag, 08. Oktober, 20:00 Venue, Basel (CH) ](url)'"""
    mons = ["januar","februar","märz","april","mai","juni","juli","august","september","oktober","november","dezember"]
    out = []
    for body, url in re.findall(r"\[ !\[Event-Image for '[^']*'\]\([^)]*\) (.*?) \]\((https://eventfrog\.ch/[^)]+)\)", md):
        if not EF_KEEP.search(url): continue
        m = re.match(r"^(?:Tickets\s+)?[A-Za-zä]{3}\s+\d{1,2}\s+(.+?)\s+\w+,\s*(\d{1,2})\.\s*(\w+),\s*(\d{1,2}:\d{2})\s+(.+?),\s*Basel\s*\(CH\)$", body)
        if not m or m.group(3).lower() not in mons: continue
        mon, day = mons.index(m.group(3).lower()) + 1, int(m.group(2))
        d = date(_year_for(mon, day, today), mon, day)
        if d < today: continue
        sub = url.split("/de/p/")[1].split("/")
        out.append(_mk(m.group(1), m.group(5).strip(), d, m.group(4), url,
                       category={"konzerte": "Konzert", "partys": "Party", "theater-buehne": "Bühne", "festivals": "Festival", "comedy": "Bühne / Comedy", "kino": "Film"}[sub[0]]))
    return out


def saali(md, today, html=""):
    """Free text: '**Freitag 02_Okt _22h** : Grober & Fug (Disco, House)' plus 'Jeden Dienstag … HULA CLUB … Konzerte ab 20h'."""
    out = []
    for m in re.finditer(r"\*\*\s*[A-Za-zä]+[\s_]+(\d{1,2})[\s_]+([A-Za-zä]+)\.?[\s_]*(\d{1,2}(?:[.:]\d{2})?)\s*h\s*:?\s*\*\*\s*:?\s*([^\n]+)", md):
        mon = _mon(m.group(2))
        if not mon: continue
        day = int(m.group(1)); d = date(_year_for(mon, day, today), mon, day)
        if d < today: continue
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", m.group(4)).strip()
        st = re.search(r"\(([^)]+)\)\s*$", text)
        title = text[:st.start()].strip() if st else text
        out.append(_mk(title.split(",")[0] if len(title) > 80 else title, "Sääli (Goldenes Fass)", d, _hhmm(m.group(3)),
                       "https://www.goldenes-fass.ch/saali/", style=st.group(1) if st else ""))
    hula = re.search(r"Jeden Dienstag.*?HULA CLUB.*?Bar ab (\d{1,2}[.:]\d{2})h.*?Konzerte ab (\d{1,2})h", md, re.S | re.I)
    if hula:
        d = today + timedelta(days=(1 - today.weekday()) % 7)
        for k in range(3):
            out.append(_mk("HULA CLUB", "Sääli (Goldenes Fass)", d + timedelta(weeks=k), _hhmm(hula.group(2)),
                           "https://www.goldenes-fass.ch/saali/", doors=_hhmm(hula.group(1)), category="Konzert"))
    return out


def no_program(md, today, html=""):
    """Venues whose site lists no dates (Hafenkran, Nebel, Derrière). Returns nothing; run.py flags it if dates appear."""
    return []


PARSERS = {"denkmal": denkmal, "renee": renee, "grenzwert": grenzwert, "nordstern": nordstern,
           "birdseye": birdseye, "kaschemme": kaschemme, "stadtcasino": stadtcasino, "viertel": viertel,
           "garedunord": garedunord, "sommercasino": sommercasino, "basso": basso, "eventfrog": eventfrog,
           "saali": saali, "no_program": no_program}
