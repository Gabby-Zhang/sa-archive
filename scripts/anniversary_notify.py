#!/usr/bin/env python3
"""
纪念日提醒 — 供 GitHub Actions 每天调用一次。
纪念日前 7 天和当天，向 ntfy 推送提醒（每天最多一条汇总）。
"""
import os
import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.anniversaries import upcoming

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "ss-calendar-update")


def main():
    hits = [a for a in upcoming() if a["days_until"] in (7, 1, 0)]
    if not hits:
        print("近期无需要提醒的纪念日")
        return

    lines = []
    for a in hits:
        when = {7: "还有 7 天", 1: "就是明天", 0: "就是今天！"}[a["days_until"]]
        nth = f"（第 {a['years']} 年）" if a.get("years") else ""
        lines.append(f"{a['label']}{nth} — {when}")

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data="\n".join(lines).encode("utf-8"),
            headers={"Title": "Anniversary reminder", "Tags": "tada"},
            timeout=10,
        )
        print(f"✅ 已推送 {len(lines)} 条纪念日提醒")
    except Exception as e:
        print(f"⚠️ ntfy 推送失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
