import html
import math
from collections import Counter
from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from utils.i18n import t
from utils.missions import BASE, CITIES, CITY_COUNTRY, COUNTRY_LABELS, ROLE_LABEL, load_missions

st.title(t("missions_title"))
st.caption(t("missions_caption"))

PARIS_PINK = "#e8559b"   # 巴黎相关一律粉色
PARIS_SOFT = "#fad1e4"
AWAY_BLUE = "#4f7bd9"    # 其他出差
BXL_GOLD, EU_BLUE = "#ffcc00", "#003399"   # 布鲁塞尔 = 欧盟旗那样的金黄星,蓝边
FR_BLUE, FR_RED = "#0055a4", "#ef4135"
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

source_title, trips_all = load_missions()


def _heart_stripes(plat, plon, height):
    """以巴黎为中心的爱心,切成蓝/白/红三条竖条。

    返回 (竖条列表 [(lat 列表, lon 列表, 颜色)], 整颗爱心的轮廓 (lat 列表, lon 列表))。

    height 是爱心高度(纬度度数);经度按 1/cos(纬度) 拉宽,墨卡托投影下看起来不变形。
    """
    pts = []
    for k in range(120):
        t_ = 2 * math.pi * k / 120
        pts.append((16 * math.sin(t_) ** 3,
                    13 * math.cos(t_) - 5 * math.cos(2 * t_) - 2 * math.cos(3 * t_) - math.cos(4 * t_)))

    def clip(poly, x0, x1):
        # Sutherland–Hodgman:把多边形裁到 x0 <= x <= x1 的竖条里
        for edge, keep in ((x0, lambda x: x >= x0), (x1, lambda x: x <= x1)):
            out = []
            for i, cur in enumerate(poly):
                prev = poly[i - 1]
                if keep(cur[0]) != keep(prev[0]):
                    r = (edge - prev[0]) / (cur[0] - prev[0])
                    out.append((edge, prev[1] + r * (cur[1] - prev[1])))
                if keep(cur[0]):
                    out.append(cur)
            poly = out
        return poly

    scale = height / 29
    stretch = 1 / math.cos(math.radians(plat))

    def to_geo(poly):
        poly = poly + poly[:1]
        return ([plat + (y + 2.5) * scale for _, y in poly], [plon + x * scale * stretch for x, _ in poly])

    third = 16 / 3
    stripes = [(*to_geo(clip(pts, x0, x1)), color)
               for (x0, x1), color in zip(((-17, -third), (-third, third), (third, 17)), (FR_BLUE, "white", FR_RED))]
    return stripes, to_geo(pts)


# ── 筛选 ─────────────────────────────────────────────────
PERIODS = {
    "2026 上半年": ("2026-01-01", "2026-06-30"),
    "2024.12 – 2025": ("2024-12-01", "2025-12-31"),
    "全部": ("0000", "9999"),
}
c1, c2, c3 = st.columns([2, 1.2, 1.2], vertical_alignment="bottom")
with c1:
    period = st.radio("时间段", list(PERIODS), horizontal=True, key="mis_period")
with c2:
    view = st.radio("地图范围", ["欧洲", "全球"], horizontal=True, key="mis_view")
with c3:
    only_paris = st.toggle("只看巴黎相关", key="mis_only_paris")

lo, hi = PERIODS[period]
trips = [x for x in trips_all if lo <= x["f"] <= hi]
paris_trips = [x for x in trips if x["role"]]
shown = paris_trips if only_paris else trips
paris_only = [x for x in paris_trips if x["role"] == "only"]

# ── 数字 ─────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("出差", f"{len(trips)} 次")
m2.metric("经过巴黎", f"{len(paris_trips)} 次")
m3.metric("估算里程（公里）", f"{sum(x['km'] for x in trips) / 10000:.1f}万")
m4.metric("只去巴黎 · 住宿 €0", f"{sum(1 for x in paris_only if x['hotel'] == 0)}/{len(paris_only)}")
m5.metric("包机", f"{sum(1 for x in trips if x['taxi'])} 次")

# ── 地图:每趟出差按 布鲁塞尔 → 各站 → 布鲁塞尔 连线,碰到巴黎的段标粉 ──
pink_lat, pink_lon, blue_lat, blue_lon = [], [], [], []
for x in shown:
    path = [BASE] + x["stops"] + [BASE]
    for a, b in zip(path, path[1:]):
        if a == b:
            continue
        lat, lon = (pink_lat, pink_lon) if "Paris" in (a, b) else (blue_lat, blue_lon)
        lat += [CITIES[a][1], CITIES[b][1], None]
        lon += [CITIES[a][2], CITIES[b][2], None]

visits = Counter(s for x in shown for s in set(x["stops"]))
fig = go.Figure()
# 法国铺浅粉、比利时铺浅蓝,其余国家用米白底色
fig.add_trace(go.Choropleth(locations=["FRA", "BEL"], z=[1, 0], locationmode="ISO-3",
                            colorscale=[[0, "#dbe6fb"], [1, "#fde2ee"]], showscale=False,
                            marker_line_color="#d8ccb6", marker_line_width=0.6, hoverinfo="skip"))
# 英文国名:去过的国家深色,其余浅色;全球视图只标欧洲以外去过的国家,免得欧洲挤成一团(那里有爱心和星星)
been = {CITY_COUNTRY[c] for c in visits} | {"Belgium"}
for dark in (False, True):
    labels = [n for n, (_, _, far) in COUNTRY_LABELS.items()
              if (n in been) == dark and (view == "欧洲" and not far or view == "全球" and dark and far)]
    if labels:
        fig.add_trace(go.Scattergeo(
            lat=[COUNTRY_LABELS[n][0] for n in labels], lon=[COUNTRY_LABELS[n][1] for n in labels],
            mode="text", text=labels, hoverinfo="skip", showlegend=False,
            textfont=dict(size=12 if dark else 10, color="#6b5b45" if dark else "#a89a80")))
fig.add_trace(go.Scattergeo(lat=blue_lat, lon=blue_lon, mode="lines", hoverinfo="skip",
                            line=dict(width=1.4, color=AWAY_BLUE), opacity=0.6, name="其他行程"))
fig.add_trace(go.Scattergeo(lat=pink_lat, lon=pink_lon, mode="lines", hoverinfo="skip",
                            line=dict(width=3, color=PARIS_PINK), opacity=0.85, name="经过巴黎的行程"))
names = [c for c in visits if c != "Paris"]
fig.add_trace(go.Scattergeo(
    lat=[CITIES[c][1] for c in names], lon=[CITIES[c][2] for c in names],
    mode="markers", name="其他目的地",
    marker=dict(size=[7 + 4 * visits[c] ** 0.5 for c in names], color=AWAY_BLUE,
                line=dict(width=1, color="white")),
    text=[f"{CITIES[c][0]} · {visits[c]} 次" for c in names], hoverinfo="text"))
if visits["Paris"]:
    # 巴黎 = 法国国旗配色(蓝|白|红竖条)的爱心,用经纬度多边形画在地图上;压在圆点上面,只让布鲁塞尔的星星在它之上
    hover = f"巴黎 · {visits['Paris']} 次"
    stripes, outline = _heart_stripes(*CITIES["Paris"][1:], 1.7 if view == "欧洲" else 5)
    for lat, lon, color in stripes:
        fig.add_trace(go.Scattergeo(lat=lat, lon=lon, mode="lines", fill="toself", fillcolor=color,
                                    line=dict(width=0, color=color), hoverinfo="text",
                                    text=hover, showlegend=False))
    # 描一圈深色边,白色那条在浅色底图上才看得出轮廓
    fig.add_trace(go.Scattergeo(lat=outline[0], lon=outline[1], mode="lines", hoverinfo="skip",
                                line=dict(width=1.2, color="#2b2d42"), showlegend=False))
fig.add_trace(go.Scattergeo(lat=[CITIES[BASE][1]], lon=[CITIES[BASE][2]], mode="markers",
                            marker=dict(size=20 if view == "欧洲" else 14, symbol="star", color=BXL_GOLD, line=dict(width=1.5, color=EU_BLUE)),
                            text=["布鲁塞尔（工作地）"], hoverinfo="text", name="布鲁塞尔"))
geo = dict(showland=True, landcolor="#f6f1e7", showcountries=True, countrycolor="#d8ccb6",
           showocean=True, oceancolor="#d6eaf8", showlakes=True, lakecolor="#d6eaf8",
           showframe=False, coastlinecolor="#b9cfe0")
if view == "欧洲":
    geo.update(projection_type="mercator", lataxis_range=[34, 63], lonaxis_range=[-16, 38])
else:
    # 固定取景:北美到日本、阿根廷到北欧,所有出差地都在画面内
    geo.update(projection_type="natural earth", lataxis_range=[-45, 72], lonaxis_range=[-130, 150])
fig.update_geos(**geo)
fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                  legend=dict(orientation="h", y=0.01, x=0.01, bgcolor="rgba(255,255,255,0.7)"))
st.plotly_chart(fig, use_container_width=True)
st.caption("国旗色爱心是巴黎，黄星是布鲁塞尔。线是按「布鲁塞尔 → 各站 → 布鲁塞尔」画的示意，不是实际航线；圆点越大去得越多。")

# ── 日历条:一格一天 ─────────────────────────────────────
st.subheader("每一天在哪")
day = {}
rank = {"away": 1, "ptrip": 2, "paris": 3}
for x in shown:
    d, end = date.fromisoformat(x["f"]), date.fromisoformat(x["t"])
    while d <= end:
        k = d.isoformat()
        cls = "away" if not x["role"] else ("paris" if x["role"] == "only" or k in x["calp"] else "ptrip")
        if k not in day or rank[cls] > rank[day[k][0]]:
            day[k] = (cls, x)
        d += timedelta(days=1)

if trips:
    first = date.fromisoformat(trips[0]["f"]).replace(day=1)
    last = date.fromisoformat(trips[-1]["t"])
    months, m = [], first
    while m <= last:
        months.append(m)
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    rows = ['<div class="mcal-row mcal-nums"><span></span>' +
            "".join(f"<span>{i if i in (1, 5, 10, 15, 20, 25, 30) else ''}</span>" for i in range(1, 32)) + "</div>"]
    for m in months:
        nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        cells = []
        for i in range(1, 32):
            if i > (nxt - timedelta(days=1)).day:
                cells.append('<span class="mcal-c mcal-none"></span>')
                continue
            d = m.replace(day=i)
            we = " mcal-we" if d.weekday() >= 5 else ""
            hit = day.get(d.isoformat())
            tip = f"{d:%d/%m} {WD[d.weekday()]}"
            if hit:
                tip += " · " + " → ".join(CITIES[s][0] for s in hit[1]["stops"])
                cells.append(f'<span class="mcal-c{we} mcal-{hit[0]}" title="{html.escape(tip)}"></span>')
            else:
                cells.append(f'<span class="mcal-c{we}" title="{tip}"></span>')
        rows.append(f'<div class="mcal-row"><span class="mcal-m">{m:%y.%m}</span>{"".join(cells)}</div>')
    st.markdown(f"""
<style>
.mcal{{display:grid;gap:3px;overflow-x:auto}}
.mcal-row{{display:grid;grid-template-columns:3.2em repeat(31,minmax(8px,1fr));gap:2px;align-items:center}}
.mcal-nums span,.mcal-m{{font-size:11px;color:var(--t2);text-align:center}}
.mcal-c{{aspect-ratio:1;border-radius:3px;background:#e9ecf3}}
.mcal-we{{background:#cfd6e3}}
.mcal-none{{visibility:hidden}}
.mcal-away{{background:#dbe4f5;box-shadow:inset 0 0 0 1.5px {AWAY_BLUE}}}
.mcal-ptrip{{background:{PARIS_SOFT}}}
.mcal-paris{{background:{PARIS_PINK}}}
.mcal-leg{{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:13px;color:var(--t2);margin:4px 0 10px}}
.mcal-leg i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
</style>
<div class="mcal-leg">
  <span><i style="background:{PARIS_PINK}"></i>在巴黎</span>
  <span><i style="background:{PARIS_SOFT}"></i>经过巴黎的行程（具体哪天不确定）</span>
  <span><i style="background:#dbe4f5;box-shadow:inset 0 0 0 1.5px {AWAY_BLUE}"></i>其他出差</span>
  <span><i style="background:#cfd6e3"></i>周末</span>
</div>
<div class="mcal">{"".join(rows)}</div>
<div style="height:1rem"></div>
""", unsafe_allow_html=True)

# ── 行程列表 ─────────────────────────────────────────────
st.subheader(f"全部行程（{len(shown)}）")
for x in reversed(shown):
    f, to = date.fromisoformat(x["f"]), date.fromisoformat(x["t"])
    when = f"{f:%d/%m/%Y} {WD[f.weekday()]}" + (f" → {to:%d/%m/%Y} {WD[to.weekday()]}" if to != f else "（当天）")
    route = " → ".join(
        f'<b style="color:{PARIS_PINK}">{CITIES[s][0]}</b>' if s == "Paris" else CITIES[s][0] for s in x["stops"])
    tags = []
    if x["role"]:
        tags.append(ROLE_LABEL[x["role"]])
    if x["role"] == "only" and x["hotel"] == 0:
        tags.append("🏠 住宿 €0")
    if x["taxi"]:
        tags.append("✈️ 包机")
    tags.append(f"≈{x['km']:,} km")
    lines = []
    if x.get("paris"):
        lines.append(f"<b>在巴黎</b>　{html.escape(x['paris'])}")
    if x.get("other"):
        lines.append(f"<b>{'其他站' if x['role'] else '事由'}</b>　{html.escape(x['other'])}")
    if x.get("calp"):
        lines.append(f'<span style="color:{PARIS_PINK}">日历确认在巴黎：' + "、".join(
            f"{date.fromisoformat(k):%d/%m} {WD[date.fromisoformat(k).weekday()]}" for k in x["calp"]) + "</span>")
    if x.get("note"):
        lines.append(f'<span style="color:var(--t3)">备注：{html.escape(x["note"])}</span>')
    border = PARIS_PINK if x["role"] else "var(--bd)"
    st.markdown(f"""
<div style="background:var(--cb);border-left:4px solid {border};padding:0.7rem 1rem;border-radius:8px;margin-bottom:0.6rem">
  <div style="font-size:0.85rem;color:var(--t2)">{when}</div>
  <div style="font-weight:600;color:var(--t1);margin:2px 0">{route}</div>
  <div style="font-size:0.8rem;color:var(--t2);margin-bottom:4px">{" · ".join(tags)}</div>
  <div style="font-size:0.9rem;color:var(--t1);line-height:1.6">{"<br>".join(lines)}</div>
</div>""", unsafe_allow_html=True)

with st.expander("数据来源与说明"):
    st.markdown(f"""
- 来源：欧委会公布的出差报销表（{html.escape(source_title)}），在他委员主页 Transparency → Missions 下载；2026 年 4 月起的具体巴黎日期来自 sejourn-calendar 日历（欧委会议程与透明度登记处会议）。
- 日期是整趟出差的起止日，报销表不写哪天在哪个城市；里程按直线距离估算。
- 「住宿 €0」只标在只去巴黎的出差上。从布鲁塞尔回家属于私人通勤，不在报销表里。
- 更新：下载新的 xlsx，运行 `python3 scripts/missions_to_json.py <文件>`，补上新条目的中文摘要后推送。
""")
