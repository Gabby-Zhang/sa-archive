import streamlit as st
from utils.auth import admin_sidebar
from utils.database import get_supabase
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
    padding: 1rem 1.2rem;
    margin: 0.3rem 0.5rem 0.5rem 0.5rem;
}
.links-card.gold { border-color: #C9A84C22; }
.social-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
}
.social-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.22rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    text-decoration: none !important;
    white-space: nowrap;
    transition: opacity 0.15s;
}
.social-btn:hover { opacity: 0.8; }
.social-btn.tw   { background:#000;    color:#fff !important; }
.social-btn.ig   { background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888); color:#fff !important; }
.social-btn.tt   { background:#010101; color:#fff !important; border:1px solid #69C9D0; }
.social-btn.fb   { background:#1877F2; color:#fff !important; }

.extra-links { display:flex; flex-direction:column; gap:0.3rem; }
.extra-link-row {
    display:flex; align-items:center; gap:0.5rem;
    font-size:0.82rem; color:var(--t1);
}
.extra-link-row a { color:#4A90D9; text-decoration:none; }
.extra-link-row a:hover { text-decoration:underline; }
.extra-link-label { color:var(--t2); font-size:0.75rem; min-width:4rem; }

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
st.markdown("""
<div class="hero">
    <h1>🗂️ 档案馆</h1>
    <p>Le Parcours de Séjourné et Attal — 持续建设中</p>
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

def _social_row(items):
    btns = "".join(
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="social-btn {cls}">{label}</a>'
        for cls, label, url in items
    )
    return f'<div class="social-row">{btns}</div>'

def _db_links(rows, color):
    if not rows:
        return ""
    items = ""
    for r in rows:
        key   = _html.escape(r.get("key","") or "")
        val   = _html.escape(r.get("value","") or "")
        items += (
            f'<div class="extra-link-row">'
            f'<span class="extra-link-label">{key}</span>'
            f'<a href="{val}" target="_blank" rel="noopener noreferrer" style="color:{color}">{val[:55]}{"…" if len(val)>55 else ""}</a>'
            f'</div>'
        )
    return f'<div class="extra-links">{items}</div>'

ss_links = _get_links("Stéphane Séjourné")
ga_links = _get_links("Gabriel Attal")

with col1:
    st.markdown("""
    <div class="profile-card">
        <h2>Stéphane Séjourné <a href="https://en.wikipedia.org/wiki/St%C3%A9phane_S%C3%A9journ%C3%A9" target="_blank" style="font-size:1rem;text-decoration:none">🌐</a></h2>
        <div class="role">🇪🇺 欧盟委员会执行副主席 · 工业战略专员</div>
        <div class="bio">
            1985年生，法国政治人物，复兴党（RE）创始成员之一。<br>
            曾任欧洲议会议员（2019–2024）、欧洲议会复兴党团主席、
            法国外交部长（2024）。<br>
            现任欧盟委员会执行副主席。
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        f'<div class="links-card">'
        f'{_social_row(_SS_SOCIAL)}'
        f'{_db_links(ss_links, "#4A90D9")}'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    st.markdown("""
    <div class="profile-card">
        <h2>Gabriel Attal <a href="https://en.wikipedia.org/wiki/Gabriel_Attal" target="_blank" style="font-size:1rem;text-decoration:none">🌐</a></h2>
        <div class="role">🏛️ 法国国民议会议员 · 复兴党（RE）主席</div>
        <div class="bio">
            1989年生，法国迄今最年轻的总理（2024年1月–9月）。<br>
            曾任教育部长、预算部长、政府发言人。<br>
            现任复兴党主席及国民议会议员（上塞纳省）。
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        f'<div class="links-card gold">'
        f'{_social_row(_GA_SOCIAL)}'
        f'{_db_links(ga_links, "#C9A84C")}'
        f'</div>',
        unsafe_allow_html=True
    )

st.divider()

# ── 统计数字 ─────────────────────────────────────────────
st.subheader("📊 档案馆概览")

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
    st.markdown(f"""
    <div class="stat-box">
        <div class="num">{events_count}</div>
        <div class="label">📅 大事记条目</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-box">
        <div class="num">{news_count}</div>
        <div class="label">📰 新闻条目</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="stat-box">
        <div class="num">{files_count}</div>
        <div class="label">📁 上传文件</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="stat-box">
        <div class="num">{images_count}</div>
        <div class="label">🖼️ 图库图片</div>
    </div>""", unsafe_allow_html=True)

st.divider()
st.info("👈 使用左侧导航栏切换各个板块")
