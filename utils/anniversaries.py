"""
纪念日 / 重要日期表 — 首页倒计时和每日 ntfy 提醒共用。

直接编辑这个列表即可增删日期：
  month/day 必填；year 填了会显示"第 N 年"，纯纪念日可不填。
不在顶层 import streamlit，GitHub Actions 脚本可直接使用。
"""
from datetime import date

ANNIVERSARIES = [
    {"month": 3,  "day": 16, "year": 1989, "label": "🎂 Gabriel Attal 生日",
     "label_en": "🎂 Gabriel Attal's birthday"},
    {"month": 3,  "day": 26, "year": 1985, "label": "🎂 Stéphane Séjourné 生日",
     "label_en": "🎂 Stéphane Séjourné's birthday"},
    {"month": 1,  "day": 9,  "year": 2024, "label": "🏛️ GA 就任总理纪念日",
     "label_en": "🏛️ GA appointed Prime Minister"},
    {"month": 1,  "day": 11, "year": 2024, "label": "🇫🇷 SS 就任外交部长纪念日",
     "label_en": "🇫🇷 SS appointed Foreign Minister"},
    {"month": 12, "day": 1,  "year": 2024, "label": "🇪🇺 SS 就任欧委会执行副主席纪念日",
     "label_en": "🇪🇺 SS took office as EU Commission EVP"},
    {"month": 4,  "day": 6,  "year": 2016, "label": "⚜️ En Marche 创党纪念日（两人共同起点）",
     "label_en": "⚜️ En Marche founded (where it all began)"},
]


def upcoming(today: date = None, within_days: int = 366) -> list:
    """返回未来 within_days 内的纪念日，按临近程度排序。
    每项附加 days_until 和 years（周年数，无 year 时为 None）。"""
    today = today or date.today()
    out = []
    for a in ANNIVERSARIES:
        try:
            nxt = date(today.year, a["month"], a["day"])
        except ValueError:   # 2/29 之类
            continue
        if nxt < today:
            nxt = date(today.year + 1, a["month"], a["day"])
        days = (nxt - today).days
        if days <= within_days:
            years = (nxt.year - a["year"]) if a.get("year") else None
            out.append({**a, "next_date": nxt, "days_until": days, "years": years})
    return sorted(out, key=lambda x: x["days_until"])
