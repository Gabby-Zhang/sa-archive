"""拿 sejourn-calendar 的 ICS 和出差报销表(data/sejourne_missions.json)对照,找出每趟出差里具体哪天在巴黎。

用法:
    python3 scripts/missions_calendar_check.py                 # 只看 calp 还空着的出差
    python3 scripts/missions_calendar_check.py --since 2026-07-01
    python3 scripts/missions_calendar_check.py --all           # 全部出差都列
    python3 scripts/missions_calendar_check.py --apply         # 把建议的巴黎日期写进 calp(只写原本为空的)

报销表只有整趟起止日;ICS 里的单场会议(透明度登记处 / 欧委会议程)带日期和地点,
地点含 Paris 的那天就能确认人在巴黎。另外检查两件事:
- ICS 里 "Mission:" 开头的事件就是同一份报销数据,对不上的会列出来(报销表有新数据但日历还没同步,或反过来)
- 同一天既有巴黎又有别的城市的条目,标 ⚠️,多半是透明度登记处地点填错(2026-04-20 Eurofer 就是这样),需要人工判断
"""
import argparse
import json
import pathlib
import re
import sys
from datetime import date

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.missions import DATA_PATH  # noqa: E402

ICS_URL = "https://raw.githubusercontent.com/Gabby-Zhang/sejourn-calendar/main/sejourn.ics"


def load_ics():
    text = requests.get(ICS_URL, timeout=30).text
    text = re.sub(r"\r?\n[ \t]", "", text)  # ICS 折行还原
    events = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        def field(name):
            m = re.search(rf"^{name}[^:\n]*:(.*)$", block, re.M)
            return m.group(1).strip().replace("\\,", ",").replace("\\n", " ") if m else ""
        start = field("DTSTART")[:8]
        if len(start) != 8:
            continue
        events.append({"date": f"{start[:4]}-{start[4:6]}-{start[6:]}", "title": field("SUMMARY"),
                       "loc": field("LOCATION")})
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="只看这天(YYYY-MM-DD)之后出发的出差")
    ap.add_argument("--all", action="store_true", help="calp 已填的也列出来")
    ap.add_argument("--apply", action="store_true", help="把建议日期写进 JSON 里 calp 为空的条目")
    args = ap.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    events = load_ics()
    mission_days = {e["date"] for e in events if e["title"].startswith("Mission:")}
    meetings = [e for e in events if not e["title"].startswith("Mission:")]

    missing = [m["f"] for m in data["missions"] if m["f"] not in mission_days]
    extra = sorted(d for d in mission_days if d not in {m["f"] for m in data["missions"]})
    print(f"报销表 {len(data['missions'])} 条 / 日历 Mission 条目 {len(mission_days)} 条")
    if missing:
        print(f"  日历里没有的出差(出发日):{missing}")
    if extra:
        print(f"  日历有、报销表没有的出差(可能报销表更新了,先跑 missions_to_json.py):{extra}")

    applied = 0
    for m in data["missions"]:
        if args.since and m["f"] < args.since:
            continue
        if m.get("calp") and not args.all:
            continue
        inside = [e for e in meetings if m["f"] <= e["date"] <= m["t"]]
        paris_days = sorted({e["date"] for e in inside if "paris" in e["loc"].lower()})
        print(f"\n■ {m['f']} → {m['t']}  {', '.join(m['stops'])}")
        if not inside:
            print("   (日历里这段时间没有单场会议)")
            continue
        by_day = {}
        for e in inside:
            by_day.setdefault(e["date"], []).append(e)
        for d in sorted(by_day):
            locs = {("Paris" if "paris" in e["loc"].lower() else e["loc"] or "?") for e in by_day[d]}
            warn = " ⚠️ 同日多地,检查地点" if "Paris" in locs and len(locs) > 1 else ""
            wd = "一二三四五六日"[date.fromisoformat(d).weekday()]
            for e in by_day[d]:
                print(f"   {d} 周{wd}  {e['loc'] or '?'} | {e['title'][:90]}")
            if warn:
                print(f"  {warn}")
        print(f"   → 建议 calp: {paris_days}")
        if args.apply and not m.get("calp") and paris_days:
            m["calp"] = paris_days
            applied += 1

    if args.apply:
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n✅ 写入 calp {applied} 条(⚠️ 标记的那几天请人工复核)")


if __name__ == "__main__":
    main()
