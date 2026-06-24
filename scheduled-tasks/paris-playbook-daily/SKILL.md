---
name: paris-playbook-daily
description: Daily: read Politico Paris Playbook emails → extract Attal/Séjourné schedule & news → insert into Supabase
---

> ⚠️ **已停用 / 仅作 Gmail-MCP 手动兜底。** 这套(Claude app 内置定时任务 + Gmail 连接器)
> 长期靠桌面 app 当时开着才触发,Mac 早上多半睡眠/没开 app,导致每天 07:07 静默漏跑、
> 半个月只成功三四次。**已迁到 launchd**(系统级、扛睡眠、关 app 也跑),走 IMAP 取信而非
> Gmail 连接器:见同目录 `SKILL_launchd.md` + `~/.claude/local-automation/paris-playbook-daily/run.sh`。
> 本文件保留:① 当你在有 Gmail 连接器的交互式会话里想手动补跑某天时仍可用;② 记录原始流程。

You are a data extraction agent for a French political archive (sa-archive) tracking Gabriel Attal and Stéphane Séjourné.

**Objective:** Process recent Politico Paris Playbook emails from Gmail and insert relevant schedule entries and news items into Supabase.

---

## Step 1 — Find recent Playbook emails

Use the Gmail MCP tool `search_threads` with:
- query: `from:playbookparis@politico.eu newer_than:2d`
- pageSize: 5

For each thread found, fetch full content with `get_thread` (messageFormat: FULL_CONTENT).

**IMPORTANT — these emails are ~120KB and will overflow the token limit.** `get_thread`
will almost always return an error like:

```
Error: result (127,762 characters) exceeds maximum allowed tokens.
Output has been saved to /Users/.../tool-results/mcp-...-get_thread-<N>.txt
```

This is expected. **Do NOT give up.** Copy the saved file path from the error message and
run the extractor script on it (it un-escapes the multiply-escaped HTML, strips tags, and
— in its **default compact mode** — prints ONLY the parts you need):

```bash
python3 /Users/junruzhang/.claude/scheduled-tasks/paris-playbook-daily/extract_playbook.py "<SAVED_FILE_PATH>"
```

The script prints, per message (output is small — a few hundred bytes to ~3KB):
- `--- AGENDA · ATTAL/SÉJOURNÉ ---` : only the agenda sentences where Attal/Séjourné are the
  **subject**, each prefixed with its day `[当天]` / `[周六]` / `[周日]` (already computed for you;
  trailing "Il s'adresse à la presse à …" continuations with the time are merged in)
- `--- NEWS 相关段 ---` : only the body sentences mentioning Attal/Séjourné (± 1 sentence context)

**Read the script's stdout DIRECTLY.** It is already small and filtered — do NOT `cat` the
saved file, do NOT re-pipe the script output into another file, do NOT grep it again. Those
extra round-trips on the raw 35KB+ dump are what burned the run's budget on 2026-06-19 and
killed it before the insert step (nothing got inserted that day). One extractor call per file,
then go straight to Step 2.

(Debug only: append `--full` to dump the complete agenda + body. You normally never need this.
If `get_thread` ever returns content inline for a small email, save it to `/tmp/*.json` and run
the script on that instead.)

---

## Step 2 — Parse each email

Work from the clean text printed by `extract_playbook.py` (Step 1). Do not try to strip HTML
by eye — the script already did it.

### A) Schedule entries — from the AGENDA block

Use the `--- AGENDA · ATTAL/SÉJOURNÉ ---` block printed by `extract_playbook.py`. The script has
already filtered it down to the sentences where Attal/Séjourné are the subject, so **every line in
that block is a real entry** — just turn each into a JSON object. For each line extract:

- `title`: the activity (e.g. "Visite de l'exploitation agricole Hectar à Lévis-Saint-Nom, qui utilise l'IA")
- `location`: city/place mentioned in the sentence (e.g. "Lévis-Saint-Nom, Yvelines" or "Paris" or "")
- `time`: time if mentioned (e.g. "11h15"), otherwise omit this field. The time is usually in the
  merged "Il s'adresse à la presse à …" tail of the same line.
- `event_date`: derive from the day label at the **start** of the line (already computed for you):
  - `[当天]` → the email's send date (YYYY-MM-DD)
  - `[周六]` → the next Saturday after the send date
  - `[周日]` → the next Sunday after the send date
- `person`: "Gabriel Attal" or "Stéphane Séjourné"

If the block says "(今日 AGENDA 无 Attal/Séjourné 行程 → schedule = [])", set `schedule` = [].

### B) News items — from the NEWS block

Use the `--- NEWS 相关段 ---` block printed by `extract_playbook.py` (already filtered to the body
sentences that mention Attal/Séjourné, with a little surrounding context).

Extract 2–5 notable political stories that meaningfully involve Gabriel Attal OR Stéphane Séjourné.

For each news item extract:
- `title`: concise French headline (50 words max)
- `summary`: 1–3 sentence description of the story
- `person`: "Gabriel Attal", "Stéphane Séjourné", or "S&A" (if both mentioned)
- `published_at`: email send date + "T05:05:00" (e.g. "2026-06-08T05:05:00")
- `source_url`: "https://www.politico.eu/newsletter/paris-playbook/"

Do NOT include items that only mention Attal or Séjourné in passing (e.g. a list of politicians). Only include items where they are a central subject of the story.

---

## Step 3 — Build JSON and insert

For each email processed, construct this JSON structure:

```json
{
  "email_date": "YYYY-MM-DD",
  "email_subject": "...",
  "schedule": [ ... ],
  "news": [ ... ]
}
```

Then save it to `/tmp/playbook_data.json` using the Bash tool (Write the JSON with Python):

```bash
python3 -c "
import json
data = <YOUR_DICT_HERE>
with open('/tmp/playbook_data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)
"
```

Then run the insertion script:

```bash
cd /Users/junruzhang/Documents/GitHub/sa-archive
python3 scripts/playbook_to_db.py < /tmp/playbook_data.json
```

Then clean up:
```bash
rm -f /tmp/playbook_data.json
```

---

## Step 4 — Repeat for each email

Process ALL emails found (not just the most recent). The insertion script is idempotent — safe to re-run, duplicates are skipped automatically.

---

## Notes

- If AUSSI À L'AGENDA has no Attal/Séjourné entries today, `schedule` array = [] — still insert the news items
- If the email has no relevant news about Attal/Séjourné, `news` array = [] — still insert schedule if any
- The script reads Supabase credentials from `/Users/junruzhang/Documents/GitHub/sa-archive/.streamlit/secrets.toml`
- Project path: `/Users/junruzhang/Documents/GitHub/sa-archive`
- Gmail MCP tool names start with `mcp__fed79870-a093-4375-b269-dc564257af24__`

Print a final summary: how many emails processed, schedule entries inserted, news items inserted.