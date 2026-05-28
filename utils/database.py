import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ── 大事记 ──────────────────────────────────────────────
def get_events(person=None, keyword=None):
    db = get_supabase()
    query = db.table("events").select("*").order("date", desc=True)
    if person and person != "全部":
        query = query.eq("person", person)
    if keyword:
        query = query.ilike("title", f"%{keyword}%")
    return query.execute().data

def add_event(data: dict):
    db = get_supabase()
    return db.table("events").insert(data).execute()

def delete_event(event_id: int):
    db = get_supabase()
    return db.table("events").delete().eq("id", event_id).execute()

# ── 新闻 ────────────────────────────────────────────────
def get_news(person=None, keyword=None, limit=50):
    db = get_supabase()
    query = db.table("news").select("*").order("published_at", desc=True).limit(limit)
    if person and person != "全部":
        query = query.eq("person", person)
    if keyword:
        query = query.ilike("title", f"%{keyword}%")
    return query.execute().data

def upsert_news(items: list):
    db = get_supabase()
    return db.table("news").upsert(items, on_conflict="url").execute()

def add_news_manual(data: dict):
    db = get_supabase()
    return db.table("news").insert(data).execute()

# ── 文件上传记录 ─────────────────────────────────────────
def get_files(person=None):
    db = get_supabase()
    query = db.table("files").select("*").order("created_at", desc=True)
    if person and person != "全部":
        query = query.eq("person", person)
    return query.execute().data

def add_file(data: dict):
    db = get_supabase()
    return db.table("files").insert(data).execute()
