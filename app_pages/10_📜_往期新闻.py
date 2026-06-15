import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase, get_supabase_admin, log_audit, add_event
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

# ── 收入大事记：把一条往期新闻预填进表单，管理员译成中文后存入 events ──────────────
# 与新闻页 / 行程日历一致：标题多为法语/英语原文，弹窗预填后由管理员手动译成中文再保存。
_IMPORT_TAG_OPTIONS = ["📰 新闻报道", "📣 重大宣布", "⭐ 重要行程/事件", "🗓️ 日常行程",
                       "📅 大事记", "🎙️ 采访", "📋 官方声明", "⚪ 其他"]
_IMPORT_PERSON_OPTIONS = ["Gabriel Attal", "Stéphane Séjourné", "S&A"]


def _event_dup_count(source_url: str) -> int:
    """events 表里同来源链接的条目数，用于重复提示（无链接时返回 0）。"""
    if not source_url:
        return 0
    try:
        rows = (get_supabase_admin().table("events").select("id")
                .eq("source_url", source_url).execute().data) or []
        return len(rows)
    except Exception:
        return 0


@st.dialog("📌 收入大事记")
def _import_news_to_timeline(entry: dict):
    """弹窗：把往期新闻条目预填进表单，管理员译成中文后存入大事记。"""
    st.caption("新闻标题多为法语/英语，请把标题译成中文后再保存。")
    dup = _event_dup_count(entry.get("source_url", ""))
    if dup:
        st.warning(f"大事记里已有 {dup} 条相同来源链接的记录，重复保存会产生多条。")

    try:
        _default_date = date.fromisoformat(str(entry.get("date", ""))[:10])
    except ValueError:
        _default_date = date.today()
    _p    = entry.get("person", "")
    _pidx = _IMPORT_PERSON_OPTIONS.index(_p) if _p in _IMPORT_PERSON_OPTIONS else 0

    with st.form("import_hist_to_timeline_form"):
        i_title = st.text_input("标题（译成中文）*", value=entry.get("title", ""))
        ic1, ic2 = st.columns(2)
        with ic1:
            i_date   = st.date_input("日期", value=_default_date)
            i_person = st.selectbox("人物", _IMPORT_PERSON_OPTIONS, index=_pidx,
                                    help="两人同框选 S&A")
        with ic2:
            i_tag = st.selectbox("类型标签", _IMPORT_TAG_OPTIONS)
            i_src = st.text_input("来源链接（可选）", value=entry.get("source_url", "") or "")
        i_source = st.text_input("来源媒体（可选）", value=entry.get("source", "") or "")
        i_note   = st.text_area("内容摘要（可选）", value=entry.get("note", "") or "", height=68)
        if st.form_submit_button("✅ 保存到大事记", use_container_width=True):
            if not i_title.strip():
                st.warning("请先填写中文标题")
            else:
                try:
                    # add_event 内部已写审计日志，这里不再重复记录
                    add_event({
                        "date":       str(i_date),
                        "person":     i_person,
                        "title":      i_title.strip(),
                        "source":     i_source.strip(),
                        "source_url": i_src or "",
                        "note":       i_note.strip(),
                        "tag":        i_tag,
                    })
                    st.cache_data.clear()
                    st.success("✅ 已收入大事记")
                    st.rerun()
                except Exception as _e:
                    st.error(f"保存失败：{_e}")

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
    """按月查询 GDELT，插入 news 表（category=historical）

    关键约束：GDELT DOC API 要求请求间隔 ≥5 秒，违规直接 429。
    且 sourcelang / sourcecountry 必须作为算子内联进 query（`sourcecountry:FR`），
    当成 &sourcelang= URL 参数传会被无视、拉回全球噪音而非法国媒体。
    每个月分两轮查：① sourcecountry:FR 捞法国本土媒体（不再按域名二次过滤，信任 GDELT 国别标签）；
    ② sourcelang:english 捞英语报道，仅保留 MAJOR_ENGLISH_DOMAINS 白名单。
    """
    QUERIES = {
        "Gabriel Attal":     ["Gabriel Attal", "Attal Renaissance", "Attal présidentielle"],
        "Stéphane Séjourné": ["Stéphane Séjourné", "Séjourné Commission européenne", "Séjourné Renaissance"],
        "S&A":               ["Séjourné Attal"],
    }
    queries = QUERIES.get(person, [person])
    db = get_supabase()
    total_added = 0
    rate_limited = 0   # 429 次数
    failed = 0         # 其它失败次数

    # 按月切片
    months = []
    cur = start.replace(day=1)
    while cur <= end:
        next_month = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        months.append((cur, min(next_month - timedelta(days=1), end)))
        cur = next_month

    # ── GDELT 限流：所有请求统一节流到 ≥5.5s 一次 ──
    GDELT_MIN_GAP = 5.5
    _last = [0.0]
    def gdelt_get(full_query, m_start, m_end):
        wait = GDELT_MIN_GAP - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        api_url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={requests.utils.quote(full_query)}"
            f"&mode=artlist&maxrecords=250"
            f"&startdatetime={m_start.strftime('%Y%m%d')}000000"
            f"&enddatetime={m_end.strftime('%Y%m%d')}235959"
            f"&format=json"
        )
        _last[0] = time.time()
        return requests.get(api_url, timeout=25)

    # 两轮抓取：法国本土（信任国别标签）+ 英语主流（按白名单过滤）
    PASSES = [
        ("sourcecountry:FR", "法语", False),
        ("sourcelang:english", "英语主流", True),
    ]
    total_calls = len(months) * len(queries) * len(PASSES)
    done = 0
    progress = st.progress(0, text="准备中…")

    for m_start, m_end in months:
        for q in queries:
            rows = []
            seen_titles = {}   # 本查询去重（跨两轮）

            for operator, pass_label, domain_filter in PASSES:
                done += 1
                progress.progress(done / total_calls,
                                  text=f"查询 {m_start.strftime('%Y-%m')} · {q} · {pass_label}")
                try:
                    resp = gdelt_get(f"{q} {operator}", m_start, m_end)
                except Exception:
                    failed += 1
                    continue
                if resp.status_code == 429:
                    rate_limited += 1
                    continue
                if not resp.ok:
                    failed += 1
                    continue
                try:
                    articles = resp.json().get("articles", [])
                except Exception:
                    failed += 1
                    continue

                for a in articles:
                    art_url = a.get("url", "")
                    if not art_url:
                        continue
                    source = a.get("domain", "").replace("www.", "")

                    # 英语轮只保留白名单大媒体；法国本土轮信任 GDELT 国别标签，不再过滤
                    if domain_filter and not _is_allowed_source(source):
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

            if rows:
                try:
                    db.table("news").upsert(rows, on_conflict="id").execute()
                    log_audit("insert", "news", None, f"GDELT 导入 {len(rows)} 条（{q}）")
                    total_added += len(rows)
                except Exception as e:
                    failed += 1
                    st.warning(f"入库失败 ({q} / {m_start.strftime('%Y-%m')}): {e}")

    progress.empty()
    st.cache_data.clear()
    st.success(f"✅ 导入完成！共处理 {total_added} 条记录（已自动去重）")
    if rate_limited or failed:
        st.warning(f"⚠️ 期间 {rate_limited} 次被 GDELT 限流（429）、{failed} 次其它失败——"
                   f"这些时间段没抓全，可稍后重跑相同范围补齐（已入库的会自动去重）。")
    st.rerun()


def _run_google_import(person: str, start: date, end: date):
    """按月用 Google News（after:/before: 日期算子）回填历史新闻，插入 news 表（category=historical）。

    与每日新闻同一套 Google 抓取逻辑，hl=fr&gl=FR → 主要出法语报道，限流远比 GDELT 宽松。
    id 取 url 的 md5、幂等可重跑补齐。
    """
    from utils.news_fetcher import collect_historical_google
    db = get_supabase()
    total_added = 0
    failed = 0

    # 按月切片
    months = []
    cur = start.replace(day=1)
    while cur <= end:
        next_month = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        months.append((cur, min(next_month - timedelta(days=1), end)))
        cur = next_month

    progress = st.progress(0, text="准备中…")
    for idx, (m_start, m_end) in enumerate(months):
        progress.progress((idx + 1) / len(months),
                          text=f"Google 查询 {m_start.strftime('%Y-%m')}…")
        after  = m_start.strftime("%Y-%m-%d")
        before = (m_end + timedelta(days=1)).strftime("%Y-%m-%d")   # before 排他，+1 天覆盖整月
        try:
            rows = collect_historical_google(person, after, before)
        except Exception as e:
            failed += 1
            st.warning(f"查询失败（{person} / {m_start.strftime('%Y-%m')}）：{e}")
            continue
        if rows:
            try:
                db.table("news").upsert(rows, on_conflict="id").execute()
                log_audit("insert", "news", None, f"Google 历史导入 {len(rows)} 条（{person} {after}）")
                total_added += len(rows)
            except Exception as e:
                failed += 1
                st.warning(f"入库失败（{m_start.strftime('%Y-%m')}）：{e}")
        time.sleep(1)   # Google 限流宽松，礼貌性间隔

    progress.empty()
    st.cache_data.clear()
    st.success(f"✅ Google 导入完成！共处理 {total_added} 条记录（已自动去重）")
    if failed:
        st.warning(f"⚠️ 期间 {failed} 个月份失败，可相同范围重跑补齐（已入库的会自动去重）。")
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
    archive_ph_url  = f"https://archive.ph/{url}" if url else ""
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
                _o_link = (f'  <a href="{o_url}" target="_blank" '
                           f'style="color:#4A90D9;font-size:0.85rem">🔗 原文</a>') if o_url else ""
                st.markdown(
                    f'<span style="background:{o_color};color:white;padding:0.05rem 0.35rem;'
                    f'border-radius:3px;font-size:0.7rem">{o_emoji} {o_label}</span> '
                    f'<span style="color:#aaa;font-size:0.85rem">{o.get("source","")}</span>'
                    f'{_o_link}',
                    unsafe_allow_html=True
                )

    if st.session_state.get("is_admin"):
        item_id = item.get("id", "")

        # ── 关联到已有大事记的搜索 UI ────────────────────────
        if st.session_state.get(f"linking_{item_id}"):
            st.markdown(
                '<div style="background:var(--cb2);border:1px solid var(--bd);'
                'border-radius:6px;padding:0.6rem 1rem;margin:0.3rem 0">'
                '<span style="color:#8B6FD4;font-size:0.8rem;font-weight:bold">'
                '📅 选择要关联的大事记条目</span></div>',
                unsafe_allow_html=True
            )
            search_q = st.text_input(
                "搜索大事记标题关键词",
                key=f"ev_search_{item_id}",
                placeholder="输入关键词搜索…",
            )
            try:
                _db = get_supabase()
                _q  = _db.table("events").select("id,title,date,person")
                if search_q:
                    _q = _q.ilike("title", f"%{search_q}%")
                _ev_rows = _q.order("date", desc=True).limit(20).execute().data
            except Exception:
                _ev_rows = []

            if _ev_rows:
                _ev_map = {
                    f"{str(e.get('date',''))[:10]}  ·  {e.get('person','')}  ·  {(e.get('title','') or '')[:45]}": e
                    for e in _ev_rows
                }
                _sel_label = st.selectbox("选择条目", list(_ev_map.keys()), key=f"ev_sel_{item_id}")
                _sel_ev    = _ev_map.get(_sel_label)
                lc1, lc2 = st.columns(2)
                with lc1:
                    if st.button("✅ 确认关联", key=f"do_link_{item_id}", use_container_width=True):
                        if _sel_ev:
                            try:
                                get_supabase_admin().table("event_links").insert({
                                    "event_id": _sel_ev["id"],
                                    "title":    item.get("title", ""),
                                    "url":      url,
                                    "type":     "📰 新闻报道",
                                    "source":   item.get("source", ""),
                                }).execute()
                                log_audit("insert", "event_links", _sel_ev["id"], f"关联往期新闻：{(item.get('title') or '')[:40]}")
                                st.session_state.pop(f"linking_{item_id}", None)
                                st.success(f"✅ 已关联到「{(_sel_ev.get('title','') or '')[:30]}…」")
                                st.rerun()
                            except Exception as _e:
                                st.error(f"关联失败：{_e}")
                with lc2:
                    if st.button("✕ 取消", key=f"cancel_link_{item_id}", use_container_width=True):
                        st.session_state.pop(f"linking_{item_id}", None)
                        st.rerun()
            else:
                st.info("未找到匹配的大事记")
                if st.button("✕ 取消", key=f"cancel_link2_{item_id}"):
                    st.session_state.pop(f"linking_{item_id}", None)
                    st.rerun()

        else:
            # ── 正常按钮行（纯 emoji，避免中文字号不一致）──────
            _, bca, bcb, bcc = st.columns([7, 1, 1, 1])
            with bca:
                if st.button("📌", key=f"pin_hist_{item_id}",
                             help="收入大事记（可改标题/翻译）", use_container_width=True):
                    _import_news_to_timeline({
                        "title":      item.get("title", ""),
                        "date":       pub_date,
                        "person":     item.get("person", ""),
                        "source":     item.get("source", ""),
                        "source_url": url,
                        "note":       item.get("summary", "") or "",
                    })
            with bcb:
                if st.button("🔗", key=f"link_hist_{item_id}",
                             help="关联已有大事记", use_container_width=True):
                    st.session_state[f"linking_{item_id}"] = True
                    st.rerun()
            with bcc:
                if st.button("🗑️", key=f"del_hist_{item_id}",
                             help="删除此条新闻", use_container_width=True):
                    get_supabase_admin().table("news").delete().eq("id", item_id).execute()
                    log_audit("delete", "news", item_id, item.get("title"))
                    st.cache_data.clear()
                    st.rerun()

if not news:
    st.info("暂无历史新闻。管理员登录后可在下方导入 GDELT 历史数据。")

st.divider()

# ── 管理员：Google News 导入（首选，主要出法语）────────────────────
if st.session_state.get("is_admin"):
    with st.expander("📥 从 Google News 导入历史新闻（法语，推荐）", expanded=False):
        st.caption("""
        与每日新闻同一套 **Google News** 抓取（`hl=fr&gl=FR`）→ **主要返回法语报道**，限流远比 GDELT 宽松。
        按月用日期算子（`after:`/`before:`）查询，自动去重、幂等可重跑补齐，不影响当期新闻页。
        每月上限约 100 条，热点月可能抓不全，重跑或缩小范围即可补。
        """)
        g1, g2, g3 = st.columns(3)
        with g1:
            g_person = st.selectbox("人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"], key="goog_person")
        with g2:
            g_start = st.date_input("开始日期", value=date(2024, 1, 1), key="goog_start")
        with g3:
            g_end = st.date_input("结束日期", value=date(2024, 12, 31), key="goog_end")

        if st.button("🔍 用 Google 导入", use_container_width=True, type="primary"):
            _run_google_import(g_person, g_start, g_end)

# ── 管理员：GDELT 导入（备选）─────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("📥 导入 GDELT 历史新闻（备选）", expanded=False):
        st.caption("""
        **GDELT** 是免费的全球新闻存档，收录法国各大媒体报道。
        选择人物和日期范围，按月分两轮查询（法国本土 + 英语主流），自动去重，不影响现有新闻页面。
        ⏳ GDELT 限流严格（每请求间隔 ≥5 秒），跨多个月份会耗时几分钟，请保持页面打开等进度条走完；
        若结尾提示有「限流/失败」，稍后用相同范围重跑即可补齐。
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

# ── 管理员：清空往期新闻数据 ───────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("🗑️ 清空往期新闻数据", expanded=False):
        st.caption("删除所有 `category='historical'` 的记录（**不影响当期新闻**），用于重导前清掉旧数据。此操作不可撤销。")
        c_person = st.selectbox(
            "清空范围", ["全部历史新闻", "Gabriel Attal", "Stéphane Séjourné", "S&A"], key="wipe_person")
        confirm = st.checkbox("我确认要删除（不可恢复）", key="wipe_confirm")
        if st.button("🗑️ 执行清空", use_container_width=True, disabled=not confirm):
            try:
                q = get_supabase_admin().table("news").delete().eq("category", "historical")
                if c_person != "全部历史新闻":
                    q = q.eq("person", c_person)
                deleted = q.execute().data or []
                log_audit("delete", "news", None, f"清空往期新闻：{c_person}，共 {len(deleted)} 条")
                st.cache_data.clear()
                st.success(f"✅ 已删除 {len(deleted)} 条往期新闻（{c_person}）")
                st.rerun()
            except Exception as e:
                st.error(f"清空失败：{e}")
