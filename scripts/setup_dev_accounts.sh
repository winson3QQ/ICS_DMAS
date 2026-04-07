#!/usr/bin/env bash
# ============================================================
# 開發環境一鍵初始化：設定 admin PIN + 建立測試帳號
# 用法: bash scripts/setup_dev_accounts.sh
# ============================================================
set -euo pipefail

ADMIN_PIN="1234"

SHELTER_ADMIN="http://127.0.0.1:8766"
MEDICAL_ADMIN="http://127.0.0.1:8776"

# --- Helper ---
post() {
  local url="$1" data="$2"
  curl -s -X POST "$url" \
    -H "Content-Type: application/json" \
    -H "X-Admin-PIN: ${ADMIN_PIN}" \
    -d "$data"
  echo ""
}

echo "=== 1. 設定 Admin PIN ==="

echo "[Shelter]"
post "${SHELTER_ADMIN}/admin/setup" "{\"admin_pin\":\"${ADMIN_PIN}\"}"

echo "[Medical]"
post "${MEDICAL_ADMIN}/admin/setup" "{\"admin_pin\":\"${ADMIN_PIN}\"}"

echo ""
echo "=== 2. 建立收容組帳號 ==="

post "${SHELTER_ADMIN}/admin/accounts" '{"username":"shelter-leader","role":"組長","pin":"1111"}'
post "${SHELTER_ADMIN}/admin/accounts" '{"username":"shelter-staff-a","role":"一般","pin":"2222"}'
post "${SHELTER_ADMIN}/admin/accounts" '{"username":"shelter-staff-b","role":"一般","pin":"3333"}'

echo ""
echo "=== 3. 建立醫療組帳號 ==="

post "${MEDICAL_ADMIN}/admin/accounts" '{"username":"medical-leader","role":"組長","pin":"1111"}'
post "${MEDICAL_ADMIN}/admin/accounts" '{"username":"triage-officer","role":"檢傷官","pin":"2222"}'
post "${MEDICAL_ADMIN}/admin/accounts" '{"username":"treatment-officer","role":"治療官","pin":"3333"}'
post "${MEDICAL_ADMIN}/admin/accounts" '{"username":"evac-officer","role":"後送官","pin":"4444"}'

echo ""
echo "=== 完成 ==="
echo ""
echo "收容組帳號："
echo "  shelter-leader  / PIN 1111 (組長)"
echo "  shelter-staff-a / PIN 2222 (一般)"
echo "  shelter-staff-b / PIN 3333 (一般)"
echo ""
echo "醫療組帳號："
echo "  medical-leader    / PIN 1111 (組長)"
echo "  triage-officer    / PIN 2222 (檢傷官)"
echo "  treatment-officer / PIN 3333 (治療官)"
echo "  evac-officer      / PIN 4444 (後送官)"
echo ""
echo "Admin PIN: ${ADMIN_PIN}"
