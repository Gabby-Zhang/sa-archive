import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

@st.cache_resource
def get_supabase_admin() -> Client:
    """使用 Service Role Key，绕过 RLS，用于管理员写操作"""
    url = st.secrets["SUPABASE_URL"]
    # 优先用 service role key；若未配置则回退到普通 key
    key = st.secrets.get("SUPABASE_SERVICE_KEY", st.secrets["SUPABASE_KEY"])
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
    db = get_supabase_admin()
    return db.table("events").insert(data).execute()

def update_event(event_id: int, data: dict):
    db = get_supabase_admin()
    return db.table("events").update(data).eq("id", event_id).execute()

def delete_event(event_id: int):
    db = get_supabase_admin()
    return db.table("events").delete().eq("id", event_id).execute()

# ── 首页「上一次同框」置顶 ───────────────────────────────
# 复用 profile_items 作为站点级键值存储：person="S&A" / section="featured_moment" / key="event_id"。
# 人物档案页只查两位真人 + 四个已知 section，这条记录不会泄漏到其它页面，也无需改库结构。
_FEAT_FILTER = dict(person="S&A", section="featured_moment", key="event_id")

def get_featured_sa_event_id():
    """管理员置顶的「上一次同框」事件 id；未设置返回 None（首页回退到取最新 S&A 事件）。"""
    try:
        rows = (get_supabase().table("profile_items").select("value")
                .eq("person", "S&A").eq("section", "featured_moment")
                .eq("key", "event_id").limit(1).execute().data) or []
        if rows and str(rows[0].get("value") or "").strip():
            return int(rows[0]["value"])
    except Exception:
        pass
    return None

def set_featured_sa_event_id(event_id):
    """置顶某条 S&A 事件作为「上一次同框」；传 None 清除置顶（恢复自动取最新）。"""
    db = get_supabase_admin()
    existing = (db.table("profile_items").select("id")
                .eq("person", "S&A").eq("section", "featured_moment")
                .eq("key", "event_id").limit(1).execute().data) or []
    if event_id is None:
        if existing:
            db.table("profile_items").delete().eq("id", existing[0]["id"]).execute()
        return
    if existing:
        db.table("profile_items").update({"value": str(event_id)}) \
            .eq("id", existing[0]["id"]).execute()
    else:
        db.table("profile_items").insert({**_FEAT_FILTER, "value": str(event_id)}).execute()

# ── 新闻 ────────────────────────────────────────────────
def get_news(person=None, keyword=None, limit=50, offset=0):
    db = get_supabase()
    # range(start, end) 两端均包含，end = offset + limit（多取1条用于判断是否有下一页）
    query = db.table("news").select("*").order("published_at", desc=True).range(offset, offset + limit)
    if person and person not in ("全部", "All"):
        query = query.eq("person", person)
    if keyword:
        query = query.ilike("title", f"%{keyword}%")
    return query.execute().data

def upsert_news(items: list):
    db = get_supabase_admin()
    # 去重：同一批次内按 id 去重
    seen = {}
    for item in items:
        seen[item["id"]] = item
    unique_items = list(seen.values())
    return db.table("news").upsert(unique_items, on_conflict="id").execute()

def add_news_manual(data: dict):
    db = get_supabase_admin()
    return db.table("news").insert(data).execute()

def delete_news(news_id: str):
    db = get_supabase_admin()
    return db.table("news").delete().eq("id", news_id).execute()

# ── 文件上传记录 ─────────────────────────────────────────
def get_files(person=None):
    db = get_supabase()
    query = db.table("files").select("*").order("created_at", desc=True)
    if person and person != "全部":
        query = query.eq("person", person)
    return query.execute().data

def add_file(data: dict):
    db = get_supabase_admin()
    return db.table("files").insert(data).execute()

# ── Supabase Storage 上传 ────────────────────────────────
def upload_to_storage(bucket: str, filename: str, data: bytes, content_type: str) -> str:
    """上传文件到 Supabase Storage，返回公开 URL。
    使用前请在 Supabase 控制台创建对应 bucket（设为 public）。
    """
    import uuid as _uuid
    sb = get_supabase_admin()
    path = f"{_uuid.uuid4().hex[:8]}_{filename}"
    sb.storage.from_(bucket).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return sb.storage.from_(bucket).get_public_url(path)
