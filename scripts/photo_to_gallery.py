#!/usr/bin/env python3
"""
照片入图库 — 供本机截图 agent 调用。

用法：
  python3 scripts/photo_to_gallery.py <图片路径> --title "说明" \
      --person "S&A" --tag "社媒截图" [--date 2026-06-10] [--note "IG @xxx"]

流程：上传到 Supabase Storage 的 gallery bucket（公开），
拿到公开 URL 后写入 images 表（drive_url 字段存任意 URL 均可正常显示）。
"""
import argparse
import mimetypes
import pathlib
import sys
import uuid
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


def _load_creds():
    secrets_path = pathlib.Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        import toml
        s = toml.load(str(secrets_path))
        return s["SUPABASE_URL"], (s.get("SUPABASE_SERVICE_KEY") or s["SUPABASE_KEY"])
    import os
    return os.environ["SUPABASE_URL"], (os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="图片文件路径")
    ap.add_argument("--title",  required=True)
    ap.add_argument("--person", default="S&A",
                    choices=["Gabriel Attal", "Stéphane Séjourné", "S&A"])
    ap.add_argument("--tag",    default="社媒截图",
                    choices=["官方活动", "私下照片", "新闻截图", "社媒截图", "其他"])
    ap.add_argument("--date",   default=date.today().isoformat())
    ap.add_argument("--note",   default="截图管道 · auto")
    args = ap.parse_args()

    img = pathlib.Path(args.image)
    if not img.exists():
        print(f"❌ 文件不存在: {img}", file=sys.stderr)
        sys.exit(1)

    url, key = _load_creds()
    from supabase import create_client
    db = create_client(url, key)

    content_type = mimetypes.guess_type(img.name)[0] or "image/png"
    ext  = img.suffix.lower() or ".png"
    path = f"{args.date}_{uuid.uuid4().hex[:8]}{ext}"

    db.storage.from_("gallery").upload(
        path=path,
        file=img.read_bytes(),
        file_options={"content-type": content_type, "upsert": "true"},
    )
    public_url = db.storage.from_("gallery").get_public_url(path)

    db.table("images").insert({
        "title":     args.title,
        "person":    args.person,
        "tag":       args.tag,
        "date":      args.date,
        "drive_url": public_url,
        "note":      args.note,
    }).execute()

    print(f"✅ 已入图库: {args.title[:50]} → {public_url}")


if __name__ == "__main__":
    main()
