#!/usr/bin/env python3
"""
Telegram 机器人入库:新闻 / 大事记(行程仍走 scripts/screenshot_to_db.py,照片走 photo_to_gallery.py)。

  python3 telegram-bot/save.py news  < {"title","url","source","person","published_at","summary"}
  python3 telegram-bot/save.py event < {"date","person","title","tag","note","source_url","image_url"}

news:按 url 的 md5 作 id upsert(和 add_news.yml / fetch_news 同一规则,重复发同一链接不会多一行)。
event:同 日期+人物+标题 已存在则跳过;写审计日志(admin_name「Telegram 机器人」)。
每次打印一行结果,claude 据此写回复。
"""
import hashlib
import json
import os
import sys

import sb

PEOPLE = {"Gabriel Attal", "Stéphane Séjourné", "S&A"}


def _ledger(table, row_id, label, storage=""):
    """Telegram 撤回用:把本次写入的行记进 $TG_LEDGER(每行一条 JSON);没设这个变量就什么都不做。"""
    path = os.environ.get("TG_LEDGER")
    if not path or not row_id:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"table": table, "id": str(row_id), "label": label, "storage": storage},
                           ensure_ascii=False) + "\n")


def save_news(d):
    url = (d.get("url") or "").strip()
    if not url or not d.get("title") or d.get("person") not in PEOPLE:
        sys.exit(f"⚠️ 新闻缺 url/title 或 person 不对: {d}")
    row = {
        "id": hashlib.md5(url.encode()).hexdigest(),
        "title": d["title"].strip(),
        "url": url,
        "source": (d.get("source") or "").strip(),
        "person": d["person"],
        "published_at": d.get("published_at") or "",
        "summary": (d.get("summary") or "").strip()[:500],
    }
    existed = sb.get_all("news", {"select": "id", "id": f"eq.{row['id']}"})
    sb.insert("news", row, upsert_on="id")
    if not existed:  # 本来就有的新闻撤回时不能删
        _ledger("news", row["id"], f"新闻 · {row['person']} · {row['title'][:60]}")
    print(f"{'↩️ 新闻已存在(已更新)' if existed else '✅ 新闻已入库'}: {row['person']} · {row['title'][:60]}")


def save_event(d):
    if not d.get("date") or not d.get("title") or d.get("person") not in PEOPLE:
        sys.exit(f"⚠️ 大事记缺 date/title 或 person 不对: {d}")
    dup = sb.get_all("events", {"select": "id", "date": f"eq.{d['date']}",
                                "person": f"eq.{d['person']}", "title": f"eq.{d['title']}"})
    if dup:
        print(f"↩️ 大事记已存在: {d['date']} · {d['title'][:60]}")
        return
    row = {k: d.get(k) or "" for k in ("date", "person", "title", "tag", "note", "source_url", "image_url")}
    row["source"] = "Telegram"
    ev = (sb.insert("events", row) or [{}])[0]
    sb.audit("insert", "events", ev.get("id"), row["title"])
    _ledger("events", ev.get("id"), f"大事记 {row['date']} · {row['person']} · {row['title'][:60]}")
    print(f"✅ 大事记已入库: {row['date']} · {row['person']} · {row['title'][:60]}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("news", "event"):
        sys.exit(__doc__)
    data = json.load(sys.stdin)
    {"news": save_news, "event": save_event}[sys.argv[1]](data)
