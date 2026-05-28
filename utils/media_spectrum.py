"""法国媒体政治立场数据 — 与媒体光谱页面保持同步"""

import unicodedata

# score: -2极左  -1左  0中  1右  2极右
MEDIA_SPECTRUM = [
    {"key": "humanite",          "score": -2.0, "label": "极左", "label_en": "Far Left",     "color": "#c0392b"},
    {"key": "mediapart",         "score": -1.5, "label": "左",   "label_en": "Left",         "color": "#e74c3c"},
    {"key": "liberation",        "score": -1.2, "label": "左",   "label_en": "Left",         "color": "#e74c3c"},
    {"key": "lacroix",           "score": -1.0, "label": "左",   "label_en": "Left",         "color": "#e74c3c"},
    {"key": "canard",            "score": -0.8, "label": "左",   "label_en": "Left",         "color": "#e74c3c"},
    {"key": "voixdunord",        "score": -0.8, "label": "左",   "label_en": "Left",         "color": "#e74c3c"},
    {"key": "obs",               "score": -0.8, "label": "左",   "label_en": "Left",         "color": "#e74c3c"},
    {"key": "monde",             "score": -0.5, "label": "中左", "label_en": "Center-Left",  "color": "#e8a838"},
    {"key": "francetvinfo",      "score": -0.3, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "franceinfo",        "score": -0.3, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "france2",           "score": -0.3, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "ouestfrance",       "score":  0.0, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "bfmtv",             "score":  0.0, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "politico",          "score":  0.0, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "parisien",          "score":  0.2, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "lci",               "score":  0.2, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "lexpress",          "score":  0.5, "label": "中间", "label_en": "Center",       "color": "#7EC8A4"},
    {"key": "opinion",           "score":  0.8, "label": "中右", "label_en": "Center-Right", "color": "#3498db"},
    {"key": "lesechos",          "score":  0.8, "label": "中右", "label_en": "Center-Right", "color": "#3498db"},
    {"key": "sudouest",          "score":  1.0, "label": "右",   "label_en": "Right",        "color": "#3498db"},
    {"key": "lepoint",           "score":  1.0, "label": "右",   "label_en": "Right",        "color": "#3498db"},
    {"key": "figaro",            "score":  1.5, "label": "右",   "label_en": "Right",        "color": "#1a5276"},
    {"key": "cnews",             "score":  1.8, "label": "极右", "label_en": "Far Right",    "color": "#7f1d1d"},
    {"key": "valeursactuelles",  "score":  2.0, "label": "极右", "label_en": "Far Right",    "color": "#7f1d1d"},
]

_UNKNOWN = {"score": None, "label": "未知", "label_en": "Unknown", "color": "#666"}

LEAN_EMOJI = {
    "极左": "⬅️⬅️",
    "左":   "⬅️",
    "中左": "↖️",
    "中间": "⏺️",
    "中右": "↗️",
    "右":   "➡️",
    "极右": "➡️➡️",
    "未知": "",
}


def _norm(s: str) -> str:
    """标准化媒体名称用于匹配（去重音、去标点、小写）"""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "").replace(".", "").replace("-", "").replace("'", "").replace("'", "")


def get_media_info(source_name: str) -> dict:
    """
    根据媒体名称返回政治立场信息。
    返回: {"score", "label", "label_en", "color"}
    """
    norm = _norm(source_name)
    for entry in MEDIA_SPECTRUM:
        if entry["key"] in norm:
            return entry
    return _UNKNOWN
