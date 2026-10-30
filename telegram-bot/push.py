#!/usr/bin/env python3
"""
Telegram 实时推送(telegram_push.yml 每 30 分钟跑一次):有新内容就推给管理员。

推什么:
  · 新闻:① 和 fetch_news 同一份源(utils/news_fetcher.collect_news,不爬 attalpresident.fr);
    ② news 表里 48 小时内的新行——主要是 ssga-news-monitor 早晚两班写进来的、Sonnet 筛过的 SS/S&A 文章
    (含 Google 快讯才搜得到的)。只看 48 小时内的,SS / GA / S&A 全推(2026-10-29 用户要求 GA 也全推)
  · 新行程:schedule 表里新出现的、今天及以后的 SS/GA/S&A 行程
    (跳过 [AN_AUTO] 推测条目和 [TELEGRAM] 管理员自己发的)
  · 新照片:photo-monitor 仓库(Getty / Alamy / Imago / Flickr / 欧盟影像库 / 欧洲议会 / Reuters /
    Shutterstock,SS 和 GA)每发现一张新图就写进 Supabase `photo_alerts` 表,这里读新行,单独发一条
    消息并打开第一张的链接预览(表里没存图片地址,靠图库页面的预览图)。photo-monitor 自己的 ntfy 照旧

标题用 Google 翻译免费接口译成中文(不需要 key、不占 Claude 额度),中文在上、原文链接在下;
翻译失败就只显示原文,不影响推送。

去重:推过的条目在 profile_items(person=S&A, section=tg_push_seen)记 key;新闻同时记 id 和标题两个 key,
同一篇文章从两条路进来(链接不同,一个是 Google 跳转链、一个是真实链接)也只推一次。
第一次运行(一行都没有)只把现有条目全部标记为已推、发一条「已启动」,不刷屏;
之后新加的来源同理:seen 里还没有这个来源前缀(如 p:)时,它的现有条目静默记为已推。
"""
import hashlib
import html
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests  # noqa: E402
import sb  # noqa: E402
import tg  # noqa: E402
from utils.news_fetcher import collect_news  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
SEEN_SECTION = "tg_push_seen"
MAX_PER_GROUP = 12

GROUPS = [  # (分组键, 标题)
    ("S&A", "💞 S&A"),
    ("Stéphane Séjourné", "🔵 Séjourné"),
    ("Gabriel Attal", "🟡 Attal"),
    ("schedule", "🗓️ 新行程"),
]
PHOTO_GROUP = "photos"
SILENT_FIRST_RUN = ("p:",)  # 新加的来源:第一次见到时现有条目静默记为已推
SHORT = {"Stéphane Séjourné": "SS", "Gabriel Attal": "GA", "S&A": "S&A"}


def _e(s):
    return html.escape(str(s or ""), quote=False)


def _link(title, url):
    return f'<a href="{html.escape(url)}">{_e(title)}</a>' if url else _e(title)


def _title_key(title):
    t = re.sub(r"[^0-9a-zà-ÿ]+", " ", (title or "").lower()).strip()
    return "t:" + hashlib.md5(t[:120].encode()).hexdigest()


def _item(title, url, source="", prefix="", suffix=""):
    """一条待推送的内容;prefix 如「10/30 GA · 」,suffix 如「 📰」。"""
    return {"title": title or "", "url": url or "", "source": source or "", "prefix": prefix, "suffix": suffix}


def _render(it, zh):
    src = f" — {_e(it['source'])}" if it["source"] else ""
    orig = f"{_link(it['title'], it['url'])}{it['suffix']}{src}"
    if zh and zh.strip().lower() != it["title"].strip().lower():
        return f"• {_e(it['prefix'])}{_e(zh)}\n   {orig}"
    return f"• {_e(it['prefix'])}{orig}"


_CJK = re.compile(r"[\u4e00-\u9fff]")


def _translate(text):
    """Google 翻译免费接口(translate.googleapis.com, client=gtx),失败返回 ""。"""
    if not text or _CJK.search(text):
        return ""
    try:
        r = requests.get("https://translate.googleapis.com/translate_a/single", timeout=10, params={
            "client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": text[:500]})
        r.raise_for_status()
        return "".join(seg[0] for seg in r.json()[0] if seg and seg[0]).strip()
    except Exception as e:
        print(f"  翻译失败({e}):{text[:50]}")
        return ""


def news_candidates():
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=48)
    out = []
    for it in collect_news(include_official=False):
        try:
            if datetime.fromisoformat(it["published_at"][:19]) < cutoff:
                continue
        except ValueError:
            continue
        out.append(([f"n:{it['id']}", _title_key(it["title"])], it["person"],
                    _item(it["title"], it["url"], it.get("source"))))
    return out


def news_table_candidates():
    since = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
    rows = sb.get_all("news", [("select", "id,title,url,source,person,category"),
                               ("published_at", f"gte.{since}")])
    return [([f"n:{r['id']}", _title_key(r.get("title"))], r.get("person"),
             _item(r.get("title"), r.get("url"), r.get("source")))
            for r in rows if r.get("category") != "historical" and r.get("person") in SHORT]


def schedule_candidates():
    today = datetime.now(PARIS).date().isoformat()
    rows = sb.get_all("schedule", [("select", "id,person,event_date,title,description,source_url"),
                                   ("event_date", f"gte.{today}")])
    out = []
    for r in rows:
        desc = r.get("description") or ""
        if "[AN_AUTO]" in desc or "[TELEGRAM]" in desc:
            continue
        d = str(r.get("event_date"))[:10]
        label = f"{d[5:7]}/{d[8:10]} {SHORT.get(r.get('person'), r.get('person'))}"
        tag = " 📰" if "[NEWS_AUTO]" in desc else ""
        out.append(([f"s:{r['id']}"], "schedule",
                    _item(r.get("title"), r.get("source_url"), prefix=f"{label} · ", suffix=tag)))
    return out


def photo_candidates():
    rows = sb.get_all("photo_alerts", {"select": "id,person,source,title,url"})
    return [([f"p:{r['id']}"], PHOTO_GROUP,
             _item(r.get("title") or "(无标题)", r.get("url"),
                   source=r.get("source"), prefix=f"{SHORT.get(r.get('person'), r.get('person'))} · "))
            for r in rows if r.get("id")]


def main():
    seen = {r["key"] for r in sb.get_all("profile_items", {
        "select": "key", "person": "eq.S&A", "section": f"eq.{SEEN_SECTION}"})}
    cands, failed = [], []
    sources = (("新闻", news_candidates), ("news 表", news_table_candidates),
               ("行程", schedule_candidates), ("新照片", photo_candidates))
    for name, fn in sources:
        try:
            got = fn()
            print(f"{name}: {len(got)} 条候选")
            cands += got
        except Exception as e:  # 单个源挂了不影响其它源
            print(f"⚠️ {name} 抓取失败: {e}")
            failed.append(name)

    fresh, keys = [], set()
    silent = {p for p in SILENT_FIRST_RUN if seen and not any(k.startswith(p) for k in seen)}
    for ks, group, item in cands:
        if any(k.startswith(p) for k in ks for p in silent):
            keys.update(ks)  # 新来源第一次运行:只记为已推,不发
            continue
        if any(k in seen or k in keys for k in ks):
            keys.update(ks)  # 同一篇的另一个 key 也记上,下次另一条路进来就认得
            continue
        keys.update(ks)
        fresh.append((ks, group, item))
    print(f"新条目 {len(fresh)} 条(已推过 {len(seen)} 条)")

    if not seen:
        tg.send(f"✅ 实时推送已启动。现有 {len(fresh)} 条内容记为已读,之后有新的会推给你。")
    elif fresh:
        now = datetime.now(PARIS).strftime("%m/%d %H:%M")
        shown = {gkey: [it for _, g, it in fresh if g == gkey] for gkey, _ in GROUPS}
        todo = [it for items in shown.values() for it in items[:MAX_PER_GROUP]]
        with ThreadPoolExecutor(max_workers=5) as pool:
            zh = dict(zip(map(id, todo), pool.map(lambda it: _translate(it["title"]), todo)))
        parts = [f"🔔 <b>新动态</b> · {now}"]
        for gkey, gtitle in GROUPS:
            items = shown[gkey]
            if not items:
                continue
            lines = [_render(it, zh.get(id(it))) for it in items[:MAX_PER_GROUP]]
            more = f"\n…等共 {len(items)} 条" if len(items) > MAX_PER_GROUP else ""
            parts.append(f"<b>{gtitle}</b>\n" + "\n".join(lines) + more)
        if len(parts) > 1:
            tg.send("\n\n".join(parts), html=True)

        photos = [it for _, g, it in fresh if g == PHOTO_GROUP]
        if photos:
            with ThreadPoolExecutor(max_workers=5) as pool:
                pz = list(pool.map(lambda it: _translate(it["title"]), photos[:MAX_PER_GROUP]))
            lines = [_render(it, z) for it, z in zip(photos, pz)]
            more = f"\n…等共 {len(photos)} 张" if len(photos) > MAX_PER_GROUP else ""
            tg.send(f"📸 <b>新照片</b> · {now}\n" + "\n".join(lines) + more,
                    html=True, preview_url=photos[0]["url"] or None)

    # 推送成功后才记为已推(推送失败下次会重推,不会漏);首次运行另记一个 init 标记
    marks = sorted(keys - seen) + ([] if seen else ["init"])
    sb.insert("profile_items", [{"person": "S&A", "section": SEEN_SECTION, "key": k, "value": ""}
                                for k in marks])
    if len(failed) == len(sources):
        sys.exit("所有来源都抓取失败")


if __name__ == "__main__":
    main()
