import streamlit as st
import html as _html
from datetime import date
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase

admin_sidebar()

st.title(t("weave_title"))
st.caption(t("weave_caption"))

SS_COLOR = "#4A90D9"
GA_COLOR = "#C9A84C"
SA_COLOR = "#FF6B9D"

# ── 样式：三列时间轴（SS 左 · 中轴 · GA 右），同框横跨全宽 ──────────────
st.markdown("""
<style>
.wv-grid {
    display:grid;
    grid-template-columns: 1fr 26px 1fr;
    column-gap: 0.6rem;
    row-gap: 0.45rem;
    align-items: stretch;
}
.wv-spine {
    position:relative;
    display:flex; align-items:center; justify-content:center;
}
.wv-spine::before {
    content:""; position:absolute; top:0; bottom:0; left:50%;
    width:2px; margin-left:-1px; background:var(--bd);
}
.wv-dot {
    position:relative; z-index:1;
    width:10px; height:10px; border-radius:50%;
    background:var(--bd);
}
.wv-dot.ss { background:#4A90D9; }
.wv-dot.ga { background:#C9A84C; }
.wv-card {
    border-radius:8px; padding:0.5rem 0.8rem;
    background:var(--cb); font-size:0.84rem; line-height:1.4;
}
.wv-card.ss { border-right:3px solid #4A90D9; text-align:right; }
.wv-card.ga { border-left:3px solid #C9A84C; }
.wv-date { font-size:0.7rem; color:var(--t3); }
.wv-title { color:var(--t1); }
.wv-title a { text-decoration:none; }
.wv-sa {
    grid-column: 1 / -1;
    background:linear-gradient(135deg,#FF6B9D14,#FF6B9D26);
    border:1px solid #FF6B9D55; border-radius:10px;
    padding:0.6rem 1rem; text-align:center;
    position:relative;
}
.wv-sa .wv-date { color:#FF6B9D; font-weight:600; }
.wv-sa .wv-title { font-size:0.9rem; }
.wv-heart { font-size:0.85rem; }
@media (max-width: 640px) {
    .wv-grid { grid-template-columns: 1fr 18px 1fr; }
    .wv-card { font-size:0.78rem; padding:0.4rem 0.55rem; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def _load_events(year: str):
    q = (get_supabase().table("events")
         .select("date,person,title,source_url,tag")
         .order("date", desc=True))
    if year != "ALL":
        q = q.gte("date", f"{year}-01-01").lte("date", f"{year}-12-31")
    return q.limit(1000).execute().data or []


@st.cache_data(ttl=3600, show_spinner=False)
def _year_options():
    """从数据提取有记录的年份列表（倒序）。"""
    try:
        rows = (get_supabase().table("events").select("date")
                .order("date", desc=True).limit(1000).execute().data) or []
        years = sorted({str(r["date"])[:4] for r in rows if r.get("date")}, reverse=True)
        return years
    except Exception:
        return [str(date.today().year)]


# ── 筛选栏 ────────────────────────────────────────────────
_years = _year_options()
fc1, fc2 = st.columns([1, 3])
with fc1:
    _year = st.selectbox(t("year_label"), _years + ["ALL"],
                         format_func=lambda v: t("all") if v == "ALL" else v)
with fc2:
    _only_sa = st.toggle(t("weave_only_sa"), value=False)

rows = _load_events(_year)
if _only_sa:
    rows = [r for r in rows if r.get("person") == "S&A"]

if not rows:
    st.info(t("no_data"))
    st.stop()

_sa_count = sum(1 for r in rows if r.get("person") == "S&A")
st.caption(f"{len(rows)} {t('weave_entries')} · 💗 ×{_sa_count}")

# ── 渲染 ──────────────────────────────────────────────────
def _card(r, cls):
    d     = str(r.get("date", ""))[:10]
    title = _html.escape((r.get("title") or "")[:90])
    url   = r.get("source_url") or ""
    link  = f' <a href="{_html.escape(url)}" target="_blank">🔗</a>' if url else ""
    return (f'<div class="wv-card {cls}">'
            f'<div class="wv-date">{d}</div>'
            f'<div class="wv-title">{title}{link}</div></div>')

_parts = ['<div class="wv-grid">']
for r in rows:
    person = r.get("person", "")
    if person == "S&A":
        d     = str(r.get("date", ""))[:10]
        title = _html.escape((r.get("title") or "")[:110])
        url   = r.get("source_url") or ""
        link  = f' <a href="{_html.escape(url)}" target="_blank">🔗</a>' if url else ""
        _parts.append(
            f'<div class="wv-sa">'
            f'<div class="wv-date"><span class="wv-heart">💗</span> {d}</div>'
            f'<div class="wv-title">{title}{link}</div></div>'
        )
    elif person == "Stéphane Séjourné":
        _parts.append(_card(r, "ss"))
        _parts.append('<div class="wv-spine"><div class="wv-dot ss"></div></div>')
        _parts.append('<div></div>')
    else:  # Gabriel Attal 及其他
        _parts.append('<div></div>')
        _parts.append('<div class="wv-spine"><div class="wv-dot ga"></div></div>')
        _parts.append(_card(r, "ga"))
_parts.append('</div>')

st.markdown("".join(_parts), unsafe_allow_html=True)

st.divider()
st.caption(f'🔵 Stéphane Séjourné　🟡 Gabriel Attal　💗 S&A')
