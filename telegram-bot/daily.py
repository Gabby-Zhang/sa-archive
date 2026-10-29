#!/usr/bin/env python3
"""
每日汇总的数据收集(telegram_daily.yml 调用):把当天的素材写成一份纯文本,交给 claude 写汇总。

  python3 telegram-bot/daily.py <输出文件>

素材:
  · 过去 24 小时入库的新闻(news,按人物分组)
  · 今天、明天的行程(schedule 表 + Séjourné 的 ICS 官方日历,跨天活动在覆盖的每一天都算)
  · 日期是今天的大事记(events)

「今天」按巴黎时间算;凌晨 4 点前运行(手动补跑)算作前一天的汇总。
"""
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests  # noqa: E402
import sb  # noqa: E402
from sync_schedule_to_events import ICS_URL, _ics_unescape  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
PREDICTED = ("[AN_AUTO]", "[EU_AUTO]", "[EP_MAYBE]", "[COUNCIL_AUTO]")


def _ics_date(v):
    m = re.search(r"(\d{4})(\d{2})(\d{2})", v)
    return date(int(m[1]), int(m[2]), int(m[3])) if m else None


def load_ics_days():
    """解析 SS 的 ICS,每条带 start / end(含)两个日期,跨天活动(如 29–30 日的峰会)两天都算。

    DTEND 是全天日期(VALUE=DATE)时按 ICS 惯例不含当天,要减一天;带时间的 DTEND 就是结束那天。
    """
    lines = []
    for raw in requests.get(ICS_URL, timeout=20).text.splitlines():
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur and cur.get("title") and cur.get("start"):
                cur.setdefault("end", cur["start"])
                events.append(cur)
            cur = None
        elif cur is None:
            continue
        elif line.startswith("SUMMARY:"):
            cur["title"] = _ics_unescape(line[8:])
        elif line.startswith("DTSTART"):
            cur["start"] = _ics_date(line.split(":")[-1])
        elif line.startswith("DTEND"):
            end = _ics_date(line.split(":")[-1])
            if end and "T" not in line.split(":")[-1]:
                end -= timedelta(days=1)
            cur["end"] = end
        elif line.startswith("LOCATION:"):
            cur["location"] = _ics_unescape(line[9:])
        elif line.startswith("DESCRIPTION:") and "description" not in cur:
            cur["description"] = _ics_unescape(line[12:])
    for e in events:
        if not e["end"] or e["end"] < e["start"]:
            e["end"] = e["start"]
    return events


def main(out_path):
    now = datetime.now(PARIS)
    today = now.date() - timedelta(days=1) if now.hour < 4 else now.date()
    tomorrow = today + timedelta(days=1)
    since_utc = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    lines = [f"今天:{today.isoformat()}({'一二三四五六日'[today.weekday()]}),现在巴黎时间 {now:%H:%M}", ""]

    news = sb.get_all("news", [("select", "title,source,person,url,published_at,category"),
                               ("published_at", f"gte.{since_utc}"), ("order", "published_at.desc")])
    news = [n for n in news if n.get("category") != "historical"]
    lines.append(f"## 过去 24 小时新闻(共 {len(news)} 条)")
    for person in ("S&A", "Stéphane Séjourné", "Gabriel Attal"):
        items = [n for n in news if n.get("person") == person]
        lines.append(f"### {person}({len(items)} 条)")
        for n in items[:40]:
            lines.append(f"- {n.get('title')} — {n.get('source') or ''} | {n.get('url') or ''}")
    lines.append("")

    sched = sb.get_all("schedule", [("select", "person,event_date,title,location,description"),
                                    ("event_date", f"gte.{today}"), ("event_date", f"lte.{tomorrow}"),
                                    ("order", "event_date.asc")])
    try:
        ics = [e for e in load_ics_days() if e["start"] <= tomorrow and e["end"] >= today]
    except Exception as e:
        ics = []
        lines.append(f"(SS 官方日历读取失败:{e})")
    for label, day in (("今天", today.isoformat()), ("明天", tomorrow.isoformat())):
        lines.append(f"## {label}行程({day})")
        for r in sched:
            if str(r.get("event_date"))[:10] == day:
                desc = r.get("description") or ""
                flag = "【推测】" if any(t in desc for t in PREDICTED) else ""
                loc = f" @ {r['location']}" if r.get("location") else ""
                lines.append(f"- {r.get('person')}:{flag}{r.get('title')}{loc}")
        for e in ics:
            if e["start"].isoformat() <= day <= e["end"].isoformat():
                flag = "【推测】" if any(t in e.get("description", "") for t in PREDICTED) else ""
                loc = f" @ {e['location']}" if e.get("location") else ""
                lines.append(f"- Stéphane Séjourné(官方日历):{flag}{e['title']}{loc}")
        lines.append("")

    events = sb.get_all("events", [("select", "person,title,tag,note"), ("date", f"eq.{today}")])
    lines.append(f"## 今天的大事记({len(events)} 条)")
    for e in events:
        lines.append(f"- {e.get('person')} · {e.get('tag') or ''} · {e.get('title')}")

    Path(out_path).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
