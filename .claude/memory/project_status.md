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

- 程式：`medical-v0.6.7-alpha`（git tag）
- 規格書：`v0.6`（medical_pwa_spec_v0_5.md）
- v0.6.7 修復：applyDelta `_id`→`id` fix，catchup 不再覆寫新資料

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
| 4 | Pi Push + L3/L4 鑽探 + calc_engine 接入 | cmd-v0.8.0 / server-v1.1.0 | ✅ 完成 |
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

### Wave 4 完成摘要（cmd-v0.8.0 / server-v1.1.0）

**架構**：Pi 主動 push current_state → Command 接收 + 衍生統計

**已完成項目**：
| 項目 | 說明 |
|------|------|
| Pi 節點管理 | `pi_nodes` 表 + CRUD API + 設定面板 UI（含一鍵推送 API key 至 Pi） |
| Pi current_state push | `current_state` / `push_queue` 表、每 60s push、hash 比對避免重複、復線補送 |
| Command 接收端 | `POST /api/pi-push/{unit_id}` Bearer 驗證 + `pi_received_batches` 儲存 |
| L3 記錄列表 | 自動載入、醫療檢傷矩陣、收容量能+狀態摘要、物資進度條 |
| L4 單筆詳情 | 點擊展開完整欄位 + 返回列表 |
| calc_engine 接入 | `_pi_batch_to_snapshot()` 衍生 snapshot、多筆歷史支援趨勢圖 |
| 主畫面統計 | 頂部人數（可點擊開 L3）、量能警示閃爍、conn dot tooltip |
| IPI 明細 | 點「未結 IPI」顯示各組未結事件來源 |

**同時修復的 bug**：
- Medical PWA syncAfterWrite 全部遺漏（47 處，根因）
- Shelter PWA syncAfterWrite 補漏（3 處）
- Medical record 用 `id` 非 `_id`（appendDelta 支援兩者）
- Medical pushRecoveryData `orderBy('timestamp')` → `orderBy('snapshot_time')`
- `startPiPush()` 延遲啟動 + 設定後立即觸發

**安全 TODO（待處理）**：
| 威脅 | 對策 | 狀態 |
|------|------|------|
| 傳輸明文 | Command HTTPS + Pi push 用 `https://` | 待做（TLS 憑證） |
| Pi 偽冒 | Bearer token + unit_id 驗證 | ✅ 已實作 |
| Pi 被奪取 | per-unit key revocation（rekey） | ✅ 已實作 |
| push_queue 撐爆磁碟 | MAX_QUEUE_AGE=24hr 清除 | ✅ 已實作 |
| Pi 本地資料外洩 | SQLCipher | defer |

### Wave 5 待做項目（UI 收尾，共 4 項）

| 項目 | 說明 |
|------|------|
| 重設 deadline 後端 API | `PATCH /api/events/{id}/deadline`，同時更新 DB 欄位 + 追加 note（目前只有 note） |
| 決策主題合併卡片 | `_zoneDecisionsTab()` group by `primary_event_id`，多筆顯示「鏈 N 筆」 |
| 物資 burn rate 預測線 | `drawSparkline()` 加 `projectToZero` dataset 屬性，虛線延伸到 Y=0 |
| 地圖流向箭頭 | `renderFlows()` 讀實際 flows 資料，`data_source` 欄位對應 calc 數值，動態粗度 |

### Pi Push 技術細節

**Pi 端 table**：
- `current_state`：`(table_name, record_id, record_json, updated_at) PK(table_name, record_id)`
- `push_queue`：`(id, records_json, pushed_at, sent, sent_at)`
- `appendDelta()` 同步 UPSERT current_state（支援 `_id` 和 `id`）
- `piPushOnce()` 每 60s：hash 比對 → 有變才 push → 復線補送
- `startPiPush()` 在設定 `command_url` 或 `pi_api_key` 後立即啟動

**Command 端 table**：
- `pi_nodes`：`(unit_id PK, label, api_key UNIQUE, last_seen_at, created_at, revoked_at)`
- `pi_received_batches`：`(id, unit_id, pushed_at, received_at, records_json)`

**資料流**：
- Pi push → `pi_received_batches` → `_pi_batch_to_snapshot()` 衍生 snapshot → `calc_engine.dashboard_calc()`
- 多筆歷史 batch 注入 → 支援趨勢圖
- L3：`GET /api/pi-data/{unit_id}/list` 讀最新批次
- L4：從已 fetch 的 `_l3Data` 取，無額外 API call

**syncTables**：
- shelter：`persons, beds, resources, incidents, shifts`
- medical：`patients, triages, incidents, shifts, transfers`

### Wave 4 後續改善（cmd-v0.8.0 之後）

| 項目 | 說明 |
|------|------|
| Pi auto-seed | 首次啟動自動設定 admin PIN=1234 + 建立 admin 帳號（對齊 Command） |
| Command 重設 DB | 設定面板「重設指揮部資料庫」按鈕（保留帳號和 Pi 節點） |
| Medical 清除測試資料 | 對齊 Shelter 的 clearAllTestData()，設定頁按鈕 |
| 傷患流向面板 | 接 Pi push source_type（A 前進/B 收容/C 自行），三色趨勢線 |
| Pi→Command heartbeat | 無資料變更時也送 heartbeat，Command 維持連線燈 |
| last_data_at | pi_nodes 區分心跳（last_seen_at）和資料推送（last_data_at） |
| PWA header 重設計 | 雙燈雙行式對齊 Command（Pi 燈 + 指揮部燈，角色・帳號 + 版號 + 登出） |
| heartbeat status check | 檢查 HTTP status code，403/401 正確顯示指揮部離線 |
| Pi 斷線重設指揮部燈 | Pi 離線時指揮部燈同步變灰 |

### 技術備忘

- HTML 固定 `commander_dashboard.html`，版號由 `CMD_VERSION` 常數控制（目前 `v0.8.0`）
- Pi server 版號 `SERVER_VERSION`（目前 `v1.1.0`）、FastAPI 版號 `1.1.0`
- Shelter PWA 版號 `v2.2.47`、Medical PWA 版號 `v0.6.7-alpha`
- 啟動：`cd command-dashboard && export PYTHONPATH=src && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
- 測試資料：`python tests/gen_test_snapshots.py --batch`
- DB schema 變更需刪除 `data/ics.db`
- UI/UX 規格：`command-dashboard/docs/指揮部儀表板設計規格_v1_3.md`

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
