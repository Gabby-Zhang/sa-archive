import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t

admin_sidebar()
from datetime import datetime
from utils.database import get_news, add_news_manual, add_event, delete_news, get_supabase, get_supabase_admin, log_audit
from utils.news_fetcher import fetch_all_news
from utils.media_spectrum import get_media_info, LEAN_EMOJI


st.title(t("news_title"))
st.caption(t("news_caption"))

# ── 收入大事记：把一条新闻预填进表单，管理员译成中文后存入 events ──────────────
# 新闻标题多为法/英原文；和行程日历一致，弹窗预填后由管理员手动译成中文再保存。
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
    """弹窗：把新闻条目预填进表单，管理员译成中文后存入大事记。"""
    st.caption("新闻标题多为法语/英语，请把标题译成中文后再保存。")
    dup = _event_dup_count(entry.get("source_url", ""))
    if dup:
        st.warning(f"大事记里已有 {dup} 条相同来源链接的记录，重复保存会产生多条。")

    from datetime import date as _date
    try:
        _default_date = _date.fromisoformat(str(entry.get("date", ""))[:10])
    except ValueError:
        _default_date = _date.today()
    _p    = entry.get("person", "")
    _pidx = _IMPORT_PERSON_OPTIONS.index(_p) if _p in _IMPORT_PERSON_OPTIONS else 0

    with st.form("import_news_to_timeline_form"):
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

st.info(t("news_vpn"), icon=None)

# ── 数据库查询缓存（2 分钟）；管理员增删后调用 st.cache_data.clear() ──
_get_news_cached = st.cache_data(ttl=120, show_spinner=False)(get_news)

# ── 刷新按钮 ─────────────────────────────────────────────
col_btn, col_info = st.columns([1, 4])
with col_btn:
    if st.button(t("news_fetch_btn")):
        with st.spinner("正在抓取…"):
            try:
                n = fetch_all_news()
                st.cache_data.clear()
                st.success(f"已更新 {n} 条新闻")
            except Exception as e:
                st.error(f"抓取失败：{e}")
with col_info:
    st.caption(t("news_fetch_hint"))

st.divider()

# ── 筛选栏 ───────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
with col1:
    person_filter = st.selectbox(t("person_label"), [t("all"), "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    # 按日期检索：留空=不限日期
    day_filter = st.date_input("按日期检索", value=None, format="YYYY-MM-DD")
with col3:
    limit = st.selectbox(t("show_count"), [50, 100, 200], index=0)
with col4:
    keyword = st.text_input(t("search_label"), placeholder=t("search_ph"))

# ── 分页状态 ─────────────────────────────────────────────
if "news_page" not in st.session_state:
    st.session_state.news_page = 0
# 筛选条件变化时重置到第一页
_fkey = f"{person_filter}|{limit}|{keyword}|{day_filter}"
if st.session_state.get("_news_fkey") != _fkey:
    st.session_state.news_page = 0
    st.session_state["_news_fkey"] = _fkey
_page   = st.session_state.news_page
_offset = _page * limit

# ── 加载数据（多取 1 条判断是否有下一页）────────────────
try:
    news = _get_news_cached(
        person=person_filter if person_filter not in ("全部", "All") else None,
        keyword=keyword if keyword else None,
        limit=limit,
        offset=_offset,
        day=day_filter if day_filter else None,
    )
except Exception as e:
    st.error(f"数据库连接失败：{e}")
    news = []

_has_next = len(news) > limit
if _has_next:
    news = news[:limit]   # 截掉多取的那 1 条

# ── 分页控件（页面上下各一份）──────────────────────────
_en_pg = st.session_state.get("lang") == "en"
_pg_info = (f"Page {_page + 1}  ·  {len(news)} items"
            if _en_pg else
            f"第 {_page + 1} 页 · 本页 {len(news)} 条")

def _render_pagination(key_prefix: str):
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button(t("pg_prev"),
                     key=f"{key_prefix}_prev", disabled=(_page == 0),
                     use_container_width=True):
            st.session_state.news_page -= 1
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align:center;color:#aaa;padding-top:0.4rem'>{_pg_info}</div>",
                    unsafe_allow_html=True)
    with c3:
        if st.button(t("pg_next"),
                     key=f"{key_prefix}_next", disabled=(not _has_next),
                     use_container_width=True):
            st.session_state.news_page += 1
            st.rerun()

_render_pagination("news_top")

# ── 新闻列表 ─────────────────────────────────────────────
PERSON_COLOR = {
    "Gabriel Attal": "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "S&A": "#FF6B9D",
}

import html as _html

for item in news:
    color = PERSON_COLOR.get(item.get("person", ""), "#888")
    url = item.get("url", "") or ""
    # 若 DB 里存的已经是 removepaywall 链接，提取真实 URL
    if "removepaywall.com/" in url:
        url = url.split("removepaywall.com/", 1)[-1]
    archive_ph_url  = f"https://archive.ph/{url}" if url else ""
    archive_rpw_url = f"https://www.removepaywall.com/{url}" if url else ""
    # 专访常用引言当标题、既无人名也无刊名，列表里一眼认不出 —— 此时在标题前挂来源
    _raw_title = item.get("title", "") or ""
    _raw_src   = item.get("source", "") or ""
    _tl = _raw_title.lower()
    if (_raw_src and _raw_src.lower() not in _tl
            and "attal" not in _tl and "séjourné" not in _tl and "sejourne" not in _tl):
        _disp_title = f"{_raw_src.split('.')[0]}：{_raw_title}"
    else:
        _disp_title = _raw_title
    safe_title   = _html.escape(_disp_title)
    safe_source  = _html.escape(_raw_src)
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

    # 媒体政治立场
    media_info = get_media_info(item.get("source", ""))
    lean_label = media_info["label"]
    lean_color = media_info["color"]
    lean_emoji = LEAN_EMOJI.get(lean_label, "")

    _link_orig     = f'<a href="{safe_url}" rel="noopener noreferrer" style="color:#4A90D9">{t("news_original")}</a>' if url else ""
    _link_arch_ph  = f'<a href="{safe_arch_ph}" rel="noopener noreferrer" style="color:#7EC8A4">{t("news_archive_ph")}</a>' if url else ""
    _link_archive  = f'<a href="{safe_archive}" rel="noopener noreferrer" style="color:#888">{t("news_archived")}</a>' if url else ""
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
        f'</div>'
        f'<div style="display:flex;gap:1rem;font-size:0.85rem">{_link_orig}{_link_arch_ph}{_link_archive}</div>'
        f'</div>'
        f'<div style="color:var(--t1);margin-top:0.4rem;font-size:0.95rem">{safe_title}</div>'
        f'</div>'
    )
    st.markdown(_card, unsafe_allow_html=True)

    # 管理员专用：操作按钮
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
                                log_audit("insert", "event_links", _sel_ev["id"], f"关联新闻：{(item.get('title') or '')[:40]}")
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
                if st.button("📌", key=f"pin_{item_id}",
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
                if st.button("🔗", key=f"link_{item_id}",
                             help="关联已有大事记", use_container_width=True):
                    st.session_state[f"linking_{item_id}"] = True
                    st.rerun()
            with bcc:
                if st.button("🗑️", key=f"del_news_{item_id}",
                             help="删除此条新闻", use_container_width=True):
                    delete_news(item_id)
                    st.cache_data.clear()
                    st.rerun()

if not news:
    st.info("暂无新闻，点击上方「抓取最新新闻」按钮开始收集。")

# ── 分页控件（下方）────────────────────────────────────
_render_pagination("news_bot")

st.divider()

# ── 管理员：批量解码 Google News 链接 ────────────────────
if st.session_state.get("is_admin"):
    with st.expander("🔧 解码数据库中的 Google News 链接"):
        st.caption("将数据库中所有 news.google.com 加密链接解码为真实文章 URL，解码后 archive.ph 和 removepaywall 均可正常使用。")
        if st.button("🔍 开始批量解码", type="primary", use_container_width=True):
            from utils.news_fetcher import _decode_gnews_url
            db = get_supabase_admin()
            try:
                records = (db.table("news")
                           .select("id,url")
                           .like("url", "%news.google.com%")
                           .execute().data)
                if not records:
                    st.info("没有找到 Google News 链接记录")
                else:
                    fixed = 0
                    failed = 0
                    prog = st.progress(0, text=f"准备解码 {len(records)} 条…")
                    for i, r in enumerate(records):
                        prog.progress((i + 1) / len(records),
                                      text=f"解码中 {i+1}/{len(records)}…")
                        decoded = _decode_gnews_url(r["url"])
                        if decoded != r["url"] and "google.com" not in decoded:
                            db.table("news").update({"url": decoded}).eq("id", r["id"]).execute()
                            fixed += 1
                        else:
                            failed += 1
                    prog.empty()
                    if fixed:
                        log_audit("update", "news", None, f"批量解码 Google News 链接 {fixed} 条")
                    st.cache_data.clear()
                    st.success(f"✅ 成功解码 {fixed} 条，{failed} 条无法解码（保留原链接）")
                    st.rerun()
            except Exception as e:
                st.error(f"操作失败：{e}")

# ── 手动添加新闻 ─────────────────────────────────────────
with st.expander("➕ 手动添加新闻"):
    with st.form("add_news_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_title = st.text_input("新闻标题 *")
            new_url = st.text_input("链接 *")
            new_person = st.selectbox("相关人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
        with c2:
            new_source = st.text_input("来源媒体")
            new_date = st.date_input("发布日期")
            new_summary = st.text_area("摘要（可选）", height=80)
        submitted = st.form_submit_button("添加")
        if submitted:
            if new_title and new_url:
                import hashlib
                add_news_manual({
                    "id": hashlib.md5(new_url.encode()).hexdigest(),
                    "title": new_title,
                    "url": new_url,
                    "source": new_source,
                    "person": new_person,
                    "published_at": str(new_date),
                    "summary": new_summary,
                })
                st.cache_data.clear()
                st.success("已添加！")
                st.rerun()
            else:
                st.warning("请填写标题和链接")
