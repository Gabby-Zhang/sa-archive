import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase
from utils.media_spectrum import get_media_info, LEAN_EMOJI
from datetime import datetime, date, timedelta
import hashlib
import requests
import time

admin_sidebar()

st.title(t("archives_title"))
st.caption(t("archives_caption"))

PERSON_COLOR = {
    "Gabriel Attal":      "#C9A84C",
    "Stéphane Séjourné":  "#4A90D9",
    "S&A":                "#FF6B9D",
}

# ── 媒体过滤规则 ──────────────────────────────────────────────────
# 法语媒体：所有 .fr 域名自动通过
# 英语媒体：只保留以下主流国际媒体
MAJOR_ENGLISH_DOMAINS = {
    'bbc.com', 'bbc.co.uk', 'theguardian.com', 'reuters.com',
    'apnews.com', 'nytimes.com', 'politico.eu', 'politico.com',
    'ft.com', 'economist.com', 'france24.com', 'euronews.com',
    'bloomberg.com', 'washingtonpost.com', 'npr.org',
    'theatlantic.com', 'foreignpolicy.com', 'independant.co.uk',
}

def _is_allowed_source(domain: str) -> bool:
    """法语媒体全部通过；英语媒体只保留主流大媒体"""
    d = domain.lower().replace("www.", "")
    if d.endswith(".fr"):
        return True
    return d in MAJOR_ENGLISH_DOMAINS

def _norm_title(title: str) -> str:
    """标准化标题用于去重（取前8个词排序）"""
    words = sorted(title.lower().split()[:8])
    return " ".join(words)


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
                # 同时查询法语和英语来源
                rows = []
                seen_titles = {}   # 用于本批次去重

                for lang, country in [("French", "France"), ("English", "")]:
                    country_param = f"&sourcecountry={country}" if country else ""
                    api_url = (
                        f"https://api.gdeltproject.org/api/v2/doc/doc"
                        f"?query={requests.utils.quote(q)}"
                        f"&mode=artlist&maxrecords=250"
                        f"&startdatetime={m_start.strftime('%Y%m%d')}000000"
                        f"&enddatetime={m_end.strftime('%Y%m%d')}235959"
                        f"&sourcelang={lang}{country_param}"
                        f"&format=json"
                    )
                    resp = requests.get(api_url, timeout=15)
                    if not resp.ok:
                        continue
                    articles = resp.json().get("articles", [])

                    for a in articles:
                        art_url = a.get("url", "")
                        if not art_url:
                            continue
                        source = a.get("domain", "").replace("www.", "")

                        # ── 媒体过滤：只保留法语媒体或英语主流大媒体 ──
                        if not _is_allowed_source(source):
                            continue

                        art_id = hashlib.md5(art_url.encode()).hexdigest()
                        title  = a.get("title", "").strip()
                        if not title:
                            continue

                        # ── 批次内去重：同一条新闻只保留最先出现的那条 ──
                        norm = _norm_title(title)
                        if norm in seen_titles:
                            continue
                        seen_titles[norm] = True

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

                    time.sleep(0.3)

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
    person_filter = st.selectbox(t("person_label"), [t("all"), "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    year_filter = st.selectbox(t("year_label"), [t("all"), "2025", "2024", "2023", "2022", "2021", "2020"])
with col3:
    limit = st.selectbox(t("show_count"), [50, 100, 200], index=0)
with col4:
    keyword = st.text_input(t("search_label"), placeholder=t("search_ph"))

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
        if year and year not in ("全部", "All"):
            query = query.gte("published_at", f"{year}-01-01").lte("published_at", f"{year}-12-31")
        return query.execute().data
    except Exception as e:
        st.error(f"加载失败：{e}")
        return []

news = get_historical_news(
    person=person_filter if person_filter not in ("全部", "All") else None,
    year=year_filter if year_filter not in ("全部", "All") else None,
    limit=limit,
)

if keyword:
    news = [n for n in news if keyword.lower() in n.get("title", "").lower()]

# ── 按标题聚合相似新闻 ───────────────────────────────────────────
from collections import defaultdict

def _source_priority(item):
    """法语媒体优先，其次英语主流媒体"""
    s = item.get("source", "")
    if s.endswith(".fr"):         return 0
    if s in MAJOR_ENGLISH_DOMAINS: return 1
    return 2

groups = defaultdict(list)
for item in news:
    key = _norm_title(item.get("title", ""))
    groups[key].append(item)

# 每组按来源质量排序，主条目取第一个
clustered = []
for key, items in groups.items():
    items.sort(key=_source_priority)
    clustered.append(items)

# 按主条目日期倒序排列
clustered.sort(key=lambda g: g[0].get("published_at", ""), reverse=True)

st.caption(f"共 {len(clustered)} 条新闻（含 {len(news)} 篇报道）")

# ── 新闻列表 ─────────────────────────────────────────────────────
import html as _html

for group in clustered:
    item = group[0]   # 主条目（来源最优）
    others = group[1:]

    color     = PERSON_COLOR.get(item.get("person", ""), "#888")
    url       = item.get("url", "") or ""
    # 若 DB 里存的已经是 removepaywall 链接，提取真实 URL
    if "removepaywall.com/" in url:
        url = url.split("removepaywall.com/", 1)[-1]
    archive_ph_url  = f"https://archive.ph/newest/{url}" if url else ""
    archive_rpw_url = f"https://www.removepaywall.com/{url}" if url else ""
    safe_title   = _html.escape(item.get("title",  "") or "")
    safe_source  = _html.escape(item.get("source", "") or "")
    safe_person  = _html.escape(item.get("person", "") or "")
    safe_url     = _html.escape(url)
    safe_arch_ph  = _html.escape(archive_ph_url)
    safe_archive  = _html.escape(archive_rpw_url)

    pub_date = item.get("published_at", "")
    if pub_date:
        try:
            pub_date = datetime.fromisoformat(pub_date).strftime("%Y-%m-%d")
        except Exception:
            pass

    media_info = get_media_info(item.get("source", ""))
    lean_label = media_info["label"]
    lean_color = media_info["color"]
    lean_emoji = LEAN_EMOJI.get(lean_label, "")

    # 多来源标记
    multi_badge = (f'<span style="background:var(--bd);color:var(--t2);padding:0.05rem 0.4rem;'
                   f'border-radius:3px;font-size:0.7rem;margin-left:0.5rem">'
                   f'📎 {len(others)+1} 家媒体</span>') if others else ""

    _link_orig    = f'<a href="{safe_url}" target="_blank" style="color:#4A90D9">{t("news_original")}</a>' if url else ""
    _link_arch_ph = f'<a href="{safe_arch_ph}" target="_blank" style="color:#7EC8A4">{t("news_archive_ph")}</a>' if url else ""
    _link_archive = f'<a href="{safe_archive}" target="_blank" style="color:#888">{t("news_archived")}</a>' if url else ""
    _card = (
        f'<div style="border-left:4px solid {color};padding:0.8rem 1.2rem;margin:0.5rem 0;background:var(--cb);border-radius:0 8px 8px 0">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.4rem">'
        f'<div>'
        f'<span style="color:{color};font-size:0.8rem;font-weight:bold">{safe_person}</span>'
        f'<span style="margin-left:0.8rem">'
        f'<span style="background:{lean_color};color:white;padding:0.05rem 0.4rem;border-radius:3px;font-size:0.7rem;font-weight:bold">{lean_emoji} {lean_label}</span>'
        f'<span style="color:#888;font-size:0.8rem;margin-left:0.3rem">{safe_source}</span>'
        f'</span>'
        f'<span style="color:#555;font-size:0.8rem;margin-left:0.8rem">{pub_date}</span>'
        f'{multi_badge}'
        f'</div>'
        f'<div style="display:flex;gap:1rem;font-size:0.85rem">{_link_orig}{_link_arch_ph}{_link_archive}</div>'
        f'</div>'
        f'<div style="color:var(--t1);margin-top:0.4rem;font-size:0.95rem">{safe_title}</div>'
        f'</div>'
    )
    st.markdown(_card, unsafe_allow_html=True)

    # 折叠显示其他来源
    if others:
        with st.expander(f"查看另外 {len(others)} 家媒体的报道"):
            for o in others:
                o_url = o.get("url", "") or ""
                if "removepaywall.com/" in o_url:
                    o_url = o_url.split("removepaywall.com/", 1)[-1]
                o_mi  = get_media_info(o.get("source", ""))
                o_emoji = LEAN_EMOJI.get(o_mi["label"], "")
                o_label = o_mi["label"]
                o_color = o_mi["color"]
                st.markdown(
                    f'<span style="background:{o_color};color:white;padding:0.05rem 0.35rem;'
                    f'border-radius:3px;font-size:0.7rem">{o_emoji} {o_label}</span> '
                    f'<span style="color:#aaa;font-size:0.85rem">{o.get("source","")}</span>'
                    f'{"  <a href=\'" + o_url + "\' target=\'_blank\' style=\'color:#4A90D9;font-size:0.85rem\'>🔗 原文</a>" if o_url else ""}',
                    unsafe_allow_html=True
                )

    if st.session_state.get("is_admin"):
        item_id = item.get("id", "")
        _, _bd = st.columns([11, 1])
        with _bd:
            if st.button("🗑️", key=f"del_hist_{item_id}",
                         help="删除此条新闻", use_container_width=True):
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
