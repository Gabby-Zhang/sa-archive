import streamlit as st

st.set_page_config(
    page_title="S&A 档案馆",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 隐藏 Streamlit Cloud 的 "Created by" 头像徽章
st.markdown("""
<style>
.viewerBadge_container__r5tak,
.viewerBadge_link__qRIco,
[data-testid="stDecoration"],
#stDecoration {
    display: none !important;
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
