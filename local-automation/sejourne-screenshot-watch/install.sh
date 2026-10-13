#!/bin/bash
# 一次性安装:在 Mac 上跑一次即可(在 sa-archive 仓库根目录:bash local-automation/sejourne-screenshot-watch/install.sh)
#   1. 建 iCloud 文件夹「Sejourne行程截图」
#   2. 生成并加载 launchd 任务 com.sa-archive.sejourne-screenshot-watch(每天 8/12/16/20:20)
#   3. 自检:python 依赖、claude、凭据、文件夹访问权限
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
LABEL="com.sa-archive.sejourne-screenshot-watch"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
STATE_DIR="$HOME/.claude/local-automation/sejourne-screenshot-watch"
WATCH="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Sejourne行程截图"

chmod +x "$HERE/run.sh"
mkdir -p "$STATE_DIR" "$WATCH" "$HOME/Library/LaunchAgents"
echo "✓ 监控文件夹:$WATCH"
echo "  (iPhone 上:文件 App → iCloud 云盘 → Sejourne行程截图,把截图存进去即可)"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$HERE/run.sh</string></array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>20</integer></dict>
    <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>20</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>20</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>20</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$STATE_DIR/launchd.out</string>
  <key>StandardErrorPath</key><string>$STATE_DIR/launchd.err</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "✓ launchd 任务已加载:$LABEL"

echo ""
echo "── 自检 ──"
PY="${PYTHON:-python3}"
"$PY" -c "import supabase, toml" 2>/dev/null \
  && echo "✓ $PY 有 supabase / toml" \
  || echo "✗ $PY 缺依赖:$PY -m pip install supabase toml(或在 $STATE_DIR/.env 里设 PYTHON=有依赖的那个 python)"
[ -f "$REPO/.streamlit/secrets.toml" ] && echo "✓ 找到 .streamlit/secrets.toml(Supabase 凭据)" \
  || echo "✗ 缺 $REPO/.streamlit/secrets.toml"
if [ -f "$HOME/.claude/local-automation/attal-screenshot-watch/.env" ]; then
  echo "✓ 复用 Attal 截图任务的 .env(CLAUDE_CODE_OAUTH_TOKEN)"
else
  echo "✗ 没找到 attal-screenshot-watch/.env —— 在 $STATE_DIR/.env 里写 CLAUDE_CODE_OAUTH_TOKEN=…(claude setup-token 生成)"
fi
echo "! 完全磁盘访问没法在这里自检(Terminal 自己有权限,会误判为通过):"
echo "  确认 系统设置 → 隐私与安全性 → 完全磁盘访问 里已有 /bin/bash 和 Claude.app(Attal 截图任务装过就已经有了),"
echo "  然后用下面的 kickstart 真跑一次,看 run.log 里是不是「无图」而不是「读不了」"
echo ""
echo "手动跑一次:launchctl kickstart -k gui/\$(id -u)/$LABEL ;日志:$STATE_DIR/run.log"
echo "只看识别结果不入库:python3 $HERE/process.py --watch \"$WATCH\" --repo \"$REPO\" --dry-run"
