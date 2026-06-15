import streamlit as st
from utils.auth import admin_sidebar, is_super_admin
from utils.database import get_audit_log

admin_sidebar()

st.title("🧾 操作记录")
st.caption("谁在什么时候做了哪些增删改 —— 仅最终管理员可见")

# 这是敏感页面：只有最终管理员能看
if not is_super_admin():
    st.warning("🔒 此页面仅最终管理员可见。")
    st.stop()

# 表名 → 中文，方便一眼看懂改的是哪块
TABLE_LABELS = {
    "events":        "📅 大事记",
    "event_links":   "🔗 相关内容",
    "news":          "📰 新闻",
    "images":        "🖼️ 图库",
    "team_members":  "🏛️ 团队成员",
    "resources":     "🔗 资源导航",
    "schedule":      "📆 行程",
    "files":         "📁 文件",
    "profile_items": "👤 人物档案",
}
ACTION_LABELS = {"insert": "➕ 新增", "update": "✏️ 修改", "delete": "🗑️ 删除"}

rows = get_audit_log(limit=300)

# 顶部筛选
f1, f2 = st.columns(2)
with f1:
    who = sorted({r.get("admin_name") or "未知" for r in rows})
    sel_who = st.selectbox("操作人", ["全部"] + who)
with f2:
    sel_act = st.selectbox("操作类型", ["全部", "insert", "update", "delete"],
                           format_func=lambda v: ACTION_LABELS.get(v, v) if v != "全部" else "全部")

if sel_who != "全部":
    rows = [r for r in rows if (r.get("admin_name") or "未知") == sel_who]
if sel_act != "全部":
    rows = [r for r in rows if r.get("action") == sel_act]

st.caption(f"共 {len(rows)} 条记录")

if not rows:
    st.info("暂无操作记录。（管理员登录后做的增删改会从此开始记录）")
    st.stop()

# 整理成表格展示
view = []
for r in rows:
    view.append({
        "时间":   str(r.get("created_at", ""))[:19].replace("T", " "),
        "操作人": r.get("admin_name") or "未知",
        "操作":   ACTION_LABELS.get(r.get("action"), r.get("action") or ""),
        "对象":   TABLE_LABELS.get(r.get("table_name"), r.get("table_name") or ""),
        "记录":   r.get("record_id") or "",
        "说明":   r.get("detail") or "",
    })

st.dataframe(view, use_container_width=True, hide_index=True)
