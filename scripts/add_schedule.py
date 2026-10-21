"""手动往 Supabase `schedule` 表加一条行程(由 .github/workflows/add_schedule.yml 工作流调用)。

用于新闻里出现、但自动抽取没收到的行程(例如已发过的文章被跨班去重跳过)。
参数走环境变量;按 (person, event_date, source_url 或 title) 幂等,重跑不重复写。
"""
import os
import sys
from datetime import datetime

import requests

PEOPLE = {"Gabriel Attal", "Stéphane Séjourné", "S&A"}
MANUAL_TAG = "[MANUAL]"


def main():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    person = os.environ.get("PERSON", "").strip()
    date = os.environ.get("EVENT_DATE", "").strip()
    title = os.environ.get("TITLE", "").strip()
    location = os.environ.get("LOCATION", "").strip()
    source_url = os.environ.get("SOURCE_URL", "").strip()
    note = os.environ.get("NOTE", "").strip()

    if not url or not key:
        sys.exit("缺少 SUPABASE_URL / SUPABASE_SERVICE_KEY secret,无法写库。")
    if person not in PEOPLE:
        sys.exit(f"person 必须是 {sorted(PEOPLE)} 之一,收到: {person!r}")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"event_date 必须是 YYYY-MM-DD,收到: {date!r}")
    if not title:
        sys.exit("title 不能为空。")

    hdr = {"apikey": key, "Authorization": f"Bearer {key}"}
    resp = requests.get(f"{url}/rest/v1/schedule", headers=hdr, params={
        "select": "id,title,source_url",
        "person": f"eq.{person}",
        "event_date": f"eq.{date}",
    }, timeout=10)
    resp.raise_for_status()
    for r in resp.json():
        if (source_url and r.get("source_url") == source_url) or r.get("title") == title:
            print(f"已存在,跳过: {date} {person} — {r.get('title')} (id={r.get('id')})")
            return

    desc = " · ".join(p for p in (f"{MANUAL_TAG} via add_schedule workflow", note) if p)
    resp = requests.post(f"{url}/rest/v1/schedule",
                         headers={**hdr, "Content-Type": "application/json",
                                  "Prefer": "return=minimal"},
                         json={"person": person, "event_date": date, "title": title,
                               "location": location, "source_url": source_url,
                               "description": desc},
                         timeout=10)
    resp.raise_for_status()
    print(f"已写入 schedule: {date} {person} — {title}")


if __name__ == "__main__":
    main()
