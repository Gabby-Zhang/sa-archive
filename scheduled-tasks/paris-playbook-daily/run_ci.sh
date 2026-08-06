#!/bin/bash
# GitHub Actions 版:抓 Politico Paris Playbook 邮件 → 抽 Attal/Séjourné 行程+新闻 → 入库 Supabase
#
# 为什么从 launchd 搬到 CI:
#   原来这步跑在本地 Mac 的 launchd 上,Mac 睡眠/关机时定时不触发(只在唤醒后补跑一次)。
#   2026-08-04~06 连续几天 Mac 白天没醒,行程整段断供、Agenda 空。搬到 GitHub Actions 后
#   彻底不依赖本地机器,和 news_monitor 一样在云端定时跑。
#
# 和 run.sh(launchd 版)的区别:
#   - 路径全用仓库相对路径(cwd = GITHUB_WORKSPACE),不碰 /Users/... 绝对路径
#   - 凭据来自 workflow 注入的环境变量(secrets),不读本地 .env / secrets.toml
#   - 超时用 GNU `timeout`(Ubuntu 自带),不用 macOS 上的 perl-alarm 变通
#   - 用 SKILL_ci.md(CI 版技能),不是 SKILL_launchd.md
set -u

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$ROOT" || { echo "::error::进不去仓库根目录 $ROOT"; exit 1; }

FETCH="scripts/fetch_playbook_email.py"
EXTRACT="scheduled-tasks/paris-playbook-daily/extract_playbook.py"
SKILL="$ROOT/scheduled-tasks/paris-playbook-daily/SKILL_ci.md"
RAW="/tmp/playbook_raw.json"
TXT="/tmp/playbook_extracted.txt"
SINCE="${SINCE_DAYS:-2}"

# Step 1 — IMAP 抓最近 N 天的 Paris Playbook 邮件(120s 硬超时;IMAP 偶发挂起)
timeout 120 python3 "$FETCH" --since-days "$SINCE" > "$RAW"
frc=$?
if [ "$frc" -eq 124 ]; then
  echo "::error::抓邮件超时(IMAP 120s 未返回)"; exit 1
elif [ "$frc" -ne 0 ]; then
  echo "::error::抓邮件失败(IMAP 登录/连接问题,看上面报错)"; exit 1
fi

# 没邮件就直接退出(正常情况,不算失败)
nmsg=$(python3 -c "import json;print(len(json.load(open('$RAW'))['messages']))" 2>/dev/null || echo 0)
if [ "$nmsg" -eq 0 ]; then
  echo "无 Paris Playbook 新邮件(近 ${SINCE} 天),跳过本次"
  rm -f "$RAW"; exit 0
fi
echo "抓到 $nmsg 封邮件,开始抽取"

# Step 2 — 抽成干净文本
if ! python3 "$EXTRACT" "$RAW" > "$TXT"; then
  echo "::error::extract_playbook.py 抽取失败"; exit 1
fi

# Step 3 — headless claude 读干净文本 → 构 JSON → 入库
# claude CLI 偶发瞬时网络错(socket closed / ECONNRESET),重试最多 3 次;
# 每次套 600s 硬超时(timeout),杜绝像本地那样永久挂起。入库脚本幂等,重试不重复写。
MAX_TRIES=3
TIMEOUT_SECS=600
rc=1
for try in $(seq 1 "$MAX_TRIES"); do
  if [ "$try" -gt 1 ]; then
    echo "↻ headless claude 第 $try 次重试(上次 exit $rc)"
    sleep $((try * 10))
  fi
  timeout "$TIMEOUT_SECS" claude -p \
    "请读取并严格按照这个文件里的指令执行:$SKILL —— 邮件已抽好在 /tmp/playbook_extracted.txt,按它构造 JSON 并入库。处理完用一行中文汇总:处理几封、入库几条行程、几条新闻。" \
    --model claude-sonnet-4-6 \
    --dangerously-skip-permissions
  rc=$?
  [ "$rc" -eq 124 ] && echo "⏱ 第 $try 次调用超过 ${TIMEOUT_SECS}s,已被 timeout 终止"
  [ "$rc" -eq 0 ] && break
done

rm -f "$RAW" "$TXT"
if [ "$rc" -ne 0 ]; then
  echo "::error::headless claude 入库步骤异常退出 (exit $rc,已重试 $MAX_TRIES 次仍失败)"; exit 1
fi
echo "✅ Paris Playbook 入库完成"
