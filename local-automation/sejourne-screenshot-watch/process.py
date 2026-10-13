#!/usr/bin/env python3
"""
Séjourné 行程截图 → Supabase(schedule / images)驱动脚本

由同目录的 run.sh(launchd)调用。和 Attal 那套的区别:Claude 在这里**只负责看图、
输出 JSON**,入库、日期校验、挪文件全在本脚本里确定性完成,模型不直接写库。

流程:
  1. 列出监控文件夹里的图片(跳过隐藏文件 / iCloud 未下载的占位符)
  2. HEIC 先用 macOS `sips` 转 JPEG(Read 工具不认 HEIC)
  3. headless `claude -p`(只开 Read 工具)按 PROMPT.md 解析 → JSON
  4. 校验:日期格式 + 合理窗口(相对截图保存日 -60 天 ~ +180 天),不合格 → 待人工
  5. 行程 → scripts/screenshot_to_db.py(幂等去重);照片 → scripts/photo_to_gallery.py
  6. 成功的图挪进 已入库/<日期>/,无法识别/日期可疑的挪进 待人工/;入库失败的原地保留、下次重试

退出码:0 = 正常(含"无图");1 = 有失败(run.sh 据此发告警邮件)。

用法:
  python3 process.py --watch <文件夹> --repo <sa-archive 根目录> [--dry-run]
  --dry-run:只解析、打印将要入库的内容,不写库、不挪文件
"""
import argparse
import datetime as dt
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
PROMPT_FILE = HERE / "PROMPT.md"
PERSON = "Stéphane Séjourné"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".heif"}
DONE_DIR = "已入库"
REVIEW_DIR = "待人工"
# 识别出的行程日期必须落在「截图保存日 -21 天 ~ +120 天」内,否则视为读错日期、交人工。
# (2026-10-12 Attal 那张 RMC/BFMTV 截图被读成了 08-27 —— 比保存日早 46 天 —— 入库后被
#  Agenda 当作过去行程丢掉。Attal 历史上补录的过去行程最多早 ~3 周,所以下限取 -21。)
DATE_WINDOW = (-21, 120)
PHOTO_TAGS = {"官方活动", "私下照片", "新闻截图", "社媒截图", "其他"}
PHOTO_PERSONS = {"Stéphane Séjourné", "S&A"}
CLAUDE_TIMEOUT = 600
CLAUDE_TRIES = 3


def log(msg):
    print(msg, flush=True)


def find_claude():
    """每次调用都重新解析(Claude.app 自动升级会改版本目录,缓存的旧路径会 exit 127)。"""
    override = os.environ.get("CLAUDE_BIN", "").strip()
    if override:
        return override
    found = shutil.which("claude")
    if found:
        return found
    roots = [pathlib.Path.home() / "Library/Application Support/Claude/claude-code",
             pathlib.Path.home() / ".claude/local"]
    cands = []
    for root in roots:
        cands += [p for p in glob.glob(str(root / "**/claude"), recursive=True)
                  if os.path.isfile(p) and os.access(p, os.X_OK)]
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


def list_images(watch):
    imgs, pending = [], []
    for p in sorted(watch.iterdir()):
        if p.is_dir():
            continue
        if p.name.startswith(".") and p.name.endswith(".icloud"):
            pending.append(p)       # iCloud 还没下载到本机的占位符
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() in IMAGE_EXTS:
            imgs.append(p)
    return imgs, pending


def readable_copy(img, tmpdir):
    """HEIC/HEIF → JPEG(macOS sips);其余格式原样使用。"""
    if img.suffix.lower() not in (".heic", ".heif"):
        return img
    out = pathlib.Path(tmpdir) / (img.stem + ".jpg")
    subprocess.run(["sips", "-s", "format", "jpeg", str(img), "--out", str(out)],
                   check=True, capture_output=True)
    return out


def build_prompt(entries):
    listing = "\n".join(
        f'- file: "{e["name"]}" | path: {e["read_path"]} | 截图保存时间: {e["saved"]}'
        for e in entries
    )
    today = dt.date.today().isoformat()
    return PROMPT_FILE.read_text(encoding="utf-8").replace("{{TODAY}}", today) \
        .replace("{{FILES}}", listing)


def call_claude(prompt):
    last_err = ""
    for attempt in range(1, CLAUDE_TRIES + 1):
        claude = find_claude()
        if not claude:
            raise RuntimeError("找不到 claude 可执行文件(可在 .env 里设 CLAUDE_BIN)")
        if attempt > 1:
            log(f"↻ headless claude 第 {attempt} 次重试(上次:{last_err[:200]})")
            time.sleep(attempt * 10)
        try:
            r = subprocess.run(
                [claude, "-p", "--model", "claude-sonnet-4-6",
                 "--allowedTools", "Read",
                 "--disallowedTools", "Bash,Write,Edit,WebFetch,WebSearch"],
                input=prompt, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            last_err = f"超时 {CLAUDE_TIMEOUT}s"
            continue
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
        last_err = f"exit {r.returncode}: {(r.stderr or r.stdout).strip()}"
    raise RuntimeError(f"headless claude 失败 {CLAUDE_TRIES} 次:{last_err[:500]}")


def parse_json(text):
    """取模型输出里最外层的 JSON 对象(容忍 ```json 围栏和前后废话)。"""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"模型输出里没有 JSON:{text[:300]}")
    return json.loads(m.group(0))


def check_date(s, saved_date):
    try:
        d = dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        return f"日期格式不对:{s!r}"
    delta = (d - saved_date).days
    if not (DATE_WINDOW[0] <= delta <= DATE_WINDOW[1]):
        return f"日期 {s} 距截图保存日 {saved_date} 相差 {delta} 天,疑似读错"
    return None


def run_script(repo, args, stdin=None):
    r = subprocess.run([sys.executable, str(repo / "scripts" / args[0]), *args[1:]],
                       input=stdin, capture_output=True, text=True, cwd=str(repo))
    out = (r.stdout + r.stderr).strip()
    if out:
        log("    " + out.replace("\n", "\n    "))
    if r.returncode != 0:
        raise RuntimeError(f"{args[0]} exit {r.returncode}")


def move(img, watch, sub):
    dest = watch / sub
    if sub == DONE_DIR:
        dest = dest / dt.date.today().isoformat()
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / img.name
    if target.exists():
        target = dest / f"{img.stem}_{int(time.time())}{img.suffix}"
    shutil.move(str(img), str(target))


def handle_file(f, entry, repo, watch, dry):
    """处理一张图的解析结果。返回 'done' / 'review' / 'failed'。"""
    name, saved_date, img = entry["name"], entry["saved_date"], entry["path"]
    kind = f.get("kind")
    if kind == "schedule":
        rows, problems = [], []
        for it in f.get("items") or []:
            title = (it.get("title") or "").strip()
            err = check_date(it.get("event_date"), saved_date) or (None if title else "缺标题")
            if err:
                problems.append(err)
                continue
            rows.append({
                "person": PERSON,
                "event_date": it["event_date"],
                "title": title,
                "location": (it.get("location") or "").strip(),
                "description": (it.get("description") or "截图").strip(),
                "source_url": (it.get("source_url") or "").strip(),
            })
        for p in problems:
            log(f"  ⚠️ {name}: {p}")
        if not rows:
            log(f"  → {name}: 没有可入库的行程,放进 {REVIEW_DIR}/")
            return "review"
        for r in rows:
            log(f"  📅 {name}: {r['event_date']} · {r['title']} · {r['description']}")
        if not dry:
            run_script(repo, ["screenshot_to_db.py"],
                       stdin=json.dumps({"schedule": rows}, ensure_ascii=False))
        # 一张图里有的行程合格、有的日期可疑:合格的已入库,图仍交人工复核剩下的
        return "review" if problems else "done"
    if kind == "photo":
        ph = f.get("photo") or {}
        date = ph.get("date") or saved_date.isoformat()
        if check_date(date, saved_date):
            date = saved_date.isoformat()
        tag = ph.get("tag") if ph.get("tag") in PHOTO_TAGS else "社媒截图"
        person = ph.get("person") if ph.get("person") in PHOTO_PERSONS else PERSON
        title = (ph.get("title") or "Stéphane Séjourné").strip()
        log(f"  🖼️ {name}: 图库 · {date} · {person} · {tag} · {title}")
        if not dry:
            run_script(repo, ["photo_to_gallery.py", str(img), "--title", title,
                              "--person", person, "--tag", tag, "--date", date,
                              "--note", (ph.get("note") or "截图管道 · Séjourné").strip()])
        return "done"
    log(f"  ❓ {name}: 无法识别({f.get('reason') or kind}),放进 {REVIEW_DIR}/")
    return "review"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    watch, repo = pathlib.Path(a.watch), pathlib.Path(a.repo)

    imgs, pending = list_images(watch)
    if pending:
        log(f"⏳ {len(pending)} 个文件还没从 iCloud 下载到本机,下次再处理")
        for p in pending:
            try:   # 触发 iCloud 下载;brctl 不在也不影响主流程
                subprocess.run(["brctl", "download", str(p)], capture_output=True, timeout=30)
            except Exception:
                pass
    if not imgs:
        log("无图")
        return 0
    log(f"发现 {len(imgs)} 张图:{', '.join(p.name for p in imgs)}")

    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        entries = {}
        for p in imgs:
            saved = dt.datetime.fromtimestamp(p.stat().st_mtime)
            try:
                read_path = readable_copy(p, tmp)
            except Exception as e:
                log(f"  ⚠️ {p.name}: 转码失败({e}),放进 {REVIEW_DIR}/")
                if not a.dry_run:
                    move(p, watch, REVIEW_DIR)
                continue
            entries[p.name] = {"name": p.name, "path": p, "read_path": read_path,
                               "saved": saved.strftime("%Y-%m-%d %H:%M (%A)"),
                               "saved_date": saved.date()}
        if not entries:
            return 0

        data = parse_json(call_claude(build_prompt(list(entries.values()))))
        results = {f.get("file"): f for f in data.get("files", []) if isinstance(f, dict)}

        for name, entry in entries.items():
            f = results.get(name)
            if f is None:
                log(f"  ❓ {name}: 模型没返回这张图的结果,下次重试")
                continue
            try:
                outcome = handle_file(f, entry, repo, watch, a.dry_run)
            except Exception as e:
                log(f"  ❌ {name}: 入库失败({e}),原地保留下次重试")
                failed += 1
                continue
            if not a.dry_run:
                move(entry["path"], watch, DONE_DIR if outcome == "done" else REVIEW_DIR)

    log("完成" + (f",{failed} 张失败" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
