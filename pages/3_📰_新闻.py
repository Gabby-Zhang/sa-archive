import streamlit as st
from utils.auth import admin_sidebar

admin_sidebar()
from datetime import datetime
from utils.database import get_news, add_news_manual, add_event, delete_news, get_supabase
from utils.news_fetcher import fetch_all_news
from utils.media_spectrum import get_media_info, LEAN_EMOJI

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
    person_filter = st.selectbox("人物", ["全部", "Gabriel Attal", "Stéphane Séjourné", "S&A"])
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
    "S&A": "#FF6B9D",
}

for item in news:
    color = PERSON_COLOR.get(item.get("person", ""), "#888")
    url = item.get("url", "")
    archive_url = f"https://www.removepaywall.com/{url}" if url else ""

    pub_date = item.get("published_at", "")
    if pub_date:
        try:
            pub_date = datetime.fromisoformat(pub_date).strftime("%Y-%m-%d")
        except Exception:
            pass

    # 媒体政治立场
    media_info = get_media_info(item.get("source", ""))
    lean_label = media_info["label"]
    lean_color = media_info["color"]
    lean_emoji = LEAN_EMOJI.get(lean_label, "")

    st.markdown(f"""
    <div style="
        border-left: 4px solid {color};
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
        background:var(--cb);
        border-radius: 0 8px 8px 0;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.4rem">
            <div>
                <span style="color:{color};font-size:0.8rem;font-weight:bold">
                    {item.get("person","")}
                </span>
                <span style="margin-left:0.8rem">
                    <span style="background:{lean_color};color:white;padding:0.05rem 0.4rem;border-radius:3px;font-size:0.7rem;font-weight:bold">{lean_emoji} {lean_label}</span>
                    <span style="color:#888;font-size:0.8rem;margin-left:0.3rem">{item.get("source","")}</span>
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
        <div style="color:var(--t1);margin-top:0.4rem;font-size:0.95rem">
            {item.get("title","")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 管理员专用：操作按钮
    if st.session_state.get("is_admin"):
        item_id = item.get("id", "")

        # ── 关联到已有大事记的搜索 UI ────────────────────────
        if st.session_state.get(f"linking_{item_id}"):
            st.markdown(
                '<div style="background:var(--cb2);border:1px solid var(--bd);'
                'border-radius:6px;padding:0.6rem 1rem;margin:0.3rem 0">'
                '<span style="color:#8B6FD4;font-size:0.8rem;font-weight:bold">'
                '📅 选择要关联的大事记条目</span></div>',
                unsafe_allow_html=True
            )
            search_q = st.text_input(
                "搜索大事记标题关键词",
                key=f"ev_search_{item_id}",
                placeholder="留空显示最近 20 条…",
            )
            try:
                _db = get_supabase()
                _q  = _db.table("events").select("id,title,date,person")
                if search_q:
                    _q = _q.ilike("title", f"%{search_q}%")
                _ev_rows = _q.order("date", desc=True).limit(20).execute().data
            except Exception:
                _ev_rows = []

            if _ev_rows:
                _ev_map = {
                    f"{str(e.get('date',''))[:10]}  ·  {e.get('person','')}  ·  {(e.get('title','') or '')[:45]}": e
                    for e in _ev_rows
                }
                _sel_label = st.selectbox("选择条目", list(_ev_map.keys()), key=f"ev_sel_{item_id}")
                _sel_ev    = _ev_map.get(_sel_label)
                lc1, lc2 = st.columns(2)
                with lc1:
                    if st.button("✅ 确认关联", key=f"do_link_{item_id}", use_container_width=True):
                        if _sel_ev:
                            get_supabase().table("event_links").insert({
                                "event_id": str(_sel_ev["id"]),
                                "title":    item.get("title", ""),
                                "url":      url,
                                "type":     "📰 新闻报道",
                                "source":   item.get("source", ""),
                            }).execute()
                            st.session_state.pop(f"linking_{item_id}", None)
                            st.success(f"✅ 已关联到「{(_sel_ev.get('title','') or '')[:30]}…」")
                            st.rerun()
                with lc2:
                    if st.button("✕ 取消", key=f"cancel_link_{item_id}", use_container_width=True):
                        st.session_state.pop(f"linking_{item_id}", None)
                        st.rerun()
            else:
                st.info("未找到匹配的大事记")
                if st.button("✕ 取消", key=f"cancel_link2_{item_id}"):
                    st.session_state.pop(f"linking_{item_id}", None)
                    st.rerun()

        else:
            # ── 正常按钮行 ───────────────────────────────────
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("📌 新建大事记", key=f"pin_{item_id}", use_container_width=True):
                    add_event({
                        "date": pub_date,
                        "person": item.get("person", ""),
                        "title": item.get("title", ""),
                        "source": item.get("source", ""),
                        "source_url": url,
                        "note": "",
                    })
                    st.success("✅ 已加入大事记！")
            with bc2:
                if st.button("🔗 关联已有", key=f"link_{item_id}", use_container_width=True):
                    st.session_state[f"linking_{item_id}"] = True
                    st.rerun()
            with bc3:
                if st.button("🗑️ 删除", key=f"del_news_{item_id}", use_container_width=True):
                    delete_news(item_id)
                    st.rerun()

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
            new_person = st.selectbox("相关人物", ["Gabriel Attal", "Stéphane Séjourné", "S&A"])
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
