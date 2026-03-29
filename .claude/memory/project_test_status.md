---
name: 測試狀態（2026-03-28）
description: Windows 本機模擬測試的當前狀態、已解決問題、待辦事項
type: project
---

## 已驗證可用 ✅

- **FastAPI（指揮部後端）**：port 8000，HTTPS，`mkcert` 憑證，uvicorn `--app-dir src main:app`
- **Shelter Pi 伺服器**：port 8765（WSS）+ 8766（HTTPS），Node.js + better-sqlite3 v12.8.0
- **iPad WSS 連線**：wss://10.0.1.16:8765，mkcert rootCA 已安裝於 iPad（Certificate Trust Settings 綠色）
- **iPad 登入流程**：Auth OK，儀表板顯示 🟢 + `3qq（組長）`
- **Staff Dashboard**：https://127.0.0.1:8000/static/staff_dashboard.html，SERVER_URL 已修正為 `window.location.origin`

## 已知問題 / 待完成

### 高優先
- [ ] **端對端資料測試**：iPad 入站登記 → 確認 staff dashboard 有顯示（尚未執行）
- [ ] **登出後降級 banner**：switchRole() 做 location.reload()，reload 後 reconnect 成功但數秒後 onerror 觸發 _enterDegraded()，顯示「Pi 連線失敗」banner（UI bug，不影響功能）

### 中優先
- [ ] **start_windows.bat 編碼問題**：bat 存 UTF-8，cmd 用 cp950 解析，中文字元把命令切碎。服務仍啟動，但 log redirect 失效（CERT_PATH/KEY_PATH 環境變數靠 bat 傳給 shelter server，目前靠手動 cmd 啟動 workaround）
- [ ] **[ThreePass] 失敗**：Node.js fetch 到 https://127.0.0.1:8000 時 TLS 被拒（Node 不信任 mkcert）。Fallback 模式，不影響 iPad 操作，但 Pi→指揮部的三 Pass 同步不作動

### 低優先
- [ ] **start_windows.bat 改為純 ASCII**：移除中文 echo，解決編碼問題，讓 bat 能正常傳 CERT_PATH/KEY_PATH 給 shelter server
- [ ] **start_mac.sh HTTPS**：Mac 版啟動腳本尚未加 SSL 旗標給 uvicorn

## 目前手動啟動方式（bat 失效的 workaround）

Shelter Pi 伺服器需手動啟動：
```cmd
cd /d "c:\Users\yello\研究計畫\ICS_DMAS\shelter-pwa"
set CERT_PATH=c:\Users\yello\研究計畫\ICS_DMAS\certs\10.0.1.16+2.pem
set KEY_PATH=c:\Users\yello\研究計畫\ICS_DMAS\certs\10.0.1.16+2-key.pem
set COMMAND_URL=https://127.0.0.1:8000
node src\shelter_ws_server.js
```
FastAPI 透過 bat 啟動仍正常（SSL 參數正確傳入）。

## 環境資訊

- Windows IP（LAN）：10.0.1.16
- iPad IP：10.0.1.12（DHCP，可能變動）
- 憑證位置：`certs/10.0.1.16+2.pem`，覆蓋 10.0.1.16, localhost, 127.0.0.1
- mkcert rootCA：`C:\Users\yello\AppData\Local\mkcert\rootCA.pem`（與 certs/rootCA.pem 相同）

**Why:** 下次 session 能直接接續測試，不需重新診斷已知問題。
**How to apply:** 開始對話時先讀此記憶，確認當前問題清單是否仍適用。
