import streamlit as st
from utils.i18n import t

st.set_page_config(
    page_title="S&A 档案馆",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局样式：CSS 变量（日间默认）+ 徽章 + 手机端 + 字体 ──────
st.markdown("""
<style>
/* ── CSS 主题变量（日间默认，与 config.toml 保持一致）── */
:root {
    --cb:  #edf1ff;   /* card background        */
    --cb2: #e4eaff;   /* card background darker */
    --t1:  #1a1a2e;   /* primary card text      */
    --t2:  #5a5a72;   /* secondary / meta text  */
    --t3:  #6a6a80;   /* tertiary / dim text    */
    --bd:  #b0bcd8;   /* border / divider color */
}

/* ── 中文字形缩放：仅针对文字内容元素，不破坏图标字体 ── */
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
/* 只覆盖文字容器，不影响 Material Icons 等图标字体 */
p, h1, h2, h3, h4, h5, h6,
label, li, td, th, caption,
.stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown div,
[data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"] p,
[data-baseweb="select"] span,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
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

/* ── 隐藏 st.navigation 自动生成的分区标签（"app" / 单分组标题）── */
[data-testid="stSidebarNavSectionHeader"] {
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

/* ── 侧边栏展开/折叠箭头：日夜模式下都清晰可见 ── */
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button {
    background-color: #4A90D9 !important;
    border-radius: 6px !important;
    opacity: 1 !important;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapsedControl"] button svg path,
[data-testid="stSidebarCollapseButton"] button svg path {
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
}

/* ── 全局标题与标签字号缩小 ── */
/* 页面标题 h1（st.title）*/
h1 { font-size: 1.55rem !important; line-height: 1.3 !important; }
h2 { font-size: 1.25rem !important; }
h3 { font-size: 1.05rem !important; }
/* 筛选栏标签（人物 / 显示条数 / 搜索关键词等）*/
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label { font-size: 0.75rem !important; }
/* 下拉框 / 输入框内的文字 */
[data-baseweb="select"] span,
[data-baseweb="select"] div[class],
[data-baseweb="input"] input   { font-size: 0.82rem !important; }
/* caption 说明行（共显示 XX 条…）*/
[data-testid="stCaptionContainer"] p { font-size: 0.70rem !important; }
/* subheader / markdown 段落 */
.stMarkdown p { font-size: 0.88rem !important; }

/* ── 卡片元数据：西文保持原始字号，中文由 size-adjust:85% 自动缩小 ──
   不再手动覆盖 0.8rem / 0.85rem span（让 CJKScaled size-adjust 做差异化）
   仅对最小的徽章 span（0.7rem）略作压缩以保持紧凑 ── */
.stMarkdown span[style*="font-size:0.7rem"],
.stMarkdown span[style*="font-size: 0.7rem"]  { font-size: 0.68rem !important; }

/* ── Streamlit 原生按钮字号 ── */
[data-testid="stButton"] > button {
    font-size: 0.78rem !important;
    min-height: 1.8rem !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)

# ── 日间模式 CSS 变量覆盖 ──────────────────────────────────
_DARK_CSS = """
<style>
/* ── 夜间模式：覆盖 CSS 变量为深色 ── */
:root {
    --cb:  #16213e;
    --cb2: #0f1a30;
    --t1:  #e0e0e0;
    --t2:  #aaa;
    --t3:  #888;
    --bd:  #2a3a5c;
}

/* ── Streamlit 原生组件背景（深色）── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #1a1a2e !important;
    color: #e0e0e0 !important;
}
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #16213e !important;
}
[data-testid="stHeader"] {
    background-color: rgba(26,26,46,0.95) !important;
}
p, .stMarkdown p, label,
.stSelectbox label, .stTextInput label,
.stTextArea label,
[data-testid="stWidgetLabel"]   { color: #e0e0e0 !important; }
[data-testid="stCaptionContainer"] p { color: #aaa !important; }
hr { border-color: #2a3a5c !important; }
[data-testid="stExpander"]          { border-color: #2a3a5c !important; }
[data-testid="stExpanderDetails"]   { background-color: #16213e !important; }
[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button,
[data-testid="stFormSubmitButton"] > button {
    border-color: #2a3a5c !important;
    color: #e0e0e0 !important;
    background-color: #16213e !important;
}
[data-testid="stInfo"] { background-color: #1e2d4a !important; }

/* ── Streamlit baseweb 组件（深色）── */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="base-input"] {
    background-color: #0f1a30 !important;
    border-color: #2a3a5c !important;
    color: #e0e0e0 !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] div { color: #e0e0e0 !important; }
[data-baseweb="select"] svg { fill: #aaa !important; }
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background-color: #0f1a30 !important;
    color: #e0e0e0 !important;
    caret-color: #e0e0e0 !important;
}
[data-baseweb="input"] input::placeholder,
[data-baseweb="textarea"] textarea::placeholder { color: #555 !important; }
[data-baseweb="popover"],
[data-baseweb="popover"] div,
[data-baseweb="menu"],
[data-baseweb="menu"] div,
[data-baseweb="list"],
[data-baseweb="list"] div,
[role="listbox"],
[role="listbox"] div {
    background-color: #16213e !important;
    border-color: #2a3a5c !important;
}
[data-baseweb="option"],
[role="option"],
[data-baseweb="menu"] li,
li[data-baseweb="list-item"] {
    color: #e0e0e0 !important;
    background-color: #16213e !important;
    opacity: 1 !important;
}
[data-baseweb="option"]:hover,
[role="option"]:hover {
    background-color: #1e3a5f !important;
    color: #e0e0e0 !important;
}
[data-baseweb="option"][aria-selected="true"],
[role="option"][aria-selected="true"] {
    background-color: #2a4a70 !important;
    color: #e0e0e0 !important;
}
[data-baseweb="checkbox"] span,
[data-baseweb="radio"] span { color: #e0e0e0 !important; }
[data-baseweb="tab"] { color: #e0e0e0 !important; }
[data-baseweb="tab-list"] { background-color: #16213e !important; }
[data-testid="stNumberInput"] button { background-color: #16213e !important; color: #e0e0e0 !important; }
[data-testid="stToggle"] span { color: #e0e0e0 !important; }
[data-testid="stExpanderToggleIcon"] { color: #e0e0e0 !important; }
summary[data-testid="stExpanderSummary"] { color: #e0e0e0 !important; }
[data-testid="stProgress"] > div { background-color: #1e3a5f !important; }

/* ── 首页 / 图库 CSS 类（深色由 :root 变量驱动，此处仅补充链接色）── */
a[style*="color:#4A90D9"] { color: #4A90D9 !important; }
a[style*="color:#888"]    { color: #888 !important; }
</style>
"""

# ── 初始化状态 ────────────────────────────────────────────
if "light_mode" not in st.session_state:
    st.session_state.light_mode = True
if "lang" not in st.session_state:
    st.session_state.lang = "zh"

# ── 侧边栏顶部：品牌标题 + 主题 + 语言切换 ────────────────
with st.sidebar:
    st.markdown(
        f'<p style="font-size:1.05rem;font-weight:700;margin:0 0 0.2rem;'
        f'padding:0.3rem 0 0;color:var(--t1)">{t("app_title")}</p>',
        unsafe_allow_html=True
    )
    light = st.toggle(t("light_mode"), value=st.session_state.light_mode, key="_theme_toggle")
    if light != st.session_state.light_mode:
        st.session_state.light_mode = light
        st.rerun()
    is_zh = st.toggle("🌐 中文 / EN", value=(st.session_state.lang == "zh"), key="_lang_toggle")
    new_lang = "zh" if is_zh else "en"
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()
    st.divider()

pg = st.navigation([
    st.Page("pages/0_🗂️_首页.py",     title=t("nav_home"),      icon="🗂️"),
    st.Page("pages/12_💞_交织时间轴.py", title=t("nav_weave"),    icon="💞"),
    st.Page("pages/1_📅_大事记.py",    title=t("nav_timeline"),  icon="📖"),
    st.Page("pages/3_📰_新闻.py",      title=t("nav_news"),      icon="📰"),
    st.Page("pages/11_📆_行程日历.py", title=t("nav_schedule"),  icon="📆"),
    st.Page("pages/2_👤_人物档案.py",  title=t("nav_profiles"),  icon="👤"),
    st.Page("pages/10_📜_往期新闻.py", title=t("nav_archives"),  icon="📜"),
    st.Page("pages/6_🔗_资源导航.py",  title=t("nav_resources"), icon="🔗"),
    st.Page("pages/8_🏛️_团队成员.py", title=t("nav_team"),      icon="🏛️"),
    st.Page("pages/5_🗳️_选举参考.py", title=t("nav_election"),  icon="🗳️"),
    st.Page("pages/4_📊_媒体光谱.py",  title=t("nav_media"),     icon="📊"),
    st.Page("pages/9_🖼️_图库.py",     title=t("nav_gallery"),   icon="🖼️"),
    st.Page("pages/7_📁_文件上传.py",  title=t("nav_files"),     icon="📁"),
])

if not st.session_state.light_mode:
    st.markdown(_DARK_CSS, unsafe_allow_html=True)

pg.run()
