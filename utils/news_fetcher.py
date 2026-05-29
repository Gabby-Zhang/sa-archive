import feedparser
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from utils.database import upsert_news


def _resolve_url(url: str) -> str:
    """占位：新抓取已改用 summary HTML 提取，此函数仅供向后兼容。"""
    return url


def _extract_url_from_summary(summary_html: str) -> str:
    """
    从 Google News RSS 条目的 description/summary HTML 里提取真实文章 URL。
    Google News RSS 的 <description> 包含 <a href="真实URL">来源</a> 的结构。
    """
    if not summary_html:
        return ""
    try:
        soup = BeautifulSoup(summary_html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "google.com" not in href:
                return href
    except Exception:
        pass
    return ""

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
            # 优先从 summary HTML 里提取真实文章 URL
            real_url = _extract_url_from_summary(entry.get("summary", ""))
            url = real_url if real_url else entry.get("link", "")
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
