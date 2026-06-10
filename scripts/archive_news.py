#!/usr/bin/env python3
"""
新闻链接存档 — 供 GitHub Actions 每天调用。

把最近 24 小时入库的新闻 URL 提交给 Internet Archive（Wayback Machine），
防止日后原文 404 / 改版 / 上付费墙。尽力而为：单条失败不影响其他。
"""
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_KEY)

MAX_PER_RUN = 30   # Wayback SPN 有限流，每天 30 条足够覆盖日增量
SLEEP_SECS  = 3


def main():
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = (db.table("news")
            .select("url,title")
            .gte("published_at", cutoff)
            .order("published_at", desc=True)
            .limit(MAX_PER_RUN * 2)
            .execute().data) or []

    # 过滤掉没解码成功的 Google News 链接（存档无意义）
    urls = []
    seen = set()
    for r in rows:
        u = (r.get("url") or "").strip()
        if not u or "google.com" in u or u in seen:
            continue
        seen.add(u)
        urls.append(u)
    urls = urls[:MAX_PER_RUN]

    if not urls:
        print("近 24 小时无新链接需要存档")
        return

    ok = failed = 0
    for u in urls:
        try:
            r = requests.get(f"https://web.archive.org/save/{u}",
                             timeout=60,
                             headers={"User-Agent": "sa-archive-bot/1.0"})
            if r.status_code in (200, 301, 302):
                ok += 1
                print(f"✅ {u[:80]}")
            else:
                failed += 1
                print(f"⚠️ HTTP {r.status_code}: {u[:80]}")
        except Exception as e:
            failed += 1
            print(f"⚠️ {type(e).__name__}: {u[:80]}")
        time.sleep(SLEEP_SECS)

    print(f"\n完成 — 提交 {ok} 条，失败 {failed} 条（失败的明天还有机会被 Wayback 自然收录）")


if __name__ == "__main__":
    main()
