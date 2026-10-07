"""Rule-based parsers (no AI). Each takes the Crawl4AI markdown of a page and returns a list of events:
{title, venue, date (YYYY-MM-DD), start, end, style, url}. Unknown fields are "".
"""
import re
from datetime import date

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


def denkmal(md, today):
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


def renee(md, today):
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


def grenzwert(md, today):
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


def nordstern(md, today):
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


PARSERS = {"denkmal": denkmal, "renee": renee, "grenzwert": grenzwert, "nordstern": nordstern}
