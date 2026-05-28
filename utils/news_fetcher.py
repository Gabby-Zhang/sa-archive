import feedparser
import hashlib
from datetime import datetime
from utils.database import upsert_news

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
        "person": "SS & GA"
    },
]

def fetch_all_news():
    results = []
    for feed_info in RSS_FEEDS:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries:
            url = entry.get("link", "")
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
