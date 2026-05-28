import streamlit as st

st.set_page_config(
    page_title="S&A 档案馆",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局样式：CSS 变量（深色默认）+ 徽章 + 手机端 + 字体 ──────
st.markdown("""
<style>
/* ── CSS 主题变量（深色默认）── */
:root {
    --cb:  #16213e;   /* card background        */
    --cb2: #0f1a30;   /* card background darker */
    --t1:  #e0e0e0;   /* primary card text      */
    --t2:  #aaa;      /* secondary / meta text  */
    --t3:  #888;      /* tertiary / dim text    */
    --bd:  #2a3a5c;   /* border / divider color */
}

/* ── 中文字形缩放：使 CJK 视觉大小与西文匹配 ── */
@font-face {
    font-family: "CJKScaled";
    src: local("PingFang SC"), local("Hiragino Sans GB"),
         local("Noto Sans SC"), local("Microsoft YaHei UI"),
         local("Microsoft YaHei"), local("WenQuanYi Micro Hei");
    unicode-range: U+4E00-9FFF, U+3400-4DBF, U+F900-FAFF,
                   U+2E80-2EFF, U+3000-303F, U+FF00-FFEF,
                   U+FE30-FE4F;
    size-adjust: 85%;
}
/* 全局字体栈：西文用 Source Sans Pro，中文用缩放版 */
.stApp, .stApp *:not(code):not(pre) {
    font-family: "Source Sans Pro", "CJKScaled", sans-serif !important;
}

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
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
}

/* ── 缩小卡片元数据标签字体（span，不影响 div 标题块）── */
.stMarkdown span[style*="font-size:0.8rem"],
.stMarkdown span[style*="font-size: 0.8rem"]  { font-size: 0.68rem !important; }
.stMarkdown span[style*="font-size:0.85rem"],
.stMarkdown span[style*="font-size: 0.85rem"] { font-size: 0.72rem !important; }
.stMarkdown span[style*="font-size:0.7rem"],
.stMarkdown span[style*="font-size: 0.7rem"]  { font-size: 0.60rem !important; }
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

# ── 日间模式 CSS 变量覆盖 ──────────────────────────────────
_LIGHT_CSS = """
<style>
/* ── 日间模式：覆盖 CSS 变量 ── */
:root {
    --cb:  #edf1ff;
    --cb2: #e4eaff;
    --t1:  #1a1a2e;
    --t2:  #5a5a72;
    --t3:  #6a6a80;
    --bd:  #b0bcd8;
}

/* ── Streamlit 原生组件背景 ── */
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
p, .stMarkdown p, label,
.stSelectbox label, .stTextInput label,
.stTextArea label,
[data-testid="stWidgetLabel"]   { color: #1a1a2e !important; }
[data-testid="stCaptionContainer"] p { color: #5a5a7a !important; }
hr { border-color: #c4c8de !important; }
[data-testid="stExpander"]          { border-color: #c4c8de !important; }
[data-testid="stExpanderDetails"]   { background-color: #edf1ff !important; }
[data-testid="stButton"] > button {
    border-color: #bfc4d8 !important;
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
[data-testid="stInfo"]  { background-color: #e2eaff !important; }

/* ── Streamlit 原生 baseweb 组件（下拉框、输入框等）── */
/* Select / Input 容器背景 */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="base-input"] {
    background-color: #ffffff !important;
    border-color: #bfc4d8 !important;
    color: #1a1a2e !important;
}
/* Select 当前值文字 & 箭头 */
[data-baseweb="select"] span,
[data-baseweb="select"] div { color: #1a1a2e !important; }
[data-baseweb="select"] svg { fill: #5a5a7a !important; }
/* 输入框内文字 */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background-color: #ffffff !important;
    color: #1a1a2e !important;
    caret-color: #1a1a2e !important;
}
/* 占位符文字 */
[data-baseweb="input"] input::placeholder,
[data-baseweb="textarea"] textarea::placeholder { color: #9a9ab0 !important; }
/* 下拉弹出菜单 */
[data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] [data-baseweb="list"] {
    background-color: #f4f6fb !important;
}
[data-baseweb="menu"] li,
[data-baseweb="list-item"] { color: #1a1a2e !important; }
[data-baseweb="menu"] li:hover,
[data-baseweb="option"]:hover { background-color: #e0e8ff !important; }
/* Checkbox / Radio */
[data-baseweb="checkbox"] span,
[data-baseweb="radio"] span { color: #1a1a2e !important; }
/* Tab / 分页 */
[data-baseweb="tab"] { color: #1a1a2e !important; }
[data-baseweb="tab-list"] { background-color: #edf1ff !important; }
/* Number input 按钮 */
[data-testid="stNumberInput"] button { background-color: #edf1ff !important; color: #1a1a2e !important; }
/* Toggle */
[data-testid="stToggle"] span { color: #1a1a2e !important; }
/* Expander title */
[data-testid="stExpanderToggleIcon"] { color: #1a1a2e !important; }
summary[data-testid="stExpanderSummary"] { color: #1a1a2e !important; }
/* Progress bar */
[data-testid="stProgress"] > div { background-color: #dce5ff !important; }

/* ── 首页 CSS 类 ── */
.profile-card {
    background: var(--cb) !important;
    border-color: #4A90D955 !important;
}
.profile-card .role  { color: var(--t2) !important; }
.profile-card .bio   { color: var(--t1) !important; }
.stat-box            { background: var(--cb) !important; }
.stat-box .label     { color: var(--t2) !important; }
.hero p              { color: var(--t2) !important; }

/* ── 图库 CSS 类 ── */
.gallery-card        { background: var(--cb) !important; }
.gallery-card .g-title { color: var(--t1) !important; }
.gallery-card .g-meta  { color: var(--t3) !important; }

/* ── 多来源徽章 ── */
a[style*="color:#4A90D9"] { color: #1a5db5 !important; }
a[style*="color:#888"]    { color: #5a6080 !important; }
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

# ── 侧边栏底部：主题切换（所有用户可见）────────────────────
if "light_mode" not in st.session_state:
    st.session_state.light_mode = False

with st.sidebar:
    st.divider()
    light = st.toggle("☀️ 日间模式", value=st.session_state.light_mode, key="_theme_toggle")
    if light != st.session_state.light_mode:
        st.session_state.light_mode = light
        st.rerun()

if st.session_state.light_mode:
    st.markdown(_LIGHT_CSS, unsafe_allow_html=True)

pg.run()
