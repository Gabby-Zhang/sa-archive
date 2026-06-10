#!/usr/bin/env python3
"""
全表备份 — 供 GitHub Actions 每周调用。

把所有表导出为 JSON 文件（写入 backup/ 目录），workflow 再把目录
打包成 artifact 保留 90 天。手工录入的 events/profile 数据无法重建，
这是唯一的灾备。

分页读取（每批 1000 行），不受 PostgREST 单次返回上限影响。
"""
import os
import json
import pathlib
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# 档案馆全部数据表；不存在的表会被跳过
TABLES = [
    "events", "news", "schedule", "files", "images", "resources",
    "profile_items", "team_members", "event_links", "photo_alerts",
]

PAGE = 1000


def dump_table(name: str) -> "int | None":
    """分页拉取整张表，返回行数；表不存在/无权限时返回 None。"""
    rows = []
    offset = 0
    while True:
        try:
            batch = (db.table(name).select("*")
                     .range(offset, offset + PAGE - 1)
                     .execute().data) or []
        except Exception as e:
            print(f"⚠️ 跳过 {name}: {e}")
            return None
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE

    out = pathlib.Path("backup") / f"{name}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    return len(rows)


def main():
    pathlib.Path("backup").mkdir(exist_ok=True)
    summary = {"backed_up_at": datetime.now(timezone.utc).isoformat(), "tables": {}}

    for tbl in TABLES:
        n = dump_table(tbl)
        if n is not None:
            summary["tables"][tbl] = n
            print(f"✅ {tbl}: {n} 行")

    pathlib.Path("backup/_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(summary["tables"].values())
    print(f"\n✅ 备份完成：{len(summary['tables'])} 张表，共 {total} 行")


if __name__ == "__main__":
    main()
