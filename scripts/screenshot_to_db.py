#!/usr/bin/env python3
"""
截图行程 → Supabase schedule 表

供本机定时 agent 使用：agent 用视觉解析截图后，把结构化 JSON 通过 stdin 传入。

输入格式：
  {
    "schedule": [
      {
        "person": "Gabriel Attal",
        "event_date": "2026-06-10",
        "title": "📺 Gabriel Attal sur BFMTV (22h40)",
        "location": "",                          # 可选
        "description": "IG 截图 · @attalpresident_",  # 可选
        "source_url": ""                         # 可选
      }
    ]
  }

去重：同 person + event_date + title 前 40 字符已存在则跳过。
凭据：读取项目 .streamlit/secrets.toml（本机），或环境变量。
"""
import os
import sys
import json
import pathlib

def _load_creds():
    secrets_path = pathlib.Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import toml
            s = toml.load(str(secrets_path))
            url = s.get("SUPABASE_URL", "")
            key = s.get("SUPABASE_SERVICE_KEY") or s.get("SUPABASE_KEY", "")
            if url and key:
                return url, key
        except Exception as e:
            print(f"⚠️ secrets.toml 读取失败: {e}", file=sys.stderr)
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url, key
    raise RuntimeError("找不到 Supabase 凭据")


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("未从 stdin 收到任何输入", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    items = data.get("schedule", [])
    if not items:
        print("schedule 为空，无事可做")
        return

    url, key = _load_creds()
    from supabase import create_client
    db = create_client(url, key)

    inserted = skipped = 0
    for item in items:
        person = item.get("person", "Gabriel Attal")
        ev_date = item.get("event_date", "")
        title = item.get("title", "").strip()
        if not ev_date or not title:
            print(f"⚠️ 缺少日期或标题，跳过: {item}", file=sys.stderr)
            continue

        existing = (db.table("schedule").select("id")
                    .eq("person", person)
                    .eq("event_date", ev_date)
                    .ilike("title", f"{title[:40]}%")
                    .execute().data)
        if existing:
            skipped += 1
            print(f"↩️ 已存在，跳过: {ev_date} · {title[:50]}")
            continue

        db.table("schedule").insert({
            "person":      person,
            "event_date":  ev_date,
            "title":       title,
            "location":    item.get("location", ""),
            "description": item.get("description", "截图 · auto"),
            "source_url":  item.get("source_url", ""),
        }).execute()
        inserted += 1
        print(f"✅ 已写入: {ev_date} · {title[:60]}")

    print(f"\n完成 — 新增 {inserted} 条，跳过 {skipped} 条")


if __name__ == "__main__":
    main()
