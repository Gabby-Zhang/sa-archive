import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t, tlabel
from utils.database import get_supabase, get_supabase_admin, log_audit

# 偏好标签翻译对照（DB 存中文，英文模式展示英文；含 emoji 变体）
_PREF_KEY_EN = {
    "喜欢的酒":        "Favourite drink",
    "🥃 喜欢的酒":     "🥃 Favourite drink",
    "喜欢的电视剧":    "Favourite TV shows",
    "📺 喜欢的电视剧": "📺 Favourite TV shows",
    "喜欢的电影":      "Favourite films",
    "🎬 喜欢的电影":   "🎬 Favourite films",
    "喜欢的书":        "Favourite books",
    "📚 喜欢的书":     "📚 Favourite books",
    "喜欢的音乐":      "Favourite music",
    "🎵 喜欢的音乐":   "🎵 Favourite music",
    "喜欢的运动":      "Favourite sport",
    "⚽ 喜欢的运动":   "⚽ Favourite sport",
    "喜欢的食物":      "Favourite food",
    "🍽️ 喜欢的食物":  "🍽️ Favourite food",
    "喜欢的地方":      "Favourite places",
    "📍 喜欢的地方":   "📍 Favourite places",
}

admin_sidebar()


st.title(t("profiles_title"))
st.caption(t("profiles_caption"))

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
    get_supabase_admin().table("profile_items").delete().eq("id", iid).execute()
    log_audit("delete", "profile_items", iid)

def update_item(iid, data):
    get_supabase_admin().table("profile_items").update(data).eq("id", iid).execute()
    log_audit("update", "profile_items", iid, data.get("key"))

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
                    get_supabase_admin().table("profile_items").insert({
                        "person": p_person, "section": p_section,
                        "key": p_key, "value": p_value, "note": p_note,
                    }).execute()
                    log_audit("insert", "profile_items", None, p_key)
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
                st.markdown(
                    f'<div style="background:var(--cb);border-left:3px solid {color};padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">'
                    f'<span style="color:{color};font-weight:bold">{key}</span>'
                    f'<span style="color:#aaa;margin-left:0.8rem;font-size:0.9rem">{value}</span>'
                    f'</div>',
                    unsafe_allow_html=True)

            elif section == "crew":
                st.markdown(
                    f'<div style="background:var(--cb);border-left:3px solid {color}44;padding:0.6rem 1rem;margin:0.4rem 0;border-radius:0 6px 6px 0">'
                    f'<span style="color:var(--t1);font-weight:bold">{key}</span>'
                    f'<div style="color:#aaa;font-size:0.85rem;margin-top:0.2rem">{note}</div>'
                    f'</div>',
                    unsafe_allow_html=True)

            elif section == "preferences":
                import html as _html
                value_html = _html.escape(value).replace("\\n", "<br>")
                _display_key = _PREF_KEY_EN.get(key, key) if st.session_state.get("lang") == "en" else key
                key_html   = _html.escape(_display_key)
                st.markdown(
                    f'<div style="background:var(--cb);border:1px solid {color}33;padding:0.8rem 1rem;margin:0.5rem 0;border-radius:8px">'
                    f'<div style="color:{color};font-size:0.85rem;margin-bottom:0.3rem">{key_html}</div>'
                    f'<div style="color:var(--t1)">{value_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True)

            elif section == "links":
                import html as _html
                _display_key = _html.escape(tlabel(key))
                _safe_val    = _html.escape(value)
                st.markdown(
                    f'<a href="{_safe_val}" target="_blank" style="color:{color}">🔗 {_display_key}</a><br>',
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
tab_ss, tab_ga = st.tabs([t("tab_ss"), t("tab_ga")])

with tab_ss:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t("section_family"))
        render_section("Stéphane Séjourné", "family")
        st.subheader(t("section_crew_ss"))
        render_section("Stéphane Séjourné", "crew")
    with col2:
        st.subheader(t("section_prefs"))
        render_section("Stéphane Séjourné", "preferences")
        st.subheader(t("section_links"))
        render_section("Stéphane Séjourné", "links")

with tab_ga:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t("section_family"))
        render_section("Gabriel Attal", "family")
    with col2:
        st.subheader(t("section_prefs"))
        render_section("Gabriel Attal", "preferences")
        st.subheader(t("section_links"))
        render_section("Gabriel Attal", "links")
