"""
独立新闻抓取脚本 — 供 GitHub Actions 定时调用
不依赖 streamlit，直接读取环境变量连接 Supabase
"""
import os
import feedparser
import hashlib
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_KEY)

RSS_FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=Gabriel+Attal&hl=fr&gl=FR&ceid=FR:fr",
        "person": "Gabriel Attal"
    },
    {
        "url": "https://news.google.com/rss/search?q=St%C3%A9phane+S%C3%A9journ%C3%A9&hl=fr&gl=FR&ceid=FR:fr",
        "person": "Stéphane Séjourné"
    },
    {
        "url": "https://news.google.com/rss/search?q=Attal+S%C3%A9journ%C3%A9&hl=fr&gl=FR&ceid=FR:fr",
        "person": "S&A"
    },
]

results = []
for feed_info in RSS_FEEDS:
    feed = feedparser.parse(feed_info["url"])
    for entry in feed.entries:
        url = entry.get("link", "")
        url_hash = hashlib.md5(url.encode()).hexdigest()
        try:
            pub_dt = datetime(*entry.published_parsed[:6]).isoformat()
        except Exception:
            pub_dt = datetime.now().isoformat()

        source = ""
        if hasattr(entry, "source"):
            source = entry.source.get("title", "")
        elif " - " in entry.get("title", ""):
            source = entry.title.split(" - ")[-1]

        results.append({
            "id": url_hash,
            "title": entry.get("title", "").split(" - ")[0].strip(),
            "url": url,
            "source": source,
            "person": feed_info["person"],
            "published_at": pub_dt,
            "summary": entry.get("summary", "")[:500],
        })

if results:
    seen = {}
    for item in results:
        seen[item["id"]] = item
    unique = list(seen.values())
    db.table("news").upsert(unique, on_conflict="id").execute()
    print(f"✅ 抓取完成，共处理 {len(unique)} 条新闻")
else:
    print("⚠️ 未获取到任何新闻")
