#!/bin/bash
# launchd 包装器:iCloud「Sejourne行程截图」文件夹 → Séjourné 行程/图库入库
# (Attal 那套 attal-screenshot-watch 的 Séjourné 版;逻辑在同目录 process.py + PROMPT.md)
#
# 由 ~/Library/LaunchAgents/com.sa-archive.sejourne-screenshot-watch.plist 定时拉起
# (install.sh 生成,每天 8/12/16/20:20,和 Attal 的 :15 错开)。
#
# 吸取过的教训(见 sa-archive CLAUDE.md):
#   - iCloud Drive 是 TCC 保护区:/bin/bash 和 Claude.app 必须有「完全磁盘访问」。
#     开头显式 ls 探一次,看不见就大声报错,绝不把"没权限"伪装成"无图"
#   - 所有失败都 exit 1 + 发告警邮件,不静默
#   - claude 路径每次重试重新解析(在 process.py 里),防 Claude.app 自动升级后旧路径失效
set -u

STATE_DIR="$HOME/.claude/local-automation/sejourne-screenshot-watch"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/run.log"
exec >>"$LOG" 2>&1

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# 凭据:复用已有任务的 .env(CLAUDE_CODE_OAUTH_TOKEN / GMAIL_USER / GMAIL_APP_PASSWORD),
# 本任务自己的 .env 最后载入、可覆盖(也可在里面设 WATCH / PYTHON / CLAUDE_BIN)
set -a
for envf in "$HOME/.claude/local-automation/attal-screenshot-watch/.env" \
            "$HOME/.claude/local-automation/paris-playbook-daily/.env" \
            "$STATE_DIR/.env"; do
  [ -f "$envf" ] && . "$envf"
done
set +a

WATCH="${WATCH:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Sejourne行程截图}"
PYTHON="${PYTHON:-python3}"

echo ""
echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="

fail() {
  echo "❌ $1"
  tail -n 25 "$LOG" | "$PYTHON" "$REPO/scripts/send_alert.py" "⚠️ Séjourné 截图入库报错" || true
  exit 1
}

[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || fail "缺 CLAUDE_CODE_OAUTH_TOKEN(headless claude 不继承桌面 app 登录态)"
[ -d "$WATCH" ] || fail "监控文件夹不存在:$WATCH"
# 显式探一次:没有完全磁盘访问时这里会 Operation not permitted
ls "$WATCH" >/dev/null 2>&1 || fail "读不了 $WATCH —— 给 /bin/bash 和 Claude.app 开「完全磁盘访问」(系统设置→隐私与安全性)"

"$PYTHON" "$HERE/process.py" --watch "$WATCH" --repo "$REPO"
rc=$?
[ "$rc" -eq 0 ] || fail "process.py exit $rc(详见上面日志)"
