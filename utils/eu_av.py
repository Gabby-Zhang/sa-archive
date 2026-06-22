"""EU Audiovisual Service（欧盟影像库）抓取——行程日历页的补充来源。

Séjourné 的官方日历常漏掉一些会议，但欧盟影像服务（audiovisual.ec.europa.eu）
会上传这些会议的照片/视频。本模块直接查它的内部 Solr API、客户端按人名过滤，
把命中的影像条目当作「日历未必收录的会议线索」展示在行程日历左栏。

只读、不入库（和 SS 的 ICS 源一样实时解析）。上游监控脚本在
~/Documents/photo-monitor/sejourn_photo_monitor.py，API 细节见那边 CLAUDE.md。
"""

import re
from datetime import datetime
from html import unescape

import requests

# EU AV Portal 内部 Solr API（不支持关键词过滤，关键词匹配必须在客户端做）
AV_API_URL  = "https://gfdwwnbuul.execute-api.eu-west-1.amazonaws.com/avsportal/avsportal"
PHOTOS_BASE = "https://ec.europa.eu/avservices/avs/files/video6/repository/prod/photo/store"
PORTAL_PHOTO_BASE = "https://audiovisual.ec.europa.eu/en/media/photo"
PORTAL_VIDEO_BASE = "https://audiovisual.ec.europa.eu/en/media/video"

# 每类抓取条数（EU AV 每天上传大量各委员的媒体，SS 占比很小，取 100 兼顾覆盖）
FETCH_COUNT = 100
MEDIA_TYPES = ["REPORTAGE", "PHOTO", "VIDEO"]
SEARCH_TERMS = ["séjourn", "sejourn"]   # 大小写不敏感

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _clean_html(s) -> str:
    return re.sub(r"<[^>]+>", "", unescape(str(s))).strip()


def _mentions_sejourn(doc: dict) -> bool:
    texts = []
    for field in ("titles_json", "summary_json"):
        val = doc.get(field, {})
        if isinstance(val, dict):
            texts.extend(val.values())
        elif isinstance(val, str):
            texts.append(val)
    combined = unescape(" ".join(str(t) for t in texts)).lower()
    return any(term in combined for term in SEARCH_TERMS)


def _base_ref(ref: str) -> str:
    """'P-068123/00-01' → 'P-068123'（视频本身没有斜杠）"""
    return ref.split("/")[0]


def _portal_url(doc: dict) -> str:
    ref = _base_ref(doc.get("ref", ""))
    if doc.get("type") == "VIDEO":
        return f"{PORTAL_VIDEO_BASE}/{ref}"
    return f"{PORTAL_PHOTO_BASE}/{ref}"


def _thumbnail_url(doc: dict) -> str:
    media = doc.get("media_json", {})
    if doc.get("type") == "VIDEO":
        # media_json["16:9"][lang]["THUMB"] 是完整 URL
        aspect = media.get("16:9", {})
        for lang in ("INT", "MS", "EN"):
            thumb = aspect.get(lang, {}).get("THUMB", "")
            if thumb:
                return thumb.split("?")[0]
        return ""
    # PHOTO / REPORTAGE：相对 PATH 需拼前缀
    for res in ("THUMB", "LOW", "MED"):
        path = media.get(res, {}).get("PATH", "")
        if path:
            return PHOTOS_BASE + path
    return ""


def _parse_date(raw: str) -> str:
    """'20260527 19:30' → '2026-05-27'"""
    try:
        return datetime.strptime(str(raw)[:8], "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return str(raw)[:10]


def _get_title(doc: dict) -> str:
    titles = doc.get("titles_json", {})
    raw = (titles.get("EN") or titles.get("FR")
           or (next(iter(titles.values()), "") if titles else ""))
    return _clean_html(raw) or "(无标题)"


def _get_summary(doc: dict) -> str:
    s = doc.get("summary_json", {})
    raw = (s.get("EN") or s.get("FR")
           or (next(iter(s.values()), "") if isinstance(s, dict) else ""))
    return _clean_html(raw)


def fetch_sejourne_av(limit: int = 30) -> list:
    """抓欧盟影像库里提到 Séjourné 的影像条目，按拍摄日期倒序返回。

    返回 dict 列表：{ref, type, date, title, summary, url, thumbnail}。
    任一类型请求失败时跳过该类型（不让单点故障拖垮整页）。
    """
    docs = []
    for media_type in MEDIA_TYPES:
        try:
            resp = requests.get(
                AV_API_URL,
                params={
                    "fl": "type,ref,titles_json,shootstartdate,summary_json,media_json,languages",
                    "hasMedia": 1, "wt": "json", "index": 1,
                    "pagesize": FETCH_COUNT, "type": media_type,
                },
                headers=_HEADERS, timeout=20,
            )
            resp.raise_for_status()
            docs.extend(resp.json().get("response", {}).get("docs", []))
        except (requests.RequestException, ValueError):
            continue

    matched, seen_ref = [], set()
    for doc in docs:
        if not _mentions_sejourn(doc):
            continue
        ref = _base_ref(doc.get("ref", ""))
        if not ref or ref in seen_ref:
            continue
        seen_ref.add(ref)
        matched.append({
            "ref":       ref,
            "type":      doc.get("type", "REPORTAGE"),
            "date":      _parse_date(doc.get("shootstartdate", "")),
            "title":     _get_title(doc),
            "summary":   _get_summary(doc),
            "url":       _portal_url(doc),
            "thumbnail": _thumbnail_url(doc),
        })

    matched.sort(key=lambda x: x["date"], reverse=True)
    return matched[:limit]
