"""页面共享的 UI 工具函数。"""


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
