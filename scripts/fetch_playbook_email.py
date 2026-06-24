#!/usr/bin/env python3
"""
Gmail IMAP → Paris Playbook 邮件抓取

为什么不用 Gmail MCP:
  原 paris-playbook-daily 是 Claude app 内置定时任务,靠桌面 app 的 Gmail 连接器读信。
  迁到 launchd(系统级,扛睡眠、关 app 也跑)后是 headless `claude -p`,
  **它不继承桌面 app 的连接器**(CLI 里没有任何 MCP server),所以读不到 Gmail。
  这个脚本用标准 IMAP 直连 Gmail 取信,输出成 extract_playbook.py 认得的 JSON
  ({messages:[{subject,date,htmlBody}]}),解析逻辑那边完全复用、一行不改。

鉴权:Gmail 普通密码无法 IMAP 登录,需「应用专用密码」(需先开两步验证):
  https://myaccount.google.com/apppasswords
  生成后连同邮箱地址写进 .env:
    GMAIL_USER=junru.zhang10@gmail.com
    GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx   # 16 位,去掉空格

用法:
  python3 scripts/fetch_playbook_email.py [--since-days N] [--sender ADDR]
  默认 --since-days 2(覆盖周末漏跑后的补抓),输出 JSON 到 stdout。
  无邮件时输出 {"messages": []} 并以 exit 0 退出(run.sh 据此跳过 claude)。
"""
import os
import sys
import json
import argparse
import imaplib
import email
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta

IMAP_HOST = "imap.gmail.com"
DEFAULT_SENDER = "playbookparis@politico.eu"


def _decode(s):
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def _html_body(msg) -> str:
    """优先取 text/html,回退 text/plain。extract_playbook.clean_html 两者都能处理。"""
    html_part = None
    plain_part = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp.lower():
                continue
            if ctype == "text/html" and html_part is None:
                html_part = part
            elif ctype == "text/plain" and plain_part is None:
                plain_part = part
    else:
        if msg.get_content_type() == "text/html":
            html_part = msg
        else:
            plain_part = msg
    part = html_part or plain_part
    if part is None:
        return ""
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, TypeError):
        return payload.decode("utf-8", errors="replace")


def fetch(sender: str, since_days: int):
    user = os.environ.get("GMAIL_USER", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not user or not pw:
        print("❌ 缺 GMAIL_USER / GMAIL_APP_PASSWORD(请写进 .env)", file=sys.stderr)
        sys.exit(2)

    since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        M.login(user, pw)
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP 登录失败(应用专用密码不对?或没开两步验证/IMAP?):{e}",
              file=sys.stderr)
        sys.exit(2)

    messages = []
    try:
        M.select("INBOX")
        typ, data = M.search(None, "FROM", f'"{sender}"', "SINCE", since)
        ids = data[0].split() if data and data[0] else []
        for num in ids:
            typ, raw = M.fetch(num, "(RFC822)")
            if typ != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            subject = _decode(msg.get("Subject"))
            try:
                dt = parsedate_to_datetime(msg.get("Date"))
                date_iso = dt.astimezone().isoformat()
            except Exception:
                date_iso = msg.get("Date", "")
            messages.append({
                "subject": subject,
                "date": date_iso,
                "htmlBody": _html_body(msg),
            })
    finally:
        try:
            M.logout()
        except Exception:
            pass

    # 老→新排序,便于 run.sh / claude 按时间处理
    messages.sort(key=lambda m: m.get("date", ""))
    return messages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=2,
                    help="抓最近 N 天的邮件(默认 2,覆盖周末漏跑补抓)")
    ap.add_argument("--sender", default=DEFAULT_SENDER)
    args = ap.parse_args()

    messages = fetch(args.sender, args.since_days)
    print(json.dumps({"messages": messages}, ensure_ascii=False))
    print(f"✅ 抓到 {len(messages)} 封 Paris Playbook 邮件", file=sys.stderr)


if __name__ == "__main__":
    main()
