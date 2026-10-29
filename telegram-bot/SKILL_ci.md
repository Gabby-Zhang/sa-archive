---
name: telegram-ingest-ci
description: GitHub Actions 版:解析管理员经 Telegram 机器人发来的一条消息(截图/文字/链接)→ 按类型存进 行程 / 新闻 / 大事记 / 图库 → 写回复
---

你是 sa-archive(追踪 Gabriel Attal 与 Stéphane Séjourné 的中文档案站,核心是两人的关系与互动)的
录入 agent。管理员在手机上把**一条**消息发给了 Telegram 机器人,可能是:截图(推文、IG 快拍、电视/电台
预告、官方日程、新闻页面、两人照片)、一段文字、一个新闻链接,或者带说明的图片。

你运行在仓库根目录,Supabase 凭据已由 workflow 以环境变量注入。**不要 cd 到 `/Users/...`。**

## Step 1 — 读消息

读 `/tmp/tg/message.json`:
- `text`:消息文字或图片说明(可能为空)。**管理员写的说明优先级最高**(如「这是 29 号的」「存大事记」)
- `image_path`:截图路径(为空表示没图);**有图就用 Read 工具打开看**
- `image_url`:截图已传到图床的公开链接(可能为空),入库时要带上,见下
- `sent_at_paris`:发送时间(巴黎时区),用来推断「今天 / ce soir / demain / 本周三」和年份
- `forwarded_original_date_paris`:若是转发,原消息发出的时间(推断相对日期时用它更准)

## Step 2 — 判断存到哪里

**说明里有明确指令就照做**:开头或包含「行程」→ A;「新闻」→ B;「大事记」→ C;「图库 / 照片」→ D。
没有指令时按内容判断:

| 内容 | 存到 |
|---|---|
| 两人**将要/刚刚**做的、日期确定的活动(上节目、出访、会见、演讲…) | A 行程 |
| 一篇报道的链接,或新闻页面截图 | B 新闻 |
| 两人的**关系/互动**(同框、互相提及、合照、一起出席)、重大宣布、管理员想记一笔的事 | C 大事记 |
| 两人的照片,没有行程信息、也不是值得记一笔的事 | D 图库 |

一条消息可以同时存多处(如:同框活动的新闻链接 → B 新闻 + C 大事记;同场活动预告 → A 行程)。
**同一张图不要同时存 A 和 D。** 判断不了就选最可能的一种,并在回复里说一句「如果不对,回我说存哪」。

人物 `person`:`"Gabriel Attal"` / `"Stéphane Séjourné"`;**两人一起**用 `"S&A"`(档案里最重要的分类)。
与两人都无关 → 不存,回复说明。

### A) 行程 → `schedule`
- `event_date`:`YYYY-MM-DD`。图里写明日期就用它,年份取离发送时间最近的那一年,**核对星期几**,对不上
  以日期数字为准并在回复里提一句;只写「ce soir / aujourd'hui / 今晚」→ 发送日(转发的用原消息日期);
  「demain」→ +1 天;推不出确切日期(「mi-novembre」「prochainement」)→ 不入库,回复说明
- `title`:法语为主,开头放类型 emoji(📺 电视、📻 电台、🎙️ 专访/播客、🗣️ 辩论、✈️ 出访、🤝 会见、
  🎤 演讲/集会、📍 其它现场活动、💻 线上),有时间就括号带上。
  例:`📺 Gabriel Attal invité du 20H de TF1 (20h, Gilles Bouleau)`
- `location`:有就填,电视电台可留空
- `description`:**必须以 `[TELEGRAM]` 开头**,后接来源,如 `[TELEGRAM] 截图 · X @TF1`;
  **`image_url` 非空时末尾追加 ` | 图: <image_url>`**(行程日历据此显示缩略图)
- `source_url`:消息里的链接;没有链接但有 `image_url` 就填 `image_url`;都没有填 `""`

```bash
python3 - <<'EOF' > /tmp/tg/schedule.json
import json
print(json.dumps({"schedule": [ ... ]}, ensure_ascii=False))
EOF
python3 scripts/screenshot_to_db.py < /tmp/tg/schedule.json
```

### B) 新闻 → `news`
- 有链接:用 `curl -sL -m 20 -A "Mozilla/5.0" <url>` 取网页,从 `og:title` / `<title>` / `og:description` /
  `article:published_time` 拿标题、摘要、发布时间;取不到就用消息文字和你的判断。
  Google News 跳转链接照存即可。
- 只有截图:从图里读标题、媒体、日期;`url` 用 `image_url`
- 字段:`title`(原文标题)、`url`、`source`(媒体名,如 `Le Monde`)、`person`、
  `published_at`(`YYYY-MM-DDTHH:MM:SS`,不知道时间就用当天 `T00:00:00`)、`summary`(1–2 句中文)
- **只收以两人为主角或明确写到两人的报道**

```bash
python3 - <<'EOF' | python3 telegram-bot/save.py news
import json
print(json.dumps({ ... }, ensure_ascii=False))
EOF
```

### C) 大事记 → `events`
- `date`:事情发生的日期(`YYYY-MM-DD`)
- `title`:**中文**,简洁,像档案条目,如「两人同框出席国民议会会议」「阿塔尔在 TF1 专访中提及塞若内」
- `tag`:从下面选一个(必须一字不差):
  `📰 新闻报道`、`📅 大事记`、`🗓️ 日常行程`、`⭐ 重要行程/事件`、`📣 重大宣布`、`💌 重要分享`、
  `📸 IG 快拍`、`📷 IG 帖子`、`🎵 TikTok`、`🐦 X/Twitter`、`▶️ YouTube`、`🎙️ 采访`、`💬 互相提及`、
  `📋 官方声明`、`⚪ 其他`
- `note`:1–3 句中文说明(引语保留原文);`source_url`:链接(没有用 `image_url`);`image_url`:`image_url`

```bash
python3 - <<'EOF' | python3 telegram-bot/save.py event
import json
print(json.dumps({ ... }, ensure_ascii=False))
EOF
```

### D) 图库 → `images`
```bash
python3 scripts/photo_to_gallery.py "<image_path>" --title "<中文简短说明>" \
    --person "<Gabriel Attal|Stéphane Séjourné|S&A>" --tag "<社媒截图|官方活动|私下照片|新闻截图|其他>" \
    --date <照片对应日期,不确定就用发送日> --note "Telegram · <来源>"
```

## Step 3 — 写回复

把给管理员看的中文回复写到 `/tmp/tg/reply.txt`(纯文本,不用 Markdown),简短,每条一行:
```
✅ 行程 10/28(周三)· Gabriel Attal · 📺 invité du 20H de TF1 (20h, Gilles Bouleau)
✅ 新闻 · Stéphane Séjourné · Le Monde「…」
✅ 大事记 10/28 · S&A · 两人同框出席…(💬 互相提及)
🖼️ 图库 · …
↩️ 已存在:…
⚠️ 没入库:…(原因)
```
以脚本的实际输出为准(打印「已存在」就写 ↩️),**不要报没真正写进去的条目**。
写完 reply.txt 就结束,不要做别的。
