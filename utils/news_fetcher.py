import feedparser
import hashlib
from datetime import datetime
from utils.database import upsert_news

# ── 直接媒体 RSS 源（真实文章 URL，无 Google 跳转）────────────────────────
MEDIA_FEEDS = [
    # 法国主流报纸
    {"url": "https://www.lemonde.fr/politique/rss_full.xml",                    "source": "lemonde.fr"},
    {"url": "https://www.lemonde.fr/international/rss_full.xml",                "source": "lemonde.fr"},
    {"url": "https://www.lefigaro.fr/rss/figaro_politique.xml",                 "source": "lefigaro.fr"},
    {"url": "https://www.lefigaro.fr/rss/figaro_international.xml",             "source": "lefigaro.fr"},
    {"url": "https://www.liberation.fr/arc/outboundfeeds/rss/?outputType=xml",  "source": "liberation.fr"},
    {"url": "https://www.lexpress.fr/rss/politique.xml",                        "source": "lexpress.fr"},
    {"url": "https://www.lepoint.fr/politique/rss.xml",                         "source": "lepoint.fr"},
    {"url": "https://www.lepoint.fr/monde/rss.xml",                             "source": "lepoint.fr"},
    {"url": "https://www.nouvelobs.com/politique/rss.xml",                      "source": "nouvelobs.com"},
    # TV & radio
    {"url": "https://www.francetvinfo.fr/politique.rss",                        "source": "francetvinfo.fr"},
    {"url": "https://www.europe1.fr/rss.xml",                                   "source": "europe1.fr"},
    {"url": "https://www.rfi.fr/fr/politiques/rss",                             "source": "rfi.fr"},
    # Médias européens / internationaux (pour Séjourné)
    {"url": "https://rss.politico.eu/politics",                                 "source": "politico.eu"},
    {"url": "https://www.france24.com/fr/europe/rss",                           "source": "france24.com"},
    {"url": "https://www.euractiv.com/feed/",                                   "source": "euractiv.com"},
    # Google News en secours (URLs nécessitent VPN/Google)
    {"url": "https://news.google.com/rss/search?q=Gabriel+Attal&hl=fr&gl=FR&ceid=FR:fr",         "source": ""},
    {"url": "https://news.google.com/rss/search?q=Stéphane+Séjourné&hl=fr&gl=FR&ceid=FR:fr",     "source": ""},
    {"url": "https://news.google.com/rss/search?q=Attal+Séjourné&hl=fr&gl=FR&ceid=FR:fr",        "source": ""},
]

# 关键词 → 人物映射
_KW_PERSON = [
    (["attal", "gabriel attal"],                          "Gabriel Attal"),
    (["séjourné", "sejourne", "stéphane séjourné"],       "Stéphane Séjourné"),
]

def _detect_person(text: str):
    t = text.lower()
    has_a = "attal" in t
    has_s = "séjourné" in t or "sejourne" in t
    if has_a and has_s:
        return "S&A"
    if has_a:
        return "Gabriel Attal"
    if has_s:
        return "Stéphane Séjourné"
    return None


def fetch_all_news():
    results = []
    seen_urls = set()

    for feed_info in MEDIA_FEEDS:
        is_google = "news.google.com" in feed_info["url"]
        try:
            feed = feedparser.parse(feed_info["url"])
        except Exception:
            continue

        for entry in feed.entries:
            raw_url = entry.get("link", "").strip()
            if not raw_url or raw_url in seen_urls:
                continue
            if "google.com" in raw_url and not is_google:
                continue

            title   = entry.get("title", "").strip()
            summary = entry.get("summary", "")
            person  = _detect_person(title + " " + summary)
            if not person:
                continue

            seen_urls.add(raw_url)

            # Google News URL → 用 removepaywall.com 代理，绕过 GDPR consent
            # removepaywall.com 服务器在美国，可直接追踪 Google 跳转
            if is_google and "news.google.com" in raw_url:
                url = f"https://www.removepaywall.com/{raw_url}"
            else:
                url = raw_url

            url_hash = hashlib.md5(raw_url.encode()).hexdigest()  # ID 仍用原始 URL 去重
            try:
                pub_dt = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                pub_dt = datetime.now().isoformat()

            source = feed_info["source"]
            if not source:
                if " - " in title:
                    source = title.split(" - ")[-1].strip()
                elif hasattr(entry, "source"):
                    source = entry.source.get("title", "")

            results.append({
                "id":           url_hash,
                "title":        title.split(" - ")[0].strip() if is_google else title,
                "url":          url,
                "source":       source,
                "person":       person,
                "published_at": pub_dt,
                "summary":      summary[:500],
            })

    if results:
        upsert_news(results)
    return len(results)
