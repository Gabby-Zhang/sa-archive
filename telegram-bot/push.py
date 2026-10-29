#!/usr/bin/env python3
"""
Telegram 实时推送(telegram_push.yml 每 30 分钟跑一次):有新内容就推给管理员。

推什么:
  · 新闻:和 fetch_news 同一份源(utils/news_fetcher.collect_news,不爬 attalpresident.fr),
    只看 48 小时内发布的,SS / GA / S&A 全推(2026-10-29 用户要求 GA 也全推,不筛)
  · 新行程:schedule 表里新出现的、今天及以后的 SS/GA/S&A 行程
    (跳过 [AN_AUTO] 推测条目和 [TELEGRAM] 管理员自己发的)
  · 欧盟影像库:新出现的 Séjourné 照片/视频(14 天内)

去重:推过的条目在 profile_items(person=S&A, section=tg_push_seen)记一行 key。
第一次运行(一行都没有)只把现有条目全部标记为已推、发一条「已启动」,不刷屏。
"""
import html
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sb  # noqa: E402
import tg  # noqa: E402
from utils.eu_av import fetch_sejourne_av  # noqa: E402
from utils.news_fetcher import collect_news  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
SEEN_SECTION = "tg_push_seen"
MAX_PER_GROUP = 12

GROUPS = [  # (分组键, 标题)
    ("S&A", "💞 S&A"),
    ("Stéphane Séjourné", "🔵 Séjourné"),
    ("Gabriel Attal", "🟡 Attal"),
    ("schedule", "🗓️ 新行程"),
    ("av", "📷 欧盟影像库 · Séjourné"),
]
SHORT = {"Stéphane Séjourné": "SS", "Gabriel Attal": "GA", "S&A": "S&A"}


def _e(s):
    return html.escape(str(s or ""), quote=False)


def _link(title, url):
    return f'<a href="{html.escape(url)}">{_e(title)}</a>' if url else _e(title)


def news_candidates():
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=48)
    out = []
    for it in collect_news(include_official=False):
        try:
            if datetime.fromisoformat(it["published_at"][:19]) < cutoff:
                continue
        except ValueError:
            continue
        src = f" — {_e(it['source'])}" if it.get("source") else ""
        out.append((f"n:{it['id']}", it["person"], f"• {_link(it['title'], it['url'])}{src}"))
    return out


def schedule_candidates():
    today = datetime.now(PARIS).date().isoformat()
    rows = sb.get_all("schedule", [("select", "id,person,event_date,title,description,source_url"),
                                   ("event_date", f"gte.{today}")])
    out = []
    for r in rows:
        desc = r.get("description") or ""
        if "[AN_AUTO]" in desc or "[TELEGRAM]" in desc:
            continue
        d = str(r.get("event_date"))[:10]
        label = f"{d[5:7]}/{d[8:10]} {SHORT.get(r.get('person'), r.get('person'))}"
        tag = " 📰" if "[NEWS_AUTO]" in desc else ""
        out.append((f"s:{r['id']}", "schedule",
                    f"• {label} · {_link(r.get('title'), r.get('source_url'))}{tag}"))
    return out


def av_candidates():
    cutoff = (datetime.now(PARIS).date() - timedelta(days=14)).isoformat()
    out = []
    for it in fetch_sejourne_av(limit=30):
        if (it.get("date") or "") < cutoff:
            continue
        out.append((f"av:{it['ref']}", "av", f"• {it.get('date', '')} · {_link(it['title'], it.get('url'))}"))
    return out


def main():
    seen = {r["key"] for r in sb.get_all("profile_items", {
        "select": "key", "person": "eq.S&A", "section": f"eq.{SEEN_SECTION}"})}
    cands, failed = [], []
    for name, fn in (("新闻", news_candidates), ("行程", schedule_candidates), ("影像库", av_candidates)):
        try:
            got = fn()
            print(f"{name}: {len(got)} 条候选")
            cands += got
        except Exception as e:  # 单个源挂了不影响其它源
            print(f"⚠️ {name} 抓取失败: {e}")
            failed.append(name)

    fresh, keys = [], set()
    for key, group, line in cands:
        if key not in seen and key not in keys:
            keys.add(key)
            fresh.append((key, group, line))
    print(f"新条目 {len(fresh)} 条(已推过 {len(seen)} 条)")

    if not seen:
        tg.send(f"✅ 实时推送已启动。现有 {len(fresh)} 条内容记为已读,之后有新的会推给你。")
    elif fresh:
        now = datetime.now(PARIS).strftime("%m/%d %H:%M")
        parts = [f"🔔 <b>新动态</b> · {now}"]
        for gkey, gtitle in GROUPS:
            lines = [line for _, g, line in fresh if g == gkey]
            if not lines:
                continue
            more = f"\n…等共 {len(lines)} 条" if len(lines) > MAX_PER_GROUP else ""
            parts.append(f"<b>{gtitle}</b>\n" + "\n".join(lines[:MAX_PER_GROUP]) + more)
        tg.send("\n\n".join(parts), html=True)

    # 推送成功后才记为已推(推送失败下次会重推,不会漏);首次运行另记一个 init 标记
    marks = [k for k, _, _ in fresh] + ([] if seen else ["init"])
    sb.insert("profile_items", [{"person": "S&A", "section": SEEN_SECTION, "key": k, "value": ""}
                                for k in marks])
    if failed and len(failed) == 3:
        sys.exit("所有来源都抓取失败")


if __name__ == "__main__":
    main()
