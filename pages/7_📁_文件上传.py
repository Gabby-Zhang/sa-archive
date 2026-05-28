import streamlit as st
from utils.auth import admin_sidebar

admin_sidebar()
from utils.database import get_files, add_file, get_supabase

st.set_page_config(page_title="文件上传 · 档案馆", page_icon="📁", layout="wide")

st.title("📁 文件存档")
st.caption("上传到 Google Drive 后，在这里登记链接")

st.info("""
**使用说明：**
1. 将文件上传到你的 Google Drive 文件夹
2. 右键文件 → 「获取链接」→ 改为「知道链接的所有人可查看」
3. 复制链接，填入下方表单
""")

# ── 筛选 ─────────────────────────────────────────────────
col1, col2 = st.columns([2, 3])
with col1:
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    type_filter = st.selectbox("文件类型", ["全部", "PDF", "截图", "视频", "文章", "其他"])

# ── 文件列表 ─────────────────────────────────────────────
try:
    files = get_files(person=person_filter if person_filter != "全部" else None)
except Exception as e:
    st.error(f"数据库连接失败：{e}")
    files = []

if type_filter != "全部":
    files = [f for f in files if f.get("file_type") == type_filter]

TYPE_ICONS = {"PDF": "📄", "截图": "🖼️", "视频": "🎬", "文章": "📝", "其他": "📎"}
PERSON_COLOR = {
    "Gabriel Attal": "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "S&A": "#FF6B9D",
}

st.caption(f"共 {len(files)} 个文件")

for f in files:
    color = PERSON_COLOR.get(f.get("person", ""), "#888")
    icon = TYPE_ICONS.get(f.get("file_type", "其他"), "📎")
    url = f.get("drive_url", "")
    st.markdown(f"""
    <div style="background:var(--cb);border-left:4px solid {color};
                padding:0.8rem 1.2rem;margin:0.4rem 0;border-radius:0 8px 8px 0">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
                <span style="font-size:1rem">{icon}</span>
                <span style="color:var(--t1);margin-left:0.5rem;font-weight:bold">
                    {f.get("title","")}
                </span>
                <span style="color:{color};font-size:0.8rem;margin-left:0.8rem">
                    {f.get("person","")}
                </span>
                <span style="color:#666;font-size:0.8rem;margin-left:0.8rem">
                    {f.get("file_type","")}
                </span>
            </div>
            {"<a href='" + url + "' target='_blank' style='color:#4A90D9;font-size:0.9rem'>📂 打开</a>" if url else ""}
        </div>
        {"<div style='color:#aaa;font-size:0.85rem;margin-top:0.3rem'>" + f.get("note","") + "</div>" if f.get("note") else ""}
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        if st.button("🗑️ 删除", key=f"del_file_{f.get('id')}", use_container_width=False):
            get_supabase().table("files").delete().eq("id", f.get("id")).execute()
            st.rerun()

if not files:
    st.info("暂无文件，在下方添加第一个文件吧！")

st.divider()

# ── 添加文件（仅管理员）──────────────────────────────────
if not st.session_state.get("is_admin"):
    st.info("🔐 登录管理员账号后可添加文件")
else:
    with st.expander("➕ 登记新文件", expanded=True if not files else False):
        with st.form("add_file_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_title = st.text_input("文件名称/标题 *")
                new_person = st.selectbox("相关人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
                new_type = st.selectbox("文件类型", ["PDF", "截图", "视频", "文章", "其他"])
            with c2:
                new_url = st.text_input("Google Drive 链接 *")
                new_date = st.date_input("日期（文件对应的时间）")
                new_note = st.text_area("备注", height=80)
            submitted = st.form_submit_button("登记")
            if submitted:
                if new_title and new_url:
                    add_file({
                        "title": new_title,
                        "person": new_person,
                        "file_type": new_type,
                        "drive_url": new_url,
                        "date": str(new_date),
                        "note": new_note,
                    })
                    st.success("已登记！")
                    st.rerun()
                else:
                    st.warning("请填写标题和链接")
