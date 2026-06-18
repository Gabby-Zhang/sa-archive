# S&A 档案馆 (sa-archive)

关于 Stéphane Séjourné (SS) 和 Gabriel Attal (GA) 的中文粉丝档案站。核心是记录两人的关系与互动,政治/新闻内容是辅助背景。Streamlit 多页应用,部署在 Streamlit Cloud,数据存 Supabase。

## 常用命令

```bash
streamlit run app.py        # 本地启动(http://localhost:8501)
pip install -r requirements.txt
```

没有测试套件;改完靠本地跑起来肉眼验证。推送到 GitHub 后 Streamlit Cloud 自动重新部署。

## 目录结构

- `app.py` — 入口:页面配置 + 全局 CSS(主题变量、中文字形缩放、手机端适配) + 侧边栏导航。改全站样式在这里。**侧边栏顺序由 app.py 里的 `st.navigation([...])` 列表决定**,改顺序就调这个列表,文件名里的数字前缀只是历史命名、不再决定顺序
- `app_pages/` — 各页面,文件名格式 `序号_emoji_中文名.py`。**目录刻意不叫 `pages/`**:否则 Streamlit 会按文件名再自动生成一份导航菜单,和 `st.navigation` 手写的顺序/名字冲突(表现为顺序乱、名字变成文件名)。`13_🧾_操作记录` 仅在 `is_super_admin()` 时才加入导航
- `utils/` — 共享模块:
  - `database.py` — Supabase 客户端和查询封装(所有页面共用);含审计日志 `log_audit`/`get_audit_log`,且 `add_event`/`update_event`/`delete_event` 内部已自动记日志(调用方别再重复记一次)
  - `i18n.py` — 中/法双语文案,`t()` 函数
  - `auth.py` — 访问鉴权
  - `ui.py` — 共享 UI 组件(卡片、徽章等);含 `video_thumb_html(url)`:把 YouTube/B站视频链接渲染成可点击略缩图(YouTube 直接拼 `img.youtube.com`,B站调 API 取封面再经 weserv 代理绕过防盗链,取不到时返回空串降级为纯链接)
  - `anniversaries.py` / `media_spectrum.py` / `news_fetcher.py` — 对应页面的业务逻辑
- `scripts/` — 数据写入脚本,**不被网页调用**,由本机 Claude 定时任务和 cron 触发:
  - `playbook_to_db.py` — Politico 邮件抽取结果入库(幂等,自动去重)
  - `screenshot_to_db.py` — 行程截图解析结果入库(幂等)
  - `photo_to_gallery.py` — 照片入图库
  - 其余:抓新闻、备份、纪念日通知等

## 数据库(Supabase)

主要表:`news`(新闻)、`schedule`(行程)、`events`(大事记)、`images`(图库)、`files`(上传文件)、`audit_log`(操作日志)。
凭据在 `.streamlit/secrets.toml`(不进 git);页面端经 `utils/database.py` 访问,scripts/ 自己读同一个 secrets 文件。

## 大事记页面(`pages/1_📅_大事记.py`)约定

- 一条大事记自带 `tag`(类型标签),并可挂多条 `event_links`(相关内容:新闻、IG、推文、视频等),后者存在 `event_links` 表,启用了 RLS,**必须用 service key(`get_supabase_admin`)才能读写**
- 视频略缩图:`source_url` 本身是视频、或 `event_links` 里的链接是视频时,自动调 `video_thumb_html` 出可点击略缩图(卡片正文 + 相关内容两处)
- 类型标签是**两级**结构:Bilibili 不是顶层类型,而是「🎙️ 采访」的平台子集(B站永远不是第一手源,但常托管采访)。存库格式 `🎙️ 采访 · 📺 Bilibili`,用 `split_event_tag` / `join_event_tag` 拆拼。事件表单顶层选项用 `EVENT_TAG_OPTIONS`(不含 Bilibili)+ 并排的 `PLATFORM_OPTIONS`;**筛选和配色都按主类型归并**(选「采访」能筛到带平台的条目),并兼容旧的独立 `📺 Bilibili` 数据(展示照旧,编辑时自动转成新格式)
- 标签清单定义在 `TAG_OPTIONS` / `TAG_OPTIONS_EN`(中英一一对应)和 `TAG_COLOR`(徽章配色)三处,加新标签要同步改这三处;`EVENT_TAG_OPTIONS` 由 `TAG_OPTIONS` 自动派生(只剔除 Bilibili),所以新标签会自动出现在添加·编辑表单和类型筛选里。行程/事件类标签:`🗓️ 日常行程`(行程日历同步默认)、`⭐ 重要行程/事件`、`📣 重大宣布`(职位升迁、重大事件等)
- 注意 `event_links` 的类型选择器仍用完整 `TAG_OPTIONS`(保留顶层 Bilibili —— 那里作为「平台」是合理的),别和事件类型混为一谈
- `st.form` 内控件不能联动(选完才提交),所以「采访平台」下拉始终显示、提示「仅采访时生效」,选别的类型时平台值会被忽略
- 图片存 `image_url`(可多张,换行/逗号分隔,`parse_image_urls` 拆、`render_images` 显示)。两种来源并存:**① 直传 Cloudinary**(添加/编辑表单的图片 `file_uploader` → `upload_to_cloudinary` → 公开 URL,凭据走 secrets.toml 的 `[cloudinary]`,所有管理员共享、不依赖私人网盘,免费额度远大于 Supabase Storage);**② 图片外链文本框**(兜底,贴已有 gdrive/IG 链接)。上传的 URL 自动追加到外链之后合并存入 `image_url`,老的 gdrive 链接经 `gdrive_to_img_url` 照常显示。**线上 Cloudinary 凭据要在 Streamlit Cloud 的 Secrets 单独填一份才生效**

## 操作日志(审计)

- 所有管理员写库操作都要落到 `audit_log` 表:`log_audit(action, table_name, record_id, detail)`,`action` 用 `insert`/`update`/`delete`。操作人(`admin_name`/`admin_role`)从会话取(登录时由 `admin_sidebar` 写入)
- `log_audit` **永不抛异常**,日志写失败也不能拖垮正常增删改;新增写库点时记得补一次调用
- `events` 的增删改已在 `database.py` 里自动记日志,**别在页面里重复记**;其它表(`schedule`/`event_links`/`images` 等)的写操作目前在各页面手动调 `log_audit`
- 「🧾 操作记录」页(`pages/13_🧾_操作记录.py`)展示最近记录,**仅最终管理员(`is_super_admin`)可见**,页内用 `st.stop()` 拦住非最终管理员

## 新闻页(`pages/3_📰_新闻.py`)约定

- 筛选栏支持:人物、**按日期检索**(`day_filter`,留空=不限,选中只看当天发布)、显示条数、标题关键词。日期检索经 `get_news(day=...)` 实现,按 `published_at` 当天 `[当天 00:00, 次日 00:00)` 范围过滤(兼容带时间戳存储);筛选条件(含日期)都并入分页重置 key,变更自动回第 1 页
- `get_news` 的 `keyword` 用 `or_(title.ilike,source.ilike)` 同时匹配**标题或来源**(不搜摘要)。专访常拿引言当标题、不含媒体/人名,只搜标题会漏,搜来源(如 `society`/`parismatch`)才定位得到
- **引言式标题挂来源**:新闻列表渲染时,若标题**既不含人名(attal/séjourné)也不含刊名**,自动在标题前挂来源(显示成 `Society：「Je ne fais pas…」`),否则一眼认不出是谁的专访。只改显示、不动库里存的原始 `title`,对已入库数据立即生效
- **新闻来源 = `utils/news_fetcher.py` 的 `MEDIA_FEEDS`(写死的 RSS 列表)+ 三条 Google News 按人名搜索 + attalpresident.fr**。网页/定时任务都走 `collect_news()`,**没在源列表里的媒体抓不到**——「某篇没进来」先查它的 RSS 在不在 `MEDIA_FEEDS`
- **覆盖单人专访,不只两人合体**:`_detect_person` 单独出现 "attal" 就判 `Gabriel Attal`、单独 "séjourné/sejourne" 判 `Stéphane Séjourné`、同现判 `S&A`;**标题或摘要不含任一人名的条目直接丢弃**。所以源里混进的无关报道会被过滤,放心加宽源
- 源除了主流报纸/电视/广播,还专门有一个**「杂志 / people」分区**(Society、Paris Match、VSD、Public、Closer、L'Obs People、Télérama、Les Inrocks、Vanity Fair、GQ 等)——人物专访、关系类内容多出在这里,靠人名过滤后入库
- **加新源前必须先实测 RSS 真能返回 entries**(法媒 RSS 地址换得勤、很多 `/feed`、`/rss.xml` 已失效返回空);死链别加进列表,白占位还拖慢抓取、污染日志。Society 当前可用地址是 `https://www.society-magazine.fr/feed/`
- `collect_news()` **顺序抓**约 40 个源,整跑约 60s;页面「抓取最新新闻」按钮会转约 1 分钟。要提速就改成并发(尚未做)

## 往期新闻页(`pages/10_📜_往期新闻.py`)约定

- 历史新闻统一以 `category='historical'` 存进同一张 `news` 表;页面只读 `category='historical'` 的记录,不和当期新闻混。两个导入入口都按人物+日期范围**按月**导入,`id` 取 url 的 md5、幂等可重跑补齐
- **首选:Google News 导入(`collect_historical_google`,主要出法语)**。与每日新闻同一套 Google 抓取,`hl=fr&gl=FR&ceid=FR:fr` + 日期算子 `after:`/`before:`(区间 `[after, before)`,按月查时 before 取下月 1 号覆盖整月)。**限流远比 GDELT 宽松**,每月上限约 100 条。来源优先取 `<source>` 发布商域名(`lemonde.fr`)、回退显示名;批量回填用 `_decode_gnews_url(..., resolve_http=False)` 只做快速 base64 解码(解不出就留 google 跳转链,点开仍可跳)。**这是解决「往期只有英语」的正解**——GDELT 的 `sourcecountry:FR` 按媒体注册国筛、会混进 connexionfrance/thelocal 这类法国本地英文媒体
- **备选:GDELT 导入**(免费全球新闻存档),保留作补充。**GDELT 用法的三条铁律**(踩过的坑,别再犯):
  - **限流极严:请求间隔必须 ≥5 秒**,违规直接 429。导入循环用闭包 `gdelt_get` 统一节流到 5.5s/请求;一旦被限流,惩罚会持续好几分钟。代价是跨多月导入耗时几分钟(有进度条)
  - **过滤算子要内联进 query**,写成 `query=...+sourcecountry:FR` / `sourcelang:english`;当成 `&sourcecountry=`/`&sourcelang=` URL 参数传会被 GDELT **静默无视**,拉回全球噪音而非法国媒体
  - 每月分两轮抓:① `sourcecountry:FR` 信任 GDELT 国别标签直收法媒,**不再按域名二次过滤**(否则误杀 connexionfrance.com/thelocal.fr 等 .com 法媒);② `sourcelang:english` 仅保留 `MAJOR_ENGLISH_DOMAINS` 白名单大媒体
- 429/失败次数会汇总后 `st.warning` 提示用户(别再像旧代码那样 `if not resp.ok: continue` 静默吞掉),失败时同范围重跑即可补齐
- 列表按 `_norm_title`(标题前 8 词排序)聚合多来源同一报道,主条目取来源质量最高的(.fr > 英语白名单 > 其它)

## 行程日历页(`pages/11_📆_行程日历.py`)约定

- 左栏 SS 行程来自 GitHub ICS 文件(实时解析,不入库),右栏 GA 行程来自 `schedule` 表;两者数据形状不同(SS 用 `date`,GA 用 `event_date`)
- **行程一键收入大事记**:管理员模式下,已发生(`past`/`ongoing`)的行程卡片右侧有「⬆️ 收入大事记」按钮(`st.columns` 加 `vertical_alignment="center"` 让按钮与多行卡片垂直居中),点开弹窗(`_import_to_timeline`)预填原文。行程原文多为法/英,**靠管理员手动译成中文再存**(刻意不接翻译 API),保存走 `add_event` 写入 `events`。类型标签默认 `🗓️ 日常行程`(`_IMPORT_TAG_OPTIONS` 列首即默认),可手动改成 `⭐ 重要行程/事件`、`📣 重大宣布` 等
- 跳过 AN 议会预测条目:`description` 含 `[AN_AUTO]` 的(只是按周几规律推测、非确定行程)不显示收录按钮
- 保存前按 `source_url` 查重并黄字提示(不强制拦截);两人同框时可在弹窗里把 person 改成 `S&A`

## 约定

- 界面文案是中文(部分法语原文保留);代码注释用中文
- 涉及两人合体的内容,person 字段用 `"S&A"`,这是档案里最重要的分类
- requirements.txt 锁定大版本上界,防止 Streamlit Cloud 重新部署时装到不兼容新版——加依赖时保持这个写法
- 改样式优先用 app.py 里已有的 CSS 变量(`--cb`/`--t1` 等),别在页面里写死颜色
