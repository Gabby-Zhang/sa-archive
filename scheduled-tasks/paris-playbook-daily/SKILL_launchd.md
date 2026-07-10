---
name: paris-playbook-launchd
description: launchd/headless 版:从预抽取的 Playbook 文本构造 JSON → 入库(不读 Gmail MCP)
---

你是 sa-archive(追踪 Gabriel Attal 与 Stéphane Séjourné 的法国政治档案)的数据抽取 agent。

**和旧版的区别:** 这是 **launchd headless 版**。邮件已经由 `run.sh` 用 IMAP 抓好、并
经 `extract_playbook.py` 抽成干净文本写到 `/tmp/playbook_extracted.txt`。**你不需要、也
没有 Gmail 连接器** —— 只管读那个文本文件,构造 JSON,入库。

---

## Step 1 — 读预抽取文本

直接读 `/tmp/playbook_extracted.txt`(很小,几百字节~几 KB,一次读完)。它的格式:

```
=== MSG 1 | 2026-06-23T05:06:40+02:00 | Jusqu'à la fin du match ===
--- AGENDA · ATTAL/SÉJOURNÉ(以两人为主语的行程句,[]内为归属日)---
[当天] Gabriel Attal participe au colloque ...
--- NEWS 相关段(正文里提到两人的句子+上下文,供抽新闻)---
...提到两人的正文段...
```

每封邮件一个 `=== MSG ... ===` 区块。**逐封处理所有区块。**

如果某封的 AGENDA 写「(今日 AGENDA 无 Attal/Séjourné 行程 → schedule = [])」,该封
schedule = [];NEWS 写「(正文未提及两人 …)」则 news = []。两个都空的邮件就跳过、不入库。

---

## Step 2 — 把每封解析成 JSON

### A) 行程(schedule)— 来自 AGENDA 区块
AGENDA 区块里每一行都是真行程(已过滤成以两人为主语的句子)。逐行转成对象:
- `title`: 活动内容(法语原文,如 "Participe au colloque « Quelle politique énergétique pour la France ? »")
- `location`: 句中地点(如 "Paris" / "Lévis-Saint-Nom, Yvelines"),没有就 ""
- `time`: 句中时间(如 "11h15"),没有就**省略该字段**
- `event_date`: 由行首日标推出(已替你算好归属日):
  - `[当天]` → 该 MSG 头部的发信日期(取 YYYY-MM-DD)
  - `[周六]` → 发信日之后的下一个周六
  - `[周日]` → 发信日之后的下一个周日
- `person`: "Gabriel Attal" 或 "Stéphane Séjourné"

其中形如「… est l'invité de RTL à 7h40」「… participe à un débat sur LCI à 21h」的行是
**当天电台/电视露出/辩论**(来自 MÉDIAS 栏),同样当行程收:`title` 保留法语原文
(含台名如 RTL/France 2/LCI)、`time` 取句中时间、`person` 取句首人名、`event_date` 用 `[当天]`。

**宾语位/顺带提及**:有的行两人不是句子主语,而是被别人会见/在场名单里出现,如
「Serge Papin s'entretient avec Stéphane Séjourné, …」——这类也已保留,照收。此时
`person` 取**行内出现的被追踪人(Gabriel Attal / Stéphane Séjourné)**,不是句子的语法主语
(上例 person = "Stéphane Séjourné",不是 Papin)。

### B) 新闻(news)— 来自 NEWS 区块
从 NEWS 区块抽 2–5 条**确实以两人之一为核心**的政治新闻。每条:
- `title`: 精炼法语标题(≤50 词)
- `summary`: 1–3 句中文或法语描述
- `person`: "Gabriel Attal" / "Stéphane Séjourné" / "S&A"(两人同现)
- `published_at`: 发信日期 + "T05:05:00"
- `source_url`: "https://www.politico.eu/newsletter/paris-playbook/"

**只收两人为主体的新闻**;仅顺带提及(如某人是某协会主席的上司、政客名单里出现一次)
的**不要收**。

---

## Step 3 — 构造 JSON 并入库

每封邮件构造:
```json
{ "email_date": "YYYY-MM-DD", "email_subject": "...", "schedule": [ ... ], "news": [ ... ] }
```

用 Python 写到 /tmp,再跑入库脚本(幂等,重复安全,自动去重):
```bash
python3 -c "
import json
data = <你的字典>
open('/tmp/playbook_data.json','w').write(json.dumps(data, ensure_ascii=False))
"
cd /Users/junruzhang/Documents/GitHub/sa-archive
python3 scripts/playbook_to_db.py < /tmp/playbook_data.json
rm -f /tmp/playbook_data.json
```

多封就重复 Step 2–3。最后用一行中文汇总:处理几封、入库几条行程、几条新闻。

---

## 注意
- 入库脚本读 `/Users/junruzhang/Documents/GitHub/sa-archive/.streamlit/secrets.toml` 里的 Supabase 凭据
- 项目路径:`/Users/junruzhang/Documents/GitHub/sa-archive`
- **不要**尝试用任何 Gmail/邮件工具 —— headless 环境没有,邮件已抽好在 /tmp 文本里
