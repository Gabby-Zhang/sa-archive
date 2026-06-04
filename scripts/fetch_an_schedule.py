#!/usr/bin/env python3
"""
Fetch the Assemblée nationale plenary session calendar for Gabriel Attal.

Sources:
  - https://www.assemblee-nationale.fr/dyn/seance-publique/textes-inscrits-ordre-du-jour
    (multi-week order of the day: dates + legislative agenda items)
  - https://www.assemblee-nationale.fr/dyn/seance-publique
    (current week sessions with exact times)

Dedup strategy:
  - All auto-synced entries carry description "[AN_AUTO]"
  - On each run: delete future [AN_AUTO] entries, then re-insert fresh data
  - Past entries are preserved as historical record

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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🏛️  Fetching Assemblée nationale plenary calendar…")

    order_of_day  = fetch_order_of_day()
    week_sessions = fetch_current_week_sessions()

    if not order_of_day:
        print("⚠️  No session data retrieved. Exiting.")
        return

    items = build_schedule_items(order_of_day, week_sessions)
    print(f"   → {len(items)} schedule items built")

    if not items:
        print("⚠️  Nothing to insert.")
        return

    clear_future_an_entries()
    insert_schedule(items)

    print("\n📅 Summary:")
    for it in sorted(items, key=lambda x: x["event_date"])[:8]:
        print(f"   {it['event_date']}  {it['title'][:70]}")
    if len(items) > 8:
        print(f"   … and {len(items) - 8} more")

    print("✅ Done.")


if __name__ == "__main__":
    main()
