#!/bin/bash
# GitHub Actions 版:Telegram 机器人收到的一条消息 → 下载截图 → headless claude 解析入库 → 回复
#
# 由 telegram_ingest.yml(repository_dispatch,Cloudflare Worker 触发)调用。
# 任何一步失败都会在 Telegram 里回「⚠️ 处理失败」+ 本次 run 链接,不静默。
set -u

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$ROOT" || { echo "::error::进不去仓库根目录 $ROOT"; exit 1; }

OUT="/tmp/tg"
SKILL="$ROOT/telegram-bot/SKILL_ci.md"
RUN_URL="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}"
mkdir -p "$OUT"

fail() {
  echo "::error::$1"
  printf '⚠️ 处理失败:%s\n日志:%s\n可以稍后重发一次。' "$1" "$RUN_URL" \
    | python3 telegram-bot/tg.py reply "$OUT" || true
  exit 1
}

# Step 1 — 取消息 + 下载图片
python3 telegram-bot/tg.py fetch "$OUT" || fail "下载 Telegram 消息/图片失败"

# Step 2 — headless claude 看图 → 入库 → 写 /tmp/tg/reply.txt
# claude CLI 偶发瞬时网络错,最多 3 次;每次 300s 硬超时。入库脚本幂等,重试不重复写。
MAX_TRIES=3
rc=1
for try in $(seq 1 "$MAX_TRIES"); do
  if [ "$try" -gt 1 ]; then
    echo "↻ headless claude 第 $try 次重试(上次 exit $rc)"
    sleep $((try * 10))
  fi
  rm -f "$OUT/reply.txt"
  timeout 300 claude -p \
    "请读取并严格按照这个文件里的指令执行:$SKILL —— 消息在 /tmp/tg/message.json。" \
    --model claude-sonnet-4-6 \
    --dangerously-skip-permissions
  rc=$?
  [ "$rc" -eq 0 ] && [ -s "$OUT/reply.txt" ] && break
  [ "$rc" -eq 0 ] && rc=1   # 正常退出但没写回复,也算失败重来
done
[ "$rc" -eq 0 ] || fail "解析入库步骤异常(exit $rc,已重试 $MAX_TRIES 次)"

# Step 3 — 回复结果
cat "$OUT/reply.txt"
python3 telegram-bot/tg.py reply "$OUT" < "$OUT/reply.txt" || { echo "::error::回复 Telegram 失败"; exit 1; }
echo "✅ Telegram 入库完成"
