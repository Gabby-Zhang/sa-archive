import streamlit as st

st.set_page_config(
    page_title="S&A 档案馆",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 全局样式：隐藏徽章 + 手机端优化
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

    /* 减少页面边距，让内容更宽 */
    [data-testid="stMainBlockContainer"] {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    /* 所有多列布局在手机上改为竖排 */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.3rem !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* 按钮更大更易点击 */
    [data-testid="stButton"] > button {
        min-height: 2.8rem !important;
        font-size: 0.95rem !important;
    }

    /* 卡片内链接区域自动换行 */
    .mobile-flex {
        flex-wrap: wrap !important;
        gap: 0.3rem !important;
    }

    /* 标题字号适配 */
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
}
</style>
""", unsafe_allow_html=True)

pg = st.navigation({
    "S&A 档案馆": [
        st.Page("pages/0_🗂️_首页.py",     title="首页",   icon="🗂️"),
        st.Page("pages/1_📅_大事记.py",    title="大事记", icon="📅"),
        st.Page("pages/2_👤_人物档案.py",  title="人物档案", icon="👤"),
        st.Page("pages/3_📰_新闻.py",      title="新闻",   icon="📰"),
        st.Page("pages/4_📊_媒体光谱.py",  title="媒体光谱", icon="📊"),
        st.Page("pages/5_🗳️_选举参考.py", title="选举参考", icon="🗳️"),
        st.Page("pages/6_🔗_资源导航.py",  title="资源导航", icon="🔗"),
        st.Page("pages/7_📁_文件上传.py",  title="文件上传", icon="📁"),
        st.Page("pages/8_🏛️_团队成员.py", title="团队成员", icon="🏛️"),
        st.Page("pages/9_🖼️_图库.py",     title="图库",   icon="🖼️"),
    ]
})
pg.run()
