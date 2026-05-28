import streamlit as st
import pandas as pd
import plotly.express as px
from utils.database import get_events, add_event, update_event, delete_event
from utils.auth import admin_sidebar

# ── Google Drive 链接转换 ─────────────────────────────────
def gdrive_to_img_url(url: str) -> str:
    if not url:
        return ""
    if "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    if "id=" in url:
        file_id = url.split("id=")[1].split("&")[0]
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url

admin_sidebar()

st.set_page_config(page_title="大事记 · 档案馆", page_icon="📅", layout="wide")

TAG_OPTIONS = [
    "📰 新闻报道",
    "📸 IG 快拍",
    "📷 IG 帖子",
    "🎵 TikTok",
    "🐦 X/Twitter",
    "▶️ YouTube",
    "📺 Bilibili",
    "🎙️ 采访",
    "📋 官方声明",
    "⚪ 其他",
]

TAG_COLOR = {
    "📰 新闻报道": "#4A90D9",
    "📸 IG 快拍":  "#E1306C",
    "📷 IG 帖子":  "#E1306C",
    "🎵 TikTok":   "#69C9D0",
    "🐦 X/Twitter":"#1DA1F2",
    "▶️ YouTube":  "#FF0000",
    "📺 Bilibili":  "#00A1D6",
    "🎙️ 采访":     "#7EC8A4",
    "📋 官方声明":  "#C9A84C",
    "⚪ 其他":      "#666666",
}

st.title("📅 大事记时间轴")
st.caption("记录 Attal 与 Séjourné 的重要事件与新闻")

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
            new_image_url = st.text_input("图片链接（Google Drive，可选）", placeholder="https://drive.google.com/file/d/...")
            if new_image_url:
                _prev = gdrive_to_img_url(new_image_url)
                st.caption("图片预览：")
                try:
                    st.image(_prev, width=200)
                except Exception:
                    st.warning("无法预览，请确认链接已设为公开")
            if st.form_submit_button("✅ 添加", use_container_width=True):
                if new_title:
                    add_event({
                        "date": str(new_date),
                        "person": new_person,
                        "title": new_title,
                        "source": new_source,
                        "source_url": new_source_url,
                        "note": new_note,
                        "image_url": new_image_url or None,
                        "tag": new_tag,
                    })
                    st.success("已添加！")
                    st.rerun()
                else:
                    st.warning("请填写标题")

# ── 筛选栏 ───────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
with col1:
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    year_options = ["全部"] + [str(y) for y in range(2026, 2009, -1)]
    year_filter = st.selectbox("年份", year_options)
with col3:
    tag_filter = st.selectbox("类型", ["全部"] + TAG_OPTIONS)
with col4:
    keyword = st.text_input("🔍 搜索关键词", placeholder="输入关键词…")

# ── 加载数据 ─────────────────────────────────────────────
try:
    events = get_events(
        person=person_filter if person_filter != "全部" else None,
        keyword=keyword if keyword else None,
    )
    df = pd.DataFrame(events) if events else pd.DataFrame()
except Exception as e:
    st.error(f"数据库连接失败：{e}")
    df = pd.DataFrame()

# 年份筛选
if not df.empty and year_filter != "全部":
    df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year.astype(str)
    df = df[df["year"] == year_filter]

# 标签筛选
if not df.empty and tag_filter != "全部":
    df = df[df["tag"] == tag_filter]

st.caption(f"共找到 {len(df)} 条记录")

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
    st.download_button("📥 导出 Excel", data=out.getvalue(),
                       file_name="大事记.xlsx",
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

if total_pages > 1:
    pc1, pc2, pc3 = st.columns([1, 3, 1])
    with pc1:
        if st.button("◀ 上一页", disabled=(page <= 1)):
            st.session_state.timeline_page -= 1
            st.rerun()
    with pc2:
        st.markdown(f"<div style='text-align:center;color:#aaa;padding-top:0.4rem'>"
                    f"第 {page} / {total_pages} 页（每页 {ITEMS_PER_PAGE} 条）</div>",
                    unsafe_allow_html=True)
    with pc3:
        if st.button("下一页 ▶", disabled=(page >= total_pages)):
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
                st.markdown(f'<div style="border-left:4px solid {color};padding:0.5rem 1rem;background:#16213e;border-radius:0 8px 8px 0;margin:0.6rem 0">', unsafe_allow_html=True)
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
                    e_image_url = st.text_input("图片链接（Google Drive，可选）", value=row.get("image_url", "") or "")
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

        # ── 正常显示模式 ──────────────────────────────────
        else:
            source_html = ""
            if row.get("source_url"):
                source_html = f'<a href="{row["source_url"]}" target="_blank" style="color:#4A90D9">🔗 原文</a>'
                archive_url = f"https://www.removepaywall.com/{row['source_url']}"
                source_html += f' &nbsp; <a href="{archive_url}" target="_blank" style="color:#aaa">📦 存档版</a>'
            elif row.get("source"):
                source_html = f'<span style="color:#aaa">{row["source"]}</span>'

            _note = row.get("note", "") or ""
            _note = "" if str(_note).strip().lower() == "nan" else _note
            note_html = f'<div style="color:#bbb;font-size:0.85rem;margin-top:0.4rem">{_note}</div>' if _note else ""

            img_url = gdrive_to_img_url(row.get("image_url", "") or "")

            tag_val   = row.get("tag", "") or ""
            tag_color = TAG_COLOR.get(tag_val, "#555")
            tag_html  = (f'<span style="background:{tag_color};color:white;padding:0.05rem 0.45rem;'
                         f'border-radius:3px;font-size:0.7rem;font-weight:bold;margin-left:0.6rem">'
                         f'{tag_val}</span>') if tag_val else ""

            st.markdown(f"""
            <div style="
                border-left: 4px solid {color};
                padding: 0.8rem 1.2rem;
                margin: 0.6rem 0;
                background: #16213e;
                border-radius: 0 8px 8px 0;
            ">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.3rem">
                    <div>
                        <span style="color:{color};font-weight:bold;font-size:0.85rem">{row.get("person","")}</span>
                        <span style="color:#777;font-size:0.8rem;margin-left:0.8rem">{row.get("date","")}</span>
                        {tag_html}
                    </div>
                    <div style="font-size:0.85rem">{source_html}</div>
                </div>
                <div style="font-size:1rem;margin-top:0.3rem;color:#e0e0e0">{row.get("title","")}</div>
                {note_html}
            </div>
            """, unsafe_allow_html=True)

            if img_url:
                try:
                    st.image(img_url, width=280)
                except Exception:
                    pass

            # 编辑和删除按钮（仅管理员可见）
            if st.session_state.get("is_admin"):
                bc1, bc2, bc3 = st.columns([6, 1, 1])
                with bc2:
                    if st.button("✏️", key=f"edit_{event_id}", help="编辑"):
                        st.session_state.editing_id = event_id
                        st.rerun()
                with bc3:
                    if st.button("🗑️", key=f"del_{event_id}", help="删除"):
                        delete_event(event_id)
                        st.rerun()
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
        new_image_url_b = st.text_input("图片链接（Google Drive，可选）", placeholder="https://drive.google.com/file/d/...", key="bottom_img_url")
        submitted = st.form_submit_button("添加")
        if submitted:
            if new_title:
                add_event({
                    "date": str(new_date),
                    "person": new_person,
                    "title": new_title,
                    "source": new_source,
                    "source_url": new_source_url,
                    "note": new_note,
                    "image_url": new_image_url_b or None,
                    "tag": new_tag_b,
                })
                st.success("已添加！")
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
                    add_event.__func__ if hasattr(add_event,'__func__') else None
                    from utils.database import get_supabase
                    get_supabase().table('events').insert(events[i:i+batch]).execute()
                    prog.progress(min((i+batch)/len(events), 1.0), text=f"已导入 {min(i+batch,len(events))}/{len(events)}")

                st.success(f"✅ 成功导入 {len(events)} 条大事记！")
                st.rerun()
