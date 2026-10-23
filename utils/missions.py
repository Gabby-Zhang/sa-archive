"""SS 出差记录(欧委会 Missions 报销表)的共享数据与工具。

数据文件 data/sejourne_missions.json 由 scripts/missions_to_json.py 从官方 xlsx 生成;
「✈️ 出差地图」页和生成脚本都从这里取城市坐标和路线计算逻辑。
"""
import json
import math
import pathlib

DATA_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "sejourne_missions.json"

BASE = "Brussels"  # 工作地,每趟出差按 布鲁塞尔 → 各站 → 布鲁塞尔 估算里程

# 报销表 Location 列里的英文地名 → (中文名, 纬度, 经度)。新报销表出现新地名时在这里补
CITIES = {
    "Brussels": ("布鲁塞尔", 50.85, 4.35),
    "Paris": ("巴黎", 48.857, 2.352),
    "Milan": ("米兰", 45.46, 9.19),
    "Strasbourg": ("斯特拉斯堡", 48.58, 7.75),
    "Roissy-En-France": ("鲁瓦西", 49.00, 2.55),
    "Bucharest": ("布加勒斯特", 44.43, 26.10),
    "Stuttgart": ("斯图加特", 48.78, 9.18),
    "Davos": ("达沃斯", 46.80, 9.84),
    "Bilbao": ("毕尔巴鄂", 43.26, -2.93),
    "Luxembourg": ("卢森堡", 49.61, 6.13),
    "Jodoigne": ("若杜瓦涅", 50.72, 4.87),
    "Warsaw": ("华沙", 52.23, 21.01),
    "Gdansk": ("格但斯克", 54.35, 18.65),
    "Flamanville": ("弗拉芒维尔", 49.53, -1.87),
    "Kyiv": ("基辅", 50.45, 30.52),
    "Antwerp": ("安特卫普", 51.22, 4.40),
    "Delhi": ("新德里", 28.61, 77.21),
    "Douai": ("杜埃", 50.37, 3.08),
    "Barcelona": ("巴塞罗那", 41.39, 2.17),
    "Duisburg": ("杜伊斯堡", 51.43, 6.76),
    "Athens": ("雅典", 37.98, 23.73),
    "Vilnius": ("维尔纽斯", 54.69, 25.28),
    "Catania": ("卡塔尼亚", 37.50, 15.09),
    "Berlin": ("柏林", 52.52, 13.40),
    "Rzeszow": ("热舒夫", 50.04, 22.00),
    "Helsinki": ("赫尔辛基", 60.17, 24.94),
    "Kemi": ("凯米", 65.74, 24.56),
    "Le Bourget": ("布尔歇", 48.93, 2.43),
    "Marseille": ("马赛", 43.30, 5.37),
    "Louviers": ("卢维耶", 49.22, 1.17),
    "Aarhus": ("奥胡斯", 56.16, 10.20),
    "Ottawa": ("渥太华", 45.42, -75.70),
    "Copenhagen": ("哥本哈根", 55.68, 12.57),
    "Evian Les Bains": ("埃维昂", 46.40, 6.59),
    "Munich": ("慕尼黑", 48.14, 11.58),
    "Osaka": ("大阪", 34.69, 135.50),
    "Tokyo": ("东京", 35.68, 139.69),
    "Stockholm": ("斯德哥尔摩", 59.33, 18.07),
    "Kiruna": ("基律纳", 67.86, 20.23),
    "Madrid": ("马德里", 40.42, -3.70),
    "Dunkerque": ("敦刻尔克", 51.03, 2.38),
    "Lisbon": ("里斯本", 38.72, -9.14),
    "Bratislava": ("布拉迪斯拉发", 48.15, 17.11),
    "Rome": ("罗马", 41.90, 12.50),
    "Nice": ("尼斯", 43.70, 7.27),
    "Buenos Aires": ("布宜诺斯艾利斯", -34.60, -58.38),
    "Johannesburg": ("约翰内斯堡", -26.20, 28.05),
    "Mbombela": ("姆博姆贝拉", -25.47, 30.98),
    "Tallinn": ("塔林", 59.44, 24.75),
    "Sittard": ("锡塔德", 51.00, 5.87),
    "Larnaca": ("拉纳卡", 34.92, 33.63),
    "Washington D.C.": ("华盛顿", 38.90, -77.04),
    "Prague": ("布拉格", 50.08, 14.44),
    "Toronto": ("多伦多", 43.65, -79.38),
    "Vienna": ("维也纳", 48.21, 16.37),
    "Hannover": ("汉诺威", 52.37, 9.73),
    "Dublin": ("都柏林", 53.35, -6.26),
    "Budapest": ("布达佩斯", 47.50, 19.04),
    "Montreal": ("蒙特利尔", 45.50, -73.57),
    "Venice": ("威尼斯", 45.44, 12.32),
    "Verona": ("维罗纳", 45.44, 10.99),
    "Annecy": ("安纳西", 45.90, 6.13),
}

ROLE_LABEL = {
    "only": "只去巴黎",
    "end": "最后回巴黎",
    "both": "巴黎出发 · 回巴黎",
    "start": "从巴黎出发",
    "via": "途经巴黎",
}


def km_between(a, b):
    """两城直线(大圆)距离,公里。"""
    _, la1, lo1 = CITIES[a]
    _, la2, lo2 = CITIES[b]
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def trip_km(stops):
    path = [BASE] + stops + [BASE]
    return sum(km_between(path[i], path[i + 1]) for i in range(len(path) - 1))


def paris_role(stops):
    """巴黎在这趟行程里的位置;不经过巴黎返回 None。"""
    if "Paris" not in stops:
        return None
    if set(stops) == {"Paris"}:
        return "only"
    if stops[0] == "Paris" and stops[-1] == "Paris":
        return "both"
    if stops[-1] == "Paris":
        return "end"
    if stops[0] == "Paris":
        return "start"
    return "via"


def load_missions():
    """读 JSON,返回 (报销表标题, 行程列表);行程补上派生字段(role / km),按出发日期升序。"""
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    trips = data["missions"]
    for t in trips:
        t["role"] = paris_role(t["stops"])
        t["km"] = round(trip_km(t["stops"]))
    return data.get("source", ""), sorted(trips, key=lambda t: t["f"])
