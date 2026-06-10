"""
新闻抓取共享模块 — 同时供两个入口使用：
  1. Streamlit 页面「抓取最新新闻」按钮 → fetch_all_news()
  2. GitHub Actions 定时任务 scripts/fetch_news.py → collect_news()

本模块不在顶层 import streamlit，保证 Actions 环境（无 streamlit）可直接使用。
"""
import re
import json
import feedparser
import hashlib
import base64
import requests
from datetime import datetime

_UA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
}


def _decode_gnews_url(gnews_url: str, timeout: int = 6) -> str:
    """
    将 Google News RSS 文章链接解析为真实文章 URL。
    先尝试 Base64 解码（快，不需网络），失败则跟随 HTTP 跳转。
    两者均失败时原样返回。
    """
    # ── 1. Base64 尝试（新格式多为 protobuf，可能失败）──────
    try:
        for marker in ["/rss/articles/", "/articles/"]:
            if marker in gnews_url:
                article_id = gnews_url.split(marker)[1].split("?")[0].split("#")[0]
                padded = article_id + "=" * (-len(article_id) % 4)
                data = base64.urlsafe_b64decode(padded)
                for prefix in [b"https://", b"http://"]:
                    idx = data.find(prefix)
                    if idx != -1:
                        end = idx
                        while end < len(data) and 0x20 <= data[end] <= 0x7E:
                            end += 1
                        candidate = data[idx:end].decode("ascii", errors="ignore")
                        if "." in candidate and len(candidate) > 15 and "google.com" not in candidate:
                            return candidate
                break
    except Exception:
        pass

    # ── 2. HTTP 跳转（Streamlit Cloud 在美国可访问 Google）──
    try:
        resp = requests.get(
            gnews_url, allow_redirects=True, timeout=timeout, headers=_UA_HEADERS,
        )
        final = resp.url
        if "google.com" not in final and "." in final and len(final) > 15:
            return final
    except Exception:
        pass

    return gnews_url


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
    {"url": "https://news.google.com/rss/search?q=Gabriel+Attal&hl=fr&gl=FR&ceid=FR:fr",                              "source": ""},
    {"url": "https://news.google.com/rss/search?q=Stéphane+Séjourné&hl=fr&gl=FR&ceid=FR:fr",                          "source": ""},
    {"url": "https://news.google.com/rss/search?q=Attal+Séjourné&hl=fr&gl=FR&ceid=FR:fr",                             "source": ""},
    # Le Canard Enchaîné（无 RSS，通过 Google News 间接捕捉）
    {"url": "https://news.google.com/rss/search?q=Canard+Enchaîné+Attal&hl=fr&gl=FR&ceid=FR:fr",                      "source": "lecanardenchaine.fr"},
    {"url": "https://news.google.com/rss/search?q=Canard+Enchaîné+Séjourné&hl=fr&gl=FR&ceid=FR:fr",                   "source": "lecanardenchaine.fr"},
    # LCP – La Chaîne Parlementaire（议会电视台，直接 RSS，含 AN 直播报道与时政新闻）
    {"url": "https://lcp.fr/rss.xml",                                                                                  "source": "lcp.fr"},
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


def fetch_attal_officiel() -> list:
    """
    抓取 attalpresident.fr 官方竞选网站：
    通过 sitemap.xml 找出所有 /actualites/* 文章，
    解析 JSON-LD 提取标题、日期、描述。
    """
    BASE = "https://attalpresident.fr"
    items = []

    try:
        sitemap = requests.get(f"{BASE}/sitemap.xml", headers=_UA_HEADERS, timeout=15).text
        urls = re.findall(r"<loc>(https://attalpresident\.fr/actualites/[^<]+)</loc>", sitemap)
    except Exception as e:
        print(f"⚠️ attalpresident.fr sitemap 失败: {e}")
        return []

    for url in urls:
        try:
            r = requests.get(url, headers=_UA_HEADERS, timeout=15)
            json_lds = re.findall(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', r.text, re.DOTALL
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

            date_raw = article.get("datePublished", "")
            try:
                pub_dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00")).isoformat()
            except Exception:
                pub_dt = datetime.now().isoformat()

            items.append({
                "id":           hashlib.md5(url.encode()).hexdigest(),
                "title":        article.get("headline", "").strip(),
                "url":          url,
                "source":       "attalpresident.fr",
                "person":       "Gabriel Attal",
                "published_at": pub_dt,
                "summary":      article.get("description", "").strip()[:500],
            })
        except Exception as e:
            print(f"  ⚠️ 解析失败 {url}: {e}")

    print(f"  attalpresident.fr: {len(items)} 篇文章")
    return items


def collect_news() -> list:
    """
    抓取全部新闻源（媒体 RSS + Google News + attalpresident.fr），
    返回去重后的条目列表，不写数据库 — 由调用方负责入库。
    """
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

            # Google News 链接解码为真实文章 URL；解码失败则保留原链接
            url = _decode_gnews_url(raw_url) if is_google else raw_url

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

    results.extend(fetch_attal_officiel())
    return results


def fetch_all_news():
    """Streamlit 页面入口：抓取并写入数据库，返回条数。"""
    from utils.database import upsert_news  # 延迟 import，避免 Actions 环境引入 streamlit
    results = collect_news()
    if results:
        upsert_news(results)
    return len(results)
