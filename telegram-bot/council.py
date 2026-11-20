#!/usr/bin/env python3
"""
欧盟理事会 Newsroom(newsroom.consilium.europa.eu)的照片/视频监控,给 push.py 用。

为什么要单独查这里:理事会主办的活动(欧盟-第三国峰会、竞争力理事会、欧洲理事会……)
照片视频只发在理事会 Newsroom,欧委会影像库(EC AV)和 photo-monitor 都看不到。
2026-11-20 EU-UK 峰会就是这样:老塞全程在场,EC AV 一张没有,理事会有 74 张照片 + 16 段视频。

难点:理事会的图说经常只写「Plenary session」,不写人名(那次 25 张里只有 1 张写了他,还标错了头衔)。
所以按两档推,每个活动一条:
  ✅ 有他 —— 照片图说 / 标签 / 相册名 或 视频标题 / 简介 / 标签 里出现 Séjourné / Attal
  ❓ 可能有他 —— 名字没出现,但活动类型是他常去的(峰会、竞争力理事会、欧洲理事会……),
                或者他的 ICS 日历当天有个关键词对得上的条目;推活动链接,自己去翻
接口:newsroomapi.consilium.europa.eu/api/events(列表)、/api/events/<urlName>(照片+视频列表)、
/api/videos/<urlName>(视频简介、标签)。全部公开、免 key。
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

API = "https://newsroomapi.consilium.europa.eu/api"
SITE = "https://newsroom.consilium.europa.eu"
ICS_URL = "https://raw.githubusercontent.com/Gabby-Zhang/sejourn-calendar/main/sejourn.ics"
LOOKBACK_DAYS = 4

NAMES = {"Stéphane Séjourné": re.compile(r"s[ée]journ[ée]", re.I),
         "Gabriel Attal": re.compile(r"\battal\b", re.I)}
# 他(欧委会执行副主席,产业战略)常出席、但图说未必写他的理事会活动
LIKELY_EVENT = re.compile(
    r"summit|sommet|competitiveness|european council|euro summit|tripartite|industr|single market"
    r"|internal market|space|steel|automotive", re.I)
_STOP = {"the", "of", "and", "for", "with", "in", "on", "at", "to", "a", "an", "de", "la", "le", "des", "du",
         "et", "meeting", "council", "european", "commission", "eu", "november", "december", "january",
         "february", "march", "april", "may", "june", "july", "august", "september", "october", "2026",
         "2027", "president", "minister", "ministers", "prime", "meets", "vice", "executive", "participation",
         "presentation", "stéphane", "séjourné", "sejourne", "brussels", "bruxelles", "state", "states", "member",
         "high", "level", "conference", "forum", "session", "date", "per", "agenda", "informal", "visit", "weekly", "college"}


def _get(path, **params):
    r = requests.get(f"{API}/{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _words(s):
    return {w for w in re.findall(r"[a-zà-ÿ]{3,}", (s or "").lower()) if w not in _STOP}


def _ics_by_date():
    """SS 的 ICS:{日期: 当天所有条目标题的关键词}。失败返回 {}(只是少一个「可能」信号)。"""
    try:
        text = requests.get(ICS_URL, timeout=20).text
    except Exception as e:
        print(f"  理事会:读 ICS 失败({e})")
        return {}
    text = re.sub(r"\r?\n[ \t]", "", text)
    out = {}
    for ev in text.split("BEGIN:VEVENT")[1:]:
        d = re.search(r"DTSTART[^:]*:(\d{4})(\d{2})(\d{2})", ev)
        s = re.search(r"SUMMARY:(.*)", ev)
        if d and s:
            out.setdefault("-".join(d.groups()), set()).update(_words(s.group(1).replace("\\,", ",")))
    return out


def _video_detail(v):
    try:
        return _get(f"videos/{v['urlName']}")
    except Exception:
        return v


def _who(text):
    return [p for p, rx in NAMES.items() if rx.search(text or "")]


def scan():
    """返回最近几天理事会活动里和两人有关的条目:
    [{key, person, status('yes'|'maybe'), title, url, detail, preview}]"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=LOOKBACK_DAYS)
    events = _get("events", pagesize=40, page=1, orderBy="date", orderDirection="descending")["data"]
    ics = _ics_by_date()
    out = []
    for ev in events:
        try:
            start = datetime.fromisoformat(ev["startDate"][:19])
        except (KeyError, ValueError):
            continue
        if not (since <= start <= now) or not (ev.get("photosCount") or ev.get("videosCount")):
            continue
        detail = _get(f"events/{ev['urlName']}")
        photos = detail.get("photos") or []
        videos = [v for v in detail.get("videos") or [] if v.get("date", "")[:10] >= since.date().isoformat()]

        hit_photos, people = [], set()
        for ph in photos:
            txt = " ".join([ph.get("caption") or "", ph.get("galleryDescription") or "", *(ph.get("tags") or [])])
            who = _who(txt)
            if who:
                hit_photos.append(ph)
                people.update(who)
        hit_videos = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            vds = list(pool.map(_video_detail, videos))
        for v, vd in zip(videos, vds):
            who = _who(" ".join([vd.get("title") or "", vd.get("description") or "", *map(str, vd.get("tags") or [])]))
            if who:
                hit_videos.append(v)
                people.update(who)

        day = start.date().isoformat()
        url = f"{SITE}/events/{ev['urlName']}"
        counts = f"照片 {len(photos)} · 视频 {len(videos)}"
        if people:
            bits = []
            if hit_photos:
                bits.append(f"{len(hit_photos)} 张图说写了名字")
            if hit_videos:
                bits.append("视频:" + "、".join(v.get("title", "") for v in hit_videos[:3]))
            person = "S&A" if len(people) > 1 else people.pop()
            out.append({"key": f"c:{ev['urlName']}:y{len(hit_photos)}v{len(hit_videos)}", "person": person,
                        "status": "yes", "title": ev["title"], "url": url,
                        "detail": f"✅ {';'.join(bits)}({counts})",
                        "preview": hit_photos[0]["urlName"] if hit_photos else None})
            continue

        overlap = _words(ev["title"]) & ics.get(day, set())
        if LIKELY_EVENT.search(ev["title"]) or overlap:
            why = f"日历当天有「{'/'.join(sorted(overlap))}」" if overlap else "他常出席的活动类型"
            out.append({"key": f"c:{ev['urlName']}:m{'p' if photos else 'v'}", "person": "Stéphane Séjourné",
                        "status": "maybe", "title": ev["title"], "url": url,
                        "detail": f"❓ 图说没写名字,{why}({counts})", "preview": None})
    return out


if __name__ == "__main__":  # 本地试跑:python telegram-bot/council.py
    for it in scan():
        print(it["status"], it["person"], it["title"], "|", it["detail"], "|", it["url"])
