import streamlit as st
import pandas as pd
import plotly.express as px
from utils.database import get_events, add_event, update_event, delete_event, upload_to_storage, upload_to_cloudinary, get_supabase_admin, log_audit
from utils.auth import admin_sidebar
from utils.i18n import t

from utils.ui import gdrive_to_img_url, video_thumb_html

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
    "🗓️ 日常行程",
    "⭐ 重要行程/事件",
    "📣 重大宣布",
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
    "🗓️ Routine schedule",
    "⭐ Key event",
    "📣 Major announcement",
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
    "🗓️ 日常行程": "#6B8FB5",
    "⭐ 重要行程/事件": "#E8A33D",
    "📣 重大宣布": "#D9534F",
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

# ── 事件「类型标签」专用：Bilibili 不再是顶层类型，而是「采访」下的平台子集 ──
# （event_links 的类型仍用完整 TAG_OPTIONS，那里 Bilibili 作为平台是合理的）
EVENT_TAG_OPTIONS    = [tg for tg in TAG_OPTIONS    if tg != "📺 Bilibili"]
EVENT_TAG_OPTIONS_EN = [tg for tg in TAG_OPTIONS_EN if tg != "📺 Bilibili"]

PLATFORM_NONE    = "（不指定）"
PLATFORM_OPTIONS = [PLATFORM_NONE, "📺 Bilibili", "▶️ YouTube", "🎬 线下", "⚪ 其他"]


def split_event_tag(tag):
    """把存库的 tag 拆成 (主类型, 平台)。兼容旧的独立「📺 Bilibili」（归入采访）。"""
    tag = (tag or "").strip()
    if not tag or tag.lower() == "nan":
        return ("", PLATFORM_NONE)
    if tag == "📺 Bilibili":            # 旧数据：独立的 Bilibili → 采访 · Bilibili
        return ("🎙️ 采访", "📺 Bilibili")
    if " · " in tag:
        base, plat = tag.split(" · ", 1)
        return (base.strip(), plat.strip())
    return (tag, PLATFORM_NONE)


def join_event_tag(primary, platform):
    """把主类型 + 平台拼回存库格式；只有「采访」才带平台。"""
    if primary == "🎙️ 采访" and platform and platform != PLATFORM_NONE:
        return f"🎙️ 采访 · {platform}"
    return primary

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
            tc1, tc2 = st.columns(2)
            with tc1:
                new_tag_base = st.selectbox("类型标签", EVENT_TAG_OPTIONS)
            with tc2:
                new_tag_plat = st.selectbox("采访平台（仅「采访」时生效）", PLATFORM_OPTIONS)
            new_tag = join_event_tag(new_tag_base, new_tag_plat)
            new_note = st.text_area("内容摘要", height=68)
            uploaded_imgs = st.file_uploader(
                "🖼️ 上传图片（可选，可多张；存到 Cloudinary，所有管理员通用）",
                type=["png", "jpg", "jpeg", "gif", "webp"],
                accept_multiple_files=True,
                key="quick_add_imgs",
                help="直接选图片文件上传，不用再贴 Google Drive 链接",
            )
            new_image_url = st.text_area(
                "或：图片外链（可选，多张用逗号或换行分隔）",
                placeholder="https://drive.google.com/file/d/...\nhttps://i.imgur.com/...",
                height=80,
                help="已有外链（Google Drive、IG 图等）时贴这里，会和上传的图片一起显示",
            )
            if new_image_url and parse_image_urls(new_image_url):
                st.caption("外链预览：")
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
                    # 上传图片到 Cloudinary，和外链一起合并进 image_url
                    _img_urls = []
                    for _f in (uploaded_imgs or []):
                        try:
                            _img_urls.append(upload_to_cloudinary(_f.name, _f.getvalue()))
                        except Exception as _ie:
                            st.warning(f"图片「{_f.name}」上传失败（请确认已配置 Cloudinary 凭据）：{_ie}")
                    _merged_imgs = "\n".join(
                        u for u in ([new_image_url] + _img_urls) if u and str(u).strip()
                    ) or None
                    result = add_event({
                        "date": str(new_date),
                        "person": new_person,
                        "title": new_title,
                        "source": new_source,
                        "source_url": new_source_url,
                        "note": new_note,
                        "image_url": _merged_imgs,
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
                            log_audit("insert", "event_links", new_id, f"附件：{uploaded_pdf.name}")
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
    _tag_opts = EVENT_TAG_OPTIONS_EN if _is_en else EVENT_TAG_OPTIONS
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
    # 用 Int64 可空整数再转字符串，避免有 NaT 时整列退化成浮点（"2025.0" ≠ "2025" 导致筛空）
    df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year.astype("Int64").astype(str)
    df = df[df["year"] == year_filter]

if not df.empty and tag_filter not in ("全部", "All"):
    # 按主类型匹配：选「采访」也能筛到「采访 · Bilibili」这类带平台的条目
    df = df[df["tag"].apply(lambda x: split_event_tag(x)[0]) == tag_filter]

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
                    cur_base, cur_plat = split_event_tag(row.get("tag", ""))
                    base_idx = EVENT_TAG_OPTIONS.index(cur_base) if cur_base in EVENT_TAG_OPTIONS else 0
                    plat_idx = PLATFORM_OPTIONS.index(cur_plat) if cur_plat in PLATFORM_OPTIONS else 0
                    etc1, etc2 = st.columns(2)
                    with etc1:
                        e_tag_base = st.selectbox("类型标签", EVENT_TAG_OPTIONS, index=base_idx)
                    with etc2:
                        e_tag_plat = st.selectbox("采访平台（仅「采访」时生效）", PLATFORM_OPTIONS, index=plat_idx)
                    e_tag = join_event_tag(e_tag_base, e_tag_plat)
                    e_note = st.text_area("内容摘要", value=row.get("note", "") or "", height=80)
                    e_uploaded_imgs = st.file_uploader(
                        "🖼️ 追加上传图片（可选，可多张；存到 Cloudinary，所有管理员通用）",
                        type=["png", "jpg", "jpeg", "gif", "webp"],
                        accept_multiple_files=True,
                        key=f"edit_imgs_{event_id}",
                        help="上传的图片会追加到下面已有的图片之后",
                    )
                    e_image_url = st.text_area("图片外链（可选，多张用逗号或换行分隔）", value=row.get("image_url", "") or "", height=80)
                    e_uploaded_pdf = st.file_uploader(
                        "📄 追加 PDF 附件（可选，将自动存档并关联到本条目）",
                        type=["pdf"],
                        key=f"edit_pdf_{event_id}",
                        help="上传完整新闻原文或相关文件（我们自己下载的 PDF）",
                    )
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        save = st.form_submit_button("💾 保存", use_container_width=True)
                    with sc2:
                        cancel = st.form_submit_button("✕ 取消", use_container_width=True)
                    if save:
                        # 追加上传的图片合并进 image_url（接在已有外链之后）
                        _e_img_urls = []
                        for _f in (e_uploaded_imgs or []):
                            try:
                                _e_img_urls.append(upload_to_cloudinary(_f.name, _f.getvalue()))
                            except Exception as _ie:
                                st.warning(f"图片「{_f.name}」上传失败（请确认已配置 Cloudinary 凭据）：{_ie}")
                        _e_merged_imgs = "\n".join(
                            u for u in ([e_image_url] + _e_img_urls) if u and str(u).strip()
                        ) or None
                        update_event(event_id, {
                            "date": e_date,
                            "person": e_person,
                            "title": e_title,
                            "source": e_source,
                            "source_url": e_source_url,
                            "note": e_note,
                            "image_url": _e_merged_imgs,
                            "tag": e_tag,
                        })
                        # 若上传了 PDF，存入 Storage 并创建 event_links 关联
                        if e_uploaded_pdf:
                            try:
                                pdf_url = upload_to_storage(
                                    "documents",
                                    e_uploaded_pdf.name,
                                    e_uploaded_pdf.getvalue(),
                                    "application/pdf",
                                )
                                get_supabase_admin().table("event_links").insert({
                                    "event_id": event_id,
                                    "title":    e_uploaded_pdf.name,
                                    "url":      pdf_url,
                                    "type":     "📄 文件附件",
                                    "source":   e_source or "",
                                }).execute()
                                log_audit("insert", "event_links", event_id, f"附件：{e_uploaded_pdf.name}")
                            except Exception as _ue:
                                st.warning(f"PDF 上传失败（请确认 Supabase 已创建 documents bucket）：{_ue}")
                        st.cache_data.clear()
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
                                log_audit("delete", "event_links", lk["id"], lk.get("title"))
                                st.cache_data.clear()
                                st.rerun()
                        _lk_thumb = video_thumb_html(lk_url, width=240)
                        if _lk_thumb:
                            st.markdown(_lk_thumb, unsafe_allow_html=True)

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
                            log_audit("insert", "event_links", event_id, lk_title_new or lk_url_new)
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
            # 配色按主类型取（「采访 · Bilibili」用采访的颜色）
            tag_color = TAG_COLOR.get(split_event_tag(tag_val)[0], TAG_COLOR.get(tag_val, "#555"))
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

            # 来源链接本身是 YouTube/B 站视频时，显示可点击略缩图
            _src_thumb = video_thumb_html(row.get("source_url", "") or "", width=320)
            if _src_thumb:
                st.markdown(_src_thumb, unsafe_allow_html=True)

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
                        _lk_thumb = video_thumb_html(lk_url, width=240)
                        if _lk_thumb:
                            st.markdown(_lk_thumb, unsafe_allow_html=True)
                        if st.session_state.get("is_admin"):
                            if st.button("🗑️", key=f"del_lk_{lk['id']}"):
                                _get_admin_db().table("event_links").delete().eq("id", lk["id"]).execute()
                                log_audit("delete", "event_links", lk["id"], lk.get("title"))
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
                            log_audit("insert", "event_links", event_id, lk_title_new or lk_url_new)
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
                                            log_audit("insert", "event_links", event_id, f"关联新闻：{(sug.get('title') or '')[:40]}")
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
                                        log_audit("insert", "event_links", event_id, f"关联大事记：{(sug_ev.get('title') or '')[:40]}")
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
        btc1, btc2 = st.columns(2)
        with btc1:
            new_tag_b_base = st.selectbox("类型标签", EVENT_TAG_OPTIONS, key="bottom_tag")
        with btc2:
            new_tag_b_plat = st.selectbox("采访平台（仅「采访」时生效）", PLATFORM_OPTIONS, key="bottom_plat")
        new_tag_b = join_event_tag(new_tag_b_base, new_tag_b_plat)
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

# ── 从 Excel 批量导入大事记（预览式：按表头名认列 + 传完先核对再入库）──────
with st.expander("📥 从 Excel 批量导入大事记"):
    st.caption("文件名随意。表里要有一行**表头**，含「人物」「标题」等列名（中英、顺序都不限）；"
               "其下每行一个事件。上传后会**出预览、可直接改**，确认无误才入库。")
    st.caption("可用列名：年份/Year · 日期/Date · 人物/Person(SS、GA、两人) · "
               "标题/事件/Title · 来源/Source · 备注/Note。识别不到列名时回退按 A~F 顺序读。")
    uploaded = st.file_uploader("选择 Excel 文件（.xlsx）", type=["xlsx"])
    if uploaded:
        import pandas as pd, re as _re
        from datetime import date as _date, datetime as _dt, timedelta

        # 人物列写法归一（大小写不敏感）
        person_map = {'ss':'Stéphane Séjourné','ga':'Gabriel Attal',
                      '两人':'两人','ss&ga':'两人','ga&ss':'两人','s&a':'S&A','sa':'S&A'}
        # 列名别名表：把表头单元格映射到内部字段
        HEADER_ALIASES = {
            'year':   ['year','年份','年'],
            'date':   ['date','日期'],
            'person': ['person','人物','人'],
            'title':  ['title','event','事件','标题','事件标题','内容','事项'],
            'source': ['source','来源','链接','link','出处','url'],
            'note':   ['note','remark','备注','说明','注'],
        }

        def _cell(v):
            if v is None:
                return ''
            try:
                if pd.isna(v):
                    return ''
            except (TypeError, ValueError):
                pass
            return str(v).strip()

        def _to_date(v, year_fb):
            # 真日期单元格直接取 ISO；纯数字按 Excel 序列号换算；其它原样
            if isinstance(v, (pd.Timestamp, _dt, _date)):
                return (v.date() if isinstance(v, (pd.Timestamp, _dt)) else v).isoformat()
            s = _cell(v)
            if not s or s == '\\':
                return year_fb
            if _re.fullmatch(r'\d+(?:\.\d+)?', s):
                try:
                    return (_date(1899, 12, 30) + timedelta(days=int(float(s)))).isoformat()
                except Exception:
                    return s
            return s

        # 1) 读第一个工作表（不管它叫什么）——任何异常都记审计 + 给人看的报错
        try:
            raw = pd.read_excel(uploaded, header=None, sheet_name=0)
        except Exception as e:
            log_audit("import_fail", "events", None,
                      f"Excel 读取失败：{type(e).__name__}: {str(e)[:200]}")
            st.error(f"❌ 文件读不开：{e}\n\n请确认是标准 .xlsx，用 Excel「另存为」后重试。")
            st.stop()
        grid = raw.values.tolist()

        # 2) 找表头行：按列名匹配出 field→列号；认不出列名时回退到旧的 A~F 位置式
        colmap, header_idx = {}, None
        for i, row in enumerate(grid):
            cells = [_cell(c).lower() for c in row]
            m = {}
            for field, aliases in HEADER_ALIASES.items():
                for j, c in enumerate(cells):
                    if c in aliases:
                        m[field] = j
                        break
            if 'person' in m and 'title' in m:        # 至少认出人物+标题才算表头
                colmap, header_idx = m, i
                break
            if 'year' in cells:                        # 兼容旧表：A 列写 Year 的位置式表头
                colmap = {'year': 0, 'date': 1, 'person': 2, 'title': 3, 'source': 4, 'note': 5}
                header_idx = i
                break

        if header_idx is None:
            log_audit("import_fail", "events", None, "导入失败：找不到表头行（缺人物/标题列名）")
            st.error("❌ 没找到表头行。表里需要一行写明列名，至少含「人物」和「标题」"
                     "（或英文 Person / Title）。")
            st.stop()

        # 3) 逐行抽取
        def _get(row, field):
            j = colmap.get(field)
            return _cell(row[j]) if j is not None and j < len(row) else ''

        events = []
        for row in grid[header_idx + 1:]:
            person = _get(row, 'person')
            title = _get(row, 'title')
            if not person or not title:
                continue
            year = _get(row, 'year')
            dj = colmap.get('date')
            date_val = row[dj] if (dj is not None and dj < len(row)) else None
            events.append({
                'date':   _to_date(date_val, year),
                'person': person_map.get(person.lower(), person),
                'title':  title[:500],
                'source': _get(row, 'source')[:300],
                'note':   _get(row, 'note')[:300],
            })

        if not events:
            log_audit("import_fail", "events", None, "导入识别 0 条：表头下无有效数据行（人物/标题为空）")
            st.error("❌ 认出了表头，但下面没有有效行——每行需同时有「人物」和「标题」。")
            st.stop()

        # 4) 预览 + 可编辑，确认才入库
        st.success(f"已识别 {len(events)} 条，请核对（可直接改、删行），确认无误再导入：")
        df = pd.DataFrame(events, columns=['date', 'person', 'title', 'source', 'note'])
        edited = st.data_editor(
            df, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                'date':   st.column_config.TextColumn('日期'),
                'person': st.column_config.TextColumn('人物'),
                'title':  st.column_config.TextColumn('标题', width='large'),
                'source': st.column_config.TextColumn('来源'),
                'note':   st.column_config.TextColumn('备注'),
            },
            key="import_preview",
        )

        if st.button("✅ 确认导入", type="primary"):
            final = [
                {'date': _cell(r['date']), 'person': _cell(r['person']),
                 'title': _cell(r['title'])[:500], 'source': _cell(r['source'])[:300],
                 'note': _cell(r['note'])[:300]}
                for _, r in edited.iterrows()
                if _cell(r['person']) and _cell(r['title'])
            ]

            # 幂等去重：日期+人物+标题指纹，跳过库里已有；同一份表内部也去重
            def _fp(d, p, t):
                return (str(d or '').strip(), str(p or '').strip(), str(t or '').strip())
            existing = get_supabase_admin().table('events').select('date,person,title').execute().data or []
            seen = {_fp(e.get('date'), e.get('person'), e.get('title')) for e in existing}
            new_events, dup = [], 0
            for ev in final:
                k = _fp(ev['date'], ev['person'], ev['title'])
                if k in seen:
                    dup += 1
                    continue
                seen.add(k)
                new_events.append(ev)

            if dup:
                st.info(f"已跳过 {dup} 条库里已存在的重复事件")
            if not new_events:
                st.success(f"✅ 没有新增内容，库已是最新（{dup} 条都已存在）")
                st.stop()

            prog = st.progress(0, text="导入中…")
            for i in range(0, len(new_events), 50):
                get_supabase_admin().table('events').insert(new_events[i:i + 50]).execute()
                prog.progress(min((i + 50) / len(new_events), 1.0),
                              text=f"已导入 {min(i + 50, len(new_events))}/{len(new_events)}")
            log_audit("insert", "events", None, f"批量导入 {len(new_events)} 条大事记")
            st.success(f"✅ 成功导入 {len(new_events)} 条大事记！")
            st.rerun()

# ── 批量删除大事记（管理员，筛选→勾选→二次确认）──────────────────
if st.session_state.get("is_admin"):
    with st.expander("🗑️ 批量删除大事记"):
        st.caption("先按条件筛选缩小范围，勾选要删的行，确认后批量删除。"
                   "每条删除都会记入操作日志，**但无法在线撤销**，请务必核对。")
        _all_ev = get_events()  # 含 id
        if not _all_ev:
            st.info("暂无数据。")
        else:
            import pandas as pd
            fc1, fc2 = st.columns([1, 2])
            with fc1:
                _persons = ["全部"] + sorted({e.get("person", "") for e in _all_ev if e.get("person")})
                _f_person = st.selectbox("人物", _persons, key="del_person")
            with fc2:
                _f_kw = st.text_input("标题关键词（可空）", key="del_kw")
            _rows = [
                e for e in _all_ev
                if (_f_person == "全部" or e.get("person") == _f_person)
                and (not _f_kw or _f_kw.lower() in (e.get("title", "") or "").lower())
            ]
            st.caption(f"筛选到 {len(_rows)} 条")
            if _rows:
                _df = pd.DataFrame([{
                    "_sel": False,
                    "id": e.get("id"),
                    "date": e.get("date"),
                    "person": e.get("person"),
                    "title": e.get("title"),
                } for e in _rows])
                _edited = st.data_editor(
                    _df, use_container_width=True, hide_index=True,
                    disabled=["id", "date", "person", "title"],
                    column_config={
                        "_sel":   st.column_config.CheckboxColumn("删除?", default=False),
                        "id":     st.column_config.NumberColumn("ID", width="small"),
                        "date":   st.column_config.TextColumn("日期"),
                        "person": st.column_config.TextColumn("人物"),
                        "title":  st.column_config.TextColumn("标题", width="large"),
                    },
                    key="del_editor",
                )
                _sel_ids = [int(r["id"]) for _, r in _edited.iterrows()
                            if r["_sel"] and pd.notna(r["id"])]
                st.write(f"已选中 **{len(_sel_ids)}** 条")
                if _sel_ids:
                    if len(_sel_ids) >= 20:
                        st.warning(f"⚠️ 你正要删除 {len(_sel_ids)} 条，数量较多，请再次核对无误。")
                    _confirm = st.checkbox(
                        f"我确认删除选中的 {len(_sel_ids)} 条（不可在线撤销）", key="del_confirm")
                    if st.button("🗑️ 删除选中", type="primary", disabled=not _confirm):
                        _prog = st.progress(0, text="删除中…")
                        for _i, _eid in enumerate(_sel_ids, 1):
                            delete_event(_eid)
                            _prog.progress(_i / len(_sel_ids), text=f"已删除 {_i}/{len(_sel_ids)}")
                        st.success(f"✅ 已删除 {len(_sel_ids)} 条")
                        st.rerun()
