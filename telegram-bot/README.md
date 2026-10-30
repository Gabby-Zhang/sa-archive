# Telegram 行程截图机器人

手机(任何品牌)把 GA / SS 的行程截图或一句话**分享给 Telegram 机器人**,约 1–2 分钟后
自动入库 `schedule` 表,机器人回复入库结果。截图本身也存进图床,行程日历卡片上显示缩略图,收入大事记时一并带过去。行程日历显示「📱 截图」徽章,ssga-news-monitor
邮件 Agenda 照常读到。**它只是多一个入口**:新闻抽取、ICS 官方日历、Playbook 等原有来源都照跑。

```
手机 → Telegram 机器人 → Cloudflare Worker(worker.js,校验白名单)
     → GitHub repository_dispatch → .github/workflows/telegram_ingest.yml
     → tg.py fetch 下载图片 → headless claude 按 SKILL_ci.md 解析
     → scripts/screenshot_to_db.py 入库(或 photo_to_gallery.py 进图库)
     → tg.py reply 回复「✅ 行程 10/28 · Gabriel Attal · …」
```

| 文件 | 作用 |
|---|---|
| `worker.js` | Cloudflare Worker:收 Telegram webhook、白名单、触发 GitHub |
| `run_ci.sh` | workflow 主脚本:取消息 → claude 解析入库(重试 3 次)→ 回复;失败也回复 |
| `SKILL_ci.md` | 给 claude 的解析规则(人物、日期推断、标题格式、`[TELEGRAM]` 标签) |
| `tg.py` | 下载 Telegram 图片 / 发回复(纯标准库) |

## 一次性部署(按顺序)

**⚠️ `repository_dispatch` 只认默认分支(main)上的 workflow,要先把这些文件合并到 main。**

1. **建机器人**:Telegram 搜 `@BotFather` → `/newbot` → 起名 → 拿到 token(形如 `123456:ABC…`)。
   建议再发 `/setprivacy` 设 Enable、`/setjoingroups` 设 Disable。
2. **GitHub token**:GitHub → Settings → Developer settings → Fine-grained tokens → Generate:
   Repository access 只选 `sa-archive`;Permissions → Repository → **Contents: Read and write**
   (触发 repository_dispatch 需要这个)。有效期选最长,记下过期日。
3. **sa-archive 的 Actions secrets** 新增 `TELEGRAM_BOT_TOKEN`(第 1 步的 token)。
   `SUPABASE_*`、`CLAUDE_CODE_OAUTH_TOKEN` 已有,和 Playbook 入库共用。
4. **Cloudflare Worker**:dash.cloudflare.com 注册(免费)→ Workers & Pages → Create → Worker →
   起名(如 `sa-archive-tg`)→ Deploy → Edit code,把 `worker.js` 全文粘进去 → Deploy。
   然后 Settings → Variables and Secrets,逐个加(类型选 **Secret**):
   - `TELEGRAM_BOT_TOKEN`:第 1 步的 token
   - `TELEGRAM_WEBHOOK_SECRET`:自己编一串字母数字(如 32 位随机串),第 5 步要用
   - `GITHUB_TOKEN`:第 2 步的 token
   - `GITHUB_REPO`:`Gabby-Zhang/sa-archive`
   - `ALLOWED_USER_IDS`:先随便填 `0`,第 6 步再改
5. **把 webhook 指到 Worker**:浏览器打开 `https://<worker名>.<你的子域>.workers.dev/setup`,
   Worker 用自己存的 token/secret 调 setWebhook,返回 `{"ok": true, ...}` 即成功。
   之后随时可开 `/status` 查看 webhook 状态(`last_error_message` 等,不含 token)。
   **本地连不上 api.telegram.org 时**(`/setup` 报 504/超时):改跑 Actions → "Telegram bot setup",
   填 webhook secret 后运行,由 GitHub 的服务器去设置;secret 留空则只查看状态。
6. **加白名单**:Telegram 里给机器人发 `/id`,它回你的用户 ID → 填进 Worker 的
   `ALLOWED_USER_IDS`(多个管理员逗号分隔)。
7. **测试**:发一张行程截图 → 先回「📥 收到」→ 1–2 分钟后回入库结果。

## 用法

- 截图 → 分享 → Telegram → 机器人。三星分享菜单会记住常用对象。
- **什么都能丢**:行程截图、新闻链接、新闻截图、两人照片、一句话。Claude 判断存到哪:
  行程 → `schedule`;新闻 → `news`;两人互动/关系/重大的事 → `events`(大事记,中文标题);
  没行程信息的照片 → 图库。一条消息可以同时存多处(如同框新闻 → 新闻 + 大事记)。
- 想指定存哪,在说明里写「行程」「新闻」「大事记」「图库」即可;也可补日期(「这是 29 号的」)。
- 纯文字也行:`GA 明早 8h20 France Inter`。
- 相册一次发多张 = 每张各跑一次,互不影响。
- 发错了:目前没有机器人删除命令,去网站对应页面手动删。

## 机器人还会主动推给你

| 内容 | workflow | 时间 |
|---|---|---|
| 任一 workflow 失败 → ⚠️ + run 链接 | `telegram_alerts.yml`(ssga-news-monitor、sejourn-calendar 各有一份) | 失败时 |
| 新动态:SS / GA / S&A 新闻全推;新行程;欧盟影像库新照片(标题自动译成中文,下面附原文链接) | `telegram_push.yml` → `push.py` | 每 30 分钟 |
| 每日汇总(Claude 写的中文汇总) | `telegram_daily.yml` → `daily.py` + `SKILL_daily.md` | 每天伦敦 21:13(cron-job.org) |

- 实时推送的去重记在 `profile_items`(person=S&A, section=`tg_push_seen`);第一次运行只发「已启动」,不刷屏
- 推送对象是 Actions secret `TELEGRAM_CHAT_ID`(你的 Telegram 用户 ID,逗号分隔可多人)

## 排查

- **没回「📥 收到」** → Worker 没收到或挂了:打开 Worker 的 `/status`
  看 `last_error_message`;Cloudflare 后台 Worker → Logs 看实时日志。
- **回「⚠️ 没转出去(GitHub 401/403/404)」** → `GITHUB_TOKEN` 过期/权限不对,或 workflow 还没合并到 main。
- **回了「📥 收到」但迟迟没有结果** → 看 Actions → "Telegram screenshot ingest" 的 run;
  脚本失败会主动回「⚠️ 处理失败」+ run 链接,完全没反应多半是 run 根本没被触发(同上一条)。
- **凭证会过期**:`GITHUB_TOKEN`(你设的有效期)、`CLAUDE_CODE_OAUTH_TOKEN`(约一年,和 Playbook 共用)。
