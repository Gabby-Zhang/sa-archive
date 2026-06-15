# S&A 档案馆 (sa-archive)

关于 Stéphane Séjourné (SS) 和 Gabriel Attal (GA) 的中文粉丝档案站。核心是记录两人的关系与互动,政治/新闻内容是辅助背景。Streamlit 多页应用,部署在 Streamlit Cloud,数据存 Supabase。

## 常用命令

```bash
streamlit run app.py        # 本地启动(http://localhost:8501)
pip install -r requirements.txt
```

没有测试套件;改完靠本地跑起来肉眼验证。推送到 GitHub 后 Streamlit Cloud 自动重新部署。

## 目录结构

- `app.py` — 入口:页面配置 + 全局 CSS(主题变量、中文字形缩放、手机端适配)。改全站样式在这里
- `pages/` — 各页面,文件名格式 `序号_emoji_中文名.py`,序号决定侧边栏顺序
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
- 注意 `event_links` 的类型选择器仍用完整 `TAG_OPTIONS`(保留顶层 Bilibili —— 那里作为「平台」是合理的),别和事件类型混为一谈
- `st.form` 内控件不能联动(选完才提交),所以「采访平台」下拉始终显示、提示「仅采访时生效」,选别的类型时平台值会被忽略

## 操作日志(审计)

- 所有管理员写库操作都要落到 `audit_log` 表:`log_audit(action, table_name, record_id, detail)`,`action` 用 `insert`/`update`/`delete`。操作人(`admin_name`/`admin_role`)从会话取(登录时由 `admin_sidebar` 写入)
- `log_audit` **永不抛异常**,日志写失败也不能拖垮正常增删改;新增写库点时记得补一次调用
- `events` 的增删改已在 `database.py` 里自动记日志,**别在页面里重复记**;其它表(`schedule`/`event_links`/`images` 等)的写操作目前在各页面手动调 `log_audit`
- 「🧾 操作记录」页(`pages/13_🧾_操作记录.py`)展示最近记录,**仅最终管理员(`is_super_admin`)可见**,页内用 `st.stop()` 拦住非最终管理员

## 行程日历页(`pages/11_📆_行程日历.py`)约定

- 左栏 SS 行程来自 GitHub ICS 文件(实时解析,不入库),右栏 GA 行程来自 `schedule` 表;两者数据形状不同(SS 用 `date`,GA 用 `event_date`)
- **行程一键收入大事记**:管理员模式下,已发生(`past`/`ongoing`)的行程卡片右侧有「⬆️ 收入大事记」按钮,点开弹窗(`_import_to_timeline`)预填原文。行程原文多为法/英,**靠管理员手动译成中文再存**(刻意不接翻译 API),保存走 `add_event` 写入 `events`
- 跳过 AN 议会预测条目:`description` 含 `[AN_AUTO]` 的(只是按周几规律推测、非确定行程)不显示收录按钮
- 保存前按 `source_url` 查重并黄字提示(不强制拦截);两人同框时可在弹窗里把 person 改成 `S&A`

## 约定

- 界面文案是中文(部分法语原文保留);代码注释用中文
- 涉及两人合体的内容,person 字段用 `"S&A"`,这是档案里最重要的分类
- requirements.txt 锁定大版本上界,防止 Streamlit Cloud 重新部署时装到不兼容新版——加依赖时保持这个写法
- 改样式优先用 app.py 里已有的 CSS 变量(`--cb`/`--t1` 等),别在页面里写死颜色
