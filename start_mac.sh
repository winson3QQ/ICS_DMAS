#!/bin/bash
# ICS_DMAS 本機模擬啟動腳本（Mac / Phase 1）
# 啟動：指揮部後端 :8000 + 收容組 Pi 伺服器 :8765/:8766
# 用法：chmod +x start_mac.sh && ./start_mac.sh

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"

echo "======================================"
echo " ICS_DMAS 本機模擬啟動（Phase 1）"
echo " 指揮部 → http://127.0.0.1:8000"
echo " 收容組 Pi → ws://127.0.0.1:8765"
echo " 收容組 Admin → http://127.0.0.1:8766"
echo "======================================"

# ── 終止舊服務 ──────────────────────────────
kill_port() {
  local port=$1
  local pid=$(lsof -ti tcp:$port 2>/dev/null)
  if [ -n "$pid" ]; then
    echo "[清理] 終止舊程序 port $port (PID $pid)"
    kill -9 $pid 2>/dev/null || true
  fi
}
kill_port 8000
kill_port 8765
kill_port 8766

sleep 0.5

# ── 指揮部後端（FastAPI）───────────────────
echo ""
echo "[啟動] 指揮部後端 FastAPI :8000 ..."
cd "$REPO/command-dashboard"

if [ ! -d ".venv" ]; then
  echo "[安裝] 建立 Python 虛擬環境..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

# COMMAND_URL 留空（指揮部就是本機，收容組 Pi 推送至此）
COMMAND_URL="" \
  .venv/bin/uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  > /tmp/ics_command.log 2>&1 &
COMMAND_PID=$!
echo "[OK] 指揮部後端 PID $COMMAND_PID"

# ── 收容組 Pi 伺服器（Node.js）────────────
echo ""
echo "[啟動] 收容組 Pi 伺服器 :8765/:8766 ..."
cd "$REPO/shelter-pwa"

if [ ! -d "node_modules" ]; then
  echo "[安裝] npm install ..."
  npm install --quiet
fi

# COMMAND_URL 指向本機指揮部
COMMAND_URL="http://127.0.0.1:8000" \
  node src/shelter_ws_server.js \
  > /tmp/ics_shelter.log 2>&1 &
SHELTER_PID=$!
echo "[OK] 收容組 Pi PID $SHELTER_PID"

# ── 等待服務就緒 ───────────────────────────
echo ""
echo "[等待] 服務啟動中..."
sleep 2

# 確認指揮部存活
if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
  echo "[OK] 指揮部後端 健康檢查通過"
else
  echo "[警告] 指揮部後端尚未就緒，請稍後手動確認"
fi

# ── 開啟瀏覽器 ────────────────────────────
echo ""
echo "======================================"
echo " 服務已啟動"
echo " 指揮部幕僚版：http://127.0.0.1:8000/static/staff_dashboard.html"
echo " 指揮官版：    http://127.0.0.1:8000/static/commander_dashboard.html"
echo " 收容組 PWA：  http://127.0.0.1:8766/shelter_pwa.html"
echo " API 文件：    http://127.0.0.1:8000/docs"
echo ""
echo " 日誌："
echo "   指揮部：tail -f /tmp/ics_command.log"
echo "   收容組：tail -f /tmp/ics_shelter.log"
echo ""
echo " 停止：kill $COMMAND_PID $SHELTER_PID"
echo "======================================"

# 開啟瀏覽器（指揮官版儀表板）
open "http://127.0.0.1:8000/static/commander_dashboard.html" 2>/dev/null || true

# 保持前景，Ctrl+C 一起結束
trap "echo ''; echo '[停止] 結束所有服務...'; kill $COMMAND_PID $SHELTER_PID 2>/dev/null; exit 0" INT
echo "[按 Ctrl+C 停止所有服務]"
wait
