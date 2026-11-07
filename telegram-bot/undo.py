#!/usr/bin/env python3
"""
Telegram 机器人的「撤回」:删掉某条消息写进档案馆的所有条目。

用法(在 Telegram 里):
  回复(左滑)你发的那条消息,或机器人回的「✅ …」结果,发「撤回」 → 撤回那条消息存进去的所有东西
  直接发「撤回」(不回复任何消息)                                  → 撤回最近一条
  「撤回 行程」/「撤回 新闻」/「撤回 大事记」/「撤回 图库」          → 只撤回那一类
  命令词:撤回 / 撤销 / /undo

原理:每次入库时,screenshot_to_db.py / save.py / photo_to_gallery.py 把新写入的行记进
$TG_LEDGER;run_ci.sh 结束时 `undo.py record` 把这份清单存进 profile_items
(person=S&A, section=tg_ledger, key=<chat_id>:<消息 id>,机器人结果回复的 id 也记一行指过去)。
撤回时按清单逐条删除,并顺带删掉:行程已被 sync_schedule_to_events 同步进大事记的那条、
截图图片(整条消息全撤回时)。每次删除都记 audit_log(admin_name「Telegram 撤回」)。

本功能上线前发的消息没有清单:截图类消息的图片名里带消息 id,按它在 行程/大事记/新闻 里找回;
纯文字的旧消息找不到,只能去网站手动删(行程可用 Actions → "Delete schedule entry (manual)")。

  python3 telegram-bot/undo.py detect          # 打印 undo=true/false(给 $GITHUB_OUTPUT)
  python3 telegram-bot/undo.py record <outdir> # 入库结束后保存清单
  python3 telegram-bot/undo.py run             # 执行撤回,打印回复正文
"""
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sb  # noqa: E402

SECTION = "tg_ledger"
COMMANDS = {"撤回", "撤销", "/undo", "undo"}
KINDS = {"行程": "schedule", "新闻": "news", "大事记": "events", "图库": "images", "照片": "images"}
TABLE_ZH = {"schedule": "行程", "news": "新闻", "events": "大事记", "images": "图库"}
WHO = "Telegram 撤回"
PARIS = ZoneInfo("Europe/Paris")
_IMG_RE = re.compile(r"/storage/v1/object/public/gallery/(schedule/[^\s|]+)")


def _event_msg():
    event = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    return event["client_payload"]["message"]


def parse_command(text):
    """「撤回 行程」→ (True, "schedule");不是撤回命令 → (False, None)。"""
    parts = (text or "").strip().split()
    if not parts:
        return False, None
    cmd = parts[0].split("@")[0].lower()  # /undo@xxx_bot
    if cmd not in COMMANDS or len(parts) > 2:
        return False, None
    if len(parts) == 2:
        if parts[1] not in KINDS:
            return False, None
        return True, KINDS[parts[1]]
    return True, None


# ── 记录 ──────────────────────────────────────────────────────
def record(outdir):
    out = pathlib.Path(outdir)
    ledger = out / "ledger.jsonl"
    items = []
    if ledger.exists():
        seen = set()
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            if (it["table"], it["id"]) not in seen:  # 重试可能记两遍
                seen.add((it["table"], it["id"]))
                items.append(it)
    if not items:
        print("本次没有新写入的条目,不记撤回清单")
        return
    msg = _event_msg()
    chat, mid = msg["chat"]["id"], msg["message_id"]
    key = f"{chat}:{mid}"
    value = {"ts": msg["date"], "items": items}
    sb.insert("profile_items", {"person": "S&A", "section": SECTION, "key": key,
                                "value": json.dumps(value, ensure_ascii=False)})
    rid = out / "reply_id.txt"
    if rid.exists() and rid.read_text().strip():
        sb.insert("profile_items", {"person": "S&A", "section": SECTION,
                                    "key": f"{chat}:{rid.read_text().strip()}",
                                    "value": json.dumps({"alias": key})})
    print(f"已记撤回清单 {key}:{len(items)} 条")


def _ledger_rows(key):
    return sb.get_all("profile_items", {"select": "id,key,value", "person": "eq.S&A",
                                        "section": f"eq.{SECTION}", "key": f"eq.{key}"})


def _find_ledger(chat, target):
    """返回 (原消息 key, 清单 dict);找不到返回 (None, None)。target=None 取最近一条。"""
    if target is None:
        rows = sb.get_all("profile_items", {"select": "key,value", "person": "eq.S&A",
                                            "section": f"eq.{SECTION}", "key": f"like.{chat}:*"})
        best = None
        for r in rows:
            v = json.loads(r["value"] or "{}")
            if v.get("items") and (best is None or v["ts"] > best[1]["ts"]):
                best = (r["key"], v)
        return best or (None, None)
    rows = _ledger_rows(f"{chat}:{target}")
    if not rows:
        return None, None
    v = json.loads(rows[0]["value"] or "{}")
    if "alias" in v:
        rows = _ledger_rows(v["alias"])
        return (v["alias"], json.loads(rows[0]["value"])) if rows else (None, None)
    return f"{chat}:{target}", v


def _legacy_items(chat, target):
    """上线前的截图消息:图片名形如 schedule/<日期>_<chat>_<消息id>.jpg,按它找回写入的条目。"""
    stem = f"_{chat}_{target}."
    pat = f"*{stem}*"
    items = []
    for r in sb.get_all("schedule", {"select": "id,person,event_date,title,description",
                                     "description": f"ilike.{pat}"}):
        if stem in (r.get("description") or ""):
            items.append({"table": "schedule", "id": str(r["id"]),
                          "label": f"行程 {r['event_date']} · {r['person']} · {r['title'][:60]}"})
    for r in sb.get_all("events", {"select": "id,person,date,title,image_url,source_url,source",
                                   "or": f"(image_url.ilike.{pat},source_url.ilike.{pat})"}):
        if r.get("source") == "行程同步":
            continue  # 跟着对应行程一起删(见 _undo_one)
        if stem in (r.get("image_url") or "") + (r.get("source_url") or ""):
            items.append({"table": "events", "id": str(r["id"]),
                          "label": f"大事记 {r['date']} · {r['person']} · {r['title'][:60]}"})
    for r in sb.get_all("news", {"select": "id,person,title,url", "url": f"ilike.{pat}"}):
        if stem in (r.get("url") or ""):
            items.append({"table": "news", "id": str(r["id"]),
                          "label": f"新闻 · {r['person']} · {r['title'][:60]}"})
    return items


# ── 删除 ──────────────────────────────────────────────────────
def _synced_event_ids(row):
    """行程已被 sync_schedule_to_events 同步进大事记的话,找出那条大事记的 id。"""
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
        from sync_schedule_to_events import fingerprint
    except Exception:
        return []
    fp = fingerprint({"person": row["person"], "date": row["event_date"], "title": row["title"]})
    rows = sb.get_all("profile_items", {"select": "value", "person": "eq.S&A",
                                        "section": "eq.schedule_sync", "key": f"eq.{fp}"})
    return [r["value"] for r in rows if r.get("value")]


def _undo_one(it, images):
    """删一条,返回回复里的一行;images 收集截图路径,最后决定删不删。"""
    table, rid = it["table"], it["id"]
    extra = ""
    if table == "schedule":
        rows = sb.get_all("schedule", {"select": "*", "id": f"eq.{rid}"})
        if rows:
            m = _IMG_RE.search(rows[0].get("description") or "")
            if m:
                images.add(m.group(1))
            for ev_id in _synced_event_ids(rows[0]):
                gone = sb.delete("events", {"id": f"eq.{ev_id}", "source": "eq.行程同步"})
                if gone:
                    sb.audit("delete", "events", ev_id, f"随行程撤回 {gone[0].get('title', '')}", who=WHO)
                    extra = "(连同已同步进大事记的那条)"
    if table == "events":
        rows = sb.get_all("events", {"select": "image_url", "id": f"eq.{rid}"})
        m = _IMG_RE.search(rows[0].get("image_url") or "") if rows else None
        if m:
            images.add(m.group(1))
    gone = sb.delete(table, {"id": f"eq.{rid}"})
    if not gone:
        return f"↩️ 已经不在了(可能已手动删):{it['label']}"
    sb.audit("delete", table, rid, f"撤回 {it['label']}", who=WHO)
    if table == "images" and it.get("storage"):
        sb.delete_storage("gallery", it["storage"])
    return f"🗑️ 已撤回 {it['label']}{extra}"


def run():
    msg = _event_msg()
    _, kind = parse_command(msg.get("text") or "")
    chat = msg["chat"]["id"]
    target_msg = msg.get("reply_to_message")
    target = target_msg["message_id"] if target_msg else None

    key, ledger = _find_ledger(chat, target)
    legacy = False
    if ledger is None and target is not None:
        items = _legacy_items(chat, target)
        if items:
            legacy, ledger = True, {"ts": target_msg.get("date", 0), "items": items}
    if ledger is None:
        if target is None:
            print("没有可撤回的记录。")
        elif time.time() - target_msg.get("date", 0) < 600:
            print("这条还没有入库记录——可能还在解析中。等机器人回了「✅ …」结果后,再回复那条消息「撤回」。")
        else:
            print("这条消息没有对应的入库记录。\n"
                  "请回复你自己发的那条原消息,或机器人回的「✅ …」结果(不是「📥 收到」那条)。\n"
                  "撤回功能上线前发的纯文字消息找不到记录,只能去网站手动删"
                  "(行程:Actions → Delete schedule entry (manual))。")
        return

    todo = [it for it in ledger["items"] if kind is None or it["table"] == kind]
    keep = [it for it in ledger["items"] if it not in todo]
    if not todo:
        print(f"那条消息没有存进「{TABLE_ZH[kind]}」的条目。现有:"
              + "、".join(sorted({TABLE_ZH[i['table']] for i in ledger['items']})))
        return

    images = set()
    lines = [_undo_one(it, images) for it in todo]
    if not keep:  # 整条消息全撤回了,截图也删掉;只撤一部分时留着(别的条目可能还在用)
        for path in images:
            sb.delete_storage("gallery", path)

    if not legacy:
        drop = [key]
        if not keep and target is not None and f"{chat}:{target}" != key:
            drop.append(f"{chat}:{target}")  # 结果回复那行别名;只撤一部分时留着,还能再回复它撤剩下的
        for k in drop:
            sb.delete("profile_items", {"person": "eq.S&A", "section": f"eq.{SECTION}", "key": f"eq.{k}"})
        if keep:
            sb.insert("profile_items", {"person": "S&A", "section": SECTION, "key": key,
                                        "value": json.dumps({**ledger, "items": keep}, ensure_ascii=False)})

    when = datetime.fromtimestamp(ledger["ts"], timezone.utc).astimezone(PARIS).strftime("%m/%d %H:%M")
    head = f"撤回 {when} 发的那条消息:" if target is None else "撤回完成:"
    print("\n".join([head] + lines + ([f"(还保留:{'、'.join(i['label'] for i in keep)})"] if keep else [])))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "detect":
        print(f"undo={'true' if parse_command(_event_msg().get('text') or '')[0] else 'false'}")
    elif cmd == "record" and len(sys.argv) == 3:
        record(sys.argv[2])
    elif cmd == "run":
        run()
    else:
        sys.exit(__doc__)
