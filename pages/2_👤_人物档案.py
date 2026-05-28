import streamlit as st

st.set_page_config(page_title="人物档案 · 档案馆", page_icon="👤", layout="wide")

st.title("👤 人物档案")
st.caption("家人、亲友团与个人喜好")

# ── 人物选择 ─────────────────────────────────────────────
tab_ss, tab_ga = st.tabs(["🟡 Stéphane Séjourné", "🔵 Gabriel Attal"])

# ════════════════════════════════════════════════════════
# STÉPHANE SÉJOURNÉ
# ════════════════════════════════════════════════════════
with tab_ss:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("👨‍👩‍👧 家人")
        family_ss = [
            ("Steph爸爸", "爸爸"),
            ("Steph妈妈", "妈妈"),
            ("Sandy", "妹妹"),
        ]
        for name, rel in family_ss:
            st.markdown(f"""
            <div style="background:#16213e;border-left:3px solid #C9A84C;
                        padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">
                <span style="color:#C9A84C;font-weight:bold">{name}</span>
                <span style="color:#aaa;margin-left:0.8rem;font-size:0.9rem">{rel}</span>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("🤝 普瓦捷帮")
        crew_ss = [
            ("Pierre Person", "2020年离开LREM，离开政坛，创业做CEO"),
            ("Sacha Houlié", "2024年离开RE/EPR，还是议员"),
            ("Aurélien Taché", "2020年离开LREM，现在是LFI 议员"),
            ("Guillaume Chiche", "2020年离开LREM，没选上议员"),
        ]
        for name, note in crew_ss:
            st.markdown(f"""
            <div style="background:#16213e;border-left:3px solid #C9A84C44;
                        padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">
                <span style="color:#e0e0e0;font-weight:bold">{name}</span>
                <div style="color:#aaa;font-size:0.85rem;margin-top:0.2rem">{note}</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("❤️ 个人喜好")
        prefs_ss = {
            "🥃 喜欢的酒": "Lagavulin（whisky）",
            "📺 喜欢的电视剧": "Nox（法剧 2018）\nThe Crown\nBaron noir（他是这个剧的剧本顾问）",
            "🎬 喜欢的电影": "Super8（提过但不喜欢，找不到更多了）",
        }
        for k, v in prefs_ss.items():
            st.markdown(f"""
            <div style="background:#16213e;border:1px solid #C9A84C33;
                        padding:0.8rem 1rem;margin:0.5rem 0;border-radius:8px">
                <div style="color:#C9A84C;font-size:0.85rem;margin-bottom:0.3rem">{k}</div>
                <div style="color:#e0e0e0;white-space:pre-line">{v}</div>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("🔗 重要链接")
        links_ss = [
            ("欧委会官方页面", "https://commission.europa.eu/about/organisation/college-commissioners/stephane-sejourne_en"),
            ("欧委会新闻室", "https://ec.europa.eu/commission/presscorner/home/en"),
            ("利益申报", "https://www.hatvp.fr/fiche-nominative/?declarant=sejourne-stephane"),
        ]
        for label, url in links_ss:
            st.markdown(f'<a href="{url}" target="_blank" style="color:#C9A84C">🔗 {label}</a><br>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# GABRIEL ATTAL
# ════════════════════════════════════════════════════════
with tab_ga:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("👨‍👩‍👧 家人")
        family_ga = [
            ("Yven Attal", "爸爸（2015年去世）"),
            ("Marie de Couriss", "妈妈"),
            ("Martin Genot", "继父"),
            ("Noémie", "同父异母的大姐"),
            ("Fanny", "妹妹"),
            ("Iris", "妹妹"),
            ("Nikolaï", "妈妈收养的弟弟"),
            ("Volta", "女儿（🐕 狗）"),
        ]
        for name, rel in family_ga:
            st.markdown(f"""
            <div style="background:#16213e;border-left:3px solid #4A90D9;
                        padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">
                <span style="color:#4A90D9;font-weight:bold">{name}</span>
                <span style="color:#aaa;margin-left:0.8rem;font-size:0.9rem">{rel}</span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("❤️ 个人喜好")
        prefs_ga = {
            "🥤 喜欢的饮品": "健怡可乐",
            "🍔 喜欢的食物": "汉堡，披萨",
            "🐾 猫还是狗": "狗（喜欢哈士奇，但养了松狮 Volta）",
            "📺 喜欢的电视剧": (
                "Clairement Game of Thrones《权力的游戏》\n"
                "Chernobyl《切尔诺贝利》\n"
                "Handmaid's Tale《使女的故事》\n"
                "Guyane《法属圭亚那》\n"
                "Casa de Papel《纸钞屋》\n"
                "Big Little Lies《大小谎言》\n"
                "The OA《先见之明》\n"
                "继承之战\n实习医生格蕾"
            ),
            "🎬 喜欢的电影": "《零花钱》（大概看了150遍，很有品位！）\n《星球大战》",
            "🎭 喜欢的综艺": "Koh-Lanta《兰塔岛》\nFort Boyard《城堡探险》",
            "🎵 喜欢的音乐": "[Spotify 歌单](https://open.spotify.com/playlist/0NSEz0wEY9sm7yVLmjFDPJ?si=12267a7df1e8449b)",
        }
        for k, v in prefs_ga.items():
            st.markdown(f"""
            <div style="background:#16213e;border:1px solid #4A90D933;
                        padding:0.8rem 1rem;margin:0.5rem 0;border-radius:8px">
                <div style="color:#4A90D9;font-size:0.85rem;margin-bottom:0.3rem">{k}</div>
                <div style="color:#e0e0e0;white-space:pre-line">{v}</div>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("🔗 重要链接")
        links_ga = [
            ("国民议会页面", "https://www.assemblee-nationale.fr/dyn/deputes/PA722190"),
            ("复兴党官网", "https://parti-renaissance.fr/le-parti"),
            ("利益申报", "https://www.hatvp.fr/fiche-nominative/?declarant=attal-gabriel"),
        ]
        for label, url in links_ga:
            st.markdown(f'<a href="{url}" target="_blank" style="color:#4A90D9">🔗 {label}</a><br>', unsafe_allow_html=True)
