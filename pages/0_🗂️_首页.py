import streamlit as st
from utils.auth import admin_sidebar
from utils.database import get_supabase
from utils.i18n import t
import html as _html

admin_sidebar()

# ── 样式 ────────────────────────────────────────────────
st.markdown("""
<style>
.hero { text-align: center; padding: 2rem 0 1rem 0; }
.hero h1 { font-size: 2.5rem; color: #4A90D9; letter-spacing: 2px; }
.hero p { color: var(--t2); font-size: 1.1rem; }
.profile-card {
    background: var(--cb);
    border: 1px solid #4A90D944;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 0.5rem;
    text-align: center;
}
.profile-card h2 { color: #4A90D9; margin-bottom: 0.5rem; }
.profile-card .role { color: var(--t2); font-size: 0.9rem; margin-bottom: 1rem; }
.profile-card .bio { color: var(--t1); font-size: 0.95rem; line-height: 1.6; }

/* ── 链接名片 ── */
.links-card {
    background: var(--cb);
    border: 1px solid #4A90D922;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.3rem 0.5rem 0.5rem 0.5rem;
}
.links-card.gold { border-color: #C9A84C22; }
.social-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-bottom: 0.7rem;
}
/* 图标按钮：正方形 + 圆角 */
.social-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    text-decoration: none !important;
    flex-shrink: 0;
    transition: opacity 0.15s, transform 0.1s;
}
.social-icon-btn:hover { opacity: 0.82; transform: scale(1.06); }
.social-icon-btn.tw { background: #000; }
.social-icon-btn.ig { background: linear-gradient(135deg,#f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%); }
.social-icon-btn.tt { background: #010101; }
.social-icon-btn.fb { background: #1877F2; }

.extra-links { display:flex; flex-direction:column; gap:0.35rem; }
.extra-link-row { font-size:0.83rem; }
.extra-link-row a {
    color:#4A90D9;
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.15s;
}
.extra-link-row a:hover { border-bottom-color: #4A90D9; }
.extra-link-row.gold a { color:#C9A84C; }
.extra-link-row.gold a:hover { border-bottom-color: #C9A84C; }

/* ── 竞选账号子区块 ── */
.campaign-sub {
    margin-top: 0.75rem;
    padding-top: 0.65rem;
    border-top: 1px solid #C9A84C22;
}
.campaign-label {
    font-size: 0.72rem;
    color: var(--t2);
    margin-bottom: 0.45rem;
    font-weight: 500;
}

.stat-box {
    background: var(--cb);
    border-left: 4px solid #4A90D9;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    margin: 0.5rem 0;
}
.stat-box .num { font-size: 2rem; font-weight: bold; color: #4A90D9; }
.stat-box .label { color: var(--t2); font-size: 0.9rem; }
@media (max-width: 640px) {
    .profile-card { margin: 0.3rem 0; }
    .links-card { margin: 0.3rem 0; }
    .stat-box .num { font-size: 1.5rem; }
}
</style>
""", unsafe_allow_html=True)

# ── 从 profile_items 加载重要链接 ────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _get_links(person: str):
    try:
        return get_supabase().table("profile_items").select("*") \
            .eq("person", person).eq("section", "links") \
            .order("sort_order").execute().data or []
    except Exception:
        return []

# ── 首页标题 ─────────────────────────────────────────────
_title = "S&amp;A 档案馆" if st.session_state.get("lang","zh") == "zh" else "S&amp;A Archive"
st.markdown(f"""
<div class="hero">
    <h1>🗂️ {_title}</h1>
    <p>{t("home_subtitle")}</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── 人物卡片 ─────────────────────────────────────────────
col1, col2 = st.columns(2)

# 社媒链接（固定）
_SS_SOCIAL = [
    ("tw", "𝕏",         "https://x.com/sejourne_s"),
    ("ig", "Instagram",  "https://www.instagram.com/stephanesejourne/"),
    ("fb", "Facebook",   "https://www.facebook.com/stephanesejourne/"),
]
_GA_SOCIAL = [
    ("tw", "𝕏",         "https://x.com/GabrielAttal"),
    ("ig", "Instagram",  "https://www.instagram.com/gabrielattal/"),
    ("tt", "TikTok",     "https://www.tiktok.com/@gabrielattal"),
    ("fb", "Facebook",   "https://www.facebook.com/gabriel.attal/"),
]

# ── 各平台 SVG 图标（内联，白色）────────────────────────
_SVG = {
    "tw": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="white">'
        '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231'
        '-5.401 6.231H2.742l7.746-8.855L1.254 2.25H8.08l4.261 5.632zm-1.161 17.52'
        'h1.833L7.084 4.126H5.117z"/></svg>'
    ),
    "ig": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="white">'
        '<path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919'
        '.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664'
        ' 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07'
        '-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204'
        '.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069'
        ' 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98'
        ' 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358'
        ' 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014'
        ' 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948'
        ' 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059'
        '-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163'
        ' 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0'
        ' 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791'
        ' 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44'
        'c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
    ),
    "tt": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="white">'
        '<path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1'
        '-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04'
        ' .79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0'
        ' 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.25 8.25 0 0 0 4.84 1.56V6.81'
        'a4.85 4.85 0 0 1-1.07-.12z"/></svg>'
    ),
    "fb": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="white">'
        '<path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388'
        ' 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669'
        ' 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925'
        '-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062'
        ' 24 12.073z"/></svg>'
    ),
}

def _social_row(items):
    btns = "".join(
        f'<a href="{url}" target="_blank" rel="noopener noreferrer"'
        f' class="social-icon-btn {cls}" title="{label}">'
        f'{_SVG[cls]}</a>'
        for cls, label, url in items
    )
    return f'<div class="social-row">{btns}</div>'

def _db_links(rows, color_cls):
    if not rows:
        return ""
    items = ""
    for r in rows:
        key = _html.escape(r.get("key","") or "")
        val = _html.escape(r.get("value","") or "")
        items += (
            f'<div class="extra-link-row {color_cls}">'
            f'<a href="{val}" target="_blank" rel="noopener noreferrer">🔗 {key}</a>'
            f'</div>'
        )
    return f'<div class="extra-links">{items}</div>'

ss_links = _get_links("Stéphane Séjourné")
ga_links = _get_links("Gabriel Attal")

with col1:
    st.markdown(f"""
    <div class="profile-card">
        <h2>Stéphane Séjourné <a href="https://en.wikipedia.org/wiki/St%C3%A9phane_S%C3%A9journ%C3%A9" target="_blank" style="font-size:1rem;text-decoration:none">🌐</a></h2>
        <div class="role">{t("ss_role")}</div>
        <div class="bio">{t("ss_bio")}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        f'<div class="links-card">'
        f'{_social_row(_SS_SOCIAL)}'
        f'{_db_links(ss_links, "")}'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    st.markdown(f"""
    <div class="profile-card">
        <h2>Gabriel Attal <a href="https://en.wikipedia.org/wiki/Gabriel_Attal" target="_blank" style="font-size:1rem;text-decoration:none">🌐</a></h2>
        <div class="role">{t("ga_role")}</div>
        <div class="bio">{t("ga_bio")}</div>
    </div>
    """, unsafe_allow_html=True)
    _ga_campaign = (
        '<div class="campaign-sub">'
        f'<div class="campaign-label">{t("campaign_label")}</div>'
        '<div class="social-row" style="margin-bottom:0">'
        '<a href="https://www.instagram.com/attalpresident_/" target="_blank" rel="noopener noreferrer"'
        ' class="social-icon-btn ig" title="Instagram">%s</a>'
        '</div>'
        '</div>'
    ) % _SVG["ig"]
    st.markdown(
        f'<div class="links-card gold">'
        f'{_social_row(_GA_SOCIAL)}'
        f'{_db_links(ga_links, "gold")}'
        f'{_ga_campaign}'
        f'</div>',
        unsafe_allow_html=True
    )

st.divider()

# ── 统计数字 ─────────────────────────────────────────────
st.subheader(t("home_stats"))

try:
    db = get_supabase()
    events_count = len(db.table("events").select("id").execute().data)
    news_count   = len(db.table("news").select("id").execute().data)
    files_count  = len(db.table("files").select("id").execute().data)
    images_count = len(db.table("images").select("id").execute().data)
except Exception:
    events_count = news_count = files_count = images_count = "—"

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-box"><div class="num">{events_count}</div><div class="label">{t("stat_events")}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-box"><div class="num">{news_count}</div><div class="label">{t("stat_news")}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-box"><div class="num">{files_count}</div><div class="label">{t("stat_files")}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="stat-box"><div class="num">{images_count}</div><div class="label">{t("stat_images")}</div></div>', unsafe_allow_html=True)

st.divider()
st.info(t("home_hint"))
