---
name: 專案狀態總覽
description: 醫療 PWA 進度、指揮部路線圖、硬體資訊、Pi 設定步驟
type: project
originSessionId: 543daa3e-1ccf-42d0-95b2-51722f37c565
---
## 目前開發重心

指揮部（command-dashboard）是目前的整備重心，所有準備工作集中在這裡。

- **硬體**：收容組/醫療組改用 Raspberry Pi 500（BCM2712 = Pi 5 晶片，鍵盤一體機）
- **民防感知 Console（:8001）**：暫時不處理，不在範圍內

---

## 醫療 PWA 進度

### 目前版號

- 程式：`medical-v0.6.7-alpha`（git tag）
- 規格書：`v0.6`（medical_pwa_spec.md）
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
| 🟢 | P9 語音建檔 | Pi 500 本地 STT 不可行（Whisper 中文醫療術語 CER 45%），改考慮雲端 API（Gemini Flash）或 N100 |

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
| 4+ | 情境設計器 + chart_utils.js 共用 + 演練模式鑽探停用 + 量能右軸 | cmd-v0.9.0 / FastAPI-v1.2.0 | ✅ 完成 |
| 5 | UI 收尾（deadline fix、決策合併、burn rate、流向箭頭） | cmd-v0.10.0 | 待做 |
| 6 | Operator Fatigue 操作者疲勞偵測（需改 PWA） | cmd-v1.0.0 | 待做 |
| 7 | TAK 整合（FreeTAKServer + CoT ↔ ICS_DMAS 雙向橋接，前進/安全組 ATAK 位置與事件） | cmd-v1.1.0 | 待做 |
| 8 | EOC/NIMS 標準對齊（ICS 表單、資源請求、單位間訊息、廣播、SitRep、附件） | cmd-v1.2.0 | 待做 |

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

### Wave 4+ 完成（cmd-v0.12.0～v0.12.3）

**已完成**：
| 項目 | 版號 | 說明 |
|------|------|------|
| 雙浮島地圖工具列 | v0.12.0 | edit-bar 拆成右上 toolbar island + 底部中央 mgrs-island，左下 place-type-wrap |
| 統一 tab active 樣式 | v0.12.0 | 站內/站外、態勢/資源 active 全改綠色（消除橘色不一致） |
| MGRS/WGS84 座標切換（Option A） | v0.12.1 | 雙擊地圖→藍十字 MGRS 顯示，點右側 WGS84/MGRS 小標籤切換；`_coordDisplayMode` + `_coordToggleBtn()` + `_coordValueHTML()` + `_refreshCoordPanel()` 統一入口 |
| coordPin 切回站外恢復 | v0.12.1 | `switchMap('indoor')` 不再呼叫 `_clearCoordPin()`，只隱藏面板，切回站外自動恢復 |
| 方形節點標記縮小 | v0.12.1 | 前進組/安全組 square marker 從 28×28 縮至 24×24 |
| 新事件樂觀更新 | v0.12.1 | `submitEvent()` 送出後立即插入 `_data.events`，不等 poll；補齊 `reported_by_unit`、`session_type` 等欄位 |
| `_populateNapsgCsel` 初始化 crash 修復 | v0.12.1 | `el('place-type-panel')` null 導致整條初始化鏈中斷（無 polling、事件列表黑色）；重建 HTML 元素並加 null guard |
| zone modal 事件去重（EOC 模式） | v0.12.2 | 回報＋指派聯集去重，單一列表依狀態分組，卡片顯示角色 tag（回報・承辦/指派協助）|
| 事件組別分類改版 | v0.12.3 | 右側事件欄改為「回報」/「處理」雙按鈕互斥切換，預設按處理組別（`assigned_unit`）分組；未指派獨立群 |
| 事件名稱統一 | v0.12.3 | `_evTypeLabel()` helper 統一所有顯示入口，優先用 NAPSG 中文類型名；description 作副標題 |
| 事件 popup 優化 | v0.12.3 | 回報單位＋MGRS 合併為單行 header，移除冗餘標題文字，縮小 inner padding |
| 流向/路線改名 | v0.12.3 | 「新增流向」→「新增調度指示」，「傷患流向」→「傷患後送」；flow/route 工具列按鈕改用 SVG icon |
| 流向表單選項分組 | v0.12.3 | 起終點選單分 ICS 節點 / 事件標記 / 基礎設施三個 optgroup；事件標記顯示 NAPSG 類型名＋事件編號 |
| 路線/區域標籤可拖曳 | v0.12.3 | 路線標籤預設路線中點，區域標籤預設重心；拖曳後存 `label_anchor`；modal 可重設至自動位置；阻止冒泡防觸發長按事件 |

### Wave 5 待做項目（UI 收尾）

| 項目 | 狀態 | 說明 |
|------|------|------|
| 重設 deadline 後端 API | 🔲 待做 | 前端 `_resetDeadline()` UI 已實作（只追加 note）；後端 `PATCH /api/events/{id}/deadline` 未建立，DB `response_deadline` 欄位未更新 |
| 決策主題合併卡片 | 🔲 待做 | 前端 `primary_event_id` 篩選邏輯已存在；group by 合併顯示「鏈 N 筆」尚未實作 |
| 物資 burn rate 預測線 | 🔲 待做 | `chart_utils.js` `drawSparkline()` 無 `projectToZero` 屬性；需新增虛線延伸至 Y=0 邏輯 |
| 地圖流向箭頭 | ✅ 完成 | 舊 SVG overlay `renderFlows()` 已移除；現由 Leaflet `_renderFlows()` 統一處理 |

---

### Wave 7：TAK 整合

> 細節待定。前進組／安全組使用 ATAK，需與 Command Console 整合。

---

### Wave 8：EOC／NIMS 標準對齊

> 依據 NIMS 教義 + ICS 標準表單規格 + WebEOC/Veoci 共同設計模式識別的缺口。
> Wave 7 完成後，本系統在 EOC 核心功能上可對標主流商用平台。

#### 優先順序說明

| 優先 | 功能 | NIMS 依據 | 說明 |
|------|------|-----------|------|
| 🔴 P1 | **ICS 標準表單輸出**（ICS 201 / 214） | NIMS Ch.3 文件化要求 | ICS 201 事故概況表（事件清單、資源摘要、地圖截圖）；ICS 214 工作日誌（各組活動紀錄）；輸出 PDF 或列印友善 HTML |
| 🔴 P1 | **資源請求工作流程** | ICS Section Chief 資源請求鏈 | 前進/醫療/收容組從 PWA 提交資源需求 → 指揮部審核/批准/拒絕 → 狀態回報請求方；對應 ICS 213RR 表單 |
| 🟡 P2 | **單位間訊息（Inter-Unit Messaging）** | NIMS EOC 協調功能 | 指揮部 ↔ 各 Pi 組之間的結構化文字訊息（非即時聊天，類似 WebEOC Message Board）；訊息綁定事件 ID；PWA 端收到後推播通知 |
| 🟡 P2 | **廣播通知（Broadcast to PWA）** | EOC 通知管理 | 指揮部發出全組或特定組的廣播（演習開始、疏散指令等）；PWA 端顯示 banner + 音效；紀錄廣播歷史 |
| 🟢 P3 | **狀況報告自動生成** | ICS 209 事故狀況報告 | 每 N 分鐘（可設定）從 DB 快照自動產生純文字狀況摘要：事件數/嚴重度、人員流向、資源消耗率、決策待裁示；指揮官一鍵確認後鎖定為正式 SitRep |
| 🟢 P3 | **照片 / 附件** | EOC 文件管理 | 事件 marker 可附加照片（PWA 相機拍攝或上傳）；指揮部地圖 popup 顯示縮圖；存 Pi 本地 + push 至 Command；容量限制：每張 ≤ 2MB，每事件 ≤ 5 張 |
| 🟢 P3 | **事後檢討報告（AAR）** | NIMS 演習文件要求 | 演習結束後自動從 DB 組裝：事件時間軸、決策紀錄、資源消耗摘要、各組活動日誌；輸出 PDF 或列印友善 HTML |
| 🟢 P3 | **稽核軌跡（操作日誌）** | EOC 責任釐清 | 每個操作（建立事件、結案、調度指示、帳號登入）記錄操作者 + 時間戳；middleware 層統一記錄至 `audit_log` 表 |

#### 各功能技術要點

**ICS 201 / 214 表單**
- 後端：`GET /api/reports/ics201` 依事件 + 時間範圍彙整；`GET /api/reports/ics214/{unit_id}` 輸出工作日誌
- 前端：`window.print()` 觸發瀏覽器列印，CSS `@media print` 控制版面
- DB：不需新表，從現有 `events` / `decisions` / `pi_received_batches` 彙整

**資源請求工作流程**
- 新增 `resource_requests` 表：`(id, requesting_unit, item, quantity, priority, status, approved_by, created_at, resolved_at)`
- PWA 端：設定頁新增「資源請求」tab，送出後 push 至 Command
- Command 端：右側欄新增「資源請求」佇列（類似現有事件列表）

**單位間訊息**
- 新增 `unit_messages` 表：`(id, from_unit, to_unit, event_id?, body, read_at, created_at)`
- 傳遞路徑：Command → Pi WS broadcast（現有 WS server `broadcast()` 可直接複用）
- PWA 端：頂部燈旁顯示未讀紅點 badge

**廣播通知**
- Command 端 `POST /api/broadcast`：body + target_units（`[]` = 全組）
- Pi WS server 收到後用現有 `broadcast()` 推給所有連線裝置
- PWA 端：`handleWsMsg()` 新增 `broadcast` type 處理

**狀況報告自動生成**
- `POST /api/sitrep/generate`：後端從 DB 快照組裝純文字模板
- `POST /api/sitrep/{id}/confirm`：指揮官確認後鎖定
- 前端：右側欄「SitRep」tab，顯示最新草稿 + 歷史列表

**照片 / 附件**
- 新增 `event_attachments` 表：`(id, event_id, unit_id, filename, mime_type, size_bytes, created_at)`
- Pi 端：`multipart/form-data POST /upload` → 存 `~/ics-dmas/uploads/`；push 時附帶 attachment metadata
- Command 端：`GET /api/attachments/{id}` Proxy 從 Pi 取圖（或直接存 Command DB blob，≤ 2MB）

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

- HTML 固定 `commander_dashboard.html`，版號由 `CMD_VERSION` 常數控制（目前 `v0.12.3`）
- Pi server 版號 `SERVER_VERSION`（目前 `v1.1.0`）、FastAPI 版號 `1.2.0`
- Shelter PWA 版號 `v2.2.48`、Medical PWA 版號 `v0.6.7-alpha`
- 啟動：`cd command-dashboard && export PYTHONPATH=src && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
- 測試資料：`python tests/gen_test_snapshots.py --batch`
- DB schema 變更需刪除 `data/ics.db`
- UI/UX 規格：`command-dashboard/docs/指揮部儀表板設計規格.md`

---

## Pi 500 部署步驟（已到貨，Phase 2 E2B 評估已完成）

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

---

## Phase 2: E2B 評估結果（2026-04-16～04-17，Pi 500 完成）

### 結果摘要

| 測試 | 結果 | 判定 |
|------|------|------|
| Gemma4 E2B 結構化輸出 | 準確率 93.5%，延遲 40~50 秒 | 準確率 PASS，延遲 FAIL |
| Gemma4 E2B 矛盾偵測 | 0/5 | FAIL |
| Ollama 調參（gemma4-fast） | decode 4.2 tok/s 為硬體天花板，無法突破 | FAIL |
| Whisper STT（Tiny/Base/Small/Medium） | CER 45.3%，繁體中文醫療術語全錯 | FAIL |

### 結論

- Pi 500 不適合跑即時 AI 推論，專注 WS server / PWA host / Pi push / 錄音暫存
- LLM 結構化能力已驗證可行（93.5%），延遲問題是硬體限制非軟體問題
- Whisper 中文醫療 STT 不可行（訓練資料問題，非模型大小問題）
- 矛盾偵測用規則引擎實作（確定性邏輯）

### 語音輸入路線決策（待定）

| 路線 | 方式 | 狀態 |
|------|------|------|
| A. 雲端 API | Gemini 2.5 Flash（音檔→JSON 一步到位） | 待評估 |
| B. N100 Console | Pi 錄音→N100 推論 | 待硬體 |
| C. 規則引擎 | 關鍵字解析（需嚴格口述格式） | 可隨時實作 |
| D. 維持手動 | 不做語音輸入 | 保底方案 |

### 相關檔案

- 評估報告：`command-dashboard/tests/phase2_e2b/BENCHMARK_REPORT.md`（branch: phase2/e2b-evaluation）
- 結構化結果：`benchmark_report_20260416_224930.json`
- STT 結果：`stt_report_20260417_*.json`
- 最佳化 Modelfile：`Modelfile.fast`
