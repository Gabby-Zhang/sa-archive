---
name: sejourne-missions
description: 更新和分析 Stéphane Séjourné 的欧委会出差报销表(Missions),维护档案馆「塞若内行程汇总」页(app_pages/14_✈️_出差地图.py)。用户发来新的 Missions xlsx、说"报销表更新了/出差记录公布了"、要统计巴黎行程/住宿费/周几、要和日历对照、要写出差年终总结文案时用。
---

# Séjourné 出差报销表(Missions)

## 数据从哪来

- 欧委会每两个月公布一次委员出差费用。入口:他的委员主页 → **Meetings and missions** → "Missions of Executive Vice-President Séjourné",页面是 `https://ec.europa.eu/transparency-initiative/meetings/mission.do?host=d8fba42d-8cc3-42c8-b1f1-e07d9b2ee8ea`(`period=2026_3` 这类参数 = 第几期,两个月一期)。可下载 xlsx,**每份都是上任(2024-12)以来的全量**,文件名形如 `Missions_of_Executive_Vice-President_Stephane_Sejourne_published_on_23_10_2026.xlsx`
- **云端会话连不上 ec.europa.eu / commission.europa.eu**(DNS 失败),必须让用户自己下载 xlsx 发过来。同一页下载多次得到的几个文件内容相同,用一个即可
- 列:Date from / Date to(DD/MM/YYYY,整趟起止日)/ Location(逗号分隔,顺序≈行程顺序)/ Purpose(法语)/ Context(佐证链接)/ Travel / Accommodation / Daily allowances / Miscellaneous / Comments
- Comments 里出现 "Air taxis are authorised…" = 这趟坐了包机(费用是机上人均),目前都是**全体委员随主席出访**(基辅、格但斯克、奥胡斯、拉纳卡)
- 同一人主页还有 Declaration of Interests(DOI,利益申报,xml/pdf)——不是报销表

## 更新流程(新报销表来了)

1. 分支:从最新 main 起(`git checkout -B <分支> origin/main`;上一个 PR 已合并就别在旧历史上叠)
2. 转换:`python3 scripts/missions_to_json.py <xlsx>`
   - 报 "没有坐标" → 在 `utils/missions.py` 的 `CITIES` 补 `"英文地名": ("中文名", 纬度, 经度)`(地名按 xlsx 原样拼写)
   - 报 "没写所在国家" → 补 `CITY_COUNTRY`;提示 "不会标国名" → 想在地图上标就在 `COUNTRY_LABELS` 补位置(`far=True` 表示只在全球视图标)。Luxembourg 是故意不标的(太小、压在巴黎的线下面)
3. 补中文摘要:新条目 `fr=true`,`other` 里是法语原文。逐条改写后把 `fr` 改成 `false`:
   - 经过巴黎的:`paris` = 只写巴黎那部分做了什么;`other` = 其他各站做了什么(只去巴黎的留空)
   - 不经过巴黎的:`paris` = null,`other` = 事由
   - 风格:中文短句、用"；"分隔,"会见 X、Y；出席 Z"。人名机构保留原文(Doctolib、AFEP、Choose France…),部长级写职务不写名
   - **Location 顺序和 Purpose 写的顺序不一致时**(例:2026-05-18 地点写 "Strasbourg, Paris",事由是先巴黎→斯堡→回巴黎),手改 `stops` 并加 `"stops_fixed": true`,重跑脚本不会被覆盖;有疑点写进 `note`
4. 对日历:`python3 scripts/missions_calendar_check.py --since <上次更新到的日期>`
   - 读 sejourn-calendar 的公开 ICS,列出每趟出差期间的单场会议;地点含 Paris 的日期就是 `calp`(日历确认在巴黎的日子)。`--apply` 写进 calp 为空的条目
   - **⚠️ 同日多地**要人工判断:透明度登记处地点会填错(2026-04-20 Eurofer 写巴黎,当天他在汉诺威 → 不算巴黎,写 note)
   - ICS 里 "Mission:" 开头的事件就是同一份报销数据,脚本会报两边对不上的条目(日历 DTEND 按 ICS 惯例晚一天,不是错)
5. 验证:用 `streamlit.testing.v1.AppTest` 跑页面(需 `PYTHONPATH=仓库根`),切三个时间段 × 两个地图范围 × 只看巴黎,确认无异常、数字对得上;要截图就 `streamlit run` + Playwright。**沙盒连不上 cdn.plot.ly**,地图底图截不出来:`npm pack sane-topojson@4.0.0` 解出 `world_110m.json`,Playwright 里 `page.route(/cdn\.plot\.ly\/.*\.json/, …)` 换成本地文件
6. 页面上 `PERIODS` 只有 "2026 上半年 / 2024.12–2025 / 全部",新到 2026 下半年时加一档
7. PR → 合并。**改了 `utils/` 下任何文件,合并后提醒用户去 Streamlit Cloud 后台 Reboot app**,否则导航/标题显示成 `nav_missions`、`missions_title` 这种原始 key

## 常用统计口径(用户问过的)

- **经过巴黎**:`stops` 含 Paris。细分 `role`:只去巴黎 / 最后回巴黎 / 巴黎出发·回巴黎 / 从巴黎出发 / 途经巴黎(`utils/missions.py` 的 `paris_role`)
- **住宿 €0**:只去巴黎的出差住宿费全部为 0(含连住 4 晚的),多城市行程只付其他城市的酒店(如斯特拉斯堡约 €403)。可作"住在巴黎自己家"的旁证;其他城市偶有 0(若杜瓦涅研讨会、2025-04 华沙、哥本哈根,东道主包住或当日返回)
- **周几**:报销表只有整趟起止日,"周几"指起止日,别说成"那天在巴黎"。2026 上半年在巴黎结束的 8 趟里 6 趟周五结束;只去巴黎的多为周四→周五
- **里程**:每趟按「布鲁塞尔 → 各站 → 布鲁塞尔」直线距离相加(`trip_km`),是估算;布鲁塞尔—巴黎直线 264 km(用户 2025 文案里用的是 308 km 公路距离)
- **天数**:把起止日之间每天都算(含周末)
- 从布鲁塞尔回家(私人通勤)不在报销表里;每日补贴只算公务日,跨周末那趟补贴偏低
- 留意的异常:2026-02 斯特拉斯堡全会(9–12 日)表里没有对应行程

## 用户偏好(做交付物时)

- Excel:英文、日期英国格式。openpyxl 的 `number_format` 用**小写** `dd/mm/yyyy`(大写 `DD/MM/YYYY` 在用户的表格软件里显示成 "DD/01/YYYY")
- 网页/PDF:白底、固定浅色主题,加 `print-color-adjust: exact`,不然导出 PDF 颜色丢失
- 地图:巴黎相关一律**粉色**;巴黎标记 = **法国国旗竖条(蓝|白|红)爱心**、大小与城市点相当;布鲁塞尔 = **欧盟旗那样的金黄星 + 蓝边**;法国国土铺浅粉;底图海洋浅蓝、陆地米白,别用纯灰;英文国名;欧洲视图经纬度范围按约 2:1 取,否则宽屏两侧留白
- 改界面先给预览:Streamlit 页面不能脱离档案馆运行,可用 AppTest 把各筛选组合的输出(plotly spec、markdown、metric)导出,拼成一个静态 Artifact(plotly.min.js 用 `files` 一起发布、topojson 通过 `window.PlotlyGeoAssets` 内联)
- 用户没说怎么做之前别急着整理/生成文件,先确认要什么
- **档案馆是公开可看的**:"家在巴黎"这类推断、"那里有你的爱人"这类文案只发在聊天里,不写进档案馆页面

## 文案模板(年终总结风)

用户要的风格:分屏(P1、P2…= 第几屏),每屏一个大数字 + 一两句,结尾落到巴黎和爱人,emoji 🇫🇷🗼🌍🏠❤️🤍💙。2026 上半年版的骨架:

> 2026 年上半年，你出差 22 次，其中 17 次都绕不开巴黎🇫🇷🗼
> 从华盛顿到蒙特利尔，从拉纳卡到汉诺威，半年里你飞过约 6.8 万公里，足够绕地球一圈半🌍
> 而在巴黎的每一晚，住宿费都是 0，因为那里本来就是家🏠
> 步履不停，但大多数周五，归途都指向巴黎；那里永远有你的爱人❤️🤍💙

可用的数字:第一趟/最后一趟去哪、出差天数、最远城市、最长一趟、最常出发的星期、最常回巴黎的月份、第二名城市(斯特拉斯堡)、包机次数、有趣的一趟(如安纳西动画节)。数字写进文案前在 JSON 上现算,口径见上节。
