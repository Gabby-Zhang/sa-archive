import streamlit as st
import pandas as pd
import plotly.express as px
from utils.database import get_events, add_event, update_event, delete_event
from utils.auth import admin_sidebar

admin_sidebar()

st.set_page_config(page_title="大事记 · 档案馆", page_icon="📅", layout="wide")

st.title("📅 大事记时间轴")
st.caption("记录 Attal 与 Séjourné 的重要事件与新闻")

st.divider()

# ── 筛选栏 ───────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "两人"])
with col2:
    year_options = ["全部"] + [str(y) for y in range(2026, 2009, -1)]
    year_filter = st.selectbox("年份", year_options)
with col3:
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

st.caption(f"共找到 {len(df)} 条记录")

# ── 时间轴展示 ───────────────────────────────────────────
PERSON_COLOR = {
    "Gabriel Attal": "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "两人": "#7EC8A4",
}

# 初始化编辑状态
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

if not df.empty:
    for _, row in df.iterrows():
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
                            ["Gabriel Attal", "Stéphane Séjourné", "两人"],
                            index=["Gabriel Attal", "Stéphane Séjourné", "两人"].index(row.get("person", "Gabriel Attal")) if row.get("person") in ["Gabriel Attal", "Stéphane Séjourné", "两人"] else 0)
                    with c2:
                        e_source = st.text_input("消息来源", value=row.get("source", ""))
                        e_source_url = st.text_input("来源链接", value=row.get("source_url", "") or "")
                    e_title = st.text_input("事件/新闻标题", value=row.get("title", ""))
                    e_note = st.text_area("备注", value=row.get("note", "") or "", height=80)
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
                archive_url = f"https://archive.ph/{row['source_url']}"
                source_html += f' &nbsp; <a href="{archive_url}" target="_blank" style="color:#aaa">📦 存档版</a>'
            elif row.get("source"):
                source_html = f'<span style="color:#aaa">{row["source"]}</span>'

            note_html = f'<div style="color:#bbb;font-size:0.85rem;margin-top:0.4rem">{row["note"]}</div>' if row.get("note") else ""

            st.markdown(f"""
            <div style="
                border-left: 4px solid {color};
                padding: 0.8rem 1.2rem;
                margin: 0.6rem 0;
                background: #16213e;
                border-radius: 0 8px 8px 0;
            ">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <span style="color:{color};font-weight:bold;font-size:0.85rem">{row.get("person","")}</span>
                        <span style="color:#777;font-size:0.8rem;margin-left:1rem">{row.get("date","")}</span>
                    </div>
                    <div style="font-size:0.85rem">{source_html}</div>
                </div>
                <div style="font-size:1rem;margin-top:0.3rem;color:#e0e0e0">{row.get("title","")}</div>
                {note_html}
            </div>
            """, unsafe_allow_html=True)

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
            new_person = st.selectbox("人物", ["Gabriel Attal", "Stéphane Séjourné", "两人"])
        with c2:
            new_source = st.text_input("消息来源（媒体名）")
            new_source_url = st.text_input("来源链接（可选）")
        new_title = st.text_input("事件/新闻标题 *")
        new_note = st.text_area("备注（Note）", height=80)
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
