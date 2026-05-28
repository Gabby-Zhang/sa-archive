import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="媒体光谱 · 档案馆", page_icon="📊", layout="wide")

st.title("📊 媒体光谱")
st.caption("法国主要媒体的政治立场参考")

st.markdown("""
<div style="background:#16213e;padding:0.8rem 1rem;border-radius:8px;margin-bottom:1rem">
    📌 数据来源参考：
    <a href="https://mediabiasfactcheck.com/" target="_blank" style="color:#C9A84C">MediaBiasFactCheck</a> ·
    <a href="https://www.allsides.com/bias-checker" target="_blank" style="color:#C9A84C">AllSides</a>
</div>
""", unsafe_allow_html=True)

# ── 媒体数据 ─────────────────────────────────────────────
# score: -2极左, -1左, 0中, 1右, 2极右
media_data = [
    # 日报
    {"name": "L'Humanité（人道报）", "score": -2, "note": "极左，曾经是法共机关刊物", "type": "日报"},
    {"name": "La Libération（解放报）", "score": -1.2, "note": "左，亲PS", "type": "日报"},
    {"name": "La Croix（十字架报）", "score": -1, "note": "左，天主教", "type": "日报"},
    {"name": "La Voix du Nord（北方之声报）", "score": -0.8, "note": "左，针对区域内容", "type": "日报"},
    {"name": "Le Monde（世界报）", "score": -0.5, "note": "中左，亲绿党、LR", "type": "日报"},
    {"name": "Ouest France（法国西部报）", "score": 0, "note": "亲欧", "type": "日报"},
    {"name": "Le Parisien（巴黎人报）", "score": 0.2, "note": "大众化，针对区域内容，亲RE", "type": "日报"},
    {"name": "L'Opinion（意见报）", "score": 0.8, "note": "自由派，亲欧，亲商", "type": "日报"},
    {"name": "Les Échos（回声报）", "score": 0.8, "note": "自由派", "type": "日报"},
    {"name": "Sud Ouest（西南报）", "score": 1, "note": "保守", "type": "日报"},
    {"name": "Le Figaro（费加罗报）", "score": 1.5, "note": "右", "type": "日报"},
    # 周刊/新闻杂志
    {"name": "Le Canard enchaîné", "score": -0.8, "note": "讽刺/调查，偏左", "type": "周刊"},
    {"name": "L'Obs", "score": -0.8, "note": "中左", "type": "周刊"},
    {"name": "Le Point", "score": 1, "note": "中右", "type": "周刊"},
    {"name": "L'Express", "score": 0.5, "note": "中间偏右", "type": "周刊"},
    {"name": "Valeurs actuelles", "score": 2, "note": "极右", "type": "周刊"},
    # 电视/网络
    {"name": "BFMTV", "score": 0, "note": "中间，收视率最高新闻台", "type": "电视/网络"},
    {"name": "LCI", "score": 0.2, "note": "中间", "type": "电视/网络"},
    {"name": "CNews", "score": 1.8, "note": "极右", "type": "电视/网络"},
    {"name": "France 2/France Info", "score": -0.3, "note": "公共媒体，中间偏左", "type": "电视/网络"},
    {"name": "Médiapart", "score": -1.5, "note": "左翼调查媒体", "type": "电视/网络"},
    {"name": "Politico Europe", "score": 0, "note": "中间，亲欧", "type": "电视/网络"},
]

# ── 光谱图 ───────────────────────────────────────────────
type_filter = st.selectbox("媒体类型", ["全部", "日报", "周刊", "电视/网络"])
filtered = [m for m in media_data if type_filter == "全部" or m["type"] == type_filter]
filtered.sort(key=lambda x: x["score"])

colors = []
for m in filtered:
    s = m["score"]
    if s <= -1.5:
        colors.append("#c0392b")
    elif s <= -0.5:
        colors.append("#e74c3c")
    elif s <= 0.5:
        colors.append("#7EC8A4")
    elif s <= 1.2:
        colors.append("#3498db")
    else:
        colors.append("#1a5276")

fig = go.Figure(go.Bar(
    x=[m["score"] for m in filtered],
    y=[m["name"] for m in filtered],
    orientation="h",
    marker_color=colors,
    text=[m["note"] for m in filtered],
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>立场分值：%{x}<br>%{text}<extra></extra>",
))

fig.update_layout(
    paper_bgcolor="#1a1a2e",
    plot_bgcolor="#16213e",
    font_color="#e0e0e0",
    height=max(400, len(filtered) * 40),
    xaxis=dict(
        range=[-2.5, 2.5],
        tickvals=[-2, -1, 0, 1, 2],
        ticktext=["极左", "左", "中间", "右", "极右"],
        gridcolor="#333",
    ),
    yaxis=dict(automargin=True),
    margin=dict(l=20, r=150, t=30, b=20),
    showlegend=False,
)

st.plotly_chart(fig, use_container_width=True)

# ── 媒体列表表格 ─────────────────────────────────────────
st.divider()
st.subheader("📋 媒体列表")
import pandas as pd
df = pd.DataFrame(filtered)[["name", "type", "note"]]
df.columns = ["媒体名称", "类型", "立场说明"]
st.dataframe(df, use_container_width=True, hide_index=True)
