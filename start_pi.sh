#!/bin/bash
# ICS_DMAS Pi 5 啟動腳本
# 啟動：指揮部 :8000 + 收容組 :8765/:8766 + 醫療組 :8775/:8776
# 用法：chmod +x start_pi.sh && ./start_pi.sh

REPO="$(cd "$(dirname "$0")" && pwd)"

# ── 取得本機 LAN IP ──────────────────────────────
LAN_IP=$(hostname -I | awk '{print $1}')

# ── TLS 憑證偵測（C1-B：step-ca 優先，mkcert fallback）─────
# 優先 1：step-ca 簽的憑證（C1-B 標準）
STEP_CA_CERT_DIR="$REPO/deploy/step-ca/certs"
STEP_ROOT_CA="$HOME/.step/certs/root_ca.crt"

# 優先 2：mkcert 既有憑證（向下相容）
MKCERT_DIR="$REPO/certs"

if [ -f "$STEP_CA_CERT_DIR/${LAN_IP}/cert.pem" ] && [ -f "$STEP_ROOT_CA" ]; then
  TLS_ENABLED=true
  CERT_FILE="$STEP_CA_CERT_DIR/${LAN_IP}/cert.pem"
  KEY_FILE="$STEP_CA_CERT_DIR/${LAN_IP}/key.pem"
  CA_FILE="$STEP_ROOT_CA"
  PROTO_HTTP="https"
  PROTO_WS="wss"
  echo "[TLS] 使用 step-ca 憑證（C1-B 標準）：$CERT_FILE"
elif [ -f "$MKCERT_DIR/192.168.100.10+2.pem" ] && [ -f "$MKCERT_DIR/192.168.100.10+2-key.pem" ]; then
  TLS_ENABLED=true
  CERT_FILE="$MKCERT_DIR/192.168.100.10+2.pem"
  KEY_FILE="$MKCERT_DIR/192.168.100.10+2-key.pem"
  CA_FILE="$MKCERT_DIR/rootCA.pem"
  PROTO_HTTP="https"
  PROTO_WS="wss"
  echo "[TLS] 使用 mkcert 憑證（fallback）：$CERT_FILE"
else
  TLS_ENABLED=false
  CERT_FILE=""
  KEY_FILE=""
  CA_FILE=""
  PROTO_HTTP="http"
  PROTO_WS="ws"
  echo "[TLS] 無憑證，退回 HTTP/WS（C1-B：演練環境必須有 TLS）"
fi

echo "======================================"
echo " ICS_DMAS Pi 500 啟動"
echo " 指揮部    → $PROTO_HTTP://$LAN_IP:8000"
echo " 收容組 Pi → $PROTO_WS://$LAN_IP:8765"
echo " 醫療組 Pi → $PROTO_WS://$LAN_IP:8775"
echo "======================================"

# ── 終止舊服務 ──────────────────────────────
kill_port() {
  local port=$1
  local pid=$(fuser $port/tcp 2>/dev/null | awk '{print $1}')
  if [ -n "$pid" ]; then
    echo "[清理] 終止舊程序 port $port (PID $pid)"
    kill -9 $pid 2>/dev/null || true
  fi
}
kill_port 8000
kill_port 8765
kill_port 8766
kill_port 8775
kill_port 8776

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

if [ "$TLS_ENABLED" = true ]; then
  COMMAND_URL="" \
    .venv/bin/uvicorn main:app --app-dir src \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-certfile "$CERT_FILE" \
    --ssl-keyfile "$KEY_FILE" \
    > /tmp/ics_command.log 2>&1 &
else
  COMMAND_URL="" \
    .venv/bin/uvicorn main:app --app-dir src \
    --host 0.0.0.0 \
    --port 8000 \
    > /tmp/ics_command.log 2>&1 &
fi
COMMAND_PID=$!
echo "[OK] 指揮部後端 PID $COMMAND_PID"

# ── Node.js 依賴安裝（根目錄）────────────
cd "$REPO"
if [ ! -d "node_modules" ]; then
  echo "[安裝] npm install ..."
  npm install --quiet
fi

# ── 收容組 Pi 伺服器 ────────────────────
echo ""
echo "[啟動] 收容組 Pi 伺服器 :8765/:8766 ..."
COMMAND_URL="$PROTO_HTTP://127.0.0.1:8000" \
  CERT_PATH="${TLS_ENABLED:+$CERT_FILE}" \
  KEY_PATH="${TLS_ENABLED:+$KEY_FILE}" \
  CA_CERT_PATH="${TLS_ENABLED:+$CA_FILE}" \
  node server/index.js --unit shelter \
  > /tmp/ics_shelter.log 2>&1 &
SHELTER_PID=$!
echo "[OK] 收容組 Pi PID $SHELTER_PID"

# ── 醫療組 Pi 伺服器 ────────────────────
echo ""
echo "[啟動] 醫療組 Pi 伺服器 :8775/:8776 ..."
COMMAND_URL="$PROTO_HTTP://127.0.0.1:8000" \
  CERT_PATH="${TLS_ENABLED:+$CERT_FILE}" \
  KEY_PATH="${TLS_ENABLED:+$KEY_FILE}" \
  CA_CERT_PATH="${TLS_ENABLED:+$CA_FILE}" \
  node server/index.js --unit medical \
  > /tmp/ics_medical.log 2>&1 &
MEDICAL_PID=$!
echo "[OK] 醫療組 Pi PID $MEDICAL_PID"

# ── 等待服務就緒 ───────────────────────────
echo ""
echo "[等待] 服務啟動中..."
sleep 3

# 確認指揮部存活
if curl -sk $PROTO_HTTP://127.0.0.1:8000/api/health > /dev/null 2>&1; then
  echo "[OK] 指揮部後端 健康檢查通過"
else
  echo "[警告] 指揮部後端尚未就緒，請稍後手動確認"
fi

# ── 服務資訊 ────────────────────────────
echo ""
echo "======================================"
echo " 服務已啟動"
echo ""
echo " 指揮官儀表板：$PROTO_HTTP://$LAN_IP:8000/static/commander_dashboard.html"
echo " API 文件：    $PROTO_HTTP://$LAN_IP:8000/docs"
echo ""
echo " 收容 PWA：    $PROTO_HTTP://$LAN_IP:8766/shelter_pwa.html"
echo " 收容 Admin：  $PROTO_HTTP://$LAN_IP:8766/admin.html"
echo " 醫療 PWA：    $PROTO_HTTP://$LAN_IP:8776/medical_pwa.html"
echo " 醫療 Admin：  $PROTO_HTTP://$LAN_IP:8776/admin.html"
echo ""
echo " 日誌："
echo "   指揮部：tail -f /tmp/ics_command.log"
echo "   收容組：tail -f /tmp/ics_shelter.log"
echo "   醫療組：tail -f /tmp/ics_medical.log"
echo ""
echo " 停止：kill $COMMAND_PID $SHELTER_PID $MEDICAL_PID"
echo "======================================"

# 保持前景，Ctrl+C 一起結束
trap "echo ''; echo '[停止] 結束所有服務...'; kill $COMMAND_PID $SHELTER_PID $MEDICAL_PID 2>/dev/null; exit 0" INT
echo "[按 Ctrl+C 停止所有服務]"
wait
