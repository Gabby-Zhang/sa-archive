import streamlit as st
from utils.auth import admin_sidebar
from utils.database import get_supabase

admin_sidebar()

st.set_page_config(page_title="图库 · 档案馆", page_icon="🖼️", layout="wide")

st.title("🖼️ 图库")
st.caption("照片、截图存档 — 图片存于 Google Drive")

# ── 灯箱 CSS + JS ─────────────────────────────────────────
st.markdown("""
<style>
#lb-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.92);
    z-index: 99999;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    flex-direction: column;
}
#lb-overlay.open { display: flex; }
#lb-overlay img { max-width: 92vw; max-height: 88vh; object-fit: contain; border-radius: 6px; }
#lb-close { position: absolute; top: 1rem; right: 1.5rem; color: #fff;
             font-size: 2rem; cursor: pointer; user-select: none; }
.lb-thumb { cursor: zoom-in; width: 100%; border-radius: 8px 8px 0 0; }
</style>
<div id="lb-overlay" onclick="document.getElementById('lb-overlay').classList.remove('open')">
    <span id="lb-close">✕</span>
    <img id="lb-img" src="">
</div>
<script>
function openLB(src) {
    document.getElementById('lb-img').src = src;
    document.getElementById('lb-overlay').classList.add('open');
}
</script>
""", unsafe_allow_html=True)

# ── Google Drive 链接转换为可显示的图片 URL ───────────────
def gdrive_to_img_url(url: str) -> str:
    """把 Google Drive 分享链接转成直接可显示的图片链接"""
    if not url:
        return ""
    # 格式1: https://drive.google.com/file/d/FILE_ID/view...
    if "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    # 格式2: https://drive.google.com/open?id=FILE_ID
    if "id=" in url:
        file_id = url.split("id=")[1].split("&")[0]
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url

# ── 加载图片数据 ─────────────────────────────────────────
def get_images(person=None, tag=None):
    try:
        db = get_supabase()
        query = db.table("images").select("*").order("date", desc=True)
        if person and person != "全部":
            query = query.eq("person", person)
        if tag and tag != "全部":
            query = query.eq("tag", tag)
        return query.execute().data
    except Exception as e:
        st.error(f"加载失败：{e}")
        return []

def add_image(data: dict):
    db = get_supabase()
    return db.table("images").insert(data).execute()

def delete_image(img_id: int):
    db = get_supabase()
    return db.table("images").delete().eq("id", img_id).execute()

# ── 筛选栏 ───────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "S&A"])
with col2:
    tag_filter = st.selectbox("分类", ["全部", "官方活动", "私下照片", "新闻截图", "社媒截图", "其他"])
with col3:
    keyword = st.text_input("🔍 搜索", placeholder="输入关键词…")

images = get_images(
    person=person_filter if person_filter != "全部" else None,
    tag=tag_filter if tag_filter != "全部" else None,
)

if keyword:
    images = [i for i in images if keyword.lower() in i.get("title", "").lower()]

st.caption(f"共 {len(images)} 张图片")

# ── 图库网格展示 ─────────────────────────────────────────
PERSON_COLOR = {
    "Gabriel Attal": "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "S&A": "#FF6B9D",
}

if images:
    cols = st.columns(2)
    for i, img in enumerate(images):
        with cols[i % 2]:
            img_url = gdrive_to_img_url(img.get("drive_url", ""))
            color = PERSON_COLOR.get(img.get("person", ""), "#888")

            if img_url:
                st.markdown(
                    f'<img class="lb-thumb" src="{img_url}" onclick="openLB(\'{img_url}\')" '
                    f'onerror="this.style.display=\'none\'">',
                    unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:#16213e;padding:0.5rem 0.8rem;
                        border-radius:0 0 8px 8px;margin-top:-8px;margin-bottom:1rem">
                <div style="color:{color};font-size:0.75rem">{img.get("person","")}</div>
                <div style="color:#e0e0e0;font-size:0.85rem;font-weight:bold">
                    {img.get("title","")}
                </div>
                <div style="color:#666;font-size:0.75rem">{img.get("date","")} · {img.get("tag","")}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("is_admin"):
                if st.button("🗑️ 删除", key=f"del_img_{img.get('id')}", use_container_width=True):
                    delete_image(img.get("id"))
                    st.rerun()
else:
    st.info("暂无图片，在下方添加第一张吧！")

st.divider()

# ── 管理员：上传图片 ─────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("➕ 添加图片", expanded=False):
        st.caption("""
        **如何获取 Google Drive 图片链接：**
        右键图片 → 「共享」→ 「知道链接的所有人」→ 复制链接
        """)
        with st.form("add_image_form"):
            c1, c2 = st.columns(2)
            with c1:
                img_title = st.text_input("图片标题/说明 *")
                img_person = st.selectbox("相关人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
                img_tag = st.selectbox("分类", ["官方活动", "私下照片", "新闻截图", "社媒截图", "其他"])
            with c2:
                img_url = st.text_input("Google Drive 分享链接 *")
                img_date = st.date_input("日期")
                img_note = st.text_input("备注（可选）")

            # 预览
            if img_url:
                preview_url = gdrive_to_img_url(img_url)
                st.caption("预览：")
                try:
                    st.image(preview_url, width=200)
                except Exception:
                    st.warning("无法预览，请确认链接已设为公开")

            if st.form_submit_button("✅ 添加图片", use_container_width=True):
                if img_title and img_url:
                    add_image({
                        "title": img_title,
                        "person": img_person,
                        "tag": img_tag,
                        "drive_url": img_url,
                        "date": str(img_date),
                        "note": img_note,
                    })
                    st.success("已添加！")
                    st.rerun()
                else:
                    st.warning("请填写标题和链接")
