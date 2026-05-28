import streamlit as st
from utils.database import get_supabase

st.set_page_config(page_title="团队成员 · 档案馆", page_icon="🏛️", layout="wide")

st.title("🏛️ 团队成员")
st.caption("SS 内阁成员 与 GA 核心团队")

tab_ss, tab_ga = st.tabs(["🟡 Stéphane Séjourné — EVP内阁", "🔵 Gabriel Attal — GA团队"])

def load_team(person):
    try:
        db = get_supabase()
        data = db.table('team_members').select('*').eq('person', person).order('team').execute().data
        return data
    except Exception as e:
        st.error(f"加载失败：{e}")
        return []

# ── SS 内阁 ──────────────────────────────────────────────
with tab_ss:
    members = load_team('Stéphane Séjourné')
    if not members:
        st.info("暂无数据，请先导入 Excel。")
    else:
        current_team = None
        for m in members:
            if m.get('team') != current_team:
                current_team = m.get('team')
                st.markdown(f"### {current_team}")
            st.markdown(f"""
            <div style="background:#16213e;border-left:3px solid #C9A84C;
                        padding:0.6rem 1.2rem;margin:0.3rem 0;border-radius:0 6px 6px 0">
                <span style="color:#C9A84C;font-weight:bold">{m.get('name','')}</span>
                <span style="color:#aaa;font-size:0.85rem;margin-left:1rem">{m.get('title','')}</span>
                {"<div style='color:#bbb;font-size:0.82rem;margin-top:0.2rem'>" + m.get('note','') + "</div>" if m.get('note') else ""}
            </div>
            """, unsafe_allow_html=True)

# ── GA 团队 ──────────────────────────────────────────────
with tab_ga:
    members = load_team('Gabriel Attal')
    if not members:
        st.info("暂无数据，请先导入 Excel。")
    else:
        current_team = None
        for m in members:
            if m.get('team') != current_team:
                current_team = m.get('team')
                st.markdown(f"### {current_team}")
            st.markdown(f"""
            <div style="background:#16213e;border-left:3px solid #4A90D9;
                        padding:0.6rem 1.2rem;margin:0.3rem 0;border-radius:0 6px 6px 0">
                <span style="color:#4A90D9;font-weight:bold">{m.get('name','')}</span>
                <span style="color:#aaa;font-size:0.85rem;margin-left:1rem">{m.get('title','')}</span>
                {"<div style='color:#bbb;font-size:0.82rem;margin-top:0.2rem'>" + m.get('note','') + "</div>" if m.get('note') else ""}
            </div>
            """, unsafe_allow_html=True)
