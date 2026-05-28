import streamlit as st

st.set_page_config(page_title="资源导航 · 档案馆", page_icon="🔗", layout="wide")

st.title("🔗 资源导航")
st.caption("实用链接、图库来源、小工具汇总")

tab1, tab2, tab3 = st.tabs(["📌 官方链接", "🖼️ 图库来源", "🛠️ 小工具"])

# ── 官方链接 ─────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟡 Stéphane Séjourné")
        ss_links = [
            ("欧委会官方页面（EC）", "https://commission.europa.eu/about/organisation/college-commissioners/stephane-sejourne_en"),
            ("欧委会新闻室（每周行程）", "https://ec.europa.eu/commission/presscorner/home/en"),
            ("利益申报（HATVP）", "https://www.hatvp.fr/fiche-nominative/?declarant=sejourne-stephane"),
        ]
        for label, url in ss_links:
            st.markdown(f'<a href="{url}" target="_blank" style="color:#4A90D9;font-size:0.95rem">🔗 {label}</a><br><br>', unsafe_allow_html=True)

        st.markdown("**📅 固定露面场合**")
        st.markdown("- 每周三：欧委会例会")

    with col2:
        st.subheader("🔵 Gabriel Attal")
        ga_links = [
            ("国民议会页面（AN）", "https://www.assemblee-nationale.fr/dyn/deputes/PA722190"),
            ("复兴党官网（RE）", "https://parti-renaissance.fr/le-parti"),
            ("利益申报（HATVP）", "https://www.hatvp.fr/fiche-nominative/?declarant=attal-gabriel"),
        ]
        for label, url in ga_links:
            st.markdown(f'<a href="{url}" target="_blank" style="color:#C9A84C;font-size:0.95rem">🔗 {label}</a><br><br>', unsafe_allow_html=True)

        st.markdown("**📅 固定露面场合**")
        st.markdown("- 每周二：一般固定 EPR 小组会")
        st.markdown("- 国民议会会期：每周出席")
        st.markdown("- 粉丝行程追踪账号：[@GAttalActu](https://x.com/GAttalActu)（X平台）")

# ── 图库来源 ─────────────────────────────────────────────
with tab2:
    st.subheader("💰 付费图库")
    st.caption("需要订阅，非购买下载的图片会带水印，不同地区图片会有所差异")
    paid_sources = [
        ("Getty Images", "https://www.gettyimages.com/", "比较全比较新 ✅"),
        ("Alamy", "https://www.alamy.com/", "比较全 ✅"),
        ("Shutterstock", "https://www.shutterstock.com/zh/editorial/", "比较全比较新 ✅"),
        ("Divergence Images", "https://www.divergence-images.com", "很多区别去Getty和Alamy的图 ✅"),
        ("Imago Images", "https://www.imago-images.com/", "偶尔有区别去Getty和Alamy的图"),
        ("AFP Forum", "https://www.afpforum.com/afoimages/index.html#/app", "法新社，视频有一些是独家的但难下载"),
        ("ANP Foto", "https://www.anpfoto.nl/", "荷兰国家通讯社，有一些些区别AFP的图，难下"),
        ("Belga Image", "https://www.belgaimage.be/", "比利时通讯社，有一些些区别AFP的图"),
    ]
    for name, url, note in paid_sources:
        st.markdown(f"""
        <div style="background:#16213e;padding:0.6rem 1rem;margin:0.3rem 0;border-radius:6px;
                    display:flex;justify-content:space-between;align-items:center">
            <a href="{url}" target="_blank" style="color:#4A90D9;font-weight:bold">{name}</a>
            <span style="color:#aaa;font-size:0.85rem">{note}</span>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("🆓 官方免费图库")
    free_sources = [
        ("Renew Europe（Flickr）", "https://www.flickr.com/photos/reneweuropegroup/", "偶有 SS"),
        ("欧委会影音库", "https://audiovisual.ec.europa.eu/en/", "常有 SS"),
        ("欧洲议会多媒体", "https://multimedia.europarl.eu/en", "偶有 SS"),
        ("法国国民议会（LCP TV）", "https://lcp.fr/guide-tv/100", "直播/回放，GA坐班，有CC字幕"),
    ]
    for name, url, note in free_sources:
        st.markdown(f"""
        <div style="background:#16213e;padding:0.6rem 1rem;margin:0.3rem 0;border-radius:6px;
                    display:flex;justify-content:space-between;align-items:center">
            <a href="{url}" target="_blank" style="color:#7EC8A4;font-weight:bold">{name}</a>
            <span style="color:#aaa;font-size:0.85rem">{note}</span>
        </div>
        """, unsafe_allow_html=True)

# ── 小工具 ───────────────────────────────────────────────
with tab3:
    tools = [
        {
            "name": "沉浸式翻译",
            "url": "https://immersivetranslate.com",
            "desc": "浏览器扩展，网页双语对照翻译，带CC字幕的视频也适用。精准翻译可多用AI模式",
            "icon": "🌐"
        },
        {
            "name": "网页图片下载工具",
            "url": "https://extract.pics",
            "desc": "一键提取网页上所有图片",
            "icon": "🖼️"
        },
        {
            "name": "Alamy去水印下载",
            "url": "https://steptodown.com/alamy-downloader.php",
            "desc": "Alamy图片无水印下载工具",
            "icon": "⬇️"
        },
        {
            "name": "archive.ph",
            "url": "https://archive.ph",
            "desc": "网页存档工具，可绕过大部分付费墙阅读新闻全文",
            "icon": "📦"
        },
        {
            "name": "12ft.io",
            "url": "https://12ft.io",
            "desc": "另一个绕过付费墙的工具，在地址栏前加 12ft.io/ 即可",
            "icon": "🔓"
        },
    ]
    for t in tools:
        st.markdown(f"""
        <div style="background:#16213e;border:1px solid #333;padding:1rem 1.2rem;
                    margin:0.5rem 0;border-radius:8px">
            <a href="{t['url']}" target="_blank"
               style="color:#4A90D9;font-size:1rem;font-weight:bold;text-decoration:none">
                {t['icon']} {t['name']}
            </a>
            <div style="color:#aaa;font-size:0.9rem;margin-top:0.3rem">{t['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
