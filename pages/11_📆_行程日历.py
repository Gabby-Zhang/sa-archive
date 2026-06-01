import streamlit as st
import requests
from datetime import date
from utils.auth import admin_sidebar
from utils.i18n import t
from utils.database import get_supabase_admin
from utils.i18n import t

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

    st.markdown(
        f'<div style="{bg};border-radius:0 8px 8px 0;padding:0.55rem 0.85rem;margin:0.3rem 0;opacity:{opacity}">'
        f'<div style="color:{date_color};font-size:0.73rem;font-weight:600">{ev_date}{badge}</div>'
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
    st.caption("📡 " + ("EU Commission · auto-sync · hourly" if st.session_state.get("lang")=="en" else "欧盟委员会官网 · 自动同步 · 每小时刷新"))

    if st.button("🔄", key="refresh_s", help="Refresh" if st.session_state.get("lang")=="en" else "强制刷新 Séjourné 日程"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Loading…" if st.session_state.get("lang")=="en" else "正在读取日程…"):
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

    _en = st.session_state.get("lang") == "en"
    if not s_events:
        st.info("No schedule data" if _en else "暂无日程数据")
    else:
        s_upcoming = sorted([e for e in s_events if e["status"] != "past"], key=lambda x: x["date"])
        s_past     = sorted([e for e in s_events if e["status"] == "past"],  key=lambda x: x["date"], reverse=True)

        if s_upcoming:
            _section_header(f"▶ {'Upcoming' if _en else '即将到来'} · {len(s_upcoming)}")
            for ev in s_upcoming:
                _event_card(ev["title"], ev["date"], ev["location"],
                            ev["status"], SEJOURNE_COLOR)
        else:
            st.info("No upcoming events" if _en else "暂无即将到来的行程")

        if s_past:
            _lbl = f"Past events ({len(s_past)})" if _en else f"历史行程（{len(s_past)} 条）"
            with st.expander(_lbl, expanded=not s_upcoming):
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
    st.caption("✏️ " + ("Maintained manually by the team" if st.session_state.get("lang")=="en" else "由团队手动维护"))

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
        st.info("No schedule entries" if st.session_state.get("lang")=="en" else "暂无行程记录")

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
