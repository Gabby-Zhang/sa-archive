import streamlit as st
import pandas as pd
import plotly.express as px
from utils.database import get_events, add_event, update_event, delete_event, upload_to_storage, get_supabase_admin
from utils.auth import admin_sidebar
from utils.i18n import t

from utils.ui import gdrive_to_img_url

import re


def parse_image_urls(raw) -> list:
    """把多行 / 逗号分隔的图片链接拆成列表（兼容旧的单条链接）。"""
    if not raw:
        return []
    parts = re.split(r"[\n,，]+", str(raw))
    return [p.strip() for p in parts if p.strip() and p.strip().lower() != "nan"]


def render_images(raw, width=280):
    """显示一条大事记关联的所有图片：单张沿用原宽度，多张用三列网格。"""
    urls = [gdrive_to_img_url(u) for u in parse_image_urls(raw)]
    if not urls:
        return
    try:
        if len(urls) == 1:
            st.image(urls[0], width=width)
        else:
            cols = st.columns(min(len(urls), 3))
            for i, u in enumerate(urls):
                with cols[i % len(cols)]:
                    st.image(u, use_container_width=True)
    except Exception:
        pass


admin_sidebar()


TAG_OPTIONS = [
    "📰 新闻报道",
    "📅 大事记",
    "📸 IG 快拍",
    "📷 IG 帖子",
    "🎵 TikTok",
    "🐦 X/Twitter",
    "▶️ YouTube",
    "📺 Bilibili",
    "🎙️ 采访",
    "💬 互相提及",
    "📋 官方声明",
    "⚪ 其他",
]

TAG_OPTIONS_EN = [
    "📰 News coverage",
    "📅 Timeline entry",
    "📸 IG Story",
    "📷 IG Post",
    "🎵 TikTok",
    "🐦 X/Twitter",
    "▶️ YouTube",
    "📺 Bilibili",
    "🎙️ Interview",
    "💬 Mentions each other",
    "📋 Official statement",
    "⚪ Other",
]

# 英文标签 → 中文标签（用于过滤查询，DB 存的仍是中文）
_TAG_EN_TO_ZH = dict(zip(TAG_OPTIONS_EN, TAG_OPTIONS))

TAG_COLOR = {
    "📰 新闻报道": "#4A90D9",
    "📅 大事记":   "#8B6FD4",
    "📸 IG 快拍":  "#E1306C",
    "📷 IG 帖子":  "#E1306C",
    "🎵 TikTok":   "#69C9D0",
    "🐦 X/Twitter":"#1DA1F2",
    "▶️ YouTube":  "#FF0000",
    "📺 Bilibili":  "#00A1D6",
    "🎙️ 采访":     "#7EC8A4",
    "💬 互相提及":  "#FF6B9D",
    "📋 官方声明":  "#C9A84C",
    "⚪ 其他":      "#666666",
}

st.title(t("timeline_title"))
st.caption(t("timeline_caption"))

st.divider()

# ── 管理员：快速添加（顶部）────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("➕ 添加新条目", expanded=False):
        with st.form("quick_add_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_date = st.date_input("日期")
                new_person = st.selectbox("人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
            with c2:
                new_source = st.text_input("消息来源")
                new_source_url = st.text_input("来源链接（可选）")
            new_title = st.text_input("事件/新闻标题 *")
            new_tag = st.selectbox("类型标签", TAG_OPTIONS)
            new_note = st.text_area("内容摘要", height=68)
            new_image_url = st.text_area(
                "图片链接（Google Drive，可选，多张用逗号或换行分隔）",
                placeholder="https://drive.google.com/file/d/...\nhttps://drive.google.com/file/d/...",
                height=80,
            )
            if new_image_url and parse_image_urls(new_image_url):
                st.caption("图片预览：")
                try:
                    render_images(new_image_url, width=200)
                except Exception:
                    st.warning("无法预览，请确认链接已设为公开")
            uploaded_pdf = st.file_uploader(
                "📄 附件 PDF（可选，将自动存档并关联到本条目）",
                type=["pdf"],
                help="上传完整新闻原文或相关文件",
            )
            if st.form_submit_button("✅ 添加", use_container_width=True):
                if new_title:
                    result = add_event({
                        "date": str(new_date),
                        "person": new_person,
                        "title": new_title,
                        "source": new_source,
                        "source_url": new_source_url,
                        "note": new_note,
                        "image_url": new_image_url or None,
                        "tag": new_tag,
                    })
                    # 保存后自动跳到该条目并打开关联内容表单
                    new_id = None
                    if result and result.data:
                        new_id = result.data[0].get("id")
                        if new_id:
                            st.session_state.adding_link_for = new_id
                            st.session_state["year_filter_select"] = str(new_date.year)
                            st.session_state.timeline_page = 1
                    # 若上传了 PDF，存入 Storage 并创建 event_links 关联
                    if uploaded_pdf and new_id:
                        try:
                            pdf_url = upload_to_storage(
                                "documents",
                                uploaded_pdf.name,
                                uploaded_pdf.getvalue(),
                                "application/pdf",
                            )
                            get_supabase_admin().table("event_links").insert({
                                "event_id": new_id,
                                "title":    uploaded_pdf.name,
                                "url":      pdf_url,
                                "type":     "📄 文件附件",
                                "source":   new_source or "",
                            }).execute()
                        except Exception as _ue:
                            st.warning(f"PDF 上传失败（请确认 Supabase 已创建 documents bucket）：{_ue}")
                    st.rerun()
                else:
                    st.warning("请填写标题")

# ── 筛选栏 ───────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
with col1:
    person_filter = st.selectbox(t("person_label"), [t("all"), "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    year_options = [t("all")] + [str(y) for y in range(2026, 2009, -1)]
    year_filter = st.selectbox(t("year_label"), year_options, key="year_filter_select")
with col3:
    _is_en = st.session_state.get("lang", "zh") == "en"
    _tag_opts = TAG_OPTIONS_EN if _is_en else TAG_OPTIONS
    tag_filter_display = st.selectbox(t("type_label"), [t("all")] + _tag_opts)
    # 若英文模式，把选中值映射回中文（DB 存的是中文）
    tag_filter = _TAG_EN_TO_ZH.get(tag_filter_display, tag_filter_display)
with col4:
    keyword = st.text_input(t("search_label"), placeholder=t("search_ph"))

# ── 加载数据 ─────────────────────────────────────────────
try:
    events = get_events(
        person=person_filter if person_filter not in ("全部", "All") else None,
        keyword=keyword if keyword else None,
    )
    df = pd.DataFrame(events) if events else pd.DataFrame()
except Exception as e:
    st.error(f"数据库连接失败：{e}")
    df = pd.DataFrame()

# 年份筛选
_all = (t("all"),)
if not df.empty and year_filter not in ("全部", "All"):
    df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year.astype(str)
    df = df[df["year"] == year_filter]

if not df.empty and tag_filter not in ("全部", "All"):
    df = df[df["tag"] == tag_filter]

st.caption(f"共找到 {len(df)} 条记录")

# ── 批量加载当前页所有事件的相关内容 ──────────────────────────
from utils.database import get_supabase as _get_db, get_supabase_admin as _get_admin_db

def _fetch_all_links(event_ids):
    if not event_ids:
        return {}
    try:
        # event_links 表启用了 RLS，必须用 service key 才能读取
        rows = _get_admin_db().table("event_links").select("*").in_("event_id", [str(i) for i in event_ids]).order("created_at").execute().data
        result = {}
        for r in rows:
            result.setdefault(str(r["event_id"]), []).append(r)
        return result
    except Exception:
        return {}

if "adding_link_for" not in st.session_state:
    st.session_state.adding_link_for = None

# ── 导出 Excel ────────────────────────────────────────────
if not df.empty:
    import io
    out = io.BytesIO()
    export_cols = [c for c in ['date','person','title','source','source_url','note'] if c in df.columns]
    df_exp = df[export_cols].copy()
    df_exp.columns = [{'date':'日期','person':'人物','title':'事件标题',
                        'source':'消息来源','source_url':'来源链接','note':'内容摘要'}.get(c,c)
                      for c in export_cols]
    df_exp.to_excel(out, index=False, engine='openpyxl')
    st.download_button(
        t("timeline_export"),
        data=out.getvalue(),
        file_name=t("timeline_export_file"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── 时间轴展示 ───────────────────────────────────────────
PERSON_COLOR = {
    "Gabriel Attal": "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "S&A": "#FF6B9D",
}

# ── 分页 ──────────────────────────────────────────────────
ITEMS_PER_PAGE = 50
total = len(df)
total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

if "timeline_page" not in st.session_state:
    st.session_state.timeline_page = 1
# 筛选条件变化时重置到第一页
filter_key = f"{person_filter}_{year_filter}_{tag_filter}_{keyword}"
if st.session_state.get("_last_filter") != filter_key:
    st.session_state.timeline_page = 1
    st.session_state["_last_filter"] = filter_key

page = st.session_state.timeline_page
start = (page - 1) * ITEMS_PER_PAGE
df_page = df.iloc[start : start + ITEMS_PER_PAGE] if not df.empty else df

# 批量获取本页所有事件的相关内容（一次查询，不做 N+1）
page_event_ids = df_page["id"].tolist() if not df_page.empty else []
all_links = _fetch_all_links(page_event_ids)

if total_pages > 1:
    _en_pg = st.session_state.get("lang") == "en"
    pc1, pc2, pc3 = st.columns([1, 3, 1])
    with pc1:
        if st.button("◀ Prev" if _en_pg else "◀ 上一页", disabled=(page <= 1)):
            st.session_state.timeline_page -= 1
            st.rerun()
    with pc2:
        _pg_text = (f"Page {page} / {total_pages} ({ITEMS_PER_PAGE} per page)"
                    if _en_pg else
                    f"第 {page} / {total_pages} 页（每页 {ITEMS_PER_PAGE} 条）")
        st.markdown(f"<div style='text-align:center;color:#aaa;padding-top:0.4rem'>{_pg_text}</div>",
                    unsafe_allow_html=True)
    with pc3:
        if st.button("Next ▶" if _en_pg else "下一页 ▶", disabled=(page >= total_pages)):
            st.session_state.timeline_page += 1
            st.rerun()

# 初始化编辑状态
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

if not df_page.empty:
    for _, row in df_page.iterrows():
        event_id = row.get("id")
        color = PERSON_COLOR.get(row.get("person", ""), "#888")

        # ── 编辑模式 ──────────────────────────────────────
        if st.session_state.editing_id == event_id:
            with st.container():
                st.markdown(f'<div style="border-left:4px solid {color};padding:0.5rem 1rem;background:var(--cb);border-radius:0 8px 8px 0;margin:0.6rem 0">', unsafe_allow_html=True)
                with st.form(key=f"edit_form_{event_id}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        e_date = st.text_input("日期", value=row.get("date", ""))
                        e_person = st.selectbox("人物",
                            ["Gabriel Attal", "Stéphane Séjourné", "S&A"],
                            index=["Gabriel Attal", "Stéphane Séjourné", "S&A"].index(row.get("person", "Gabriel Attal")) if row.get("person") in ["Gabriel Attal", "Stéphane Séjourné", "S&A"] else 0)
                    with c2:
                        e_source = st.text_input("消息来源", value=row.get("source", ""))
                        _src_url = row.get("source_url", "") or ""
                        _src_url = "" if str(_src_url).strip().lower() == "nan" else _src_url
                        e_source_url = st.text_input("来源链接", value=_src_url)
                    e_title = st.text_input("事件/新闻标题", value=row.get("title", ""))
                    cur_tag = row.get("tag", TAG_OPTIONS[0]) or TAG_OPTIONS[0]
                    tag_idx = TAG_OPTIONS.index(cur_tag) if cur_tag in TAG_OPTIONS else 0
                    e_tag = st.selectbox("类型标签", TAG_OPTIONS, index=tag_idx)
                    e_note = st.text_area("内容摘要", value=row.get("note", "") or "", height=80)
                    e_image_url = st.text_area("图片链接（Google Drive，可选，多张用逗号或换行分隔）", value=row.get("image_url", "") or "", height=80)
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        save = st.form_submit_button("💾 保存", use_container_width=True)
                    with sc2:
                        cancel = st.form_submit_button("✕ 取消", use_container_width=True)
                    if save:
                        update_event(event_id, {
                            "date": e_date,
                            "person": e_person,
                            "title": e_title,
                            "source": e_source,
                            "source_url": e_source_url,
                            "note": e_note,
                            "image_url": e_image_url or None,
                            "tag": e_tag,
                        })
                        st.session_state.editing_id = None
                        st.rerun()
                    if cancel:
                        st.session_state.editing_id = None
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # ── 编辑模式下也显示相关内容 + 管理入口 ──────────
            event_links_edit = all_links.get(str(event_id), [])
            if event_links_edit:
                with st.expander(f"📎 {len(event_links_edit)} 个相关内容（可在此删除）", expanded=True):
                    for lk in event_links_edit:
                        lk_type   = lk.get("type", "")
                        lk_color  = TAG_COLOR.get(lk_type, "#555")
                        lk_url    = lk.get("url", "")
                        lk_title  = lk.get("title", "")
                        lk_source = lk.get("source", "")
                        link_a    = (f' <a href="{lk_url}" target="_blank" '
                                     f'style="color:#4A90D9;font-size:0.85rem">🔗</a>') if lk_url else ""
                        _lc1, _lc2 = st.columns([11, 1])
                        with _lc1:
                            st.markdown(
                                f'<div style="padding:0.3rem 0;border-bottom:1px solid var(--bd)">'
                                f'<span style="background:{lk_color};color:white;padding:0.05rem 0.35rem;'
                                f'border-radius:3px;font-size:0.7rem">{lk_type}</span> '
                                f'<span style="color:var(--t2);font-size:0.8rem">{lk_source}</span> '
                                f'<span style="color:var(--t1);font-size:0.88rem"> {lk_title}</span>{link_a}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                        with _lc2:
                            if st.button("🗑️", key=f"del_lk_edit_{lk['id']}",
                                         help="删除此关联", use_container_width=True):
                                _get_admin_db().table("event_links").delete().eq("id", lk["id"]).execute()
                                st.cache_data.clear()
                                st.rerun()

            # 在编辑模式下也可以添加相关内容
            if st.button("📎 添加相关内容", key=f"add_lk_in_edit_{event_id}",
                         use_container_width=False):
                st.session_state.adding_link_for = event_id
                st.rerun()

            # 添加相关内容表单（编辑模式下）
            if st.session_state.get("adding_link_for") == event_id:
                with st.form(key=f"add_lk_form_edit_{event_id}"):
                    st.caption("添加相关内容")
                    lf1, lf2 = st.columns(2)
                    with lf1:
                        lk_type_new   = st.selectbox("类型", TAG_OPTIONS, key=f"lkt_edit_{event_id}")
                        lk_source_new = st.text_input("来源（可选）", key=f"lks_edit_{event_id}")
                    with lf2:
                        lk_url_new   = st.text_input("链接（可选）", key=f"lku_edit_{event_id}")
                        lk_title_new = st.text_input("标题/说明（可选）", key=f"lkti_edit_{event_id}")
                    ls1, ls2 = st.columns(2)
                    with ls1:
                        if st.form_submit_button("💾 保存", use_container_width=True):
                            _get_admin_db().table("event_links").insert({
                                "event_id": str(event_id),
                                "title":    lk_title_new,
                                "url":      lk_url_new,
                                "type":     lk_type_new,
                                "source":   lk_source_new,
                            }).execute()
                            st.session_state.adding_link_for = None
                            st.cache_data.clear()
                            st.rerun()
                    with ls2:
                        if st.form_submit_button("✕ 取消", use_container_width=True):
                            st.session_state.adding_link_for = None
                            st.rerun()

        # ── 正常显示模式 ──────────────────────────────────
        else:
            source_html = ""
            if row.get("source_url"):
                source_html = f'<a href="{row["source_url"]}" target="_blank" style="color:#4A90D9">🔗 原文</a>'
                archive_url = f"https://www.removepaywall.com/{row['source_url']}"
                source_html += f' &nbsp; <a href="{archive_url}" target="_blank" style="color:var(--t3)">📦 存档版</a>'
            elif row.get("source"):
                source_html = f'<span style="color:var(--t2)">{row["source"]}</span>'

            _note = row.get("note", "") or ""
            _note = "" if str(_note).strip().lower() == "nan" else _note
            note_html = f'<div style="color:var(--t2);font-size:0.85rem;margin-top:0.4rem">{_note}</div>' if _note else ""

            tag_val   = row.get("tag", "") or ""
            tag_color = TAG_COLOR.get(tag_val, "#555")
            tag_html  = (f'<span style="background:{tag_color};color:white;padding:0.05rem 0.45rem;'
                         f'border-radius:3px;font-size:0.7rem;font-weight:bold;margin-left:0.6rem">'
                         f'{tag_val}</span>') if tag_val else ""

            _card = (
                f'<div style="border-left:4px solid {color};padding:0.8rem 1.2rem;margin:0.6rem 0;background:var(--cb);border-radius:0 8px 8px 0">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.3rem">'
                f'<div>'
                f'<span style="color:{color};font-weight:bold;font-size:0.85rem">{row.get("person","")}</span>'
                f'<span style="color:var(--t2);font-size:0.8rem;margin-left:0.8rem">{row.get("date","")}</span>'
                f'{tag_html}'
                f'</div>'
                f'<div style="font-size:0.85rem">{source_html}</div>'
                f'</div>'
                f'<div style="font-size:1rem;margin-top:0.3rem;color:var(--t1)">{row.get("title","")}</div>'
                f'{note_html}'
                f'</div>'
            )
            st.markdown(_card, unsafe_allow_html=True)

            render_images(row.get("image_url", ""), width=280)

            # ── 相关内容折叠展示 ──────────────────────────────
            event_links = all_links.get(str(event_id), [])
            if event_links:
                with st.expander(f"📎 {len(event_links)} 个相关内容"):
                    for lk in event_links:
                        lk_type   = lk.get("type", "")
                        lk_color  = TAG_COLOR.get(lk_type, "#555")
                        lk_url    = lk.get("url", "")
                        lk_title  = lk.get("title", "")
                        lk_source = lk.get("source", "")
                        link_a    = (f' <a href="{lk_url}" target="_blank" '
                                     f'style="color:#4A90D9;font-size:0.85rem">🔗</a>') if lk_url else ""
                        st.markdown(
                            f'<div style="padding:0.3rem 0;border-bottom:1px solid var(--bd)">'
                            f'<span style="background:{lk_color};color:white;padding:0.05rem 0.35rem;'
                            f'border-radius:3px;font-size:0.7rem">{lk_type}</span> '
                            f'<span style="color:var(--t2);font-size:0.8rem">{lk_source}</span> '
                            f'<span style="color:var(--t1);font-size:0.88rem"> {lk_title}</span>{link_a}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        if st.session_state.get("is_admin"):
                            if st.button("🗑️", key=f"del_lk_{lk['id']}"):
                                _get_admin_db().table("event_links").delete().eq("id", lk["id"]).execute()
                                st.rerun()

            # ── 管理员：操作按钮（紧凑 emoji 风格）────────────
            if st.session_state.get("is_admin"):
                _, bca, bcb, bcc = st.columns([7, 1, 1, 1])
                with bca:
                    if st.button("📎", key=f"add_lk_btn_{event_id}",
                                 help="添加相关内容", use_container_width=True):
                        st.session_state.adding_link_for = event_id
                        st.rerun()
                with bcb:
                    if st.button("✏️", key=f"edit_{event_id}",
                                 help="编辑", use_container_width=True):
                        st.session_state.editing_id = event_id
                        st.rerun()
                with bcc:
                    if st.button("🗑️", key=f"del_{event_id}",
                                 help="删除", use_container_width=True):
                        delete_event(event_id)
                        st.rerun()

            # ── 添加相关内容表单 ──────────────────────────────
            if st.session_state.get("is_admin") and st.session_state.adding_link_for == event_id:
                with st.form(key=f"add_lk_form_{event_id}"):
                    st.caption("手动添加相关内容（新闻、IG 快拍、推文等）")
                    lf1, lf2 = st.columns(2)
                    with lf1:
                        lk_type_new   = st.selectbox("类型", TAG_OPTIONS, key=f"lkt_{event_id}")
                        lk_source_new = st.text_input("来源（可选）", key=f"lks_{event_id}")
                    with lf2:
                        lk_url_new   = st.text_input("链接（可选）", key=f"lku_{event_id}")
                        lk_title_new = st.text_input("标题/说明（可选）", key=f"lkti_{event_id}")
                    ls1, ls2 = st.columns(2)
                    with ls1:
                        if st.form_submit_button("💾 保存", use_container_width=True):
                            _get_admin_db().table("event_links").insert({
                                "event_id": str(event_id),
                                "title":    lk_title_new,
                                "url":      lk_url_new,
                                "type":     lk_type_new,
                                "source":   lk_source_new,
                            }).execute()
                            st.session_state.adding_link_for = None
                            st.rerun()
                    with ls2:
                        if st.form_submit_button("✕ 取消", use_container_width=True):
                            st.session_state.adding_link_for = None
                            st.rerun()

                # ── 相关新闻自动推荐（表单外，一键关联）────────────
                from datetime import datetime as _dt, timedelta as _td
                try:
                    ev_date_str = str(row.get("date", ""))
                    ev_person   = row.get("person", "")
                    if ev_date_str and ev_person:
                        d       = _dt.fromisoformat(ev_date_str).date()
                        d_start = (d - _td(days=7)).isoformat()
                        d_end   = (d + _td(days=7)).isoformat()
                        # 已关联的 url 集合（避免重复推荐）
                        linked_urls = {lk.get("url","") for lk in all_links.get(str(event_id), [])}
                        suggested = (
                            _get_db().table("news")
                            .select("id,title,source,published_at,url,person")
                            .eq("person", ev_person)
                            .gte("published_at", d_start)
                            .lte("published_at", d_end)
                            .order("published_at", desc=True)
                            .limit(15)
                            .execute().data
                        )
                        # 过滤掉已经关联过的
                        suggested = [s for s in suggested if s.get("url","") not in linked_urls]
                        if suggested:
                            st.markdown(
                                f'<div style="background:var(--cb2);border:1px solid var(--bd);'
                                f'border-radius:6px;padding:0.6rem 1rem;margin-top:0.5rem">'
                                f'<span style="color:#7EC8A4;font-size:0.8rem;font-weight:bold">'
                                f'💡 {ev_date_str} 前后找到 {len(suggested)} 篇相关新闻，点击 📌 一键关联</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            for sug in suggested:
                                s1, s2 = st.columns([11, 1])
                                with s1:
                                    sug_date = str(sug.get("published_at",""))[:10]
                                    sug_src  = sug.get("source","")
                                    sug_ttl  = (sug.get("title","") or "")[:90]
                                    st.markdown(
                                        f'<span style="color:var(--t3);font-size:0.73rem">{sug_date}</span>'
                                        f' <span style="color:var(--t2);font-size:0.73rem">{sug_src}</span>'
                                        f' <span style="color:var(--t1);font-size:0.82rem">{sug_ttl}</span>',
                                        unsafe_allow_html=True
                                    )
                                with s2:
                                    sug_key = f"auto_lk_{event_id}_{str(sug.get('id',''))[:8]}"
                                    if st.button("📌", key=sug_key, help="关联到此事件"):
                                        try:
                                            _get_admin_db().table("event_links").insert({
                                                "event_id": event_id,   # 直接传原始值
                                                "title":    sug.get("title",""),
                                                "url":      sug.get("url",""),
                                                "type":     "📰 新闻报道",
                                                "source":   sug.get("source",""),
                                            }).execute()
                                            st.rerun()
                                        except Exception as _e:
                                            st.error(f"关联失败：{_e}")
                except Exception:
                    pass

                # ── 相关大事记推荐（同期条目，一键关联）─────────────
                try:
                    ev_date_str2 = str(row.get("date", ""))
                    ev_person2   = row.get("person", "")
                    if ev_date_str2 and ev_person2:
                        d2      = _dt.fromisoformat(ev_date_str2).date()
                        d2_s    = (d2 - _td(days=7)).isoformat()
                        d2_e    = (d2 + _td(days=7)).isoformat()
                        linked_titles = {lk.get("title","") for lk in all_links.get(str(event_id), [])}
                        # 查同人物或 S&A 的同期大事记（排除自身）
                        person_filter_ev = ev_person2
                        sug_events = (
                            _get_db().table("events")
                            .select("id,title,date,person,source_url")
                            .gte("date", d2_s)
                            .lte("date", d2_e)
                            .order("date", desc=True)
                            .limit(10)
                            .execute().data
                        )
                        # 排除自身 & 已关联的
                        sug_events = [
                            e for e in sug_events
                            if str(e.get("id","")) != str(event_id)
                            and e.get("title","") not in linked_titles
                        ]
                        if sug_events:
                            st.markdown(
                                f'<div style="background:var(--cb2);border:1px solid #3d2a6e;'
                                f'border-radius:6px;padding:0.6rem 1rem;margin-top:0.4rem">'
                                f'<span style="color:#8B6FD4;font-size:0.8rem;font-weight:bold">'
                                f'📅 同期找到 {len(sug_events)} 条相关大事记，点击 📌 一键关联</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            for sug_ev in sug_events:
                                se1, se2 = st.columns([11, 1])
                                with se1:
                                    ev_p_color = PERSON_COLOR.get(sug_ev.get("person",""), "#888")
                                    st.markdown(
                                        f'<span style="color:#666;font-size:0.73rem">'
                                        f'{str(sug_ev.get("date",""))[:10]}</span>'
                                        f' <span style="color:{ev_p_color};font-size:0.73rem;font-weight:bold">'
                                        f'{sug_ev.get("person","")}</span>'
                                        f' <span style="color:#ccc;font-size:0.82rem">'
                                        f'{(sug_ev.get("title","") or "")[:90]}</span>',
                                        unsafe_allow_html=True
                                    )
                                with se2:
                                    sev_key = f"auto_ev_{event_id}_{sug_ev.get('id','')}"
                                    if st.button("📌", key=sev_key, help="关联到此事件"):
                                        _get_admin_db().table("event_links").insert({
                                            "event_id": str(event_id),
                                            "title":    sug_ev.get("title",""),
                                            "url":      sug_ev.get("source_url","") or "",
                                            "type":     "📅 大事记",
                                            "source":   sug_ev.get("person",""),
                                        }).execute()
                                        st.rerun()
                except Exception:
                    pass
else:
    st.info("暂无数据，请先在下方添加或导入数据。")

st.divider()

# ── 添加新条目 ───────────────────────────────────────────
with st.expander("➕ 手动添加新条目"):
    with st.form("add_event_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_date = st.date_input("日期")
            new_person = st.selectbox("人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
        with c2:
            new_source = st.text_input("消息来源（媒体名）")
            new_source_url = st.text_input("来源链接（可选）")
        new_title = st.text_input("事件/新闻标题 *")
        new_tag_b = st.selectbox("类型标签", TAG_OPTIONS, key="bottom_tag")
        new_note = st.text_area("内容摘要", height=80)
        new_image_url_b = st.text_area("图片链接（Google Drive，可选，多张用逗号或换行分隔）", placeholder="https://drive.google.com/file/d/...\nhttps://drive.google.com/file/d/...", key="bottom_img_url", height=80)
        submitted = st.form_submit_button("添加")
        if submitted:
            if new_title:
                result = add_event({
                    "date": str(new_date),
                    "person": new_person,
                    "title": new_title,
                    "source": new_source,
                    "source_url": new_source_url,
                    "note": new_note,
                    "image_url": new_image_url_b or None,
                    "tag": new_tag_b,
                })
                if result and result.data:
                    new_id = result.data[0].get("id")
                    if new_id:
                        st.session_state.adding_link_for = new_id
                        st.session_state["year_filter_select"] = str(new_date.year)
                        st.session_state.timeline_page = 1
                st.rerun()
            else:
                st.warning("请填写事件标题")

# ── 导入 Excel（SA档案馆专用）────────────────────────────
with st.expander("📥 从腾讯文档 Excel 一键导入"):
    st.caption("上传你从腾讯文档导出的【SA档案馆.xlsx】，自动识别格式，无需手动配置列名")
    uploaded = st.file_uploader("选择 Excel 文件", type=["xlsx", "xls"])
    if uploaded:
        st.info("检测到文件，点击下方按钮开始导入")
        if st.button("🚀 开始导入大事记"):
            import zipfile, xml.etree.ElementTree as ET
            from datetime import date as _date, timedelta

            def _shared_strings(z):
                root = ET.fromstring(z.read('xl/sharedStrings.xml'))
                ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
                return [''.join(t.text or '' for t in si.iter(f'{{{ns}}}t'))
                        for si in root.findall(f'{{{ns}}}si')]

            def _excel_date(n):
                try:
                    return (_date(1899,12,30) + timedelta(days=int(float(n)))).isoformat()
                except Exception:
                    return None

            def _read_sheet(z, fname, shared):
                root = ET.fromstring(z.read(f'xl/worksheets/{fname}'))
                ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
                rows = []
                for row_el in root.findall(f'.//{{{ns}}}row'):
                    rd = {}
                    for cell in row_el.findall(f'{{{ns}}}c'):
                        ref = cell.get('r','')
                        col = ''.join(c for c in ref if c.isalpha())
                        t = cell.get('t','')
                        v_el = cell.find(f'{{{ns}}}v')
                        rd[col] = (shared[int(v_el.text)] if t=='s' else v_el.text) if v_el is not None and v_el.text else ''
                    if any(rd.values()):
                        rows.append(rd)
                return rows

            person_map = {'SS':'Stéphane Séjourné','GA':'Gabriel Attal','两人':'两人','SS&GA':'两人','GA&SS':'两人'}

            with st.spinner("正在解析…"):
                with zipfile.ZipFile(uploaded) as z:
                    shared = _shared_strings(z)
                    rows = _read_sheet(z, 'sheet1.xml', shared)

                events, header_passed = [], False
                for row in rows:
                    year = row.get('A','').strip()
                    if year == 'Year':
                        header_passed = True
                        continue
                    if not header_passed:
                        continue
                    char = row.get('C','').strip()
                    if not char:
                        continue
                    date_raw = row.get('B','').strip()
                    date_str = _excel_date(date_raw) if date_raw and date_raw != '\\' else year
                    event = row.get('D','').strip()
                    source = row.get('E','').strip()
                    remark = row.get('F','').strip()
                    if not event:
                        continue
                    events.append({
                        'date': date_str or year,
                        'person': person_map.get(char, char),
                        'title': event[:500],
                        'source': source[:300],
                        'note': remark[:300],
                    })

                prog = st.progress(0, text="导入中…")
                batch = 50
                for i in range(0, len(events), batch):
                    get_supabase_admin().table('events').insert(events[i:i+batch]).execute()
                    prog.progress(min((i+batch)/len(events), 1.0), text=f"已导入 {min(i+batch,len(events))}/{len(events)}")

                st.success(f"✅ 成功导入 {len(events)} 条大事记！")
                st.rerun()
