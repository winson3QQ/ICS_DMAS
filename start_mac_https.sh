#!/bin/bash
# start_mac_https.sh — C1-B 完整 HTTPS stack 啟動（Mac dev 驗證 + 演練前測試用）
#
# 與 start_mac.sh 的差別：
#   start_mac.sh        → HTTP fast path（dev iteration 用，無 TLS）
#   start_mac_https.sh  → HTTPS full stack：step-ca + nginx 反代 + FastAPI loopback + Pi TLS
#
# 前置（一次性）：
#   1. brew install step nginx
#   2. deploy/step-ca/init-mac-dev.sh
#   3. deploy/step-ca/trust-root-mac.sh
#   4. deploy/step-ca/start-ca.sh &      # 背景跑（或用 launchd）
#   5. deploy/step-ca/issue-cert.sh command.ics.local 127.0.0.1 localhost
#   6. deploy/step-ca/issue-cert.sh shelter.ics.local 127.0.0.1
#   7. deploy/step-ca/issue-cert.sh medical.ics.local 127.0.0.1
#   8. /etc/hosts 加：127.0.0.1 command.ics.local shelter.ics.local medical.ics.local

set -eo pipefail   # 不用 -u（nounset）：$! 在某些 bash 版本與 backgrounded subshell 互動會誤觸

REPO="$(cd "$(dirname "$0")" && pwd)"
STEP_CERT_DIR="$REPO/deploy/step-ca/certs"
ROOT_CA="$HOME/.step/certs/root_ca.crt"

# ── 前置檢查 ────────────────────────────────────
fail() { echo "✗ $1" >&2; exit 1; }

[[ -f "$ROOT_CA" ]] || fail "step-ca root 不存在。先跑：deploy/step-ca/init-mac-dev.sh"
[[ -f "$STEP_CERT_DIR/command.ics.local/cert.pem" ]] || fail "Command 憑證未簽。跑：deploy/step-ca/issue-cert.sh command.ics.local 127.0.0.1 localhost"
[[ -f "$STEP_CERT_DIR/shelter.ics.local/cert.pem" ]] || fail "Shelter 憑證未簽。跑：deploy/step-ca/issue-cert.sh shelter.ics.local 127.0.0.1"
[[ -f "$STEP_CERT_DIR/medical.ics.local/cert.pem" ]] || fail "Medical 憑證未簽。跑：deploy/step-ca/issue-cert.sh medical.ics.local 127.0.0.1"
grep -q "command.ics.local" /etc/hosts || fail "/etc/hosts 缺主機名。執行：echo '127.0.0.1 command.ics.local shelter.ics.local medical.ics.local' | sudo tee -a /etc/hosts"
command -v nginx >/dev/null 2>&1 || fail "nginx 未安裝。brew install nginx"

echo "======================================"
echo " ICS_DMAS HTTPS Stack 啟動（C1-B）"
echo " Command  → https://command.ics.local"
echo " Shelter  → https://shelter.ics.local:8766/shelter_pwa.html"
echo " Medical  → https://medical.ics.local:8776/medical_pwa.html"
echo "======================================"

# ── 終止舊服務 ──────────────────────────────
kill_port() {
  local port=$1
  local pid=$(lsof -ti tcp:$port 2>/dev/null)
  if [ -n "$pid" ]; then
    echo "[清理] kill port $port (PID $pid)"
    kill -9 $pid 2>/dev/null || true
  fi
}
kill_port 8000
kill_port 8765
kill_port 8766
kill_port 8775
kill_port 8776
sleep 0.5

# ── FastAPI loopback :8000（HTTP，由 nginx 終結 TLS）────
echo ""
echo "[啟動] FastAPI :8000 loopback ..."
cd "$REPO/command-dashboard"
[[ -d ".venv" ]] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }

ALLOWED_ORIGINS="https://command.ics.local,https://localhost" \
CSP_MODE="report-only" \
.venv/bin/uvicorn main:app --app-dir src \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  > /tmp/ics_command.log 2>&1 &
COMMAND_PID=$!
echo "[OK] FastAPI PID $COMMAND_PID"

# ── nginx 反代 :443 → :8000 ─────────────────────
cd "$REPO"
echo ""
echo "[啟動] nginx 反代 :443 ..."
deploy/nginx/start-dev.sh > /tmp/ics_nginx.log 2>&1 &
NGINX_PID=$!
echo "[OK] nginx PID $NGINX_PID（log：/tmp/ics_nginx.log）"

# ── Pi servers with TLS ────────────────────────
[[ -d node_modules ]] || npm install --quiet

echo ""
echo "[啟動] 收容組 Pi（TLS）..."
COMMAND_URL="https://command.ics.local" \
CERT_PATH="$STEP_CERT_DIR/shelter.ics.local/cert.pem" \
KEY_PATH="$STEP_CERT_DIR/shelter.ics.local/key.pem" \
CA_CERT_PATH="$ROOT_CA" \
NODE_EXTRA_CA_CERTS="$ROOT_CA" \
node server/index.js --unit shelter > /tmp/ics_shelter.log 2>&1 &
SHELTER_PID=$!
echo "[OK] Shelter PID $SHELTER_PID"

echo "[啟動] 醫療組 Pi（TLS）..."
COMMAND_URL="https://command.ics.local" \
CERT_PATH="$STEP_CERT_DIR/medical.ics.local/cert.pem" \
KEY_PATH="$STEP_CERT_DIR/medical.ics.local/key.pem" \
CA_CERT_PATH="$ROOT_CA" \
NODE_EXTRA_CA_CERTS="$ROOT_CA" \
node server/index.js --unit medical > /tmp/ics_medical.log 2>&1 &
MEDICAL_PID=$!
echo "[OK] Medical PID $MEDICAL_PID"

# ── 健康檢查 ──────────────────────────────────
sleep 3
echo ""
if curl -s --cacert "$ROOT_CA" https://command.ics.local/api/health > /dev/null 2>&1; then
  echo "[OK] Command HTTPS health 通過"
else
  echo "[警告] Command HTTPS health 未通過，檢查 /tmp/ics_nginx.log"
fi

# ── 開瀏覽器 ──────────────────────────────────
open "https://command.ics.local/static/commander_dashboard.html" 2>/dev/null || true

echo ""
echo "======================================"
echo " 服務已啟動（HTTPS Full Stack）"
echo " 日誌：tail -f /tmp/ics_*.log"
echo " 停止：Ctrl+C"
echo "======================================"

trap "echo '[停止] 結束所有服務...'; sudo kill ${NGINX_PID:-0} 2>/dev/null; kill ${COMMAND_PID:-0} ${SHELTER_PID:-0} ${MEDICAL_PID:-0} 2>/dev/null; exit 0" INT
wait
