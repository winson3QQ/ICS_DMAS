#!/bin/bash
# ICS_DMAS Pi 500 程式碼更新腳本
# 用法：./update_pi.sh

set -e

REPO="/home/ics/ics-dmas"
cd "$REPO"

echo "[更新] git pull ..."
git pull

# 檢查 Python 依賴是否有變動
if git diff HEAD~1 --name-only | grep -q "requirements.txt"; then
  echo "[更新] requirements.txt 有變動，重新安裝依賴..."
  cd "$REPO/command-dashboard"
  .venv/bin/pip install -q -r requirements.txt
  cd "$REPO"
fi

# 檢查 Node.js 依賴是否有變動
if git diff HEAD~1 --name-only | grep -q "package.json"; then
  echo "[更新] package.json 有變動，重新安裝依賴..."
  npm install --quiet
fi

# 重新複製 systemd service files（如有更新）
if git diff HEAD~1 --name-only | grep -q "systemd/"; then
  echo "[更新] systemd service files 有變動，重新載入..."
  sudo cp "$REPO/systemd/"*.service /etc/systemd/system/
  sudo systemctl daemon-reload
fi

echo "[重啟] 重啟所有服務..."
sudo systemctl restart ics-command
sleep 2
sudo systemctl restart ics-shelter ics-medical
sleep 2

# 驗證
echo ""
echo "[驗證]"
for svc in ics-command ics-shelter ics-medical; do
  if systemctl is-active --quiet "$svc"; then
    echo "  [OK] $svc"
  else
    echo "  [失敗] $svc — journalctl -u $svc 查看原因"
  fi
done

echo ""
echo "[完成] 更新成功"
