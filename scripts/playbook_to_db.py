#!/usr/bin/env python3
"""
Politico Paris Playbook → Supabase

Accepts structured JSON via stdin:
  {
    "schedule": [
      {
        "person": "Gabriel Attal",
        "event_date": "2026-06-08",
        "title": "Visite lycée François Villon à Beaugency",
        "location": "Beaugency, Loiret",
        "time": "10h00",          # optional
        "source_url": "https://www.politico.eu/newsletter/paris-playbook/..."
      }
    ],
    "news": [
      {
        "title": "Attal lance sa campagne présidentielle",
        "summary": "Gabriel Attal a tenu son premier meeting...",
        "person": "Gabriel Attal",      # or "Stéphane Séjourné" or "S&A"
        "published_at": "2026-06-08T05:05:00",
        "source_url": "https://www.politico.eu/newsletter/paris-playbook/..."
      }
    ],
    "email_date": "2026-06-08",   # ISO date of the email (for dedup tracking)
    "email_subject": "Retailleau sort le bâton du retour"
  }

Credentials: reads from .streamlit/secrets.toml first, then env vars.
"""
import os
import sys
import json
import hashlib
from datetime import datetime

# ── Credentials ──────────────────────────────────────────────────────────────
def _load_creds():
    # 1. Try .streamlit/secrets.toml (local dev + scheduled agent)
    import pathlib
    secrets_path = pathlib.Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import toml
            s = toml.load(str(secrets_path))
            url = s.get("SUPABASE_URL", "")
            key = s.get("SUPABASE_SERVICE_KEY") or s.get("SUPABASE_KEY", "")
            if url and key:
                return url, key
        except Exception as e:
            print(f"   ⚠️  Could not read secrets.toml: {e}", file=sys.stderr)

    # 2. Fall back to environment variables (GitHub Actions)
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url, key

    raise RuntimeError(
        "Supabase credentials not found. "
        "Create .streamlit/secrets.toml with SUPABASE_URL + SUPABASE_SERVICE_KEY, "
        "or set those as environment variables."
    )


SUPABASE_URL, SUPABASE_KEY = _load_creds()
from supabase import create_client
db = create_client(SUPABASE_URL, SUPABASE_KEY)

PLAYBOOK_SOURCE = "Paris Playbook · Politico"
PLAYBOOK_TAG    = "[PLAYBOOK]"


# ── Schedule insertion ────────────────────────────────────────────────────────
def insert_schedule(items: list[dict], email_subject: str) -> int:
    """Insert schedule entries, skip duplicates by (person + event_date + title prefix)."""
    if not items:
        return 0

    # Fetch existing source_url and (date+title) combos to avoid duplicates
    try:
        existing = (
            db.table("schedule")
            .select("event_date,title,source_url")
            .eq("person", "Gabriel Attal")
            .ilike("description", f"%{PLAYBOOK_TAG}%")
            .execute().data or []
        )
        existing_keys = {
            (r["event_date"], r["title"][:40].lower())
            for r in existing
        }
    except Exception as e:
        print(f"   ⚠️  Could not fetch existing schedule entries: {e}", file=sys.stderr)
        existing_keys = set()

    inserted = 0
    for item in items:
        key = (item.get("event_date",""), item.get("title","")[:40].lower())
        if key in existing_keys:
            print(f"   ↩️  Skip (already exists): {item.get('event_date')} · {item.get('title','')[:50]}")
            continue

        time_str = f" · {item['time']}" if item.get("time") else ""
        row = {
            "person":      item.get("person", "Gabriel Attal"),
            "event_date":  item["event_date"],
            "title":       item["title"],
            "location":    item.get("location", ""),
            "description": f"{PLAYBOOK_TAG} {email_subject or ''}".strip(),
            "source_url":  item.get("source_url", "https://www.politico.eu/newsletter/paris-playbook/"),
        }
        try:
            db.table("schedule").insert(row).execute()
            inserted += 1
            existing_keys.add(key)
            print(f"   ✅ Schedule: {row['event_date']} · {row['title'][:60]}")
        except Exception as e:
            print(f"   ⚠️  Insert schedule error: {e}", file=sys.stderr)

    return inserted


# ── News insertion ────────────────────────────────────────────────────────────
def insert_news(items: list[dict]) -> int:
    """Insert news items, dedup by URL hash."""
    if not items:
        return 0

    inserted = 0
    for item in items:
        url = item.get("source_url", "")
        # Use url+title hash as unique ID
        uid = hashlib.md5((url + item.get("title","")).encode()).hexdigest()

        row = {
            "id":           uid,
            "title":        item["title"],
            "url":          url,
            "source":       PLAYBOOK_SOURCE,
            "person":       item.get("person", "Gabriel Attal"),
            "published_at": item.get("published_at", datetime.now().isoformat()),
            "summary":      item.get("summary", "")[:500],
        }
        try:
            db.table("news").upsert(row, on_conflict="id").execute()
            inserted += 1
            print(f"   ✅ News: {row['title'][:70]}")
        except Exception as e:
            print(f"   ⚠️  Upsert news error: {e}", file=sys.stderr)

    return inserted


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("No input received via stdin.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    email_subject = data.get("email_subject", "")
    schedule_items = data.get("schedule", [])
    news_items     = data.get("news", [])

    print(f"\n📰  Paris Playbook: {email_subject}")
    print(f"   📅 {len(schedule_items)} schedule entries · 📰 {len(news_items)} news items")

    s_count = insert_schedule(schedule_items, email_subject)
    n_count = insert_news(news_items)

    print(f"\n✅ Done — inserted {s_count} schedule + {n_count} news items.")


if __name__ == "__main__":
    main()
