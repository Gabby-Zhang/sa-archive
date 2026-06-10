"""
独立新闻抓取脚本 — 供 GitHub Actions 定时调用。
抓取逻辑全部在 utils/news_fetcher.py（与页面按钮共用同一份源列表），
本脚本只负责连接 Supabase 并入库。
"""
import os
import sys
from pathlib import Path

# 让 utils 包可被 import（脚本位于 scripts/ 子目录）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase import create_client
from utils.news_fetcher import collect_news

SUPABASE_URL = os.environ["SUPABASE_URL"]
# 优先 service key（RLS 收紧后 anon 不可写）；缺失时回退 anon key
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_KEY)

results = collect_news()

if results:
    seen = {}
    for item in results:
        seen[item["id"]] = item
    unique = list(seen.values())
    db.table("news").upsert(unique, on_conflict="id").execute()
    print(f"✅ 抓取完成，共处理 {len(unique)} 条新闻")
else:
    print("⚠️ 未获取到任何新闻")
