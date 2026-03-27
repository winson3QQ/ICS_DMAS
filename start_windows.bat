@echo off
chcp 65001 > nul
echo ======================================
echo  ICS_DMAS 本機模擬啟動（Windows / Phase 1）
echo  指揮部    ^> http://127.0.0.1:8000
echo  收容組 Pi ^> ws://127.0.0.1:8765
echo  收容組 Admin ^> http://127.0.0.1:8766
echo ======================================
echo.

set REPO=%~dp0
set REPO=%REPO:~0,-1%

:: ── 終止舊服務 ──────────────────────────
echo [清理] 終止舊程序...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F > nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F > nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8766 " ^| findstr "LISTENING"') do (
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

start "ICS-指揮部後端" /min cmd /c ".venv\Scripts\uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > %TEMP%\ics_command.log 2>&1"
echo [OK] 指揮部後端已啟動（背景視窗）

:: ── 收容組 Pi 伺服器（Node.js）────────
echo.
echo [啟動] 收容組 Pi 伺服器 :8765/:8766 ...
cd /d "%REPO%\shelter-pwa"

if not exist "node_modules" (
    echo [安裝] npm install ...
    npm install --quiet
)

start "ICS-收容組Pi" /min cmd /c "set COMMAND_URL=http://127.0.0.1:8000 && node src\shelter_ws_server.js > %TEMP%\ics_shelter.log 2>&1"
echo [OK] 收容組 Pi 已啟動（背景視窗）

:: ── 等待就緒 ──────────────────────────
echo.
echo [等待] 服務啟動中（3 秒）...
timeout /t 3 /nobreak > nul

:: ── 開啟瀏覽器 ────────────────────────
echo.
echo ======================================
echo  服務已啟動
echo  指揮部幕僚版：http://127.0.0.1:8000/static/staff_dashboard.html
echo  指揮官版：    http://127.0.0.1:8000/static/commander_dashboard.html
echo  收容組 PWA：  http://127.0.0.1:8766/shelter_pwa.html
echo  API 文件：    http://127.0.0.1:8000/docs
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
