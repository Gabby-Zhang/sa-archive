import streamlit as st
from utils.auth import admin_sidebar
from utils.database import get_supabase
from utils.media_spectrum import get_media_info, LEAN_EMOJI
from datetime import datetime, date, timedelta
import hashlib
import requests
import time

admin_sidebar()

st.title("📜 往期新闻")
st.caption("历史新闻存档 — 来自 GDELT 数据库及手动添加")

PERSON_COLOR = {
    "Gabriel Attal":      "#C9A84C",
    "Stéphane Séjourné":  "#4A90D9",
    "S&A":                "#FF6B9D",
}

# ── GDELT 导入函数（定义在前，调用在后）────────────────────────────
def _run_gdelt_import(person: str, start: date, end: date):
    """按月查询 GDELT，插入 news 表（category=historical）"""
    QUERIES = {
        "Gabriel Attal":     ["Gabriel Attal", "Attal Renaissance", "Attal présidentielle"],
        "Stéphane Séjourné": ["Stéphane Séjourné", "Séjourné Commission européenne", "Séjourné Renaissance"],
        "S&A":               ["Séjourné Attal"],
    }
    queries = QUERIES.get(person, [person])
    db = get_supabase()
    total_added = 0

    # 按月切片
    months = []
    cur = start.replace(day=1)
    while cur <= end:
        next_month = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        months.append((cur, min(next_month - timedelta(days=1), end)))
        cur = next_month

    progress = st.progress(0, text="准备中…")

    for idx, (m_start, m_end) in enumerate(months):
        progress.progress((idx + 1) / len(months), text=f"查询 {m_start.strftime('%Y-%m')}…")

        for q in queries:
            try:
                api_url = (
                    f"https://api.gdeltproject.org/api/v2/doc/doc"
                    f"?query={requests.utils.quote(q)}"
                    f"&mode=artlist&maxrecords=250"
                    f"&startdatetime={m_start.strftime('%Y%m%d')}000000"
                    f"&enddatetime={m_end.strftime('%Y%m%d')}235959"
                    f"&sourcelang=French&sourcecountry=France"
                    f"&format=json"
                )
                resp = requests.get(api_url, timeout=15)
                if not resp.ok:
                    continue
                articles = resp.json().get("articles", [])

                rows = []
                for a in articles:
                    art_url = a.get("url", "")
                    if not art_url:
                        continue
                    art_id = hashlib.md5(art_url.encode()).hexdigest()
                    title  = a.get("title", "").strip()
                    source = a.get("domain", "").replace("www.", "")
                    seen_date = a.get("seendate", "")
                    try:
                        pub_date = datetime.strptime(seen_date[:8], "%Y%m%d").strftime("%Y-%m-%d")
                    except Exception:
                        pub_date = m_start.strftime("%Y-%m-%d")

                    # 判断人物
                    title_l = title.lower()
                    has_s = "séjourné" in title_l or "sejourne" in title_l
                    has_a = "attal" in title_l
                    if has_s and has_a:
                        art_person = "S&A"
                    elif has_s:
                        art_person = "Stéphane Séjourné"
                    elif has_a:
                        art_person = "Gabriel Attal"
                    else:
                        art_person = person

                    rows.append({
                        "id":           art_id,
                        "title":        title,
                        "url":          art_url,
                        "source":       source,
                        "person":       art_person,
                        "published_at": pub_date,
                        "summary":      "",
                        "category":     "historical",
                    })

                if rows:
                    db.table("news").upsert(rows, on_conflict="id").execute()
                    total_added += len(rows)

                time.sleep(0.5)  # 避免请求过频

            except Exception as e:
                st.warning(f"查询失败 ({q} / {m_start.strftime('%Y-%m')}): {e}")

    progress.empty()
    st.cache_data.clear()
    st.success(f"✅ 导入完成！共处理 {total_added} 条记录（已自动去重）")
    st.rerun()


# ── 筛选栏 ───────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
with col1:
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    year_filter = st.selectbox("年份", ["全部", "2025", "2024", "2023", "2022", "2021", "2020"])
with col3:
    limit = st.selectbox("显示条数", [50, 100, 200], index=0)
with col4:
    keyword = st.text_input("🔍 搜索关键词", placeholder="输入关键词…")

# ── 加载数据 ─────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def get_historical_news(person=None, year=None, limit=50):
    try:
        db = get_supabase()
        query = (db.table("news")
                   .select("*")
                   .eq("category", "historical")
                   .order("published_at", desc=True)
                   .limit(limit))
        if person:
            query = query.eq("person", person)
        if year and year != "全部":
            query = query.gte("published_at", f"{year}-01-01").lte("published_at", f"{year}-12-31")
        return query.execute().data
    except Exception as e:
        st.error(f"加载失败：{e}")
        return []

news = get_historical_news(
    person=person_filter if person_filter != "全部" else None,
    year=year_filter if year_filter != "全部" else None,
    limit=limit,
)

if keyword:
    news = [n for n in news if keyword.lower() in n.get("title", "").lower()]

st.caption(f"共 {len(news)} 条历史新闻")

# ── 新闻列表 ─────────────────────────────────────────────────────
for item in news:
    color     = PERSON_COLOR.get(item.get("person", ""), "#888")
    url       = item.get("url", "")
    archive_url = f"https://www.removepaywall.com/{url}" if url else ""

    pub_date = item.get("published_at", "")
    if pub_date:
        try:
            pub_date = datetime.fromisoformat(pub_date).strftime("%Y-%m-%d")
        except Exception:
            pass

    media_info  = get_media_info(item.get("source", ""))
    lean_label  = media_info["label"]
    lean_color  = media_info["color"]
    lean_emoji  = LEAN_EMOJI.get(lean_label, "")

    st.markdown(f"""
    <div style="
        border-left: 4px solid {color};
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
        background: #16213e;
        border-radius: 0 8px 8px 0;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.4rem">
            <div>
                <span style="color:{color};font-size:0.8rem;font-weight:bold">
                    {item.get("person","")}
                </span>
                <span style="margin-left:0.8rem">
                    <span style="background:{lean_color};color:white;padding:0.05rem 0.4rem;
                          border-radius:3px;font-size:0.7rem;font-weight:bold">{lean_emoji} {lean_label}</span>
                    <span style="color:#888;font-size:0.8rem;margin-left:0.3rem">{item.get("source","")}</span>
                </span>
                <span style="color:#555;font-size:0.8rem;margin-left:0.8rem">{pub_date}</span>
            </div>
            <div style="display:flex;gap:1rem;font-size:0.85rem">
                {"<a href='" + url + "' target='_blank' style='color:#4A90D9'>🔗 原文</a>" if url else ""}
                {"<a href='" + archive_url + "' target='_blank' style='color:#888'>📦 存档版</a>" if url else ""}
            </div>
        </div>
        <div style="color:#e0e0e0;margin-top:0.4rem;font-size:0.95rem">
            {item.get("title","")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        item_id = item.get("id", "")
        if st.button("🗑️ 删除", key=f"del_hist_{item_id}"):
            get_supabase().table("news").delete().eq("id", item_id).execute()
            st.cache_data.clear()
            st.rerun()

if not news:
    st.info("暂无历史新闻。管理员登录后可在下方导入 GDELT 历史数据。")

st.divider()

# ── 管理员：GDELT 导入 ───────────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("📥 导入 GDELT 历史新闻", expanded=False):
        st.caption("""
        **GDELT** 是免费的全球新闻存档，收录法国各大媒体报道。
        选择人物和日期范围，每次按月查询，自动去重，不影响现有新闻页面。
        """)
        c1, c2, c3 = st.columns(3)
        with c1:
            import_person = st.selectbox("人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"], key="gdelt_person")
        with c2:
            import_start = st.date_input("开始日期", value=date(2024, 1, 1), key="gdelt_start")
        with c3:
            import_end = st.date_input("结束日期", value=date(2024, 12, 31), key="gdelt_end")

        if st.button("🔍 开始导入", use_container_width=True, type="primary"):
            _run_gdelt_import(import_person, import_start, import_end)
