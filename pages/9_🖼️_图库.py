import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase

admin_sidebar()

st.set_page_config(page_title="图库 · 档案馆", page_icon="🖼️", layout="wide")

st.title(t("gallery_title"))
st.caption(t("gallery_caption"))

# ── 最新图片动态（photo-monitor 自动抓取）────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_photo_alerts(limit=300):
    try:
        return get_supabase().table("photo_alerts") \
            .select("*").order("found_at", desc=True).limit(limit).execute().data or []
    except Exception:
        return []

_PERSON_COLOR = {"Gabriel Attal": "#C9A84C", "Stéphane Séjourné": "#4A90D9"}
_en = st.session_state.get("lang") == "en"

alerts = get_photo_alerts()
if alerts:
    from collections import defaultdict
    from datetime import datetime as _dt

    _header = "📸 Latest photo finds" if _en else "📸 最新图片动态"
    st.markdown(
        f'<div style="font-size:1rem;font-weight:700;margin:0.3rem 0 0.5rem">{_header}</div>',
        unsafe_allow_html=True
    )

    # ── 图库来源 → 搜索页 URL（点徽章直接跳转）──────────────
    _SEARCH_URLS = {
        "Gabriel Attal": {
            "Getty Images":       "https://www.gettyimages.com/photos/gabriel-attal",
            "Imago Images":       "https://www.imago-images.de/search?term=gabriel+attal",
            "Alamy":              "https://www.alamy.com/search.html?qt=gabriel+attal",
            "Flickr RenewEurope":"https://www.flickr.com/groups/reneweuropegroup/",
            "EU Audiovisual":     "https://audiovisual.ec.europa.eu/en/search?term=attal",
        },
        "Stéphane Séjourné": {
            "Getty Images":       "https://www.gettyimages.com/photos/stephane-sejourne",
            "Imago Images":       "https://www.imago-images.de/search?term=sejourne",
            "Alamy":              "https://www.alamy.com/search.html?qt=sejourne",
            "Flickr RenewEurope":"https://www.flickr.com/groups/reneweuropegroup/",
            "EU Audiovisual":     "https://audiovisual.ec.europa.eu/en/search?term=sejourne",
        },
    }

    # ── 按「人物 → 发现日期 → 图库来源」三级分组 ──────────────
    _by_person = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for _a in alerts:
        _p = _a.get("person") or "Unknown"
        _d = (_a.get("found_at") or "")[:10]
        _s = _a.get("source") or "Unknown"
        _by_person[_p][_d][_s].append(_a)

    def _render_person_col(person: str, color: str):
        _dates = _by_person.get(person, {})
        if not _dates:
            st.caption("暂无数据" if not _en else "No data yet")
            return
        _search_map = _SEARCH_URLS.get(person, {})

        for _date in sorted(_dates.keys(), reverse=True):
            _src_map = _dates[_date]
            try:
                _dl = _dt.fromisoformat(_date)
                _date_label = f"{_dl.month}.{_dl.day}"
            except Exception:
                _date_label = _date

            # 每行：日期 + 各图库徽章（点击直接跳转搜索页）
            _badges = ""
            for _src, _items in sorted(_src_map.items()):
                _href  = _search_map.get(_src, _items[0].get("url", "#"))
                _count = len(_items)
                _badges += (
                    f'<a href="{_href}" target="_blank" style="text-decoration:none">'
                    f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
                    f'font-size:0.72rem;padding:0.1rem 0.45rem;border-radius:4px;'
                    f'margin-left:0.4rem;white-space:nowrap">'
                    f'{_src} {_count}</span></a>'
                )

            st.markdown(
                f'<div style="padding:0.3rem 0;border-bottom:1px solid var(--bd)">'
                f'<span style="color:var(--t3);font-size:0.78rem;font-weight:600">{_date_label}</span>'
                f'{_badges}'
                f'</div>',
                unsafe_allow_html=True
            )

    # 两栏并排：左 Séjourné，右 Attal
    _col_s, _col_a = st.columns(2)
    with _col_s:
        st.markdown(
            f'<div style="color:#4A90D9;font-size:0.9rem;font-weight:700;margin-bottom:0.3rem">'
            f'🔵 Stéphane Séjourné</div>',
            unsafe_allow_html=True
        )
        _render_person_col("Stéphane Séjourné", "#4A90D9")
    with _col_a:
        st.markdown(
            f'<div style="color:#C9A84C;font-size:0.9rem;font-weight:700;margin-bottom:0.3rem">'
            f'🟡 Gabriel Attal</div>',
            unsafe_allow_html=True
        )
        _render_person_col("Gabriel Attal", "#C9A84C")

st.divider()

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

            st.markdown(
                f'<div style="background:var(--cb);padding:0.5rem 0.8rem;border-radius:0 0 8px 8px;margin-top:-8px;margin-bottom:1rem">'
                f'<div style="color:{color};font-size:0.75rem">{img.get("person","")}</div>'
                f'<div style="color:var(--t1);font-size:0.85rem;font-weight:bold">{img.get("title","")}</div>'
                f'<div style="color:#666;font-size:0.75rem">{img.get("date","")} · {img.get("tag","")}</div>'
                f'</div>',
                unsafe_allow_html=True)

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
