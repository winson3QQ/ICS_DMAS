@echo off
chcp 65001 > nul

:: ── 取得本機 LAN IP（供平板連線用）──────────
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do (
    set LAN_IP=%%a
    goto :found_ip
)
:found_ip
set LAN_IP=%LAN_IP: =%

echo ======================================
echo  ICS_DMAS 本機模擬啟動（Windows / Phase 1）
echo  本機 LAN IP：%LAN_IP%
echo  指揮部    ^> http://%LAN_IP%:8000
echo  收容組 Pi ^> ws://%LAN_IP%:8765
echo  收容組 PWA^> http://%LAN_IP%:8766/shelter_pwa.html
echo ======================================
echo.

set REPO=%~dp0
set REPO=%REPO:~0,-1%

:: ── 終止舊服務 ──────────────────────────
echo [清理] 終止舊程序...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%p /F > nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%p /F > nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8766 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%p /F > nul 2>&1
)
timeout /t 1 /nobreak > nul

:: ── 指揮部後端（FastAPI）───────────────
echo [啟動] 指揮部後端 FastAPI :8000 ...
cd /d "%REPO%\command-dashboard"

if not exist ".venv" (
    echo [安裝] 建立 Python 虛擬環境...
    python -m venv .venv
    .venv\Scripts\pip install -q -r requirements.txt
)

start "ICS-指揮部後端" /min cmd /c ".venv\Scripts\uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000 --reload > %TEMP%\ics_command.log 2>&1"
echo [OK] 指揮部後端已啟動

:: ── 收容組 Pi 伺服器（Node.js）────────
echo.
echo [啟動] 收容組 Pi 伺服器 :8765/:8766 ...
cd /d "%REPO%\shelter-pwa"

if not exist "node_modules" (
    echo [安裝] npm install ...
    npm install --quiet
)

:: COMMAND_URL 用 127.0.0.1（Pi 與指揮部同機模擬，localhost 永遠可達，不受網路拓撲影響）
:: 若未來 Pi 硬體獨立部署，改成指揮部的 LAN/Tailscale/公網 IP 即可
start "ICS-收容組Pi" /min cmd /c "set COMMAND_URL=http://127.0.0.1:8000 && node src\shelter_ws_server.js > %TEMP%\ics_shelter.log 2>&1"
echo [OK] 收容組 Pi 已啟動

:: ── 等待就緒 ──────────────────────────
echo.
echo [等待] 服務啟動中（4 秒）...
timeout /t 4 /nobreak > nul

:: ── 防火牆規則（初次需要）──────────────
echo [防火牆] 確認放行 TCP 8000/8765/8766 ...
netsh advfirewall firewall add rule name="ICS-Command-8000" dir=in action=allow protocol=TCP localport=8000 > nul 2>&1
netsh advfirewall firewall add rule name="ICS-Shelter-WS-8765" dir=in action=allow protocol=TCP localport=8765 > nul 2>&1
netsh advfirewall firewall add rule name="ICS-Shelter-Admin-8766" dir=in action=allow protocol=TCP localport=8766 > nul 2>&1
echo [OK] 防火牆規則已套用

:: ── 偵測 Tailscale IP（走大網情境）───────────────
set TS_IP=
for /f "tokens=1" %%a in ('tailscale ip 2^>nul') do (
    set TS_IP=%%a
    goto :found_ts
)
:found_ts

:: ── 顯示連線資訊 ──────────────────────
echo.
echo ======================================
echo  本機（Windows）——指揮官介面
echo    指揮官版：  http://127.0.0.1:8000/static/commander_dashboard.html
echo    幕僚版：    http://127.0.0.1:8000/static/staff_dashboard.html
echo    API 文件：  http://127.0.0.1:8000/docs
echo.
echo  ── 情境 1A：同一 WiFi（平板與 Windows 同網段）──
echo    PWA 網址：  http://%LAN_IP%:8766/shelter_pwa.html
echo    Pi URL：    ws://%LAN_IP%:8765
echo.
if defined TS_IP (
echo  ── 情境 1B：走大網（Tailscale VPN）──
echo    PWA 網址：  http://%TS_IP%:8766/shelter_pwa.html
echo    Pi URL：    ws://%TS_IP%:8765
echo    ^> 平板也需安裝 Tailscale 並登入同帳號
) else (
echo  ── 情境 1B：走大網（Tailscale 未偵測到）──
echo    選項 A：安裝 Tailscale（tailscale.com，美國公司）
echo             平板與 Windows 各裝後，改用 Tailscale IP 取代上方 LAN IP
echo    選項 B：路由器 port-forward 8765/8766/8000 到此機，使用公網 IP
echo    ^> 平板 PWA 設定頁面可手動輸入任意 Pi URL，無需修改程式碼
)
echo.
echo  日誌：
echo    指揮部：%TEMP%\ics_command.log
echo    收容組：%TEMP%\ics_shelter.log
echo ======================================
echo.

start "" "http://127.0.0.1:8000/static/commander_dashboard.html"

echo [完成] 關閉此視窗不會停止背景服務。
echo 若要停止服務，請關閉 "ICS-指揮部後端" 和 "ICS-收容組Pi" 視窗。
pause
