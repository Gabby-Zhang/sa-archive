import streamlit as st
from utils.auth import admin_sidebar

admin_sidebar()
from utils.database import get_files, add_file, get_supabase, get_supabase_admin, upload_to_storage
from utils.i18n import t
import html as _html

st.set_page_config(page_title="文件存档 · 档案馆", page_icon="📁", layout="wide")

st.title(t("files_title"))
st.caption(t("files_caption"))

FILE_TYPES = [
    "📚 书籍", "📖 传记", "🔍 调查报告",
    "📄 PDF", "📝 文章", "🎬 视频", "🖼️ 截图",
    "📱 百度网盘（二维码）", "📎 其他",
]

TYPE_ICONS = {ft: ft.split()[0] for ft in FILE_TYPES}
# 兼容旧数据
TYPE_ICONS.update({"PDF": "📄", "截图": "🖼️", "视频": "🎬", "文章": "📝", "其他": "📎"})

PERSON_COLOR = {
    "Gabriel Attal":     "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "S&A":               "#FF6B9D",
}

# ── 筛选 ─────────────────────────────────────────────────
col1, col2 = st.columns([2, 3])
with col1:
    person_filter = st.selectbox(t("person_label"), [t("all"), "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    type_filter = st.selectbox(t("file_type_label"), [t("all")] + FILE_TYPES)

# ── 文件列表 ─────────────────────────────────────────────
try:
    files = get_files(person=person_filter if person_filter not in ("全部", "All") else None)
except Exception as e:
    st.error(f"数据库连接失败：{e}")
    files = []

if type_filter not in ("全部", "All"):
    files = [f for f in files if f.get("file_type") == type_filter]

st.caption(f"共 {len(files)} 个文件")

for f in files:
    color    = PERSON_COLOR.get(f.get("person", ""), "#888")
    ftype    = f.get("file_type", "其他") or "其他"
    icon     = TYPE_ICONS.get(ftype, "📎")
    url      = f.get("drive_url", "") or ""
    is_qr    = ftype == "📱 百度网盘（二维码）"
    safe_title = _html.escape(f.get("title", "") or "")
    safe_note  = _html.escape(f.get("note",  "") or "")
    safe_person = _html.escape(f.get("person","") or "")
    safe_ftype  = _html.escape(ftype)

    st.markdown(f"""
    <div style="background:var(--cb);border-left:4px solid {color};
                padding:0.8rem 1.2rem;margin:0.4rem 0;border-radius:0 8px 8px 0">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.4rem">
            <div>
                <span style="font-size:1rem">{icon}</span>
                <span style="color:var(--t1);margin-left:0.5rem;font-weight:bold">{safe_title}</span>
                <span style="color:{color};font-size:0.8rem;margin-left:0.8rem">{safe_person}</span>
                <span style="color:#666;font-size:0.8rem;margin-left:0.8rem">{safe_ftype}</span>
            </div>
            {"<a href='" + url + "' target='_blank' style='color:#4A90D9;font-size:0.9rem'>📂 打开</a>" if url and not is_qr else ""}
        </div>
        {("<div style='color:#aaa;font-size:0.85rem;margin-top:0.3rem'>" + safe_note + "</div>") if safe_note else ""}
    </div>
    """, unsafe_allow_html=True)

    # 二维码图片内嵌显示
    if is_qr and url:
        with st.expander(t("file_qr_view")):
            st.image(url, width=220, caption="扫码获取文件（百度网盘）")

    # 管理员删除按钮
    if st.session_state.get("is_admin"):
        if st.button("🗑️", key=f"del_file_{f.get('id')}", help="删除此文件记录"):
            get_supabase_admin().table("files").delete().eq("id", f.get("id")).execute()
            st.rerun()

if not files:
    st.info("暂无文件。")

st.divider()

# ── 添加文件（仅管理员）──────────────────────────────────
if not st.session_state.get("is_admin"):
    st.caption("🔐 仅管理员可上传文件")
else:
    # 平台选择放在 form 外面，用 session_state 控制显示
    st.subheader("➕ 登记新文件")

    source_type = st.radio(
        "存储来源",
        ["🌐 Google Drive / 外部链接", "📱 百度网盘（上传二维码图片）"],
        horizontal=True,
        key="file_source_type",
    )
    is_baidu = source_type.startswith("📱")

    with st.form("add_file_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_title  = st.text_input("文件名称/标题 *")
            new_person = st.selectbox("相关人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
            _types_no_qr = [ft for ft in FILE_TYPES if ft != "📱 百度网盘（二维码）"]
            new_type   = st.selectbox(
                "文件类型",
                ["📱 百度网盘（二维码）"] + _types_no_qr if is_baidu else _types_no_qr,
            )
        with c2:
            if is_baidu:
                qr_image = st.file_uploader(
                    "上传二维码图片 *",
                    type=["png", "jpg", "jpeg", "webp"],
                    help="上传百度网盘分享二维码截图",
                )
                new_url = ""
            else:
                qr_image = None
                new_url = st.text_input("文件链接 *", placeholder="https://drive.google.com/...")
            new_date = st.date_input("日期（文件对应的时间）")
            new_note = st.text_area("备注（作者、出版年份等）", height=80)

        submitted = st.form_submit_button("✅ 登记", use_container_width=True)
        if submitted:
            if not new_title:
                st.warning("请填写标题")
            elif is_baidu and not qr_image:
                st.warning("请上传二维码图片")
            elif not is_baidu and not new_url:
                st.warning("请填写文件链接")
            else:
                final_url = new_url
                final_type = new_type

                # 上传二维码图片到 Supabase Storage
                if is_baidu and qr_image:
                    try:
                        final_url = upload_to_storage(
                            "qrcodes",
                            qr_image.name,
                            qr_image.getvalue(),
                            qr_image.type or "image/png",
                        )
                        final_type = "📱 百度网盘（二维码）"
                    except Exception as _ue:
                        st.error(f"图片上传失败（请确认 Supabase 已创建 qrcodes bucket）：{_ue}")
                        st.stop()

                add_file({
                    "title":     new_title,
                    "person":    new_person,
                    "file_type": final_type,
                    "drive_url": final_url,
                    "date":      str(new_date),
                    "note":      new_note,
                })
                st.success("✅ 已登记！")
                st.rerun()
