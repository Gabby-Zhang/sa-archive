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

# ── 操作审计日志 ─────────────────────────────────────────
def log_audit(action: str, table_name: str, record_id=None, detail: str = None):
    """记录一次管理员写操作。操作人从当前会话取（admin_sidebar 登录时写入）。

    永远不抛异常：日志写失败也绝不能拖垮正常的增删改操作。
    在每个写库点调用一次，action 用 insert/update/delete。
    """
    try:
        get_supabase_admin().table("audit_log").insert({
            "admin_name": st.session_state.get("admin_name") or "未知",
            "admin_role": st.session_state.get("admin_role") or "",
            "action": action,
            "table_name": table_name,
            "record_id": None if record_id is None else str(record_id),
            "detail": (detail or "")[:200],
        }).execute()
    except Exception:
        pass

def get_audit_log(limit=200):
    """读取最近的操作记录（供最终管理员的「操作记录」页用）。"""
    try:
        return (get_supabase_admin().table("audit_log").select("*")
                .order("created_at", desc=True).limit(limit).execute().data) or []
    except Exception:
        return []

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
    res = db.table("events").insert(data).execute()
    new_id = (res.data[0].get("id") if res.data else None)
    log_audit("insert", "events", new_id, data.get("title"))
    return res

def update_event(event_id: int, data: dict):
    db = get_supabase_admin()
    res = db.table("events").update(data).eq("id", event_id).execute()
    log_audit("update", "events", event_id, data.get("title"))
    return res

def delete_event(event_id: int):
    db = get_supabase_admin()
    res = db.table("events").delete().eq("id", event_id).execute()
    log_audit("delete", "events", event_id)
    return res

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
        log_audit("update", "profile_items", "featured_moment", "清除「上一次同框」置顶")
        return
    if existing:
        db.table("profile_items").update({"value": str(event_id)}) \
            .eq("id", existing[0]["id"]).execute()
    else:
        db.table("profile_items").insert({**_FEAT_FILTER, "value": str(event_id)}).execute()
    log_audit("update", "profile_items", "featured_moment", f"置顶「上一次同框」为事件 {event_id}")

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
    res = db.table("news").insert(data).execute()
    new_id = (res.data[0].get("id") if res.data else None)
    log_audit("insert", "news", new_id, data.get("title"))
    return res

def delete_news(news_id: str):
    db = get_supabase_admin()
    res = db.table("news").delete().eq("id", news_id).execute()
    log_audit("delete", "news", news_id)
    return res

# ── 文件上传记录 ─────────────────────────────────────────
def get_files(person=None):
    db = get_supabase()
    query = db.table("files").select("*").order("created_at", desc=True)
    if person and person != "全部":
        query = query.eq("person", person)
    return query.execute().data

def add_file(data: dict):
    db = get_supabase_admin()
    res = db.table("files").insert(data).execute()
    new_id = (res.data[0].get("id") if res.data else None)
    log_audit("insert", "files", new_id, data.get("title") or data.get("filename"))
    return res

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
