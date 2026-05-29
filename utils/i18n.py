"""
UI 国际化（中/英）工具。
用法：from utils.i18n import t
      st.title(t("timeline_title"))
"""

_S = {
    # ── App / Sidebar ─────────────────────────────────────
    "app_title":        {"zh": "🗂️ S&A 档案馆",          "en": "🗂️ S&A Archive"},
    "light_mode":       {"zh": "☀️ 日间模式",             "en": "☀️ Light mode"},

    # ── Navigation ────────────────────────────────────────
    "nav_home":         {"zh": "首页",                    "en": "Home"},
    "nav_timeline":     {"zh": "大事记",                  "en": "Timeline"},
    "nav_news":         {"zh": "新闻",                    "en": "News"},
    "nav_schedule":     {"zh": "行程日历",                "en": "Schedule"},
    "nav_profiles":     {"zh": "人物档案",                "en": "Profiles"},
    "nav_archives":     {"zh": "往期新闻",                "en": "News Archive"},
    "nav_resources":    {"zh": "资源导航",                "en": "Resources"},
    "nav_team":         {"zh": "团队成员",                "en": "Team"},
    "nav_election":     {"zh": "选举参考",                "en": "Elections"},
    "nav_media":        {"zh": "媒体光谱",                "en": "Media Spectrum"},
    "nav_gallery":      {"zh": "图库",                    "en": "Gallery"},
    "nav_files":        {"zh": "文件存档",                "en": "File Archive"},

    # ── Common ────────────────────────────────────────────
    "all":              {"zh": "全部",                    "en": "All"},
    "person_label":     {"zh": "人物",                    "en": "Person"},
    "year_label":       {"zh": "年份",                    "en": "Year"},
    "show_count":       {"zh": "显示条数",                "en": "Show"},
    "search_label":     {"zh": "🔍 搜索关键词",           "en": "🔍 Search"},
    "search_ph":        {"zh": "输入关键词…",             "en": "Enter keywords…"},
    "no_data":          {"zh": "暂无数据",                "en": "No data"},
    "type_label":       {"zh": "类型",                    "en": "Type"},

    # ── 首页 ─────────────────────────────────────────────
    "home_subtitle":    {"zh": "Le Parcours de Séjourné et Attal — 持续建设中",
                         "en": "Le Parcours de Séjourné et Attal — ongoing"},
    "home_stats":       {"zh": "📊 档案馆概览",           "en": "📊 Archive Overview"},
    "stat_events":      {"zh": "📅 大事记条目",           "en": "📅 Timeline entries"},
    "stat_news":        {"zh": "📰 新闻条目",             "en": "📰 News items"},
    "stat_files":       {"zh": "📁 上传文件",             "en": "📁 Files"},
    "stat_images":      {"zh": "🖼️ 图库图片",            "en": "🖼️ Gallery images"},
    "home_hint":        {"zh": "👈 使用左侧导航栏切换各个板块",
                         "en": "👈 Use the left sidebar to navigate"},
    "ss_role":          {"zh": "🇪🇺 欧盟委员会执行副主席 · 工业战略专员",
                         "en": "🇪🇺 Executive VP, EU Commission · Industrial Strategy"},
    "ss_bio":           {"zh": ("1985年生，法国政治人物，复兴党（RE）创始成员之一。<br>"
                                "曾任欧洲议会议员（2019–2024）、欧洲议会复兴党团主席、"
                                "法国外交部长（2024）。<br>现任欧盟委员会执行副主席。"),
                         "en": ("Born 1985. French politician, co-founder of Renaissance (RE).<br>"
                                "Former MEP (2019–2024), President of the Renew Europe group, "
                                "Foreign Minister of France (2024).<br>"
                                "Currently Executive VP of the European Commission.")},
    "ga_role":          {"zh": "🏛️ 法国国民议会议员 · 复兴党（RE）主席",
                         "en": "🏛️ Member of the French National Assembly · President of Renaissance (RE)"},
    "ga_bio":           {"zh": ("1989年生，法国迄今最年轻的总理（2024年1月–9月）。<br>"
                                "曾任教育部长、预算部长、政府发言人。<br>"
                                "现任复兴党主席及国民议会议员（上塞纳省）。"),
                         "en": ("Born 1989. France's youngest ever Prime Minister (Jan–Sep 2024).<br>"
                                "Former Minister of Education, Budget Minister, Government Spokesperson.<br>"
                                "Currently President of Renaissance and MP for Hauts-de-Seine.")},
    "campaign_label":   {"zh": "🗳️ Attal Président · 2027年法国总统竞选账号",
                         "en": "🗳️ Attal Président · 2027 French presidential campaign"},

    # ── 大事记 ────────────────────────────────────────────
    "timeline_title":   {"zh": "📅 大事记时间轴",         "en": "📅 Timeline"},
    "timeline_caption": {"zh": "记录 Attal 与 Séjourné 的重要事件与新闻",
                         "en": "Key events and news about Attal and Séjourné"},
    "timeline_empty":   {"zh": "没有符合条件的大事记条目", "en": "No matching entries"},
    "related_links":    {"zh": "相关内容",                "en": "Related links"},
    "no_related":       {"zh": "暂无相关内容",            "en": "No related links yet"},
    "read_more":        {"zh": "查看详情",                "en": "Details"},

    # ── 新闻 ─────────────────────────────────────────────
    "news_title":       {"zh": "📰 新闻档案",             "en": "📰 News"},
    "news_caption":     {"zh": "自动抓取 + 手动添加的新闻汇总",
                         "en": "Auto-fetched and manually added news"},
    "news_fetch_btn":   {"zh": "🔄 抓取最新新闻",         "en": "🔄 Fetch latest news"},
    "news_fetch_hint":  {"zh": "点击按钮从 Google News 抓取最新报道（每次约 30–60 条）",
                         "en": "Fetch latest reports from Google News (~30–60 per run)"},
    "news_vpn":         {"zh": ("🌐 部分新闻链接来自 Google News，"
                                "在中国大陆需要开启 **VPN 全局模式** 才能正常访问。"),
                         "en": ("🌐 Some links are from Google News and may require a VPN "
                                "in mainland China.")},
    "news_showing":     {"zh": "共显示",                  "en": "Showing"},
    "news_items":       {"zh": "条新闻",                  "en": "news items"},
    "news_empty":       {"zh": "暂无新闻，点击上方「抓取最新新闻」按钮开始收集。",
                         "en": "No news yet. Click 'Fetch latest news' to start."},
    "news_original":    {"zh": "🔗 原文",                 "en": "🔗 Source"},
    "news_archived":    {"zh": "📦 存档版",               "en": "📦 Bypass Paywall"},

    # ── 行程日历 ─────────────────────────────────────────
    "schedule_title":   {"zh": "📆 行程日历",             "en": "📆 Schedule"},
    "schedule_caption": {"zh": "Séjourné 行程来自 GitHub ICS 文件 · Attal 行程由团队手动维护",
                         "en": "Séjourné schedule from GitHub ICS · Attal schedule maintained manually"},
    "schedule_ss_col":  {"zh": "🔵 Séjourné 行程",       "en": "🔵 Séjourné Schedule"},
    "schedule_ga_col":  {"zh": "🟡 Attal 行程",          "en": "🟡 Attal Schedule"},
    "sched_upcoming":   {"zh": "即将",                    "en": "Soon"},
    "sched_today":      {"zh": "今天",                    "en": "Today"},
    "sched_tomorrow":   {"zh": "明天",                    "en": "Tomorrow"},
    "sched_days":       {"zh": "天后",                    "en": "days"},
    "sched_past":       {"zh": "已结束",                  "en": "Past"},
    "sched_empty":      {"zh": "暂无日程",                "en": "No events"},
    "sched_load_err":   {"zh": "抓取失败",                "en": "Failed to load"},

    # ── 人物档案 ─────────────────────────────────────────
    "profiles_title":   {"zh": "👤 人物档案",             "en": "👤 Profiles"},
    "profiles_caption": {"zh": "家人、亲友团与个人喜好",  "en": "Family, circle & preferences"},
    "section_family":   {"zh": "👨‍👩‍👧 家人",               "en": "👨‍👩‍👧 Family"},
    "section_crew_ss":  {"zh": "🤝 普瓦捷帮",            "en": "🤝 Poitiers network"},
    "section_crew_ga":  {"zh": "🤝 亲友团",              "en": "🤝 Inner circle"},
    "section_prefs":    {"zh": "❤️ 个人喜好",            "en": "❤️ Preferences"},
    "section_links":    {"zh": "🔗 重要链接",             "en": "🔗 Key links"},
    "tab_ss":           {"zh": "🔵 Stéphane Séjourné",   "en": "🔵 Stéphane Séjourné"},
    "tab_ga":           {"zh": "🟡 Gabriel Attal",       "en": "🟡 Gabriel Attal"},

    # ── 往期新闻 ─────────────────────────────────────────
    "archives_title":   {"zh": "📜 往期新闻",             "en": "📜 News Archive"},
    "archives_caption": {"zh": "历史新闻存档 — 来自 GDELT 数据库及手动添加",
                         "en": "Historical news — from GDELT and manual entries"},
    "archives_empty":   {"zh": "暂无历史新闻。",          "en": "No archive news yet."},
    "multi_sources":    {"zh": "家媒体",                  "en": "sources"},
    "view_others":      {"zh": "查看另外",                "en": "View"},
    "more_sources":     {"zh": "家媒体的报道",            "en": "more sources"},

    # ── 媒体光谱 ─────────────────────────────────────────
    "media_title":      {"zh": "📊 媒体光谱",             "en": "📊 Media Spectrum"},
    "media_caption":    {"zh": "法国主流媒体的政治立场分布",
                         "en": "Political leaning of French media outlets"},

    # ── 文件存档 ─────────────────────────────────────────
    "files_title":      {"zh": "📁 文件存档",             "en": "📁 File Archive"},
    "files_caption":    {"zh": "书籍、传记、调查报告及相关文件",
                         "en": "Books, biographies, investigations and related documents"},
    "files_empty":      {"zh": "暂无文件。",              "en": "No files yet."},
    "file_open":        {"zh": "📂 打开",                 "en": "📂 Open"},
    "file_type_label":  {"zh": "文件类型",                "en": "File type"},
    "file_qr_view":     {"zh": "📱 查看百度网盘二维码",   "en": "📱 View Baidu Netdisk QR code"},

    # ── 图库 ─────────────────────────────────────────────
    "gallery_title":    {"zh": "🖼️ 图库",                "en": "🖼️ Gallery"},
    "gallery_caption":  {"zh": "照片、截图存档 — 图片存于 Google Drive",
                         "en": "Photos and screenshots — stored on Google Drive"},

    # ── 资源导航 ─────────────────────────────────────────
    "resources_title":  {"zh": "🔗 资源导航",             "en": "🔗 Resources"},

    # ── 团队成员 ─────────────────────────────────────────
    "team_title":       {"zh": "🏛️ 团队成员",            "en": "🏛️ Team"},

    # ── 选举参考 ─────────────────────────────────────────
    "election_title":   {"zh": "🗳️ 选举参考",            "en": "🗳️ Elections"},
}


def t(key: str) -> str:
    """根据当前语言返回对应字符串。"""
    import streamlit as st
    lang = st.session_state.get("lang", "zh")
    entry = _S.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get("zh", key)


# ── DB 内容翻译对照表（profile_items key / resources name）─────────────────
# 数据库里以中文存储，英文模式下展示英文
DB_LABEL_EN: dict[str, str] = {
    # profile_items — links section
    "欧委会官方页面":             "EU Commission page",
    "欧委会官方页面（EC）":       "EU Commission page (EC)",
    "欧委会新闻室":               "EU Commission Newsroom",
    "欧委会新闻室（每周行程）":   "EU Newsroom (weekly schedule)",
    "利益申报":                   "Asset declaration",
    "利益申报（HATVP）":          "Asset declaration (HATVP)",
    "国民议会页面":               "National Assembly page",
    "国民议会页面（AN）":         "National Assembly page (AN)",
    "复兴党官网":                 "Renaissance party website",
    "复兴党官网（RE）":           "Renaissance party (RE)",
    # resources — regular appearances
    "每周三：欧委会例会":         "Every Wednesday: EU Commission meeting",
    "每周二：一般固定 EPR 小组会":"Every Tuesday: EPR group meeting",
    "国民议会会期：每周出席":     "National Assembly sessions: weekly attendance",
    "粉丝行程追踪账号：@GAttalActu（X平台）": "Fan schedule tracker: @GAttalActu (X)",
}


def tlabel(chinese_label: str) -> str:
    """翻译 DB 里存的中文标签；英文模式下查字典，找不到则原样返回。"""
    import streamlit as st
    if st.session_state.get("lang") != "en":
        return chinese_label
    return DB_LABEL_EN.get(chinese_label, chinese_label)
