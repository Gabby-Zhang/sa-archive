"""手动从 Supabase `schedule` 表删一条错误行程(由 .github/workflows/delete_schedule.yml 调用)。

用于删掉入库错了的条目(Telegram 截图解析错、新闻抽取日期错等)。SS 的这类条目
在行程日历里没有删除按钮,只能走这里。

按 人 + 日期 + 标题关键词(不区分大小写的子串)定位;命中多条时默认拒绝,
需要更精确的关键词或打开 allow_multiple。DRY_RUN=true(默认)只打印不删。
同时删掉 sync_schedule_to_events 已经同步进 `events`(大事记)的同一条
(source="行程同步"、同人同日、标题含同一关键词)。删除都记 audit_log。
"""
import os
import sys
from datetime import datetime

import requests

PEOPLE = {"Gabriel Attal", "Stéphane Séjourné", "S&A"}


def _truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes", "y")


def main():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    person = os.environ.get("PERSON", "").strip()
    date = os.environ.get("EVENT_DATE", "").strip()
    match = os.environ.get("MATCH", "").strip()
    dry_run = _truthy(os.environ.get("DRY_RUN", "true"))
    allow_multiple = _truthy(os.environ.get("ALLOW_MULTIPLE", "false"))
    also_events = _truthy(os.environ.get("ALSO_EVENTS", "true"))

    if not url or not key:
        sys.exit("缺少 SUPABASE_URL / SUPABASE_SERVICE_KEY secret。")
    if person not in PEOPLE:
        sys.exit(f"person 必须是 {sorted(PEOPLE)} 之一,收到: {person!r}")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"event_date 必须是 YYYY-MM-DD,收到: {date!r}")
    if len(match) < 3:
        sys.exit("标题关键词至少 3 个字符,防止误删。")

    hdr = {"apikey": key, "Authorization": f"Bearer {key}"}
    needle = match.lower()

    def find(table, params):
        r = requests.get(f"{url}/rest/v1/{table}", headers=hdr, params=params, timeout=10)
        r.raise_for_status()
        return [row for row in r.json() if needle in (row.get("title") or "").lower()]

    def delete(table, rows, label):
        for row in rows:
            print(f"  {'[dry-run] 将删除' if dry_run else '删除'} {table} id={row['id']}: {row.get('title')}")
            if dry_run:
                continue
            r = requests.delete(f"{url}/rest/v1/{table}", headers=hdr,
                                params={"id": f"eq.{row['id']}"}, timeout=10)
            r.raise_for_status()
            try:
                requests.post(f"{url}/rest/v1/audit_log",
                              headers={**hdr, "Content-Type": "application/json",
                                       "Prefer": "return=minimal"},
                              json={"admin_name": "手动删除(workflow)", "admin_role": "",
                                    "action": "delete", "table_name": table,
                                    "record_id": str(row["id"]),
                                    "detail": f"{label} {date} {row.get('title') or ''}"[:200]},
                              timeout=10)
            except Exception:
                pass  # 审计失败不影响删除

    sched = find("schedule", {"select": "id,title,description",
                              "person": f"eq.{person}", "event_date": f"eq.{date}"})
    print(f"schedule 命中 {len(sched)} 条({person} {date} 标题含 {match!r})")
    if not sched:
        sys.exit("没找到匹配的行程,什么都没删。检查日期/人物/关键词。")
    if len(sched) > 1 and not allow_multiple:
        for row in sched:
            print(f"  id={row['id']}: {row.get('title')}")
        sys.exit("命中多条,已拒绝。请用更精确的关键词,或勾选 allow_multiple。")
    delete("schedule", sched, person)

    if also_events:
        evs = find("events", {"select": "id,title,source", "person": f"eq.{person}",
                              "date": f"eq.{date}", "source": "eq.行程同步"})
        print(f"大事记(行程同步)命中 {len(evs)} 条")
        delete("events", evs, person)

    print("dry-run 完成,未改动数据库。确认无误后取消勾选 dry_run 再跑一次。" if dry_run
          else "已删除。sejourn.ics 会在下次同步后去掉这条。")


if __name__ == "__main__":
    main()
