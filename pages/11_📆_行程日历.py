import streamlit as st
import requests
from datetime import date
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase_admin

admin_sidebar()

st.title(t("schedule_title"))
st.caption(t("schedule_caption"))

SEJOURNE_COLOR = "#4A90D9"
ATTAL_COLOR    = "#C9A84C"

# Séjourné ICS 文件托管在 GitHub 公开仓库
_ICS_URL = "https://raw.githubusercontent.com/Gabby-Zhang/sejourn-calendar/main/sejourn.ics"


def _parse_ics(text: str) -> list:
    """解析 ICS 文本，返回事件列表。"""
    events, current = [], {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current.get("title") and current.get("date"):
                events.append(current)
            current = {}
        elif line.startswith("SUMMARY:"):
            current["title"] = line[8:].replace("\\,", ",").replace("\\n", " ").strip()
        elif line.startswith("DTSTART"):
            # DTSTART;VALUE=DATE:YYYYMMDD  或  DTSTART:YYYYMMDDTHHMMSSZ
            val = line.split(":")[-1][:8]
            try:
                y, m, d_ = int(val[:4]), int(val[4:6]), int(val[6:8])
                current["date"] = date(y, m, d_).isoformat()
            except (ValueError, IndexError):
                pass
        elif line.startswith("LOCATION:"):
            current["location"] = line[9:].replace("\\,", ",").strip()
    return events


@st.cache_data(ttl=300, show_spinner=False)
def get_sejourne_schedule() -> list:
    """从 GitHub ICS 文件读取 Séjourné 日程，缓存 5 分钟。"""
    import time as _time
    # 加时间戳（5 分钟精度）绕过 GitHub CDN 缓存
    bust = int(_time.time() // 300)
    r = requests.get(f"{_ICS_URL}?_={bust}", timeout=15)
    r.raise_for_status()
    # 只返回原始事件列表，状态在展示时实时计算（避免缓存过期导致 past/upcoming 错误）
    return _parse_ics(r.text)


@st.cache_data(ttl=300, show_spinner=False)
def get_attal_schedule() -> list:
    """从 Supabase schedule 表读取 Attal 行程。失败时抛出异常，由调用方提示。"""
    rows = (get_supabase_admin()
            .table("schedule")
            .select("*")
            .eq("person", "Gabriel Attal")
            .order("event_date", desc=False)
            .execute().data)
    return rows or []


# ── 卡片渲染 ─────────────────────────────────────────────────────────────────
def _event_card(title: str, ev_date: str, location: str,
                status: str, color: str, source_url: str = "",
                description: str = ""):
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

    # AN 自动同步标签
    an_badge = ""
    if description and "[AN_AUTO]" in description:
        an_badge = (f'<span style="color:#888;font-size:0.62rem;'
                    f'border:1px solid #888;border-radius:3px;padding:0.02rem 0.3rem;'
                    f'margin-left:0.4rem">🏛️ AN</span>')

    loc_html  = (f'<div style="color:var(--t3);font-size:0.73rem;margin-top:0.15rem">'
                 f'📍 {location}</div>') if location else ""
    link_html = (f' <a href="{source_url}" target="_blank" '
                 f'style="color:#4A90D9;font-size:0.75rem">🔗</a>') if source_url else ""

    st.markdown(
        f'<div style="{bg};border-radius:0 8px 8px 0;padding:0.55rem 0.85rem;margin:0.3rem 0;opacity:{opacity}">'
        f'<div style="color:{date_color};font-size:0.73rem;font-weight:600">{ev_date}{badge}{an_badge}</div>'
        f'<div style="color:var(--t1);font-size:0.88rem;margin-top:0.1rem;line-height:1.35">{title}{link_html}</div>'
        f'{loc_html}'
        f'</div>',
        unsafe_allow_html=True)


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
    st.caption("📡 " + t("sched_ss_src"))

    if st.button("🔄", key="refresh_s", help=t("sched_refresh")):
        st.cache_data.clear()
        st.rerun()

    with st.spinner(t("sched_loading")):
        try:
            s_events = get_sejourne_schedule()
        except Exception as _e:
            st.error(f"读取失败：{_e}")
            s_events = []

    # 实时计算 status（不依赖缓存时的日期判断）
    _today = date.today()
    for ev in s_events:
        try:
            ev_date = date.fromisoformat(ev["date"])
            if ev_date < _today:
                ev["status"] = "past"
            elif ev_date == _today:
                ev["status"] = "ongoing"
            else:
                ev["status"] = "upcoming"
        except Exception:
            ev["status"] = "past"

    if not s_events:
        st.info(t("sched_no_data"))
    else:
        s_upcoming = sorted([e for e in s_events if e["status"] != "past"], key=lambda x: x["date"])
        s_past     = sorted([e for e in s_events if e["status"] == "past"],  key=lambda x: x["date"], reverse=True)

        if s_upcoming:
            _section_header(f"▶ {t('sched_upcoming_hdr')} · {len(s_upcoming)}")
            for ev in s_upcoming:
                _event_card(ev["title"], ev["date"], ev["location"],
                            ev["status"], SEJOURNE_COLOR)
        else:
            st.info(t("sched_no_upcoming"))

        if s_past:
            with st.expander(f"{t('sched_past_hdr')}（{len(s_past)}）", expanded=not s_upcoming):
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
    st.caption("🏛️ " + t("sched_ga_src"))
    st.markdown(
        '<a href="https://lcp.fr/recherche?q=attal&f%5B0%5D=type_de_contenu%3Aepisode" '
        'target="_blank" style="color:#aaa;font-size:0.75rem;text-decoration:none">'
        '📺 ' + t("sched_lcp") + '</a>',
        unsafe_allow_html=True
    )

    try:
        a_events = get_attal_schedule()
    except Exception as _e:
        st.warning(f"{t('sched_load_err')}: {_e}")
        a_events = []
    today_str = date.today().isoformat()

    a_upcoming = [e for e in a_events if str(e.get("event_date",""))[:10] >= today_str]
    a_past     = sorted(
        [e for e in a_events if str(e.get("event_date",""))[:10] < today_str],
        key=lambda x: x.get("event_date",""), reverse=True
    )

    def _attal_row(ev, status: str, key_prefix: str):
        """渲染一条 Attal 行程卡片；管理员模式附带删除按钮。"""
        ev_date_str = str(ev.get("event_date", ""))[:10]

        def _card():
            _event_card(ev.get("title", ""), ev_date_str,
                        ev.get("location", ""), status,
                        ATTAL_COLOR, ev.get("source_url", ""),
                        ev.get("description", ""))

        if st.session_state.get("is_admin"):
            _c1, _c2 = st.columns([11, 1])
            with _c1:
                _card()
            with _c2:
                if st.button("🗑️", key=f"{key_prefix}_{ev.get('id')}",
                             help="删除", use_container_width=True):
                    get_supabase_admin().table("schedule").delete().eq("id", ev["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()
        else:
            _card()

    if a_upcoming:
        _section_header(f"▶ {t('sched_upcoming_hdr')} · {len(a_upcoming)}")
        for ev in a_upcoming:
            ev_date_str = str(ev.get("event_date",""))[:10]
            try:
                delta = (date.fromisoformat(ev_date_str) - date.today()).days
            except ValueError:
                delta = 1
            _attal_row(ev, "ongoing" if delta == 0 else "upcoming", "del_attal")
    elif not a_events:
        st.info(t("sched_no_entries"))

    if a_past:
        with st.expander(f"{t('sched_past_hdr')}（{len(a_past)}）"):
            for ev in a_past:
                _attal_row(ev, "past", "del_attal_past")

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
