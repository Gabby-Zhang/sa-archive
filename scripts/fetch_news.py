"""
独立新闻抓取脚本 — 供 GitHub Actions 定时调用
不依赖 streamlit，直接读取环境变量连接 Supabase
"""
import os
import re
import json
import feedparser
import hashlib
import requests
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


# ── attalpresident.fr sitemap 抓取 ──────────────────────────────────────────
def fetch_attal_officiel():
    """
    通过 sitemap.xml 找出所有 /actualites/* 文章，
    解析 JSON-LD 提取标题、日期、描述，存入 news 表。
    """
    HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    BASE = "https://attalpresident.fr"
    items = []

    try:
        sitemap = requests.get(f"{BASE}/sitemap.xml", headers=HEADERS, timeout=15).text
        urls = re.findall(r'<loc>(https://attalpresident\.fr/actualites/[^<]+)</loc>', sitemap)
    except Exception as e:
        print(f"⚠️ attalpresident.fr sitemap 失败: {e}")
        return []

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            text = r.text

            # 提取 JSON-LD NewsArticle
            json_lds = re.findall(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', text, re.DOTALL
            )
            article = None
            for jld in json_lds:
                try:
                    data = json.loads(jld)
                    objs = data if isinstance(data, list) else [data]
                    for obj in objs:
                        if obj.get("@type") in ("NewsArticle", "Article", "BlogPosting"):
                            article = obj
                            break
                except Exception:
                    pass
                if article:
                    break

            if not article:
                continue

            headline = article.get("headline", "").strip()
            description = article.get("description", "").strip()
            date_raw = article.get("datePublished", "")

            try:
                pub_dt = datetime.fromisoformat(
                    date_raw.replace("Z", "+00:00")
                ).isoformat()
            except Exception:
                pub_dt = datetime.now().isoformat()

            url_hash = hashlib.md5(url.encode()).hexdigest()
            items.append({
                "id":           url_hash,
                "title":        headline,
                "url":          url,
                "source":       "attalpresident.fr",
                "person":       "Gabriel Attal",
                "published_at": pub_dt,
                "summary":      description[:500],
            })
        except Exception as e:
            print(f"  ⚠️ 解析失败 {url}: {e}")

    print(f"  attalpresident.fr: {len(items)} 篇文章")
    return items


attal_officiel = fetch_attal_officiel()
results.extend(attal_officiel)

if results:
    seen = {}
    for item in results:
        seen[item["id"]] = item
    unique = list(seen.values())
    db.table("news").upsert(unique, on_conflict="id").execute()
    print(f"✅ 抓取完成，共处理 {len(unique)} 条新闻")
else:
    print("⚠️ 未获取到任何新闻")
