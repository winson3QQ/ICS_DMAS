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
| 3 | Escalation/De-escalation + 佈局重構 + 全中文化 + 登入認證 | cmd-v0.4.0～v0.7.0+ | ✅ 完成 |
| 4 | Pi Read-Only API + L3/L4 地圖鑽探 | cmd-v0.8.0 | 🔲 進行中 |
| 5 | UI 收尾（deadline fix、決策合併、burn rate、流向箭頭） | cmd-v0.9.0 | 待做 |
| 6 | Operator Fatigue 操作者疲勞偵測（需改 PWA） | cmd-v1.0.0 | 待做 |

### Wave 3 版本歷史摘要

**v0.4.0～v0.4.9**（commit 5d084f8 / b8566ad）
- `escalation_check()` 5升5降規則、新鮮度圓點、Decision 完整生命週期
- 事件 marker 自動建 DB、事件編號 EV-MMDD-NNN、response_deadline 依嚴重度

**v0.5.0～v0.5.7**（commit 8d7da77 / 01d7bbf）
- 佈局重構：左側 3+2 切換（態勢/資源）+ 右側事件追蹤 60% + 待裁示 40%
- edit-bar 重設計、放置流程（3 click 零打字）、SVG icon 重繪、事件 marker 顏色動態

**v0.6.0～v0.6.10**（commit 7a2a2b5 / 68660c7）
- 齒輪移除、全中文化、確認 modal、結案驗證
- UI/UX 規格對齊、操作員金色、事件篩選、長按地圖定位
- 頂部狀態列重設計、地圖 tab/側欄版面調整

**v0.7.0**（commit 2209b3a）
- 登入頁 + 帳號管理 + 設定面板 + 認證中介層（FastAPI 端）

**v0.7.0 之後**（commit 551de99、202a83e）
- Zone A 登出按鈕 + 地圖 marker 清除機制
- CA 憑證下載頁 + Pi 程式碼更新腳本

### Wave 4 實作項目（依順序，共 5 項）

**架構決策（2026-04-07 討論定案）**：
- Pi 主動 push current_state 至 Command（Pi 在小網 NAT 後，Command 無法主動連 Pi）
- Command 自行從收到的記錄衍生 aggregate counts，不依賴 Pi 端的 snapshot 計算
- Pi 本地維護 push_queue，斷線期間緩衝，復線後補送，Command 以 pushed_at 寫入歷史
- 移除 Pi 端 snapshot push 及 Command Proxy pull 兩個機制

| 順序 | 項目 | 類別 | 說明 |
|------|------|------|------|
| 1 | Pi 節點管理 | 後端 DB + 設定 UI | `pi_nodes` 表（unit_id / label / api_key / last_seen_at）+ `/api/pi-nodes` CRUD + 設定面板 UI；api_key 用於驗證 Pi push |
| 2 | Pi current_state push | `ics_ws_server.js` | 加 `push_queue` 表（pushed_at / records_json / sent）；每 60s UPSERT current_state → enqueue → push `POST /api/pi-push/{unit_id}`；失敗留 sent=0；復線後補送所有 sent=0（按 pushed_at 順序）；push_queue 保留 MAX_QUEUE_AGE=24hr |
| 3 | Command 接收端 | 後端 | `POST /api/pi-push/{unit_id}`（Bearer API key 驗證）→ INSERT `pi_received_batches(unit_id, pushed_at, received_at, records_json)`；驗證失敗回 401；unit_id 不符回 403 |
| 4 | L3 個別記錄列表 | 前端 | 數據 tab 讀 `pi_received_batches` 最新一筆的 records_json，展示傷患/住民列表；Pi 離線（無最新批次）顯示提示，不 crash；顯示 pushed_at 作為資料新鮮度 |
| 5 | L4 單筆資料 Modal | 前端 | 從 L3 列表點單筆，從 records_json 取對應 record 展開顯示；無須額外 API call |

### Wave 4 安全 TODO（尚未決定優先序）

| 威脅 | 對策 | 狀態 |
|------|------|------|
| 傳輸明文 | Command 強制 HTTPS（TLS），Pi push 用 `https://` | 必須，Wave 4 同步處理 |
| Pi 偽冒 | `pi_nodes.api_key` Bearer token + unit_id 配對驗證 | 必須，Wave 4 Item 1/3 |
| Pi 被奪取 | Command 支援 per-unit key revocation（`DELETE /api/pi-nodes/{id}/key`） | 必須，Wave 4 Item 1 |
| push_queue 撐爆磁碟 | MAX_QUEUE_AGE=24hr，定期清除 | 必須，Wave 4 Item 2 |
| Pi 本地資料外洩 | SQLite 加密（SQLCipher） | defer，Wave 6 或另排 |

### Recovery 機制（各情境）

| 情境 | Pi → Command | Recovery |
|------|-------------|---------|
| 1A WiFi + 大網 | 穩定推送 | 短暫中斷 → buffer → 自動補送 |
| 1B 行動網路 + WireGuard | VPN 掉線時中斷 | VPN 重連後補送 |
| 2 自建 AP，無大網 | push 永遠失敗，buffer 累積 | 復線後補送；Command 端顯示「Pi 離線」；QR fallback |
| 3 完全離線 | 同情境 2 | QR code 唯一出口 |

### Wave 5 待做項目（UI 收尾，共 4 項）

| 項目 | 說明 |
|------|------|
| 重設 deadline 後端 API | `PATCH /api/events/{id}/deadline`，同時更新 DB 欄位 + 追加 note（目前只有 note） |
| 決策主題合併卡片 | `_zoneDecisionsTab()` group by `primary_event_id`，多筆顯示「鏈 N 筆」 |
| 物資 burn rate 預測線 | `drawSparkline()` 加 `projectToZero` dataset 屬性，虛線延伸到 Y=0 |
| 地圖流向箭頭 | `renderFlows()` 讀實際 flows 資料，`data_source` 欄位對應 calc 數值，動態粗度 |

### Pi Push 技術細節

**Pi 端新增**：
- `push_queue` 表：`(id, pushed_at TEXT, records_json TEXT, sent INTEGER DEFAULT 0)`
- `current_state` 表：`(table_name, record_id, record_json, updated_at) PRIMARY KEY (table_name, record_id)`，在 `appendDelta()` 中 UPSERT
- 每 60s：讀 current_state → 寫入 push_queue → 嘗試 push → 成功則 `UPDATE push_queue SET sent=1`
- 復線偵測：push 成功後，查 `sent=0` 的舊 queue，按 pushed_at 順序補送
- 定期清理：`DELETE FROM push_queue WHERE pushed_at < datetime('now', '-24 hours')`

**Command 端新增**：
- `pi_received_batches` 表：`(id, unit_id, pushed_at, received_at, records_json)`
- `pi_nodes.api_key` 欄位，驗證 Bearer token
- calc_engine 讀 `pi_received_batches`，GROUP BY time window，COUNT by status 衍生趨勢資料
- L3/L4 讀最新一筆（`ORDER BY pushed_at DESC LIMIT 1`）

**syncTables 參考**：
- shelter：`persons, beds, resources, incidents, shifts`
- medical：`patients, triages, incidents, shifts`

### 技術備忘

- HTML 固定 `commander_dashboard.html`，版號由 `CMD_VERSION` 常數控制（目前 `v0.7.0`）
- 啟動：`cd command-dashboard && export PYTHONPATH=src && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
- 測試資料：`python tests/gen_test_snapshots.py --batch`
- DB schema 變更需刪除 `data/ics.db`
- UI/UX 規格：`command-dashboard/docs/指揮部儀表板設計規格_v1_1.md`

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
