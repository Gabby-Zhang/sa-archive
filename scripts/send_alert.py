#!/usr/bin/env python3
"""
出错告警邮件(复用 Gmail 应用专用密码,SMTP 发给自己)

给 launchd 任务(paris-playbook / screenshot 等)在报错时发一封提醒邮件。
不抛异常拖垮调用方:发信本身失败只打到 stderr,绝不影响退出码。

用法:
  echo "<正文>" | python3 scripts/send_alert.py "<标题>"
环境变量(run.sh 已从 .env 载入):
  GMAIL_USER / GMAIL_APP_PASSWORD —— 复用 IMAP 那把,收发同一邮箱
"""
import os
import sys
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "sa-archive 任务报错"
    body = sys.stdin.read() if not sys.stdin.isatty() else ""

    user = os.environ.get("GMAIL_USER", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not user or not pw:
        print("send_alert: 缺 GMAIL_USER / GMAIL_APP_PASSWORD,跳过发信", file=sys.stderr)
        return  # 不报错,避免影响调用方退出码

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = user            # 发给自己
    msg["Subject"] = subject
    msg.set_content(body or "(无正文)")

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.login(user, pw)
            s.send_message(msg)
        print("send_alert: 已发送告警邮件", file=sys.stderr)
    except Exception as e:
        print(f"send_alert: 发信失败(忽略):{e}", file=sys.stderr)


if __name__ == "__main__":
    main()
