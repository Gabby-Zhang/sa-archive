import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t, tlabel
from utils.database import get_supabase

admin_sidebar()

st.set_page_config(page_title="资源导航 · 档案馆", page_icon="🔗", layout="wide")

st.title(t("resources_title"))
st.caption("实用链接、图库来源、小工具汇总")

db = get_supabase()

def load_resources(tab):
    try:
        return db.table("resources").select("*").eq("tab", tab).order("category").order("sort_order").execute().data
    except Exception as e:
        st.error(f"加载失败：{e}")
        return []

def delete_resource(rid):
    db.table("resources").delete().eq("id", rid).execute()

# ── 管理员：添加条目 ─────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("➕ 添加条目", expanded=False):
        with st.form("add_resource_form"):
            c1, c2 = st.columns(2)
            with c1:
                r_tab      = st.selectbox("所属页签", ["官方链接", "图库来源", "小工具"])
                r_category = st.text_input("分类", placeholder="如：SS、GA、付费图库、小工具…")
                r_name     = st.text_input("名称 *")
            with c2:
                r_url  = st.text_input("链接（可选）")
                r_desc = st.text_area("说明/备注", height=80)
                r_icon = st.text_input("图标 emoji（可选）", placeholder="🔗")
            if st.form_submit_button("✅ 添加", use_container_width=True):
                if r_name:
                    db.table("resources").insert({
                        "tab": r_tab, "category": r_category,
                        "name": r_name, "url": r_url,
                        "description": r_desc, "icon": r_icon or "🔗",
                    }).execute()
                    st.success("已添加！")
                    st.rerun()
                else:
                    st.warning("请填写名称")

st.divider()

# ── 渲染函数 ─────────────────────────────────────────────
def render_link_card(r, color):
    url  = r.get("url", "")
    name = r.get("name", "")
    desc = r.get("description", "")
    icon = r.get("icon", "🔗")
    rid  = r.get("id")

    display_name = tlabel(name)
    if url:
        st.markdown(
            f'<a href="{url}" target="_blank" style="color:{color};font-size:0.95rem">'
            f'{icon} {display_name}</a><br><br>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<span style="color:#aaa;font-size:0.9rem">{icon} {display_name}</span><br><br>',
            unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        if st.button("🗑️", key=f"del_res_{rid}", help="删除"):
            delete_resource(rid)
            st.rerun()

def render_box_card(r, color):
    url  = r.get("url", "")
    name = r.get("name", "")
    desc = r.get("description", "")
    rid  = r.get("id")

    st.markdown(f"""
    <div style="background:var(--cb);padding:0.6rem 1rem;margin:0.3rem 0;border-radius:6px;
                display:flex;justify-content:space-between;align-items:center">
        <a href="{url}" target="_blank" style="color:{color};font-weight:bold">{name}</a>
        <span style="color:#aaa;font-size:0.85rem">{desc}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        if st.button("🗑️", key=f"del_res_{rid}", help="删除"):
            delete_resource(rid)
            st.rerun()

def render_tool_card(r):
    url  = r.get("url", "")
    name = r.get("name", "")
    desc = r.get("description", "")
    icon = r.get("icon", "🔧")
    rid  = r.get("id")

    st.markdown(f"""
    <div style="background:var(--cb);border:1px solid #333;padding:1rem 1.2rem;
                margin:0.5rem 0;border-radius:8px">
        <a href="{url}" target="_blank"
           style="color:#4A90D9;font-size:1rem;font-weight:bold;text-decoration:none">
            {icon} {name}
        </a>
        <div style="color:#aaa;font-size:0.9rem;margin-top:0.3rem">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        if st.button("🗑️", key=f"del_res_{rid}", help="删除"):
            delete_resource(rid)
            st.rerun()

# ── 三个 Tab ─────────────────────────────────────────────
_en = st.session_state.get("lang") == "en"
tab1, tab2, tab3 = st.tabs(
    ["📌 Official links", "🖼️ Image sources", "🛠️ Tools"]
    if _en else
    ["📌 官方链接", "🖼️ 图库来源", "🛠️ 小工具"]
)

# ── 官方链接 ─────────────────────────────────────────────
with tab1:
    items = load_resources("官方链接")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔵 Stéphane Séjourné")
        st.markdown(f"**🔗 {'Official pages' if _en else '官方页面'}**")
        for r in [i for i in items if i.get("category") == "SS"]:
            render_link_card(r, "#4A90D9")
        st.markdown(f"**📅 {'Regular appearances' if _en else '固定露面场合'}**")
        for r in [i for i in items if i.get("category") == "SS_日程"]:
            st.markdown(f"- {tlabel(r.get('name',''))}")
            if st.session_state.get("is_admin"):
                if st.button("🗑️", key=f"del_res_{r.get('id')}", help="删除"):
                    delete_resource(r.get("id"))
                    st.rerun()

    with col2:
        st.subheader("🟡 Gabriel Attal")
        st.markdown(f"**🔗 {'Official pages' if _en else '官方页面'}**")
        for r in [i for i in items if i.get("category") == "GA"]:
            render_link_card(r, "#C9A84C")
        st.markdown(f"**📅 {'Regular appearances' if _en else '固定露面场合'}**")
        for r in [i for i in items if i.get("category") == "GA_日程"]:
            url = r.get("url","")
            name = tlabel(r.get("name",""))
            if url:
                st.markdown(f"- [{name}]({url})")
            else:
                st.markdown(f"- {name}")
            if st.session_state.get("is_admin"):
                if st.button("🗑️", key=f"del_res_{r.get('id')}", help="删除"):
                    delete_resource(r.get("id"))
                    st.rerun()
        st.markdown(f"**📺 {'Video replays' if _en else '视频回放'}**")
        st.markdown(
            "- [📺 LCP – Replays Attal (QAG · débats · interviews)]"
            "(https://lcp.fr/recherche?q=attal&f%5B0%5D=type_de_contenu%3Aepisode)"
        )
        st.caption("La Chaîne Parlementaire · " + ("parliament TV channel" if _en else "议会电视台"))

# ── 图库来源 ─────────────────────────────────────────────
with tab2:
    items = load_resources("图库来源")

    st.subheader("💰 " + ("Paid archives" if _en else "付费图库"))
    st.caption("Subscription required; downloaded images may have watermarks and vary by region." if _en else "需要订阅，非购买下载的图片会带水印，不同地区图片会有所差异")
    for r in [i for i in items if i.get("category") == "付费图库"]:
        render_box_card(r, "#4A90D9")

    st.subheader("🆓 " + ("Official free archives" if _en else "官方免费图库"))
    for r in [i for i in items if i.get("category") == "官方免费图库"]:
        render_box_card(r, "#7EC8A4")

# ── 小工具 ───────────────────────────────────────────────
with tab3:
    items = load_resources("小工具")
    for r in items:
        render_tool_card(r)
