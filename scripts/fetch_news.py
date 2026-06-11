"""
独立新闻抓取脚本 — 供 GitHub Actions 定时调用。
抓取逻辑全部在 utils/news_fetcher.py（与页面按钮共用同一份源列表），
本脚本只负责连接 Supabase 入库，并对新发现的 S&A 同框报道推送 ntfy 提醒。
"""
import os
import sys
import requests
from pathlib import Path

# 让 utils 包可被 import（脚本位于 scripts/ 子目录）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase import create_client
from utils.news_fetcher import collect_news

SUPABASE_URL = os.environ["SUPABASE_URL"]
# 优先 service key（RLS 收紧后 anon 不可写）；缺失时回退 anon key
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "ss-calendar-update")
db = create_client(SUPABASE_URL, SUPABASE_KEY)


def notify_new_sa(items: list):
    """新的 S&A 同框报道 → ntfy 推送，提醒人工鉴别是否收录大事记。"""
    sa_items = [i for i in items if i.get("person") == "S&A"]
    if not sa_items:
        return
    # 只对数据库里不存在的（真正新发现的）推送
    ids = [i["id"] for i in sa_items]
    try:
        existing = db.table("news").select("id").in_("id", ids).execute().data or []
        existing_ids = {r["id"] for r in existing}
    except Exception:
        return
    fresh = [i for i in sa_items if i["id"] not in existing_ids]
    if not fresh:
        return

    lines = [f"· {i['title'][:60]}（{i['source']}）" for i in fresh[:3]]
    if len(fresh) > 3:
        lines.append(f"…等共 {len(fresh)} 篇")
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data="\n".join(lines).encode("utf-8"),
            headers={
                "Title": "Found SA news - check & pin?".encode("utf-8"),
                "Tags": "two_hearts",
            },
            timeout=10,
        )
        print(f"💗 已推送 {len(fresh)} 篇新同框报道提醒")
    except Exception as e:
        print(f"⚠️ ntfy 推送失败: {e}")


results = collect_news()

if results:
    seen = {}
    for item in results:
        seen[item["id"]] = item
    unique = list(seen.values())
    notify_new_sa(unique)   # 必须在 upsert 之前比对，否则全都"已存在"
    db.table("news").upsert(unique, on_conflict="id").execute()
    print(f"✅ 抓取完成，共处理 {len(unique)} 条新闻")
else:
    print("⚠️ 未获取到任何新闻")
