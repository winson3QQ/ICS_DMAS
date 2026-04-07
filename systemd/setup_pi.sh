#!/bin/bash
# ICS_DMAS Pi 500 一次性初始化腳本
# Pi 到貨後 SSH 進去跑一次即可
# 用法：curl/scp 這個檔案到 Pi 後執行：
#   chmod +x setup_pi.sh && ./setup_pi.sh

set -e

REPO_URL="https://github.com/winson3QQ/ICS_DMAS.git"
DEPLOY_DIR="/home/ics/ics-dmas"

echo "======================================"
echo " ICS_DMAS Pi 500 初始化"
echo "======================================"

# ── 1. 系統套件 ──────────────────────────────
echo ""
echo "[1/6] 安裝系統套件..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3 python3-venv python3-pip \
  nodejs npm \
  build-essential \
  git curl

# 確認版本
echo "  Python: $(python3 --version)"
echo "  Node:   $(node --version)"
echo "  npm:    $(npm --version)"

# ── 2. Clone 程式碼 ──────────────────────────
echo ""
echo "[2/6] 部署程式碼到 $DEPLOY_DIR ..."
if [ -d "$DEPLOY_DIR" ]; then
  echo "  目錄已存在，執行 git pull ..."
  cd "$DEPLOY_DIR"
  git pull
else
  git clone "$REPO_URL" "$DEPLOY_DIR"
  cd "$DEPLOY_DIR"
fi

# ── 3. Python 虛擬環境 ──────────────────────
echo ""
echo "[3/6] 建立 Python 虛擬環境 + 安裝依賴..."
cd "$DEPLOY_DIR/command-dashboard"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
echo "  FastAPI 依賴安裝完成"

# ── 4. Node.js 依賴 ─────────────────────────
echo ""
echo "[4/6] 安裝 Node.js 依賴（含編譯 better-sqlite3，約 2-3 分鐘）..."
cd "$DEPLOY_DIR"
npm install --quiet
echo "  Node.js 依賴安裝完成"

# ── 5. 安裝 systemd 服務 ────────────────────
echo ""
echo "[5/6] 安裝 systemd 服務..."
sudo cp "$DEPLOY_DIR/systemd/ics-command.service" /etc/systemd/system/
sudo cp "$DEPLOY_DIR/systemd/ics-shelter.service" /etc/systemd/system/
sudo cp "$DEPLOY_DIR/systemd/ics-medical.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ics-command ics-shelter ics-medical
echo "  三個服務已設定開機自動啟動"

# ── 6. 啟動服務 ─────────────────────────────
echo ""
echo "[6/6] 啟動服務..."
sudo systemctl start ics-command
sleep 3
sudo systemctl start ics-shelter ics-medical
sleep 2

# ── 驗證 ────────────────────────────────────
echo ""
echo "======================================"
echo " 驗證服務狀態"
echo "======================================"

LAN_IP=$(hostname -I | awk '{print $1}')

check_service() {
  local name=$1
  if systemctl is-active --quiet "$name"; then
    echo "  [OK] $name"
  else
    echo "  [失敗] $name — 執行 journalctl -u $name 查看原因"
  fi
}

check_service ics-command
check_service ics-shelter
check_service ics-medical

echo ""
if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
  echo "  [OK] 指揮部 API 健康檢查通過"
else
  echo "  [警告] 指揮部 API 尚未就緒"
fi

echo ""
echo "======================================"
echo " 初始化完成！"
echo ""
echo " 從其他裝置存取："
echo "   指揮官儀表板：http://$LAN_IP:8000/static/commander_dashboard.html"
echo "   收容 PWA：    http://$LAN_IP:8766/shelter_pwa.html"
echo "   醫療 PWA：    http://$LAN_IP:8776/medical_pwa.html"
echo ""
echo " 常用指令："
echo "   看狀態：sudo systemctl status ics-command ics-shelter ics-medical"
echo "   看 log：journalctl -u ics-command -f"
echo "   重啟：  sudo systemctl restart ics-command ics-shelter ics-medical"
echo "   更新：  cd ~/ics-dmas && git pull && sudo systemctl restart ics-command ics-shelter ics-medical"
echo "======================================"
