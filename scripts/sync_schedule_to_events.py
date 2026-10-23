"""把行程日历里「已发生」的行程同步进大事记(`events` 表),交汇时刻页随之更新。

由 .github/workflows/sync_schedule_to_events.yml 每天调用;首次手动带 SINCE=2026-07-01 补录。

数据源与行程日历页一致:
  - SS:sejourn-calendar 的公开 ICS + Supabase `schedule` 表(person=Stéphane Séjourné)
  - GA(及 S&A):Supabase `schedule` 表
跳过推测条目([AN_AUTO]/[EU_AUTO]/[EP_MAYBE]/[COUNCIL_AUTO])和未来行程。

标题只做轻量中文化(「Séjourné meets X」→「与X会晤」等),其余保留原文,管理员事后再改。

幂等:每条同步过的行程把指纹记进 profile_items(person=S&A / section=schedule_sync,
沿用首页置顶那种键值存储),所以**管理员改了标题、或删掉不要的条目,都不会被重新加回来**。
首次运行另按 同人同日 + 同链接/同标题 跳过大事记里已有的条目。

环境变量:SUPABASE_URL、SUPABASE_SERVICE_KEY;可选 SINCE(YYYY-MM-DD,默认今天往前 14 天)、
DRY_RUN=1(只打印不写库)。
"""
import hashlib
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta

import requests

ICS_URL = "https://raw.githubusercontent.com/Gabby-Zhang/sejourn-calendar/main/sejourn.ics"
PREDICTED_TAGS = ("[AN_AUTO]", "[EU_AUTO]", "[EP_MAYBE]", "[COUNCIL_AUTO]")
SS, GA = "Stéphane Séjourné", "Gabriel Attal"
SYNC_SECTION = "schedule_sync"
EVENT_TAG = "🗓️ 日常行程"
EVENT_SOURCE = "行程同步"

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
HDR = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")


# ── Supabase(PostgREST)────────────────────────────────────
def _get_all(table: str, params) -> list:
    """分页拉全量(PostgREST 单次上限 1000 行)。"""
    rows, offset = [], 0
    while True:
        r = requests.get(f"{URL}/rest/v1/{table}", headers={**HDR, "Range": f"{offset}-{offset + 999}"},
                         params=params, timeout=20)
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < 1000:
            return rows
        offset += 1000


def _insert(table: str, data: dict) -> dict:
    r = requests.post(f"{URL}/rest/v1/{table}",
                      headers={**HDR, "Content-Type": "application/json", "Prefer": "return=representation"},
                      json=data, timeout=20)
    r.raise_for_status()
    out = r.json()
    return out[0] if out else {}


# ── 读取行程 ─────────────────────────────────────────────
def _ics_unescape(s: str) -> str:
    return s.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").strip()


def load_ics() -> list:
    """解析 SS 的 ICS(折行续接),返回 {person,date,title,location,source_url,description}。"""
    text = requests.get(ICS_URL, timeout=20).text
    lines = []
    for raw in text.splitlines():
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur and cur.get("title") and cur.get("date"):
                events.append({"person": SS, "location": "", "source_url": "", "description": "", **cur})
            cur = None
        elif cur is None:
            continue
        elif line.startswith("SUMMARY:"):
            cur["title"] = _ics_unescape(line[8:])
        elif line.startswith("DTSTART"):
            v = line.split(":")[-1][:8]
            try:
                cur["date"] = date(int(v[:4]), int(v[4:6]), int(v[6:8])).isoformat()
            except ValueError:
                pass
        elif line.startswith("LOCATION:"):
            cur["location"] = _ics_unescape(line[9:])
        elif line.startswith("DESCRIPTION:") and "description" not in cur:
            cur["description"] = _ics_unescape(line[12:])
        elif line.startswith("URL:"):
            cur["source_url"] = line[4:].strip()
    return events


def load_schedule(since: str, until: str) -> list:
    rows = _get_all("schedule", [
        ("select", "person,event_date,title,location,source_url,description"),
        ("event_date", f"gte.{since}"), ("event_date", f"lte.{until}"),
    ])
    return [{"person": r.get("person") or "", "date": str(r.get("event_date") or "")[:10],
             "title": (r.get("title") or "").strip(), "location": r.get("location") or "",
             "source_url": r.get("source_url") or "", "description": r.get("description") or ""}
            for r in rows if r.get("title") and r.get("event_date")]


# ── 去重 / 指纹 ──────────────────────────────────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


_STOP = {"de", "la", "le", "les", "des", "du", "et", "a", "au", "en", "avec", "il", "s", "the", "of",
         "and", "in", "to", "mr", "ms", "sejourne", "stephane", "attal", "gabriel", "executive",
         "vice", "president", "commissaire", "europeen", "charge", "puis", "ensuite"}


def _words(s: str) -> set:
    return {w for w in _norm(s).split() if len(w) > 2 and w not in _STOP}


def _similar(a: str, b: str) -> bool:
    """同人同日的两条是否其实是同一件事(ICS 和 schedule 表常各有一份,Playbook 也常重复)。"""
    if _norm(a) == _norm(b):
        return True
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.6


# GA/S&A 的行程同一件事常有 Playbook + 官网文章 + IG 三份、措辞完全不同,
# 所以额外按「同一家媒体」或「同一个地名」判重(SS 不用:会晤条目常同含 Republic/Croatia 之类)
_MEDIA = {
    "rtl": "rtl", "lci": "lci", "france 2": "france2", "france 3": "france3", "france inter": "inter",
    "franceinfo": "franceinfo", "france info": "franceinfo", "bfm": "bfm", "rmc": "bfm", "tf1": "tf1",
    "cnews": "cnews", "europe 1": "europe1", "le parisien": "parisien", "le monde": "lemonde",
    "jdd": "jdd", "la tribune": "tribune", "figaro": "figaro", "politico": "politico",
    "telegramme": "telegramme", "sud radio": "sudradio", "public senat": "publicsenat",
}
_PLACE_STOP = _STOP | {
    "renaissance", "france", "francais", "francaise", "francaises", "presidentielle", "premier",
    "ministre", "interview", "europe", "assemblee", "nationale", "lettre", "ecole", "pacte",
    "jeunesse", "etats", "unis", "sont", "parmi", "edouard", "philippe", "marine", "tondelier",
    "meeting", "dossiers", "episode", "youtube", "bistrots", "candidat", "invite", "elysee",
    "elyseenne", "sommet", "suite", "president", "gauche", "droite", "republique", "etat",
    "deplacement", "cafe", "gare", "visite", "marche", "foire", "festival", "debat", "conference",
    "presse", "rencontre", "rencontres", "campagne", "equipe", "forum", "plateau", "emission",
}


def _media_keys(title: str) -> set:
    n = _norm(title)
    return {v for k, v in _MEDIA.items() if re.search(rf"\b{k}\b", n)}


def _place_keys(title: str) -> set:
    """标题里(除句首外)大写开头的专有名词,当地名用。"""
    caps = [m.group(1) for m in re.finditer(r"(?<![\w'’])([A-ZÀ-Ý][\w'’-]{3,})", title)
            if m.start() > 0]  # 句首大写词多是动词(Participe/Entame…),不算
    keys = set()
    for c in caps:
        for w in _norm(c).split():
            if len(w) > 3 and w not in _PLACE_STOP and not any(w in k.split() for k in _MEDIA):
                keys.add(w)
    return keys


def _same_event(a: dict, b: dict) -> bool:
    if a["person"] != b["person"] or a["date"] != b["date"]:
        return False
    if _similar(a["title"], b["title"]):
        return True
    if a["person"] == SS:
        return False
    return bool(_media_keys(a["title"]) & _media_keys(b["title"])
                or _place_keys(a["title"]) & _place_keys(b["title"]))


# Playbook 里抽出的「名单/预告」句,主语不是他本人,不算行程
_NOISE = re.compile(r"^(sont notamment|parmi les|le match|j-\d+|sont attendus)", re.I)


def fingerprint(e: dict) -> str:
    return hashlib.md5(f"{e['person']}|{e['date']}|{_norm(e['title'])}".encode()).hexdigest()


# ── 标题轻量中文化 ────────────────────────────────────────
_WHO = r"(?:European Commission\s+)?(?:Executive\s+)?(?:Vice-President\s+)?(?:Stéphane\s+)?S[ée]journ[ée]"


def to_zh_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title).strip()
    m = re.match(rf"^{_WHO}\s+(?:meets|receives)\s+(.+)$", t, re.I)
    if m:
        return f"与{m.group(1).strip()} 会晤"
    m = re.match(rf"^{_WHO}\s+visits\s+(.+)$", t, re.I)
    if m:
        return f"参观{m.group(1).strip()}"
    m = re.match(rf"^{_WHO}\s+participates in\s+(.+)$", t, re.I)
    if m:
        return f"参加{m.group(1).strip()}"
    if re.match(r"^(Opening |Press |Closing )?(remarks|speech|statement)\b", t, re.I):
        return f"发表讲话:{t}"
    return t


# ── 主流程 ───────────────────────────────────────────────
def main():
    if not URL or not KEY:
        sys.exit("缺少 SUPABASE_URL / SUPABASE_SERVICE_KEY,无法读写库。")
    today = date.today().isoformat()
    since = os.environ.get("SINCE", "").strip() or (date.today() - timedelta(days=14)).isoformat()
    datetime.strptime(since, "%Y-%m-%d")
    print(f"同步区间 {since} ~ {today}{'(DRY RUN)' if DRY_RUN else ''}")

    # schedule 表放前面:同一件事两边都有时,优先保留(通常更具体的)Playbook/手动条目
    cands = load_schedule(since, today) + [e for e in load_ics() if since <= e["date"] <= today]
    # 重复条目里优先留带链接的(大事记卡片能点开)
    cands.sort(key=lambda e: not e["source_url"])
    picked = []
    for e in cands:
        if any(tag in e["description"] for tag in PREDICTED_TAGS) or _NOISE.match(e["title"]):
            continue
        if any(_same_event(p, e) for p in picked):
            continue
        picked.append(e)
    picked.sort(key=lambda e: (e["date"], e["person"]))

    synced = {r["key"] for r in _get_all("profile_items", {
        "select": "key", "person": "eq.S&A", "section": f"eq.{SYNC_SECTION}"})}
    existing = _get_all("events", {"select": "date,person,title,source_url", "date": f"gte.{since}"})

    added = skipped = 0
    for e in picked:
        fp = fingerprint(e)
        zh = to_zh_title(e["title"])
        if fp in synced:
            skipped += 1
            continue
        if any(str(x.get("date"))[:10] == e["date"] and x.get("person") == e["person"]
               and ((e["source_url"] and x.get("source_url") == e["source_url"])
                    or (x.get("title") or "").strip() in (e["title"], zh))
               for x in existing):
            print(f"  = 大事记已有,跳过: {e['date']} {e['person']} — {e['title'][:70]}")
            skipped += 1
            continue
        print(f"  + {e['date']} {e['person']} — {zh[:90]}")
        added += 1
        if DRY_RUN:
            continue
        note = f"📍 {e['location']}" if e["location"] else ""
        ev = _insert("events", {"date": e["date"], "person": e["person"], "title": zh,
                                "source": EVENT_SOURCE, "source_url": e["source_url"],
                                "note": note, "tag": EVENT_TAG})
        _insert("profile_items", {"person": "S&A", "section": SYNC_SECTION, "key": fp,
                                  "value": str(ev.get("id", ""))})
        try:  # 审计日志失败不影响同步
            _insert("audit_log", {"admin_name": "行程同步(自动)", "admin_role": "", "action": "insert",
                                  "table_name": "events", "record_id": str(ev.get("id", "")),
                                  "detail": zh[:200]})
        except Exception:
            pass

    print(f"完成:新增 {added} 条,跳过 {skipped} 条(已同步过/大事记已有)")


if __name__ == "__main__":
    main()
