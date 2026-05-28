import streamlit as st
from utils.auth import admin_sidebar
from utils.database import get_supabase

admin_sidebar()

# ── 样式 ────────────────────────────────────────────────
st.markdown("""
<style>
.hero { text-align: center; padding: 2rem 0 1rem 0; }
.hero h1 { font-size: 2.5rem; color: #4A90D9; letter-spacing: 2px; }
.hero p { color: #aaa; font-size: 1.1rem; }
.profile-card {
    background: #16213e;
    border: 1px solid #4A90D944;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 0.5rem;
    text-align: center;
}
.profile-card h2 { color: #4A90D9; margin-bottom: 0.5rem; }
.profile-card .role { color: #aaa; font-size: 0.9rem; margin-bottom: 1rem; }
.profile-card .bio { color: #ccc; font-size: 0.95rem; line-height: 1.6; }
.stat-box {
    background: #16213e;
    border-left: 4px solid #4A90D9;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    margin: 0.5rem 0;
}
.stat-box .num { font-size: 2rem; font-weight: bold; color: #4A90D9; }
.stat-box .label { color: #aaa; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

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

with col1:
    st.markdown("""
    <div class="profile-card">
        <h2>Stéphane Séjourné</h2>
        <div class="role">🇪🇺 欧盟委员会执行副主席 · 工业战略专员</div>
        <div class="bio">
            1985年生，法国政治人物，复兴党（RE）创始成员之一。<br>
            曾任欧洲议会议员（2019–2024）、欧洲议会复兴党团主席、
            法国外交部长（2024）。<br>
            现任欧盟委员会执行副主席。
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="profile-card">
        <h2>Gabriel Attal</h2>
        <div class="role">🏛️ 法国国民议会议员 · 复兴党（RE）主席</div>
        <div class="bio">
            1989年生，法国迄今最年轻的总理（2024年1月–9月）。<br>
            曾任教育部长、预算部长、政府发言人。<br>
            现任复兴党主席及国民议会议员（上塞纳省）。
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── 统计数字 ─────────────────────────────────────────────
st.subheader("📊 档案馆概览")

try:
    db = get_supabase()
    events_count = len(db.table("events").select("id").execute().data)
    news_count = len(db.table("news").select("id").execute().data)
    files_count = len(db.table("files").select("id").execute().data)
except Exception:
    events_count = news_count = files_count = "—"

c1, c2, c3 = st.columns(3)
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

st.divider()
st.info("👈 使用左侧导航栏切换各个板块")
