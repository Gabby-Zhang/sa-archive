import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import time
from utils.auth import admin_sidebar
from utils.database import get_supabase_admin

admin_sidebar()

st.title("📆 行程日历")
st.caption("Séjourné 行程自动抓取自欧盟委员会官网 · Attal 行程由团队手动维护")

SEJOURNE_COLOR = "#4A90D9"
ATTAL_COLOR    = "#C9A84C"

# ── EU Commission 抓取逻辑（同 sejourn_calendar_sync.py）────────────────────
_BASE = (
    "https://commission.europa.eu/about/organisation/college-commissioners"
    "/calendar-items-president-and-commissioners_en"
)
_FILTER = (
    "f[0]=commissioner_dynamic_commissioner_dynamic:"
    "http://publications.europa.eu/resource/authority/political-leader/COM_00006A047C6D"
    "&f[1]=ewcms_calendar_status:past"
    "&f[2]=ewcms_calendar_status:upcoming"
)
_HDRS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
_MONTH = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5,  "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _fetch_eu_page(page: int):
    url = f"{_BASE}?{_FILTER}&page={page}"
    r = requests.get(url, headers=_HDRS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _parse_eu_events(soup) -> list:
    events = []
    for article in soup.select("article.ecl-content-item--inline"):
        time_el = article.select_one("time.ecl-content-item__date")
        if not time_el:
            continue
        day   = time_el.select_one(".ecl-date-block__day")
        month = time_el.select_one(".ecl-date-block__month")
        year  = time_el.select_one(".ecl-date-block__year")
        if not (day and month and year):
            continue
        try:
            ev_date = date(
                int(year.get_text(strip=True)),
                _MONTH[month.get_text(strip=True)],
                int(day.get_text(strip=True)),
            )
        except (KeyError, ValueError):
            continue
        classes = time_el.get("class", [])
        status  = ("past"    if "ecl-date-block--past"    in classes else
                   "ongoing" if "ecl-date-block--ongoing" in classes else
                   "upcoming")
        title_el    = article.select_one(".ecl-content-block__title")
        location_el = article.select_one(".ecl-content-block__secondary-meta-label")
        events.append({
            "title":    title_el.get_text(strip=True) if title_el else "—",
            "date":     ev_date.isoformat(),
            "location": location_el.get_text(strip=True) if location_el else "",
            "status":   status,
        })
    return events


@st.cache_data(ttl=3600, show_spinner=False)
def get_sejourne_schedule(days_back: int = 45) -> list:
    """从欧委会官网抓取 Séjourné 日程，缓存 1 小时。"""
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    all_events = []
    for page in range(20):
        if page > 0:
            time.sleep(0.3)
        try:
            soup = _fetch_eu_page(page)
        except Exception:
            break
        batch = _parse_eu_events(soup)
        if not batch:
            break
        in_window = [e for e in batch
                     if e["date"] >= cutoff or e["status"] in ("upcoming", "ongoing")]
        all_events.extend(in_window)
        # 本页最早日期已早于 cutoff → 后面页面不用再看
        if min((e["date"] for e in batch), default="9999") < cutoff:
            break
    upcoming = sorted([e for e in all_events if e["status"] != "past"],
                      key=lambda x: x["date"])
    past     = sorted([e for e in all_events if e["status"] == "past"],
                      key=lambda x: x["date"], reverse=True)
    return upcoming + past


@st.cache_data(ttl=300, show_spinner=False)
def get_attal_schedule() -> list:
    """从 Supabase schedule 表读取 Attal 行程。"""
    try:
        rows = (get_supabase_admin()
                .table("schedule")
                .select("*")
                .eq("person", "Gabriel Attal")
                .order("event_date", desc=False)
                .execute().data)
        return rows or []
    except Exception:
        return []


# ── 卡片渲染 ─────────────────────────────────────────────────────────────────
def _event_card(title: str, ev_date: str, location: str,
                status: str, color: str, source_url: str = ""):
    if status in ("upcoming", "ongoing"):
        bg           = f"background:var(--cb);border-left:4px solid {color}"
        date_color   = color
        opacity      = "1"
    else:
        bg           = f"background:var(--cb2);border-left:3px solid var(--bd)"
        date_color   = "var(--t3)"
        opacity      = "0.7"

    # 徽章
    badge = ""
    if status == "ongoing":
        badge = (f'<span style="background:{color};color:white;font-size:0.62rem;'
                 f'padding:0.03rem 0.35rem;border-radius:3px;margin-left:0.4rem">进行中</span>')
    elif status == "upcoming":
        try:
            delta = (date.fromisoformat(ev_date) - date.today()).days
            if delta == 0:
                lbl = "今天"
            elif delta == 1:
                lbl = "明天"
            elif 2 <= delta <= 7:
                lbl = f"{delta} 天后"
            else:
                lbl = ""
            if lbl:
                badge = (f'<span style="background:{color};color:white;font-size:0.62rem;'
                         f'padding:0.03rem 0.35rem;border-radius:3px;margin-left:0.4rem">'
                         f'{lbl}</span>')
        except ValueError:
            pass

    loc_html  = (f'<div style="color:var(--t3);font-size:0.73rem;margin-top:0.15rem">'
                 f'📍 {location}</div>') if location else ""
    link_html = (f' <a href="{source_url}" target="_blank" '
                 f'style="color:#4A90D9;font-size:0.75rem">🔗</a>') if source_url else ""

    st.markdown(f"""
    <div style="{bg};border-radius:0 8px 8px 0;
                padding:0.55rem 0.85rem;margin:0.3rem 0;opacity:{opacity}">
        <div style="color:{date_color};font-size:0.73rem;font-weight:600">
            {ev_date}{badge}
        </div>
        <div style="color:var(--t1);font-size:0.88rem;margin-top:0.1rem;line-height:1.35">
            {title}{link_html}
        </div>
        {loc_html}
    </div>
    """, unsafe_allow_html=True)


def _section_header(label: str):
    st.markdown(
        f'<div style="color:var(--t3);font-size:0.72rem;font-weight:600;'
        f'letter-spacing:0.04em;margin:0.6rem 0 0.2rem">{label}</div>',
        unsafe_allow_html=True
    )


# ── 页面主体：并排两栏 ───────────────────────────────────────────────────────
col_s, col_a = st.columns(2)

# ════════════════════════════════════════════════════════════════════════════
# 左栏：Stéphane Séjourné（自动抓取）
# ════════════════════════════════════════════════════════════════════════════
with col_s:
    st.markdown(
        f'<div style="color:{SEJOURNE_COLOR};font-size:1.05rem;font-weight:700;'
        f'margin-bottom:0.2rem">🔵 Stéphane Séjourné</div>',
        unsafe_allow_html=True
    )
    st.caption("📡 欧盟委员会官网 · 自动同步 · 每小时刷新")

    if st.button("🔄", key="refresh_s", help="强制刷新 Séjourné 日程"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("正在从欧委会官网获取日程…"):
        try:
            s_events = get_sejourne_schedule()
        except Exception as _e:
            st.error(f"抓取失败：{_e}")
            s_events = []

    if not s_events:
        st.info("暂时无法获取日程，请稍后重试")
    else:
        s_upcoming = [e for e in s_events if e["status"] != "past"]
        s_past     = [e for e in s_events if e["status"] == "past"]

        if s_upcoming:
            _section_header(f"▶ 即将到来 · {len(s_upcoming)} 项")
            for ev in s_upcoming:
                _event_card(ev["title"], ev["date"], ev["location"],
                            ev["status"], SEJOURNE_COLOR)
        else:
            st.info("暂无即将到来的行程")

        if s_past:
            with st.expander(f"历史行程（{len(s_past)} 条）"):
                for ev in s_past:
                    _event_card(ev["title"], ev["date"], ev["location"],
                                "past", SEJOURNE_COLOR)

# ════════════════════════════════════════════════════════════════════════════
# 右栏：Gabriel Attal（手动维护）
# ════════════════════════════════════════════════════════════════════════════
with col_a:
    st.markdown(
        f'<div style="color:{ATTAL_COLOR};font-size:1.05rem;font-weight:700;'
        f'margin-bottom:0.2rem">🟡 Gabriel Attal</div>',
        unsafe_allow_html=True
    )
    st.caption("✏️ 由团队手动维护")

    a_events  = get_attal_schedule()
    today_str = date.today().isoformat()

    a_upcoming = [e for e in a_events if str(e.get("event_date",""))[:10] >= today_str]
    a_past     = sorted(
        [e for e in a_events if str(e.get("event_date",""))[:10] < today_str],
        key=lambda x: x.get("event_date",""), reverse=True
    )

    if a_upcoming:
        _section_header(f"▶ 即将到来 · {len(a_upcoming)} 项")
        for ev in a_upcoming:
            ev_date_str = str(ev.get("event_date",""))[:10]
            try:
                delta = (date.fromisoformat(ev_date_str) - date.today()).days
            except ValueError:
                delta = 1
            status = "ongoing" if delta == 0 else "upcoming"

            if st.session_state.get("is_admin"):
                _c1, _c2 = st.columns([11, 1])
                with _c1:
                    _event_card(ev.get("title",""), ev_date_str,
                                ev.get("location",""), status,
                                ATTAL_COLOR, ev.get("source_url",""))
                with _c2:
                    if st.button("🗑️", key=f"del_attal_{ev.get('id')}",
                                 help="删除", use_container_width=True):
                        get_supabase_admin().table("schedule").delete().eq("id", ev["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()
            else:
                _event_card(ev.get("title",""), ev_date_str,
                            ev.get("location",""), status,
                            ATTAL_COLOR, ev.get("source_url",""))
    elif not a_events:
        st.info("暂无行程记录")

    if a_past:
        with st.expander(f"历史行程（{len(a_past)} 条）"):
            for ev in a_past:
                ev_date_str = str(ev.get("event_date",""))[:10]
                if st.session_state.get("is_admin"):
                    _c1, _c2 = st.columns([11, 1])
                    with _c1:
                        _event_card(ev.get("title",""), ev_date_str,
                                    ev.get("location",""), "past",
                                    ATTAL_COLOR, ev.get("source_url",""))
                    with _c2:
                        if st.button("🗑️", key=f"del_attal_past_{ev.get('id')}",
                                     help="删除", use_container_width=True):
                            get_supabase_admin().table("schedule").delete().eq("id", ev["id"]).execute()
                            st.cache_data.clear()
                            st.rerun()
                else:
                    _event_card(ev.get("title",""), ev_date_str,
                                ev.get("location",""), "past",
                                ATTAL_COLOR, ev.get("source_url",""))

    # ── 管理员：添加 Attal 行程 ──────────────────────────────
    if st.session_state.get("is_admin"):
        st.divider()
        with st.expander("➕ 添加 Attal 行程"):
            with st.form("add_attal_schedule"):
                new_title    = st.text_input("活动标题 *")
                af1, af2     = st.columns(2)
                with af1:
                    new_date     = st.date_input("日期")
                    new_location = st.text_input("地点（可选）")
                with af2:
                    new_url      = st.text_input("来源链接（可选）")
                    new_desc     = st.text_area("备注（可选）", height=68)
                if st.form_submit_button("💾 添加", use_container_width=True):
                    if new_title:
                        try:
                            get_supabase_admin().table("schedule").insert({
                                "person":      "Gabriel Attal",
                                "event_date":  str(new_date),
                                "title":       new_title,
                                "location":    new_location or "",
                                "description": new_desc or "",
                                "source_url":  new_url or "",
                            }).execute()
                            st.cache_data.clear()
                            st.success("✅ 已添加")
                            st.rerun()
                        except Exception as _e:
                            st.error(f"添加失败：{_e}")
                    else:
                        st.warning("请填写活动标题")
