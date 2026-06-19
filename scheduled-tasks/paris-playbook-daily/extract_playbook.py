#!/usr/bin/env python3
"""
Paris Playbook 邮件正文提取器

背景:Playbook 邮件约 120KB+,Gmail MCP 的 get_thread(FULL_CONTENT) 会因
「超过 token 上限」报错,并把完整 JSON 甩到一个 tool-results 文件里。
这个脚本直接吃那个文件(或任意含 {messages:[...]} 的 JSON),把双重转义的
HTML 还原成干净纯文本,并切出「AUSSI À L'AGENDA」→「MÉDIAS」那一段(行程在这里)。

用法:
    python3 extract_playbook.py <get_thread 甩出来的文件路径>
    # 或从 stdin:
    cat dump.json | python3 extract_playbook.py
    # 调试:打印完整 AGENDA + 整篇正文(旧行为,输出很大)
    python3 extract_playbook.py <文件> --full

输出(默认 = 精简模式,只给上层 agent 它真正要的几百字节):
    === MSG 1 | <date> | <subject> ===
    --- AGENDA · ATTAL/SÉJOURNÉ(只保留两人为主语的行程句,已标注周几归属)---
    [当天] Gabriel Attal visite, ce matin à …
    --- NEWS 相关段(正文里提到两人的句子 + 上下文,供抽新闻)---
    …Gabriel Attal est "probablement passé pour…

注意:**默认精简模式输出极小**,不会触发「Output too large」,agent 无需 cat/转存,
一步就能读完 → 避免预算烧光、死在插入步骤之前(2026-06-19 漏库的根因)。
"""
import json
import sys
import re
import html


def clean_html(s: str) -> str:
    """双重转义 HTML → 纯文本。邮件里标签本身被转义成 &lt;p&gt; 这种。"""
    if not s:
        return ""
    # 邮件 HTML 是多重转义(&amp;lt;p&amp;gt; …),循环反转义到稳定,
    # 真标签才会现形成 <p>,否则去标签的正则永远匹配不到。
    for _ in range(5):
        prev = s
        s = html.unescape(s)
        if s == prev:
            break
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)  # 去标签
    s = html.unescape(s)           # 残留实体
    s = s.replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def slice_agenda(text: str) -> str:
    """切出「AUSSI À L'AGENDA」到「MÉDIAS」之间的行程段。"""
    low = text.lower()
    start = low.find("aussi à l")
    if start < 0:
        start = low.find("agenda")
    if start < 0:
        return ""
    end = low.find("médias", start)
    if end < 0:
        end = low.find("medias", start)
    if end < 0:
        end = start + 4000  # 兜底:取后续一段
    return text[start:end].strip()


# 两人姓名的各种写法(clean_html 已去掉加粗标记,剩纯文本)
_NAMES = ("gabriel attal", "stéphane séjourné", "stephane sejourne",
          "stéphane sejourné", "séjourné", "sejourné")


def _mentions(s: str) -> bool:
    low = s.lower()
    return "attal" in low or "séjourné" in low or "sejourn" in low


def filter_agenda(agenda: str) -> str:
    """只保留以 Gabriel Attal / Stéphane Séjourné 为主语(句首)的行程句,
    并按 AGENDA 里的「Samedi :」「Dimanche :」分节标注归属日。"""
    if not agenda:
        return ""
    low = agenda.lower()
    sam = low.find("samedi :")
    dim = low.find("dimanche :")

    def day_of(pos: int) -> str:
        if dim >= 0 and pos >= dim:
            return "周日"
        if sam >= 0 and pos >= sam:
            return "周六"
        return "当天"

    # 切句并记原文起点;剥掉转发版每行的引用/加粗前缀(> 、* 、空白)
    sents = []
    for m in re.finditer(r"[^.!?]*[.!?]", agenda):
        s = re.sub(r"^[\s>*]+", "", m.group()).strip()
        if s:
            sents.append((m.start(), s))

    def is_subject(s: str) -> bool:
        low = s.lower()
        return low.startswith("gabriel attal") or low.startswith(
            ("stéphane séjourné", "stephane sejourne", "séjourné", "sejourné")
        )

    # 延续句:同一人行程的后续(含时间/地点),句首是代词而非新主语
    _CONT = ("il ", "elle ", "a ", "à ", "puis ", "il s", "elle s")

    out = []
    for i, (pos, sent) in enumerate(sents):
        if not is_subject(sent):
            continue
        parts = [sent]
        # 把紧跟的延续句并进来(如「Il s'adresse à la presse à 11h15.」带上时间)
        for _, nxt in sents[i + 1:]:
            if is_subject(nxt):
                break
            if nxt.lower().startswith(_CONT):
                parts.append(nxt)
            else:
                break
        out.append(f"[{day_of(pos)}] {' '.join(parts)}")
    return "\n".join(out)


def filter_news(body: str) -> str:
    """正文里提到两人的句子 + 前后各一句上下文,供抽新闻。输出保持很小。"""
    if not body:
        return ""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    keep_idx = set()
    for i, s in enumerate(sents):
        if _mentions(s):
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(sents):
                    keep_idx.add(j)
    if not keep_idx:
        return ""
    # 连续区间合并,段间用空行分隔
    blocks, cur = [], []
    for i in sorted(keep_idx):
        if cur and i != cur[-1] + 1:
            blocks.append(" ".join(sents[k] for k in cur))
            cur = []
        cur.append(i)
    if cur:
        blocks.append(" ".join(sents[k] for k in cur))
    return "\n\n".join(b[:600] for b in blocks)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    full = "--full" in sys.argv[1:]
    if args:
        raw = open(args[0], encoding="utf-8").read()
    else:
        raw = sys.stdin.read()

    data = json.loads(raw)
    messages = data.get("messages") or ([data] if "htmlBody" in data else [])
    if not messages:
        print("⚠️  JSON 里没找到 messages。", file=sys.stderr)
        sys.exit(1)

    for i, m in enumerate(messages, 1):
        subject = m.get("subject", "")
        date = m.get("date", "")
        body_src = m.get("plaintextBody") or m.get("plaintext_body") or ""
        if not body_src:
            body_src = m.get("htmlBody") or m.get("html_body") or ""
        text = clean_html(body_src)

        agenda = slice_agenda(text)
        # 正文(抽新闻用):取 AGENDA 之前的部分,去掉顶部订阅 boilerplate
        cut = text.lower().find("aussi à l")
        body = text[:cut] if cut > 0 else text

        print(f"=== MSG {i} | {date} | {subject} ===")
        if full:
            # 调试用:完整 AGENDA + 整篇正文(输出很大,平时别用)
            print("--- AGENDA(完整)---")
            print(agenda if agenda else "(未找到 AGENDA 段)")
            print("\n--- BODY(完整正文)---")
            print(body)
        else:
            # 默认:只给 agent 它真正要的,几百字节,不会触发 Output too large
            fa = filter_agenda(agenda)
            print("--- AGENDA · ATTAL/SÉJOURNÉ(以两人为主语的行程句,[]内为归属日)---")
            print(fa if fa else "(今日 AGENDA 无 Attal/Séjourné 行程 → schedule = [])")
            fn = filter_news(body)
            print("\n--- NEWS 相关段(正文里提到两人的句子+上下文,供抽新闻)---")
            print(fn if fn else "(正文未提及两人 → 该邮件 news 可为 [])")
        print("\n")


if __name__ == "__main__":
    main()
