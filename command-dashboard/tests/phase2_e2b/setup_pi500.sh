#!/bin/bash
# Phase 2: Pi 500 E2B 評估環境安裝腳本
# 用法: chmod +x setup_pi500.sh && ./setup_pi500.sh
#
# 前提: Pi 500 已安裝 Raspberry Pi OS 64-bit，已連網

set -euo pipefail

echo "============================================"
echo " Phase 2: Gemma 4 E2B 評估環境安裝"
echo " 目標: Pi 500 (BCM2712, 8GB RAM)"
echo "============================================"
echo ""

# --- 1. 系統更新 ---
echo "[1/5] 系統更新..."
sudo apt update && sudo apt upgrade -y

# --- 2. 安裝 Ollama ---
echo ""
echo "[2/5] 安裝 Ollama..."
if command -v ollama &> /dev/null; then
    echo "  Ollama 已安裝: $(ollama --version)"
else
    curl -fsSL https://ollama.com/install.sh | sh
    echo "  Ollama 安裝完成: $(ollama --version)"
fi

# 確保 Ollama 服務啟動
echo "  啟動 Ollama 服務..."
sudo systemctl enable ollama
sudo systemctl start ollama
sleep 3

# --- 3. 下載 Gemma 4 E2B 模型 ---
echo ""
echo "[3/5] 下載 Gemma 4 E2B 模型..."
echo "  注意: 模型約 1.5-2GB，下載時間依網路速度而定"
ollama pull gemma4:e2b || {
    echo ""
    echo "  ⚠️ gemma4:e2b 可能尚未在 Ollama registry 上架"
    echo "  嘗試替代方案: 手動載入 GGUF..."
    echo ""
    echo "  請手動執行以下步驟:"
    echo "  1. 從 HuggingFace 下載 Gemma 4 E2B GGUF (Q4_K_M)"
    echo "     https://huggingface.co/google/gemma-4-e2b-gguf"
    echo "  2. 建立 Modelfile:"
    echo '     echo "FROM ./gemma-4-e2b-Q4_K_M.gguf" > Modelfile'
    echo "  3. ollama create gemma4:e2b -f Modelfile"
    echo ""
    echo "  或嘗試其他名稱:"
    echo "  ollama pull gemma4"
    echo "  ollama pull gemma3"
}

# --- 4. 安裝 Python 依賴 ---
echo ""
echo "[4/5] 安裝 Python 依賴..."
sudo apt install -y python3-pip python3-venv

# 在測試目錄建立 venv
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install requests
deactivate

echo "  Python venv 建立於: ${VENV_DIR}"

# --- 5. 驗證安裝 ---
echo ""
echo "[5/5] 驗證安裝..."
echo ""

# 檢查 Ollama
echo "  Ollama 版本: $(ollama --version 2>/dev/null || echo '未安裝')"

# 檢查模型
echo "  已安裝的模型:"
ollama list 2>/dev/null || echo "    (無法列出)"

# 檢查系統資訊
echo ""
echo "  系統資訊:"
echo "    CPU: $(cat /proc/cpuinfo | grep 'Model' | head -1 | cut -d: -f2 | xargs)"
echo "    RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "    OS:  $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
echo "    Kernel: $(uname -r)"
echo "    Arch: $(uname -m)"

echo ""
echo "============================================"
echo " 安裝完成！"
echo ""
echo " 執行 benchmark:"
echo "   cd ${SCRIPT_DIR}"
echo "   source venv/bin/activate"
echo "   python run_benchmark.py --text-only"
echo ""
echo " 搭配資源監測:"
echo "   python monitor_resources.py --interval 2 --output resource_log.csv &"
echo "   python run_benchmark.py --text-only"
echo "   kill %1"
echo "============================================"
