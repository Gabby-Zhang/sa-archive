"""页面共享的 UI 工具函数。"""

import re
import functools
from urllib.parse import quote


def gdrive_to_img_url(url: str) -> str:
    """把 Google Drive 分享链接转成直接可显示的图片链接。"""
    if not url:
        return ""
    # 格式1: https://drive.google.com/file/d/FILE_ID/view...
    if "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    # 格式2: https://drive.google.com/open?id=FILE_ID
    if "id=" in url:
        file_id = url.split("id=")[1].split("&")[0]
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url


# ── 视频略缩图：YouTube / 哔哩哔哩 ────────────────────────────

def youtube_id(url: str):
    """从各种 YouTube 链接里抠出 11 位视频 ID，认不出返回 None。"""
    if not url:
        return None
    m = re.search(
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)"
        r"([A-Za-z0-9_-]{11})",
        url,
    )
    return m.group(1) if m else None


def bilibili_bvid(url: str):
    """从哔哩哔哩链接里抠出 BV 号，认不出返回 None。"""
    if not url:
        return None
    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    return m.group(1) if m else None


@functools.lru_cache(maxsize=256)
def _bilibili_cover(bvid: str):
    """调 B 站 API 拿封面图，并用 weserv 代理绕过防盗链。失败返回 None（结果缓存，不重复请求）。"""
    try:
        import requests
        r = requests.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={"bvid": bvid},
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"},
            timeout=5,
        )
        pic = (r.json().get("data") or {}).get("pic", "")
        if pic:
            # B 站封面在 hdslb.com 上有 Referer 防盗链，经 weserv 代理后浏览器可直接显示
            return f"https://images.weserv.nl/?url={quote(pic, safe='')}"
    except Exception:
        pass
    return None


def video_thumb(url: str):
    """识别视频链接，返回 (略缩图URL, 平台名)；非视频或取不到封面返回 None。"""
    yid = youtube_id(url)
    if yid:
        return (f"https://img.youtube.com/vi/{yid}/hqdefault.jpg", "YouTube")
    bvid = bilibili_bvid(url)
    if bvid:
        cover = _bilibili_cover(bvid)
        if cover:
            return (cover, "Bilibili")
    return None


def video_thumb_html(url: str, width: int = 320) -> str:
    """把视频链接渲染成可点击的略缩图（带播放图标和平台角标）；非视频返回空串。"""
    info = video_thumb(url)
    if not info:
        return ""
    thumb, platform = info
    return (
        f'<a href="{url}" target="_blank" '
        f'style="display:inline-block;position:relative;text-decoration:none;margin:0.4rem 0">'
        f'<img src="{thumb}" loading="lazy" '
        f'style="width:{width}px;max-width:100%;border-radius:8px;display:block">'
        f'<span style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);'
        f'font-size:2.4rem;text-shadow:0 2px 10px rgba(0,0,0,0.65)">▶️</span>'
        f'<span style="position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,0.72);color:#fff;'
        f'padding:1px 7px;border-radius:4px;font-size:0.72rem">{platform}</span>'
        f'</a>'
    )
