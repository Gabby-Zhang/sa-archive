import base64
import feedparser
import hashlib
from datetime import datetime
from utils.database import upsert_news


def _resolve_url(url: str) -> str:
    """
    将 Google News 的 Base64 编码 URL 解码为真实文章 URL。
    Google News 的 CBMi... 部分是 Base64 编码，内含真实地址，无需 HTTP 请求。
    """
    if "news.google.com" not in url:
        return url
    try:
        # 提取编码部分
        if "/rss/articles/" in url:
            encoded = url.split("/rss/articles/")[1].split("?")[0]
        elif "/articles/" in url:
            encoded = url.split("/articles/")[1].split("?")[0]
        else:
            return url

        # 补齐 base64 padding 并解码
        encoded += "=" * ((4 - len(encoded) % 4) % 4)
        decoded = base64.urlsafe_b64decode(encoded)

        # 在解码后的字节中找 http(s):// 开头的真实 URL
        for prefix in (b"https://", b"http://"):
            idx = decoded.find(prefix)
            if idx >= 0:
                # 取到第一个不可打印字符（控制符）为止
                end = idx
                while end < len(decoded) and decoded[end] >= 32:
                    end += 1
                candidate = decoded[idx:end].decode("utf-8", errors="replace")
                if "." in candidate and len(candidate) > 10:
                    return candidate
        return url
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
