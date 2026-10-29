#!/usr/bin/env python3
"""
Telegram 机器人入库的两个小工具(workflow telegram_ingest.yml 调用),只用标准库。

  python3 telegram-bot/tg.py fetch <outdir>
      读 $GITHUB_EVENT_PATH 里 Worker 转来的 Telegram message,
      下载图片到 <outdir>/image.<ext>,写 <outdir>/message.json 给 claude 读。
  python3 telegram-bot/tg.py reply <outdir> < 正文
      把正文回复到原消息下面(chat_id / message_id 从 message.json 取)。
  python3 telegram-bot/tg.py send < 正文
      主动推送给管理员(报错推送、实时推送、每日汇总用;其他脚本 import tg 调 send())。

环境变量:TELEGRAM_BOT_TOKEN;send 另需 TELEGRAM_CHAT_ID(逗号分隔可多人)
"""
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API = "https://api.telegram.org"
PARIS = ZoneInfo("Europe/Paris")


def _token():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        sys.exit("缺 TELEGRAM_BOT_TOKEN")
    return tok


def _api(method, payload):
    req = urllib.request.Request(
        f"{API}/bot{_token()}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} 失败: {data}")
    return data["result"]


def _paris(ts):
    return datetime.fromtimestamp(ts, timezone.utc).astimezone(PARIS).isoformat(timespec="minutes")


def _upload(image_path, stem):
    """截图传到 Supabase Storage 的公开 gallery bucket,返回公开 URL;失败返回 "" 不中断入库。"""
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if not base or not key:
        print("⚠️ 缺 Supabase 凭据,截图不上传", file=sys.stderr)
        return ""
    ext = pathlib.Path(image_path).suffix.lower() or ".jpg"
    obj = f"{stem}{ext}"
    ctype = {".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    req = urllib.request.Request(
        f"{base}/storage/v1/object/gallery/{obj}",
        data=pathlib.Path(image_path).read_bytes(),
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": ctype, "x-upsert": "true"},
    )
    try:
        urllib.request.urlopen(req, timeout=60).close()
    except Exception as e:
        print(f"⚠️ 截图上传失败(行程照常入库,只是没图): {e}", file=sys.stderr)
        return ""
    return f"{base}/storage/v1/object/public/gallery/{obj}"


def fetch(outdir):
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    event = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    msg = event["client_payload"]["message"]

    # 照片取最大尺寸那张;以「文件」形式发的图片走 document
    file_id = None
    if msg.get("photo"):
        file_id = msg["photo"][-1]["file_id"]
    elif (msg.get("document") or {}).get("mime_type", "").startswith("image/"):
        file_id = msg["document"]["file_id"]

    image_path = ""
    if file_id:
        fpath = _api("getFile", {"file_id": file_id})["file_path"]
        ext = pathlib.Path(fpath).suffix or ".jpg"
        image_path = str(out / f"image{ext}")
        url = f"{API}/file/bot{_token()}/{urllib.parse.quote(fpath)}"
        urllib.request.urlretrieve(url, image_path)

    image_url = _upload(image_path, f"schedule/{_paris(msg['date'])[:10]}_{msg['chat']['id']}_{msg['message_id']}") \
        if image_path else ""

    origin = msg.get("forward_origin") or {}
    info = {
        "chat_id": msg["chat"]["id"],
        "message_id": msg["message_id"],
        "sender": msg["from"].get("first_name", ""),
        "sent_at_paris": _paris(msg["date"]),
        "forwarded_original_date_paris": _paris(origin["date"]) if origin.get("date") else "",
        "text": msg.get("text") or msg.get("caption") or "",
        "image_path": image_path,
        "image_url": image_url,
    }
    (out / "message.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in info.items() if k != "chat_id"}, ensure_ascii=False))


def reply(outdir):
    p = pathlib.Path(outdir) / "message.json"
    if p.exists():
        info = json.loads(p.read_text())
    else:  # fetch 那步就挂了,直接从事件里取
        msg = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text())["client_payload"]["message"]
        info = {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"]}
    text = sys.stdin.read().strip() or "(无输出)"
    _api("sendMessage", {
        "chat_id": info["chat_id"],
        "text": text[:4000],
        "reply_parameters": {"message_id": info["message_id"], "allow_sending_without_reply": True},
    })


def send(text, html=False):
    """推给 TELEGRAM_CHAT_ID 里的每个人;超长自动按行切成多条(单条上限 4096)。"""
    chats = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]
    if not chats:
        sys.exit("缺 TELEGRAM_CHAT_ID")
    chunks, cur = [], ""
    for line in text.strip().splitlines():
        if len(cur) + len(line) + 1 > 3800:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    for chat in chats:
        for chunk in chunks:
            payload = {"chat_id": chat, "text": chunk, "link_preview_options": {"is_disabled": True}}
            if html:
                payload["parse_mode"] = "HTML"
            _api("sendMessage", payload)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "send" and len(sys.argv) == 2:
        send(sys.stdin.read())
    elif cmd in ("fetch", "reply") and len(sys.argv) == 3:
        {"fetch": fetch, "reply": reply}[cmd](sys.argv[2])
    else:
        sys.exit(__doc__)
