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


# 两人的「人名」匹配(大写开头,天然避开小写动词 séjourner/séjournant——
# CLAUDE.md 早就警告过裸搜 séjourné 会吃进动词)。Attal 无歧义。
_PERSON = re.compile(r"\bAttal\b|\bS[ée]journ[ée]s?\b")


def filter_agenda(agenda: str) -> str:
    """AGENDA 段里凡真提到 Gabriel Attal / Stéphane Séjourné 的句子一律保留,
    按「Samedi :」「Dimanche :」标注归属日。两类都收(是不是"正经行程"交给人判断):
      1) 句首主语句(「Gabriel Attal se rend à …」)——并把紧跟的代词延续句合并进来;
      2) 宾语位/顺带提及(「Serge Papin s'entretient avec Stéphane Séjourné …」、
         「… en présence de … Attal」)——过去只留 1)、把 2) 全丢了,导致
         2026-06-26 那条"部长会见 Séjourné"整条漏掉。现在 2) 也留。"""
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
    consumed = set()  # 已被主语句作为延续句吸收的句子,别再当"顺带提及"重复收
    for i, (pos, sent) in enumerate(sents):
        if i in consumed:
            continue
        if is_subject(sent):
            parts = [sent]
            for k in range(i + 1, len(sents)):
                nxt = sents[k][1]
                if is_subject(nxt):
                    break
                if nxt.lower().startswith(_CONT):
                    parts.append(nxt)
                    consumed.add(k)
                else:
                    break
            out.append(f"[{day_of(pos)}] {' '.join(parts)}")
        elif _PERSON.search(sent):
            # 两人不是句子主语,但真出现了(宾语/在场名单)→ 也留,交给人判断
            out.append(f"[{day_of(pos)}] {sent}")
    return "\n".join(out)


# MÉDIAS 段:只认全大写表头 MÉDIAS(邮件里栏目头一定大写)。别用 lower().find,
# 会误命中正文里 titlecase 的 "Médias de Rhénanie-du-Nord-Westphalie" 这类地名。
_MEDIA_HEADER = re.compile(r"MÉDIAS\b")
# 露出条目里的人名(冒号后 = 上节目的嘉宾)
_MEDIA_NAMES = r"(Gabriel Attal|Stéphane Séjourné|Stéphane Sejourné|Stephane Sejourne)"


# MÉDIAS 电台列表之后,Playbook 依次接:「PLUS TARD.」(稍晚的电视辩论,要保留)、
# 「À LA UNE :」(各报头版,非广播)、「CARNET / NOS NEWSLETTERS PRO」(自家促销)。
# 终止边界设在 À LA UNE / CARNET / NEWSLETTERS——既切掉头版和促销噪音,又保住
# PLUS TARD 辩论(2026-06-29 Attal 上 LCI 辩论就在这段)。
_MEDIA_END = re.compile(r"À LA UNE|CARNET|NOS NEWSLETTERS|NEWSLETTERS? PRO")
_MEDIA_JUNK = re.compile(r"[A-ZÉÈÀÊ]{3,}\s+[A-ZÉÈÀÊ&]{2,}")  # 促销小标题特征,非真台名


def slice_media(text: str) -> str:
    """切出「MÉDIAS」表头之后的电台/电视露出段(到头版/促销区止,3000 字兜底)。"""
    m = _MEDIA_HEADER.search(text)
    if not m:
        return ""
    sec = text[m.end():m.end() + 3000]
    end = _MEDIA_END.search(sec)
    return sec[:end.start()] if end else sec


def filter_media(text: str) -> str:
    """从 MÉDIAS 段抽出以 Attal/Séjourné 为主语的电台/电视露出,改写成
    以人名开头的法语行程句(下游 SKILL 按「句首主语」判定 person、译成英文)。
    原格式:'7h40. RTL : Gabriel Attal, secrétaire général du parti Renaissance …'
    输出:  '[当天] Gabriel Attal est l'invité de RTL à 7h40 (secrétaire général …).'"""
    sec = slice_media(text)
    if not sec:
        return ""
    # MÉDIAS 段里每档以「<可选时间>. <站名> : 嘉宾1, 头衔1, 嘉宾2, 头衔2 …」排布,
    # 同一时间多个台用「…」分隔。冒号只出现在站名后,故先扫出所有「站名 :」标记的
    # 位置,再把每个 Attal/Séjourné 归到它前面最近的那档——这样即便两人是某档的
    # 第 2/3 位嘉宾(前面还有别的政客)也能正确取到台名(2026-07-09 修:多嘉宾同台会漏)。
    stations = []  # (冒号结束位置, 站名)
    for cm in re.finditer(r"\s:\s", sec):
        before = sec[:cm.start()]
        # 站名 = 冒号前、上一个句号/省略号之后的那段,去掉前导时间
        name = re.split(r"[.…]", before)[-1]
        name = re.sub(r"^\s*\d+h\d+\s*", "", name).strip()
        stations.append((cm.end(), name))
    times = [(t.start(), t.group()) for t in re.finditer(r"\d+h\d+", sec)]

    def nearest(seq, pos):
        val = ""
        for p, v in seq:
            if p <= pos:
                val = v
            else:
                break
        return val

    # 站名冒号位置(用于距离保护:名字离最近的「站名 :」太远,说明不是那档嘉宾)
    colon_pos = [p for p, _ in stations]

    out = []
    for m in re.finditer(_MEDIA_NAMES, sec):
        person = re.sub(r"sejourne", "Séjourné",
                        m.group(1), flags=re.I).replace("Stephane", "Stéphane")
        # 名字所在整句(用于辨认「PLUS TARD … débattent sur <台> à <时>」辩论式)
        s0 = sec.rfind(".", 0, m.start()) + 1
        s1 = sec.find(".", m.end())
        s1 = len(sec) if s1 < 0 else s1
        sentence, after = sec[s0:s1], sec[m.end():s1]

        if re.search(r"débatt?", sentence, re.I):
            # 辩论式:频道在「sur <台>」、时间在「à <时>」,人名不在「站名 :」后
            cm = re.search(r"\bsur ([A-ZÉ][\w/. ]{1,18}?)\s*(?:,|\.|à | à|$)", after)
            station = cm.group(1).strip(" .") if cm else ""
            tm = re.search(r"à (\d{1,2}\s?h\d{0,2}|\d{1,2}\s?heures?)", sentence)
            at_ = re.sub(r"\s+", "", tm.group(1)) if tm else ""
            verb, role = "participe à un débat sur", ""
        else:
            # 常规「<时>. <台> : … <名>, <头衔> …」;距离>220 视作非本档,弃站名
            cp = max([p for p in colon_pos if p <= m.start()], default=None)
            station = nearest(stations, m.start()) if cp is not None and m.start() - cp <= 220 else ""
            at_ = nearest(times, m.start())
            tail = re.split(r"[.…]", after, 1)[0]
            role = ""
            mr = re.match(r"\s*,\s*([^,]+)", tail)
            if mr:
                role = re.split(r"\s+et\s+[A-ZÉ]", mr.group(1).strip())[0].strip()
            verb = "est l'invité de"

        # 站名校验:空 / 过长 / 连续全大写词(促销小标题) = 噪音,丢
        if not station or len(station) > 24 or _MEDIA_JUNK.search(station):
            continue
        line = f"[当天] {person} {verb} {station}"
        if at_:
            line += f" à {at_}"
        if role:
            line += f" ({role})"
        out.append(line + ".")
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
            # MÉDIAS 段的电台/电视露出也算行程(2026-07-09 加):Playbook 把两人
            # 当天上哪个台放在 MÉDIAS 栏,过去被 slice_agenda 在「MÉDIAS」处切掉、
            # 整段漏掉(如 07-09 "7h40 RTL : Gabriel Attal" 就这么没进 Agenda)。
            fm = filter_media(text)
            combined = "\n".join(x for x in (fa, fm) if x)
            print("--- AGENDA · ATTAL/SÉJOURNÉ(以两人为主语的行程句 + 当天电台/电视露出,[]内为归属日)---")
            print(combined if combined else "(今日 AGENDA/MÉDIAS 无 Attal/Séjourné → schedule = [])")
            fn = filter_news(body)
            print("\n--- NEWS 相关段(正文里提到两人的句子+上下文,供抽新闻)---")
            print(fn if fn else "(正文未提及两人 → 该邮件 news 可为 [])")
        print("\n")


if __name__ == "__main__":
    main()
