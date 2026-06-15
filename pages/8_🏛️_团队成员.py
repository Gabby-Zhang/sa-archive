import streamlit as st
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase, get_supabase_admin, log_audit

admin_sidebar()


st.title(t("team_title"))
st.caption("SS 内阁成员 与 GA 核心团队")

db = get_supabase()

PERSON_COLOR = {
    "Stéphane Séjourné": "#4A90D9",
    "Gabriel Attal":     "#C9A84C",
}

# 分组的层级顺序（内阁/团队从高到低）。未列出的组别排在最后，按字母序。
TEAM_ORDER = ["内阁领导", "内阁专家", "内阁成员", "政策助理", "支持团队"]

def load_team(person):
    try:
        rows = db.table("team_members").select("*").eq("person", person).execute().data
    except Exception as e:
        st.error(f"加载失败：{e}")
        return []
    rank = {name: i for i, name in enumerate(TEAM_ORDER)}
    # 先按层级顺序分组，组内按姓名排序（主任 Bertrand 自然排在副主任 Estelle 前）
    rows.sort(key=lambda m: (rank.get(m.get("team"), 999), m.get("team", ""), m.get("name", "")))
    return rows

def delete_member(mid):
    get_supabase_admin().table("team_members").delete().eq("id", mid).execute()
    log_audit("delete", "team_members", mid)

def update_member(mid, data):
    get_supabase_admin().table("team_members").update(data).eq("id", mid).execute()
    log_audit("update", "team_members", mid, data.get("name"))

# ── 管理员：添加成员 ─────────────────────────────────────
if st.session_state.get("is_admin"):
    with st.expander("➕ 添加成员", expanded=False):
        with st.form("add_member_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_person = st.selectbox("所属人物", ["Stéphane Séjourné", "Gabriel Attal"])
                new_team   = st.text_input("团队/组别 *", placeholder="如：欧委会内阁、竞选团队…")
                new_name   = st.text_input("姓名 *")
            with c2:
                new_title  = st.text_input("职位/头衔")
                new_note   = st.text_area("备注", height=80)
            if st.form_submit_button("✅ 添加", use_container_width=True):
                if new_name and new_team:
                    get_supabase_admin().table("team_members").insert({
                        "person": new_person,
                        "team":   new_team,
                        "name":   new_name,
                        "title":  new_title,
                        "note":   new_note,
                    }).execute()
                    log_audit("insert", "team_members", None, new_name)
                    st.success("已添加！")
                    st.rerun()
                else:
                    st.warning("请填写姓名和团队")

st.divider()

# ── 初始化编辑状态 ────────────────────────────────────────
if "editing_member_id" not in st.session_state:
    st.session_state.editing_member_id = None

# ── 两个 Tab ─────────────────────────────────────────────
tab_ss, tab_ga = st.tabs(["🔵 Stéphane Séjourné — EVP内阁", "🟡 Gabriel Attal — GA团队"])

for tab, person in [(tab_ss, "Stéphane Séjourné"), (tab_ga, "Gabriel Attal")]:
    color = PERSON_COLOR[person]
    with tab:
        members = load_team(person)
        if not members:
            st.info("暂无成员，点击上方「➕ 添加成员」开始录入。")
            continue

        current_team = None
        for m in members:
            mid = m.get("id")

            # ── 分组标题 ──────────────────────────────────
            if m.get("team") != current_team:
                current_team = m.get("team")
                st.markdown(f"### {current_team}")

            # ── 编辑模式 ──────────────────────────────────
            if st.session_state.editing_member_id == mid:
                with st.form(key=f"edit_member_{mid}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_name  = st.text_input("姓名",  value=m.get("name",""))
                        e_team  = st.text_input("团队",  value=m.get("team",""))
                    with ec2:
                        e_title = st.text_input("职位",  value=m.get("title",""))
                        e_note  = st.text_area("备注",   value=m.get("note","") or "", height=68)
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("💾 保存", use_container_width=True):
                            update_member(mid, {"name": e_name, "team": e_team,
                                                "title": e_title, "note": e_note})
                            st.session_state.editing_member_id = None
                            st.rerun()
                    with sc2:
                        if st.form_submit_button("✕ 取消", use_container_width=True):
                            st.session_state.editing_member_id = None
                            st.rerun()

            # ── 正常显示 ──────────────────────────────────
            else:
                # title 约定格式「职位 · 分管领域」：职位作小灰字，分管领域用主色突出。
                _parts = [p.strip() for p in (m.get("title", "") or "").split("·")]
                _role = _parts[0] if _parts else ""
                _area = " · ".join(_parts[1:]) if len(_parts) > 1 else ""
                _role_span = f'<span style="color:#aaa;font-size:0.85rem;margin-left:1rem">{_role}</span>' if _role else ""
                _area_span = f'<span style="color:{color};font-size:0.82rem;margin-left:0.6rem;opacity:0.95">· {_area}</span>' if _area else ""

                # note 若是邮箱 → ✉️ 可点击 mailto；否则当普通备注显示（兼容旧数据）。
                _note = (m.get("note", "") or "").strip()
                if "@" in _note and " " not in _note:
                    _contact = (f'<div style="margin-top:0.25rem">'
                                f'<a href="mailto:{_note}" style="color:#888;font-size:0.78rem;text-decoration:none">✉️ {_note}</a></div>')
                elif _note:
                    _contact = f'<div style="color:#bbb;font-size:0.82rem;margin-top:0.2rem">{_note}</div>'
                else:
                    _contact = ""

                st.markdown(
                    f'<div style="background:var(--cb);border-left:3px solid {color};padding:0.6rem 1.2rem;margin:0.3rem 0;border-radius:0 6px 6px 0">'
                    f'<span style="color:{color};font-weight:bold">{m.get("name","")}</span>'
                    f'{_role_span}{_area_span}'
                    f'{_contact}'
                    f'</div>',
                    unsafe_allow_html=True)

                if st.session_state.get("is_admin"):
                    bc1, bc2, bc3 = st.columns([8, 1, 1])
                    with bc2:
                        if st.button("✏️", key=f"edit_m_{mid}", help="编辑"):
                            st.session_state.editing_member_id = mid
                            st.rerun()
                    with bc3:
                        if st.button("🗑️", key=f"del_m_{mid}", help="删除"):
                            delete_member(mid)
                            st.rerun()
