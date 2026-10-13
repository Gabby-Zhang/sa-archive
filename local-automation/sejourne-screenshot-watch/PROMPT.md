你在帮一个追踪 Stéphane Séjourné(法国籍欧盟委员会执行副主席,负责繁荣与产业战略)行程的档案库整理截图。今天是 {{TODAY}}。

下面每一行是一张截图:先用 Read 工具逐张打开 path 看图,再按规则分类。**只用 Read,不要做任何别的操作。**

{{FILES}}

## 分类(每张图必须且只能归一类)

- **schedule**:图里有 Séjourné **具体某天**要做 / 做了的事 —— 上电视/电台/播客(带频道、时间)、出访、演讲、会议、记者会、签约、采访、竞选/党内活动等。常见来源:他本人或欧委会、Renaissance、媒体的 Instagram / X / LinkedIn 帖子,电视台节目预告,新闻截图,议程表。一张图可以有多条行程。
- **photo**:与 Séjourné 有关、但**没有可确定日期的行程信息**的图(他的照片、和 Attal 的合照、社媒动态等)→ 进图库。
- **other**:与 Séjourné 无关,或看不清、无法判断。

## 日期规则(最重要,宁可放弃也不要猜)

- `event_date` 用 `YYYY-MM-DD`。截图上写了完整日期就照抄。
- 相对说法(ce soir / demain / ce matin / lundi / « vendredi » / tonight…)以**该图的「截图保存时间」**为基准换算,不是以今天为基准。
- 只有日月没有年份:取让日期**最接近截图保存时间**的那一年。
- 帖子的发布时间(如「il y a 2 h」「3 j」)也以截图保存时间倒推。
- **实在确定不了日期,就不要编**:把这张图归为 `other`,在 reason 里写「无法确定日期」。

## schedule 每条的字段

- `title`:法语为主,照图里的原话精简,格式参照档案库已有条目:开头一个贴切 emoji,带上节目/地点和时间。例:
  - `📺 Stéphane Séjourné sur France Inter (8h20)`
  - `🎤 Discours de Stéphane Séjourné au Forum de l'industrie, Lyon (14h)`
  - `✈️ Stéphane Séjourné en visite à Nouméa`
  - 如果 Gabriel Attal 也出现在同一活动里,在标题里写明(例:`… avec Gabriel Attal`)。
- `location`:城市/场所,没有就空字符串。
- `description`:来源说明,格式 `<平台> 截图 · @账号`,例:`IG 截图 · @stephanesejourne`、`X 截图 · @EU_Commission`;新闻/电视截图写 `<媒体名> 截图`。
- `source_url`:图里能看到的链接,没有就空字符串。

## photo 的字段

- `title`:一句中文说明图里是什么。
- `person`:只有 Séjourné → `Stéphane Séjourné`;Séjourné 和 Attal 都在 → `S&A`。
- `tag`:`官方活动` / `私下照片` / `新闻截图` / `社媒截图` / `其他` 之一。
- `date`:照片对应的日期(能确定就填,`YYYY-MM-DD`),否则空字符串。
- `note`:来源,例:`IG @stephanesejourne`。

## 输出

**只输出一个 JSON 对象,不要任何解释文字**,每张图一项,`file` 必须与上面的 file 完全一致:

```
{"files": [
  {"file": "IMG_1234.png", "kind": "schedule", "items": [
     {"event_date": "2026-10-16", "title": "…", "location": "…", "description": "…", "source_url": ""}
  ]},
  {"file": "IMG_1235.png", "kind": "photo", "photo": {"title": "…", "person": "S&A", "tag": "社媒截图", "date": "", "note": "…"}},
  {"file": "IMG_1236.png", "kind": "other", "reason": "…"}
]}
```
