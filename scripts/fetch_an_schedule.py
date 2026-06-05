#!/usr/bin/env python3
"""
Fetch Gabriel Attal's schedule from two sources:

  1. Assemblée nationale plenary calendar
     - QAG days (Tue/Wed) only
     - Dedup: delete future [AN_AUTO] entries, re-insert fresh data

  2. attalpresident.fr official campaign articles
     - Parses sitemap.xml → extracts date/title/location from each article
     - Dedup: checks existing source_url before inserting (never duplicates)

Stored in Supabase 'schedule' table, person = "Gabriel Attal".
"""
import os
import re
import requests
from datetime import datetime, date, timedelta
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_KEY)

AN_ORDER_OF_DAY = "https://www.assemblee-nationale.fr/dyn/seance-publique/textes-inscrits-ordre-du-jour"
AN_SEANCE       = "https://www.assemblee-nationale.fr/dyn/seance-publique"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

AN_AUTO_TAG = "[AN_AUTO]"

# ── French date parsing ───────────────────────────────────────────────────────

_FR_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

_FR_DAY_NAMES = r"(?:Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)"
_FR_DATE_PAT  = re.compile(
    rf"{_FR_DAY_NAMES}\s+(\d{{1,2}})\s*(?:er|ème|e)?\s+([a-záéèêëîïôùûü]+)\s+(\d{{4}})",
    re.IGNORECASE
)


def _parse_fr_date(day_str: str, month_str: str, year_str: str) -> str | None:
    month = _FR_MONTHS.get(month_str.lower())
    if not month:
        return None
    try:
        return date(int(year_str), month, int(day_str)).isoformat()
    except ValueError:
        return None


# ── Scrape order-of-day page ──────────────────────────────────────────────────

def fetch_order_of_day() -> dict[str, list[str]]:
    """
    Returns {date_iso: [agenda_item, ...], ...} for all upcoming plenary dates.
    """
    try:
        r = requests.get(AN_ORDER_OF_DAY, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"   ⚠️  Could not fetch order-of-day page: {e}")
        return {}

    # Strip HTML and decode HTML entities
    text = re.sub(r"<[^>]+>", " ", r.text)
    text = (text
            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&#039;", "'").replace("&nbsp;", " ").replace("&#8217;", "'"))
    text = re.sub(r"\s+", " ", text).strip()

    # Find the start of the actual content (first day name)
    start = re.search(_FR_DAY_NAMES, text)
    if not start:
        print("   ⚠️  Could not locate calendar content in page")
        return {}
    text = text[start.start():]

    # Split into sections by date headers
    schedule: dict[str, list[str]] = {}
    current_date: str | None = None
    current_items: list[str] = []

    # Tokenise: split on day-name patterns
    segments = re.split(
        rf"({_FR_DAY_NAMES}\s+\d{{1,2}}\s*(?:er|ème|e)?\s+[a-záéèêëîïôùûü]+\s+\d{{4}})",
        text, flags=re.IGNORECASE
    )

    for seg in segments:
        m = _FR_DATE_PAT.match(seg.strip())
        if m:
            # Save previous block
            if current_date:
                schedule[current_date] = current_items
            current_date = _parse_fr_date(m.group(1), m.group(2), m.group(3))
            current_items = []
        else:
            if current_date:
                # Parse arrow-prefixed items (➜ or ►)
                items = re.split(r"[➜►→]", seg)
                for item in items:
                    item = item.strip()
                    if len(item) > 10:
                        current_items.append(item)

    # Save last block
    if current_date and current_items:
        schedule[current_date] = current_items

    # Filter to future dates only
    today = date.today().isoformat()
    schedule = {d: v for d, v in schedule.items() if d >= today}
    print(f"   → {len(schedule)} upcoming plenary session dates found")
    return schedule


# ── Scrape current-week sessions for time slots ───────────────────────────────

def fetch_current_week_sessions() -> dict[str, list[tuple[str, str]]]:
    """
    Returns {date_iso: [(time, session_title), ...]} from the seance-publique page.
    """
    try:
        r = requests.get(AN_SEANCE, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"   ⚠️  Could not fetch seance-publique page: {e}")
        return {}

    text = r.text
    result: dict[str, list[tuple[str, str]]] = {}

    # Find ICS links with dates (they're embedded in download buttons)
    ics_matches = re.findall(
        r"agendas/ics/(\d{4}-\d{2}-\d{2})/reunion/([A-Za-z0-9_]+)",
        text
    )

    # Find time+title pairs near ICS links
    # The page HTML has: <b>09h00</b> - Première séance publique
    time_title_matches = re.findall(
        r"<b>(\d{1,2}h\d{2})</b>\s*[-–]\s*([^<]{5,60})",
        text
    )

    # Also try to get the date for these sessions
    # The page header has the day name "Jeudi 4 juin 2026"
    date_header = re.search(
        rf"{_FR_DAY_NAMES}\s+(\d{{1,2}})\s*(?:er)?\s+([a-z]+)\s+(\d{{4}})",
        text, re.IGNORECASE
    )
    current_date = None
    if date_header:
        current_date = _parse_fr_date(date_header.group(1), date_header.group(2), date_header.group(3))

    if current_date and time_title_matches:
        result[current_date] = [
            (t.replace("h", ":"), title.strip())
            for t, title in time_title_matches
        ]

    return result


# ── Build schedule items ──────────────────────────────────────────────────────

def build_schedule_items(
    order_of_day: dict[str, list[str]],
    week_sessions: dict[str, list[tuple[str, str]]],
) -> list[dict]:
    """
    Only create entries for Tuesdays and Wednesdays with plenary sessions —
    those are QAG (Questions au Gouvernement) days where Attal, as opposition
    group president, regularly takes the floor.
    """
    items = []

    for ev_date, agenda_items in order_of_day.items():
        try:
            dow = date.fromisoformat(ev_date).weekday()  # 0=Mon … 6=Sun
        except ValueError:
            continue

        # Only Tuesdays (1) and Wednesdays (2) have QAG at 15h
        if dow not in (1, 2):
            continue

        day_label = "Mardi" if dow == 1 else "Mercredi"
        items.append({
            "person":      "Gabriel Attal",
            "event_date":  ev_date,
            "title":       f"📢 QAG – {day_label} de séance (Attal intervient régulièrement, 15h)",
            "location":    "Assemblée nationale, Paris",
            "description": AN_AUTO_TAG,
            "source_url":  "https://www.assemblee-nationale.fr/dyn/seance-publique",
        })

    return items


# ── Supabase operations ───────────────────────────────────────────────────────

def clear_future_an_entries():
    """Delete upcoming auto-synced AN entries before re-inserting fresh data."""
    today = date.today().isoformat()
    try:
        result = (
            db.table("schedule")
            .delete()
            .eq("person", "Gabriel Attal")
            .eq("description", AN_AUTO_TAG)
            .gte("event_date", today)
            .execute()
        )
        deleted = len(result.data) if result.data else 0
        print(f"   🗑️  Deleted {deleted} stale future AN_AUTO entries")
    except Exception as e:
        print(f"   ⚠️  Could not clear old entries: {e}")


def insert_schedule(items: list[dict]):
    inserted = 0
    for item in items:
        try:
            db.table("schedule").insert(item).execute()
            inserted += 1
        except Exception as e:
            print(f"   ⚠️  Insert error: {e}")
    print(f"   ✅ Inserted {inserted} / {len(items)} items")


# ── attalpresident.fr → schedule ─────────────────────────────────────────────

import json as _json

_MEDIA_KEYWORDS = re.compile(
    r"\b(?:RTL|TF1|France Inter|France 2|France 3|BFM|CNews|LCI|Europe 1|"
    r"Figaro|Monde|Libération|Journal du dimanche|JDD|LCP|Mediapart)\b",
    re.IGNORECASE,
)

_LOCATION_PATTERNS = [
    # "dans l'Ain", "dans le Var", "dans les Hauts-de-Seine"
    re.compile(r"\bdans\s+(?:l[ae']|les\s+)?([A-ZÀ-Ö][A-Za-zÀ-öù-ÿ\-\s]+?)(?:\.|,|$)", re.UNICODE),
    # "en Aveyron", "en Saône-et-Loire"
    re.compile(r"\ben\s+([A-ZÀ-Ö][A-Za-zÀ-öù-ÿ\-]+(?:\s+et\s+[A-ZÀ-Ö][A-Za-zÀ-öù-ÿ\-]+)?)(?:\.|,|\s)", re.UNICODE),
    # "à Paris", "à Bourg-en-Bresse"
    re.compile(r"\bà\s+([A-ZÀ-Ö][A-Za-zÀ-öù-ÿ\-]+(?:\s+[A-ZÀ-Ö][A-Za-zÀ-öù-ÿ\-]+)?)(?:\s|\.|,|$)", re.UNICODE),
    # "au lycée … d'Orléans"  → capture trailing city after de/d'
    re.compile(r"\bd[e']([A-ZÀ-Ö][A-Za-zÀ-öù-ÿ\-]+)(?:\s|\.|,|$)", re.UNICODE),
]


def _extract_location(headline: str, description: str) -> str:
    """Try to extract a location from headline then description."""
    for text in (headline, description[:200]):
        for pat in _LOCATION_PATTERNS:
            m = pat.search(text)
            if m:
                loc = m.group(1).strip().rstrip(".")
                if len(loc) > 2 and not any(w in loc.lower() for w in ("son", "ses", "sa", "la", "le")):
                    return loc
    return ""


def fetch_attal_officiel_schedule() -> list[dict]:
    """
    Scrape attalpresident.fr sitemap → extract schedule entries.
    Uses source_url for dedup (never re-inserts an existing article).
    """
    BASE = "https://attalpresident.fr"
    items = []

    # 1. Get sitemap
    try:
        sitemap = requests.get(f"{BASE}/sitemap.xml", headers=HEADERS, timeout=15).text
        urls = re.findall(
            r"<loc>(https://attalpresident\.fr/actualites/[^<]+)</loc>", sitemap
        )
    except Exception as e:
        print(f"   ⚠️  attalpresident.fr sitemap failed: {e}")
        return []

    # 2. Fetch existing source_urls to avoid duplicates
    try:
        existing = db.table("schedule") \
            .select("source_url") \
            .eq("person", "Gabriel Attal") \
            .ilike("source_url", "%attalpresident.fr%") \
            .execute().data or []
        existing_urls = {r["source_url"] for r in existing}
    except Exception as e:
        print(f"   ⚠️  Could not fetch existing entries: {e}")
        existing_urls = set()

    new_urls = [u for u in urls if u not in existing_urls]
    print(f"   attalpresident.fr: {len(urls)} articles, {len(new_urls)} new")

    if not new_urls:
        return []

    # 3. Fetch and parse each new article
    for url in new_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            text = r.text

            # Extract JSON-LD NewsArticle
            json_lds = re.findall(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                text, re.DOTALL
            )
            article = None
            for jld in json_lds:
                try:
                    data = _json.loads(jld)
                    objs = data if isinstance(data, list) else [data]
                    for obj in objs:
                        if obj.get("@type") in ("NewsArticle", "Article", "BlogPosting"):
                            article = obj
                            break
                except Exception:
                    pass
                if article:
                    break

            if not article:
                continue

            headline    = article.get("headline", "").strip().rstrip(".")
            description = article.get("description", "").strip()
            date_raw    = article.get("datePublished", "")

            try:
                ev_date = date.fromisoformat(date_raw[:10]).isoformat()
            except Exception:
                ev_date = date.today().isoformat()

            # Location: skip media appearances, extract for déplacements
            is_media = bool(_MEDIA_KEYWORDS.search(headline))
            location = "" if is_media else _extract_location(headline, description)

            items.append({
                "person":      "Gabriel Attal",
                "event_date":  ev_date,
                "title":       headline,
                "location":    location,
                "description": "attalpresident.fr · auto-sync",
                "source_url":  url,
            })

        except Exception as e:
            print(f"   ⚠️  Failed to parse {url}: {e}")

    return items


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🏛️  Fetching Assemblée nationale plenary calendar…")

    order_of_day  = fetch_order_of_day()
    week_sessions = fetch_current_week_sessions()

    if not order_of_day:
        print("⚠️  No AN session data retrieved.")
    else:
        items = build_schedule_items(order_of_day, week_sessions)
        print(f"   → {len(items)} QAG items built")
        if items:
            clear_future_an_entries()
            insert_schedule(items)

    print("\n📰  Fetching attalpresident.fr campaign articles…")
    officiel_items = fetch_attal_officiel_schedule()
    if officiel_items:
        insert_schedule(officiel_items)
        print("\n📅  New entries from attalpresident.fr:")
        for it in sorted(officiel_items, key=lambda x: x["event_date"], reverse=True)[:8]:
            loc = f"  📍 {it['location']}" if it["location"] else ""
            print(f"   {it['event_date']}  {it['title'][:60]}{loc}")
    else:
        print("   → No new articles to add")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
