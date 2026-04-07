#!/bin/bash
# Pi 500 靜態 IP 設定腳本
# 設定 eth0 為 192.168.100.10/24
# 用法：chmod +x setup_static_ip.sh && sudo ./setup_static_ip.sh

set -e

INTERFACE="eth0"
STATIC_IP="192.168.100.10/24"
GATEWAY="192.168.100.1"
DNS="8.8.8.8 8.8.4.4"

echo "======================================"
echo " Pi 500 靜態 IP 設定"
echo " 介面：$INTERFACE"
echo " IP：  $STATIC_IP"
echo " 閘道：$GATEWAY"
echo "======================================"

# Raspberry Pi OS (Bookworm) 使用 NetworkManager
if command -v nmcli &> /dev/null; then
  echo "[設定] 使用 NetworkManager 設定靜態 IP ..."

  # 取得目前的連線名稱
  CON_NAME=$(nmcli -t -f NAME,DEVICE con show --active | grep "$INTERFACE" | cut -d: -f1)

  if [ -z "$CON_NAME" ]; then
    echo "[錯誤] 找不到 $INTERFACE 的活躍連線"
    echo "  請確認網路線已接上"
    exit 1
  fi

  echo "  連線名稱：$CON_NAME"

  nmcli con mod "$CON_NAME" \
    ipv4.method manual \
    ipv4.addresses "$STATIC_IP" \
    ipv4.gateway "$GATEWAY" \
    ipv4.dns "$DNS"

  nmcli con up "$CON_NAME"

  echo ""
  echo "[OK] 靜態 IP 設定完成"
  echo "  IP：$(hostname -I | awk '{print $1}')"

else
  # 備援：舊版 dhcpcd 方式
  echo "[設定] 使用 dhcpcd 設定靜態 IP ..."

  DHCPCD_CONF="/etc/dhcpcd.conf"

  # 檢查是否已設定過
  if grep -q "interface $INTERFACE" "$DHCPCD_CONF" 2>/dev/null; then
    echo "[警告] $DHCPCD_CONF 已有 $INTERFACE 設定，跳過"
    echo "  請手動確認設定是否正確"
    exit 0
  fi

  cat >> "$DHCPCD_CONF" << EOF

# ICS_DMAS 靜態 IP 設定
interface $INTERFACE
static ip_address=$STATIC_IP
static routers=$GATEWAY
static domain_name_servers=$DNS
EOF

  echo "[OK] 已寫入 $DHCPCD_CONF"
  echo "  重開機後生效：sudo reboot"
fi

echo ""
echo "======================================"
echo " 驗證："
echo "   ip addr show $INTERFACE"
echo "   ping -c 1 $GATEWAY"
echo "======================================"
