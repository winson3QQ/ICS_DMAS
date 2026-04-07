---
name: 專案狀態總覽
description: 醫療 PWA 進度、指揮部路線圖、硬體資訊、Pi 設定步驟
type: project
---

## 目前開發重心

指揮部（command-dashboard）是目前的整備重心，所有準備工作集中在這裡。

- **硬體**：收容組/醫療組改用 Raspberry Pi 500（BCM2712 = Pi 5 晶片，鍵盤一體機）
- **民防感知 Console（:8001）**：暫時不處理，不在範圍內

---

## 醫療 PWA 進度

### 目前版號

- 程式：`medical-v0.6.3-alpha`（git tag）
- 規格書：`v0.6`（medical_pwa_spec_v0_5.md）

### 已完成 P 項

| 版號 | 項目 |
|------|------|
| v0.5.x | P0-10 後送流程拆分（治療區一鍵後送，目的地移至後送區 ISBAR） |
| v0.5.x | P0-12 ISBAR B 欄自動預填治療摘要 |
| v0.5.x | P1-4 待評估佇列改 display_id 排序 |
| v0.5.5 | P1-5 年齡改數字輸入，`_ageToCode()` 換算識別碼，`source_age` 存原始數字 |
| v0.5.6/v0.5.8/v0.5.9 | P1-6 姓名欄選填，卡片/詳情頁顯示，加性別/年齡欄位 |
| v0.5.7 | P1-7 重評預填前次生命徵象與主訴 |
| v0.6.0 | P2-8 創傷評估加 MOI + 用藥史 + 過敏史（`tr-` 前綴 ID 避免與非創衝突） |
| v0.6.0 | P2-9 非創 SAMPLE 順序改 A→M→S→P→L→E |
| v0.6.1 | P2-11 ISBAR 醫院選單近到遠排序，priority 院所置頂加 ★ |
| v0.6.1～v0.6.3 | P3-14 物資編輯/停用（軟刪除灰顯可恢復）/JSON 匯入 |

### 待辦 P 項

| 優先 | 項目 | 說明 |
|------|------|------|
| ⏸ | P0-3 簡化登入 | 帳號快選晶片，保留完整 PIN 驗證不動，方案確認中 |
| 🔴 | P3 紅區容量 | `getRedSlotsFree()` 永遠回傳 999；從 config 讀 `red_capacity`，預設 5，管理員可調整 |
| 🟡 | P4 生命徵象分開 | 現場 MIST-S vs 到院 START 數值混用；DB 加 `arrival_vitals` 欄位分開顯示 |
| 🟡 | Badge 定義 | 分區 tab badge 建議改為「待評估 + 逾時合計」，待決定 |
| 🟢 | P5 Pi URL config | IP hardcode `192.168.100.30`，改為 admin 介面設定，換場地不需改程式碼 |
| 🟢 | P6 WS 多裝置同步 | `handleWsMsg()` 目前空函式，最小實作：收 `patient_updated` 後 `loadPatients()` 再重繪 |
| 🟢 | P7 腕帶 QR | 演習不需要（display_id 手寫），熱感應印表機到位後再做 |
| 🟢 | P8 全域掃碼 | 同 P7，演習後 |
| 🟢 | P9 語音建檔 | Pi 5 離線辨識（faster-whisper），P3–P6 完成後再做 |

### 技術注意事項

- 創傷的用藥/過敏 ID 使用 `tr-allergy-*` / `tr-sample-a` / `tr-sample-m`（與非創的 `allergy-*` / `sample-a` / `sample-m` 分開，兩個 section 同時在 DOM 中）
- `_confirmInModal(title, msg, confirmFnStr, cancelFnStr)` 第三參數必須是**字串**，不可傳 function。需要 async callback 時用 `window._pendingXxxId` 暫存再用 `doXxx()` 函式字串
- 設定 tab 只有角色 `=== '組長'` 才顯示（`showApp()` 第 838 行控制），Demo 模式不走 `showApp()` 所以設定 tab 不會出現
- 物資停用：`db.resources.update(id, { disabled: true })`，渲染時 `activeItems = items.filter(r => !r.disabled)`
- Medical PWA 已完全對齊 shelter（WsManager/登入/同步），完成於 medical-v0.5.0-alpha

---

## 指揮部儀表板路線圖

| Wave | 內容 | 版號 | 狀態 |
|------|------|------|------|
| 1 | 三區佈局 + 雙地圖 + calc_engine 基礎智慧 | cmd-v0.2.0 | ✅ 完成 |
| 2 | 互動地圖事件輸入 + Decision Countdown + DCI + staff API | cmd-v0.3.0 | ✅ 完成 |
| 3 | Escalation/De-escalation + 地圖流向箭頭 + 規格缺口補齊 + 佈局重構 | cmd-v0.4.0～v0.6.0 | ✅ 完成 |
| 4 | Operator Fatigue 操作者疲勞偵測（需改 PWA） | cmd-v0.7.0 | 待做 |
| 5 | Pi Read-Only API + L3/L4 地圖鑽探 | cmd-v0.8.0 | 待做 |

### Wave 3 完整版本歷史

**v0.4.0～v0.4.2**（commit 5d084f8）
- `escalation_check()` 5升5降規則、新鮮度圓點、Decision 完整生命週期
- 事件類型對齊 PWA、events 表加 location_zone_id
- 版號統一 CMD_VERSION、HTML rename → commander_dashboard.html

**v0.4.3～v0.4.9**（commit b8566ad）
- 事件 marker 自動建 DB、事件編號 EV-MMDD-NNN
- response_deadline 依嚴重度分鐘設定、處置 modal 完整流程
- 結案 marker 灰色半透明

**v0.5.0**（commit 8d7da77）
- 佈局重構：左側 3+2 切換（態勢/資源）+ 右側事件追蹤 60% + 待裁示 40%

**v0.5.1～v0.5.7**（commit 01d7bbf）
- edit-bar 重設計、放置流程（3 click 零打字）、SVG icon 重繪
- 事件 marker 顏色動態、各組按鈕專屬色

**v0.6.0**（未 commit）
- 齒輪移除、按鈕顏色修復、全中文化
- 展開/收合、結案驗證、確認 modal
- 後端 `/api/dashboard` 加回傳 resolved 事件

### Wave 3 v0.6.x 待做

- 地圖流向箭頭填入實際 flows 資料 + 動態粗度
- 物資 burn rate 預測線（展開 sparkline 疊加虛線到 Y=0）
- 決策主題合併卡片（同 primary_event_id 合併）
- ⏱ 重設 deadline 後端 API（目前只追加 notes）

### 技術備忘

- HTML 固定 `commander_dashboard.html`，版號由 `CMD_VERSION` 常數控制
- 啟動：`cd command-dashboard && set PYTHONPATH=src && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
- 測試資料：`python tests/gen_test_snapshots.py --batch`
- DB schema 變更需 `del data/ics.db`
- UI/UX 規格：`command-dashboard/static/指揮部儀表板設計規格_v1_1.md`（舊路徑 command_dashboard_spec_v1_0.md）

---

## Pi 500 設定步驟（到貨後執行）

1. SSD 插上 Pi 500（USB 3.0），接網路線，開機
2. `ssh ics@ics-pi.local`
3. `git clone https://github.com/winson3QQ/ICS_DMAS.git ~/ics-dmas`
4. **從 Mac scp 憑證**（重要！certs 不在 repo 裡）：
   ```bash
   scp -r ~/Desktop/ICS_DMAS/certs/ ics@ics-pi.local:~/ics-dmas/certs/
   ```
5. `cd ~/ics-dmas/systemd && chmod +x *.sh`
6. `sudo ./setup_static_ip.sh` → 設定 192.168.100.10
7. `./setup_pi.sh` → 裝套件 + 啟動服務
8. 重開機驗證自動啟動

硬體資訊：Pi 500（BCM2712）、OS Lite 64-bit（SSD）、主機名 ics-pi、用戶 ics、靜態 IP 192.168.100.10、自建 WiFi AP（192.168.100.0/24）
