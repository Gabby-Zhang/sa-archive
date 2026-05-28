import streamlit as st

st.set_page_config(
    page_title="S&A 档案馆",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局样式：徽章 + 手机端 + 字体缩小 ──────────────────────
st.markdown("""
<style>
/* ── 隐藏 Created by 徽章 ── */
[data-testid="stDecoration"],
[data-testid="stDeployButton"],
.viewerBadge_container__r5tak,
.viewerBadge_link__qRIco,
[class*="viewerBadge"],
[class*="ViewerBadge"] {
    display: none !important;
}

/* ── 手机端响应式布局 ── */
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.3rem !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    [data-testid="stButton"] > button {
        min-height: 2.8rem !important;
        font-size: 0.95rem !important;
    }
    .mobile-flex { flex-wrap: wrap !important; gap: 0.3rem !important; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
}

/* ── 缩小所有卡片元数据标签（人名、来源、日期、徽章等）── */
/* 针对 span 元素（不影响 div 标题块）*/
.stMarkdown span[style*="font-size:0.8rem"],
.stMarkdown span[style*="font-size: 0.8rem"]  { font-size: 0.68rem !important; }
.stMarkdown span[style*="font-size:0.85rem"],
.stMarkdown span[style*="font-size: 0.85rem"] { font-size: 0.72rem !important; }
.stMarkdown span[style*="font-size:0.7rem"],
.stMarkdown span[style*="font-size: 0.7rem"]  { font-size: 0.60rem !important; }
.stMarkdown span[style*="font-size:0.73rem"],
.stMarkdown span[style*="font-size: 0.73rem"] { font-size: 0.62rem !important; }
/* 链接区小字 div */
.stMarkdown div[style*="font-size:0.85rem"],
.stMarkdown div[style*="font-size: 0.85rem"]  { font-size: 0.72rem !important; }
/* 备注 note div（0.85rem）也缩小 */
.stMarkdown div[style*="font-size:0.85rem"],
.stMarkdown div[style*="font-size: 0.85rem"]  { font-size: 0.72rem !important; }

/* ── Streamlit 原生按钮字号缩小 ── */
[data-testid="stButton"] > button {
    font-size: 0.78rem !important;
    min-height: 1.8rem !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)

# ── 日/夜间模式切换 ────────────────────────────────────────
if "light_mode" not in st.session_state:
    st.session_state.light_mode = False

_LIGHT_CSS = """
<style>
/* ════ 日间模式覆盖 ════ */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #f4f6fb !important;
    color: #1a1a2e !important;
}
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #e8ecf5 !important;
}
[data-testid="stHeader"] {
    background-color: rgba(244,246,251,0.95) !important;
}
/* ── 原生 Streamlit 组件 ── */
p, .stMarkdown p, label,
.stSelectbox label, .stTextInput label,
.stTextArea label, .stNumberInput label,
[data-testid="stWidgetLabel"] { color: #1a1a2e !important; }
[data-testid="stCaptionContainer"] p,
.stCaption, small { color: #5a5a7a !important; }
hr { border-color: #c4c8de !important; }
[data-testid="stExpander"] { border-color: #c4c8de !important; }
[data-testid="stExpanderDetails"] { background-color: #edf1ff !important; }
[data-testid="stButton"] > button {
    border-color: #bfc4d8 !important;
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
[data-testid="stInfo"] { background-color: #e2eaff !important; }
/* ── 自定义卡片背景 ── */
div[style*="background: #16213e"],
div[style*="background:#16213e"]  { background: #e8eeff !important; }
div[style*="background: #0f1a30"],
div[style*="background:#0f1a30"]  { background: #dce5ff !important; }
div[style*="background: #1e2d4a"],
div[style*="background:#1e2d4a"]  { background: #e2eaff !important; }
/* ── 自定义卡片文字 ── */
div[style*="color:#e0e0e0"], span[style*="color:#e0e0e0"] { color: #1a1a2e !important; }
div[style*="color:#ddd"],    span[style*="color:#ddd"]    { color: #2a2a3e !important; }
div[style*="color:#ccc"],    span[style*="color:#ccc"]    { color: #3a3a4e !important; }
div[style*="color:#bbb"],    span[style*="color:#bbb"]    { color: #4a4a60 !important; }
div[style*="color:#aaa"],    span[style*="color:#aaa"]    { color: #5a5a72 !important; }
div[style*="color:#888"],    span[style*="color:#888"]    { color: #6a6a80 !important; }
div[style*="color:#777"],    span[style*="color:#777"]    { color: #5a5a72 !important; }
div[style*="color:#666"],    span[style*="color:#666"]    { color: #5a5a70 !important; }
div[style*="color:#555"],    span[style*="color:#555"]    { color: #4a4a60 !important; }
/* ── 多来源徽章 / 分隔线 ── */
span[style*="background:#2a3a5c"],
span[style*="background: #2a3a5c"] { background: #c0c8e8 !important; color: #333 !important; }
div[style*="border-bottom:1px solid #2a3a5c"],
div[style*="border-bottom: 1px solid #2a3a5c"] { border-bottom-color: #b0bcd8 !important; }
div[style*="border:1px solid #2a3a5c"],
div[style*="border: 1px solid #2a3a5c"]        { border-color: #b0bcd8 !important; }
div[style*="border:1px solid #3d2a6e"],
div[style*="border: 1px solid #3d2a6e"]        { border-color: #b0a0d8 !important; }
/* ── 链接 ── */
a[style*="color:#4A90D9"],
a[style*="color: #4A90D9"] { color: #1a5db5 !important; }
a[style*="color:#888"]     { color: #5a6080 !important; }
</style>
"""

pg = st.navigation({
    "S&A 档案馆": [
        st.Page("pages/0_🗂️_首页.py",     title="首页",     icon="🗂️"),
        st.Page("pages/1_📅_大事记.py",    title="大事记",   icon="📅"),
        st.Page("pages/3_📰_新闻.py",      title="新闻",     icon="📰"),
        st.Page("pages/2_👤_人物档案.py",  title="人物档案", icon="👤"),
        st.Page("pages/4_📊_媒体光谱.py",  title="媒体光谱", icon="📊"),
        st.Page("pages/5_🗳️_选举参考.py", title="选举参考", icon="🗳️"),
        st.Page("pages/6_🔗_资源导航.py",  title="资源导航", icon="🔗"),
        st.Page("pages/7_📁_文件上传.py",   title="文件上传", icon="📁"),
        st.Page("pages/8_🏛️_团队成员.py", title="团队成员", icon="🏛️"),
        st.Page("pages/9_🖼️_图库.py",     title="图库",     icon="🖼️"),
        st.Page("pages/10_📜_往期新闻.py", title="往期新闻", icon="📜"),
    ]
})

# 侧边栏底部：主题切换（所有用户可见）
with st.sidebar:
    st.divider()
    light = st.toggle("☀️ 日间模式", value=st.session_state.light_mode, key="_theme_toggle")
    if light != st.session_state.light_mode:
        st.session_state.light_mode = light
        st.rerun()

if st.session_state.light_mode:
    st.markdown(_LIGHT_CSS, unsafe_allow_html=True)

pg.run()
