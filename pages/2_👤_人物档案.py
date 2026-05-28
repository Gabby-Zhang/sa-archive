import streamlit as st
from utils.auth import admin_sidebar
from utils.database import get_supabase

admin_sidebar()

st.set_page_config(page_title="人物档案 · 档案馆", page_icon="👤", layout="wide")

st.title("👤 人物档案")
st.caption("家人、亲友团与个人喜好")

db = get_supabase()

PERSON_COLOR = {
    "Stéphane Séjourné": "#4A90D9",
    "Gabriel Attal":     "#C9A84C",
}

SECTION_LABELS = {
    "family":      "👨‍👩‍👧 家人",
    "crew":        "🤝 亲友团",
    "preferences": "❤️ 个人喜好",
    "links":       "🔗 重要链接",
}

def load_section(person, section):
    try:
        return db.table("profile_items").select("*") \
            .eq("person", person).eq("section", section) \
            .order("sort_order").execute().data
    except:
        return []

def delete_item(iid):
    db.table("profile_items").delete().eq("id", iid).execute()

def update_item(iid, data):
    db.table("profile_items").update(data).eq("id", iid).execute()

# ── 管理员：添加条目 ─────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("➕ 添加条目", expanded=False):
        with st.form("add_profile_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_person  = st.selectbox("人物", ["Stéphane Séjourné", "Gabriel Attal"])
                p_section = st.selectbox("分类", ["family", "crew", "preferences", "links"],
                                         format_func=lambda x: SECTION_LABELS.get(x, x))
                p_key     = st.text_input("名称 / 标签 *", placeholder="如：Sandy、🥃 喜欢的酒")
            with c2:
                p_value = st.text_input("内容 / 链接", placeholder="关系、偏好内容或 URL")
                p_note  = st.text_area("备注", height=80)
            if st.form_submit_button("✅ 添加", use_container_width=True):
                if p_key:
                    db.table("profile_items").insert({
                        "person": p_person, "section": p_section,
                        "key": p_key, "value": p_value, "note": p_note,
                    }).execute()
                    st.success("已添加！")
                    st.rerun()
                else:
                    st.warning("请填写名称")

st.divider()

# ── 渲染各区块 ────────────────────────────────────────────
def render_section(person, section):
    items = load_section(person, section)
    color = PERSON_COLOR[person]

    if not items:
        st.caption("暂无数据")
        return

    if "editing_profile" not in st.session_state:
        st.session_state.editing_profile = None

    for item in items:
        iid = item.get("id")

        # ── 编辑模式 ──────────────────────────────────────
        if st.session_state.editing_profile == iid:
            with st.form(key=f"edit_profile_{iid}"):
                ek = st.text_input("名称/标签", value=item.get("key",""))
                ev = st.text_input("内容/链接", value=item.get("value","") or "")
                en = st.text_area("备注", value=item.get("note","") or "", height=68)
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.form_submit_button("💾 保存", use_container_width=True):
                        update_item(iid, {"key": ek, "value": ev, "note": en})
                        st.session_state.editing_profile = None
                        st.rerun()
                with sc2:
                    if st.form_submit_button("✕ 取消", use_container_width=True):
                        st.session_state.editing_profile = None
                        st.rerun()

        # ── 正常显示 ──────────────────────────────────────
        else:
            key   = item.get("key","")
            value = item.get("value","") or ""
            note  = item.get("note","") or ""

            if section == "family":
                st.markdown(f"""
                <div style="background:var(--cb);border-left:3px solid {color};
                            padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">
                    <span style="color:{color};font-weight:bold">{key}</span>
                    <span style="color:#aaa;margin-left:0.8rem;font-size:0.9rem">{value}</span>
                </div>""", unsafe_allow_html=True)

            elif section == "crew":
                st.markdown(f"""
                <div style="background:var(--cb);border-left:3px solid {color}44;
                            padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">
                    <span style="color:var(--t1);font-weight:bold">{key}</span>
                    <div style="color:#aaa;font-size:0.85rem;margin-top:0.2rem">{note}</div>
                </div>""", unsafe_allow_html=True)

            elif section == "preferences":
                st.markdown(f"""
                <div style="background:var(--cb);border:1px solid {color}33;
                            padding:0.8rem 1rem;margin:0.5rem 0;border-radius:8px">
                    <div style="color:{color};font-size:0.85rem;margin-bottom:0.3rem">{key}</div>
                    <div style="color:var(--t1);white-space:pre-line">{value}</div>
                </div>""", unsafe_allow_html=True)

            elif section == "links":
                st.markdown(
                    f'<a href="{value}" target="_blank" style="color:{color}">🔗 {key}</a><br>',
                    unsafe_allow_html=True)

            if st.session_state.get("is_admin"):
                bc1, bc2, bc3 = st.columns([8, 1, 1])
                with bc2:
                    if st.button("✏️", key=f"edit_p_{iid}", help="编辑"):
                        st.session_state.editing_profile = iid
                        st.rerun()
                with bc3:
                    if st.button("🗑️", key=f"del_p_{iid}", help="删除"):
                        delete_item(iid)
                        st.rerun()


# ── 两个 Tab ─────────────────────────────────────────────
tab_ss, tab_ga = st.tabs(["🔵 Stéphane Séjourné", "🟡 Gabriel Attal"])

with tab_ss:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👨‍👩‍👧 家人")
        render_section("Stéphane Séjourné", "family")
        st.subheader("🤝 普瓦捷帮")
        render_section("Stéphane Séjourné", "crew")
    with col2:
        st.subheader("❤️ 个人喜好")
        render_section("Stéphane Séjourné", "preferences")
        st.subheader("🔗 重要链接")
        render_section("Stéphane Séjourné", "links")

with tab_ga:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👨‍👩‍👧 家人")
        render_section("Gabriel Attal", "family")
    with col2:
        st.subheader("❤️ 个人喜好")
        render_section("Gabriel Attal", "preferences")
        st.subheader("🔗 重要链接")
        render_section("Gabriel Attal", "links")
