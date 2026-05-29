import feedparser
import hashlib
import requests
from datetime import datetime
from utils.database import upsert_news


def _resolve_url(url: str, timeout: int = 5) -> str:
    """将 Google News 重定向链接解析为真实文章 URL。"""
    if "news.google.com" not in url:
        return url
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout,
                          headers={"User-Agent": "Mozilla/5.0"})
        final = r.url
        # 如果还是 google 域名（重定向失败），改用 GET
        if "google.com" in final:
            r = requests.get(url, allow_redirects=True, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0"})
            final = r.url
        return final if "google.com" not in final else url
    except Exception:
        return url

RSS_FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=Gabriel+Attal&hl=fr&gl=FR&ceid=FR:fr",
        "person": "Gabriel Attal"
    },
    {
        "url": "https://news.google.com/rss/search?q=Stéphane+Séjourné&hl=fr&gl=FR&ceid=FR:fr",
        "person": "Stéphane Séjourné"
    },
    {
        "url": "https://news.google.com/rss/search?q=Attal+Séjourné&hl=fr&gl=FR&ceid=FR:fr",
        "person": "S&A"
    },
]

def fetch_all_news():
    results = []
    for feed_info in RSS_FEEDS:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries:
            raw_url = entry.get("link", "")
            url = _resolve_url(raw_url)          # 追踪到真实文章 URL
            url_hash = hashlib.md5(url.encode()).hexdigest()
            published = entry.get("published", "")
            try:
                pub_dt = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                pub_dt = datetime.now().isoformat()

            # 提取媒体来源
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
        upsert_news(results)
    return len(results)
