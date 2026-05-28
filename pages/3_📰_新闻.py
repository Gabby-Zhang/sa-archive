import streamlit as st
from datetime import datetime
from utils.database import get_news, add_news_manual
from utils.news_fetcher import fetch_all_news

st.set_page_config(page_title="新闻 · 档案馆", page_icon="📰", layout="wide")

st.title("📰 新闻档案")
st.caption("自动抓取 + 手动添加的新闻汇总")

# ── 刷新按钮 ─────────────────────────────────────────────
col_btn, col_info = st.columns([1, 4])
with col_btn:
    if st.button("🔄 抓取最新新闻"):
        with st.spinner("正在抓取…"):
            try:
                n = fetch_all_news()
                st.success(f"已更新 {n} 条新闻")
            except Exception as e:
                st.error(f"抓取失败：{e}")
with col_info:
    st.caption("点击按钮从 Google News 抓取最新报道（每次约 30–60 条）")

st.divider()

# ── 筛选栏 ───────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "两人"])
with col2:
    limit = st.selectbox("显示条数", [50, 100, 200], index=0)
with col3:
    keyword = st.text_input("🔍 搜索关键词", placeholder="输入关键词…")

# ── 加载数据 ─────────────────────────────────────────────
try:
    news = get_news(
        person=person_filter if person_filter != "全部" else None,
        keyword=keyword if keyword else None,
        limit=limit,
    )
except Exception as e:
    st.error(f"数据库连接失败：{e}")
    news = []

st.caption(f"共显示 {len(news)} 条新闻")

# ── 新闻列表 ─────────────────────────────────────────────
PERSON_COLOR = {
    "Gabriel Attal": "#C9A84C",
    "Stéphane Séjourné": "#4A90D9",
    "两人": "#7EC8A4",
}

for item in news:
    color = PERSON_COLOR.get(item.get("person", ""), "#888")
    url = item.get("url", "")
    archive_url = f"https://archive.ph/{url}" if url else ""

    pub_date = item.get("published_at", "")
    if pub_date:
        try:
            pub_date = datetime.fromisoformat(pub_date).strftime("%Y-%m-%d")
        except Exception:
            pass

    st.markdown(f"""
    <div style="
        border-left: 4px solid {color};
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
        background: #16213e;
        border-radius: 0 8px 8px 0;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem">
            <div>
                <span style="color:{color};font-size:0.8rem;font-weight:bold">
                    {item.get("person","")}
                </span>
                <span style="color:#666;font-size:0.8rem;margin-left:0.8rem">
                    {item.get("source","")}
                </span>
                <span style="color:#555;font-size:0.8rem;margin-left:0.8rem">
                    {pub_date}
                </span>
            </div>
            <div style="display:flex;gap:1rem;font-size:0.85rem">
                {"<a href='" + url + "' target='_blank' style='color:#4A90D9'>🔗 原文</a>" if url else ""}
                {"<a href='" + archive_url + "' target='_blank' style='color:#888'>📦 存档版</a>" if url else ""}
            </div>
        </div>
        <div style="color:#e0e0e0;margin-top:0.4rem;font-size:0.95rem">
            {item.get("title","")}
        </div>
    </div>
    """, unsafe_allow_html=True)

if not news:
    st.info("暂无新闻，点击上方「抓取最新新闻」按钮开始收集。")

st.divider()

# ── 手动添加新闻 ─────────────────────────────────────────
with st.expander("➕ 手动添加新闻"):
    with st.form("add_news_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_title = st.text_input("新闻标题 *")
            new_url = st.text_input("链接 *")
            new_person = st.selectbox("相关人物", ["Gabriel Attal", "Stéphane Séjourné", "两人"])
        with c2:
            new_source = st.text_input("来源媒体")
            new_date = st.date_input("发布日期")
            new_summary = st.text_area("摘要（可选）", height=80)
        submitted = st.form_submit_button("添加")
        if submitted:
            if new_title and new_url:
                import hashlib
                add_news_manual({
                    "id": hashlib.md5(new_url.encode()).hexdigest(),
                    "title": new_title,
                    "url": new_url,
                    "source": new_source,
                    "person": new_person,
                    "published_at": str(new_date),
                    "summary": new_summary,
                })
                st.success("已添加！")
                st.rerun()
            else:
                st.warning("请填写标题和链接")
