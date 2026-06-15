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
  - `database.py` — Supabase 客户端和查询封装(所有页面共用)
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

主要表:`news`(新闻)、`schedule`(行程)、`events`(大事记)、`images`(图库)、`files`(上传文件)。
凭据在 `.streamlit/secrets.toml`(不进 git);页面端经 `utils/database.py` 访问,scripts/ 自己读同一个 secrets 文件。

## 大事记页面(`pages/1_📅_大事记.py`)约定

- 一条大事记自带 `tag`(类型标签),并可挂多条 `event_links`(相关内容:新闻、IG、推文、视频等),后者存在 `event_links` 表,启用了 RLS,**必须用 service key(`get_supabase_admin`)才能读写**
- 视频略缩图:`source_url` 本身是视频、或 `event_links` 里的链接是视频时,自动调 `video_thumb_html` 出可点击略缩图(卡片正文 + 相关内容两处)
- 类型标签是**两级**结构:Bilibili 不是顶层类型,而是「🎙️ 采访」的平台子集(B站永远不是第一手源,但常托管采访)。存库格式 `🎙️ 采访 · 📺 Bilibili`,用 `split_event_tag` / `join_event_tag` 拆拼。事件表单顶层选项用 `EVENT_TAG_OPTIONS`(不含 Bilibili)+ 并排的 `PLATFORM_OPTIONS`;**筛选和配色都按主类型归并**(选「采访」能筛到带平台的条目),并兼容旧的独立 `📺 Bilibili` 数据(展示照旧,编辑时自动转成新格式)
- 注意 `event_links` 的类型选择器仍用完整 `TAG_OPTIONS`(保留顶层 Bilibili —— 那里作为「平台」是合理的),别和事件类型混为一谈
- `st.form` 内控件不能联动(选完才提交),所以「采访平台」下拉始终显示、提示「仅采访时生效」,选别的类型时平台值会被忽略

## 约定

- 界面文案是中文(部分法语原文保留);代码注释用中文
- 涉及两人合体的内容,person 字段用 `"S&A"`,这是档案里最重要的分类
- requirements.txt 锁定大版本上界,防止 Streamlit Cloud 重新部署时装到不兼容新版——加依赖时保持这个写法
- 改样式优先用 app.py 里已有的 CSS 变量(`--cb`/`--t1` 等),别在页面里写死颜色
