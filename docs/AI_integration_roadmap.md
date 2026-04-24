# ICS_DMAS AI 整合開發 Roadmap

> **層級**：L2 技術路線圖，由 [commercialization_plan_v1.md](commercialization_plan_v1.md) §C 章節引用
> **里程碑進度**：見 [ROADMAP.md](ROADMAP.md)（Wave 9 / C5-C / C5-D 對應段落）
> **整合來源**：Wave 5 待辦、AI_reference.md（已廢棄）、民防感知系統規格書/開發計畫/測試計畫 v1.4

## 進度追蹤

| Phase | 狀態 | 備註 |
|-------|------|------|
| 0-1 sw.js bug fix | ✅ 完成 | `b6b26a5` shelter-v2.2.48 |
| 0-2 role_detail | ✅ 完成 | `b6b26a5` accounts + 兩個 admin.html |
| 0-3 session_type | ✅ 完成 | `b6b26a5` + `308dbbc` 6 表 schema + 14 函式過濾 |
| 3-1 TTX 資料表 | ✅ 完成 | `f5b572e` ttx_sessions + ttx_injects |
| 3-2 TTX API | ✅ 完成 | `f5b572e` + `fba0592` 12 endpoints + inject push |
| 3-2+ 10 情境 JSON | ✅ 完成 | `f5b572e` scenarios/ 目錄 10 檔 |
| 3-2+ CLI runner | ✅ 完成 | `fba0592` ttx_runner.py --live/--batch |
| 3-5 Dashboard TTX toggle | ✅ 完成 | `9c854cd` 實戰/演練切換 + session_type query |
| **驗證** | 🔍 **驗證中** | 情境 01(24/24)、02 live(22/22)、09(23/23) 已通過；剩餘 7 個情境待人工 Dashboard 視覺確認 |
| 1 Wave 5 UI | 🔲 待做 | |
| 2 E2B 評估 | ⚠️ **部分完成** | Gemma4 E2B 結構化輸出準確率 93.5% ✅；延遲 40-50s ❌；矛盾偵測 0% ❌；Whisper 全部失敗（醫療中文 CER ~45%）；Phase 2b 小模型評估待執行 |
| 3-3 scenario_designer.html | ✅ 完成 | v0.9.9 壓力等級 + 敘事階段 + 共用 chart_utils.js + Dashboard 圖表對齊驗證通過 |
| 3-4/3-5 PWA TTX 模式 | 🔲 待做 | |
| 3-6~3-8 Field Node MVP | 🔲 待做 | |
| 4~7 | 🔲 待做 | |

---

## Context

- Wave 1-4 已完成（cmd-v0.8.0 / server-v1.1.0），Pi push 資料管線已通
- 硬體：Pi 500（收容/醫療/指揮部）、Pi Zero 2W（前進/安全組 Field Node，未到貨）
- **AI 推論硬體**：N100 或替代方案，共用一台跑民防感知 Console + ICS_DMAS AI，正在評估更便宜方案
- Console 端模型：Whisper Large + Llama 3 8B（原規格）或 Gemma 4 26B MoE（藍圖提案），硬體到位後實測決定
- 使用者決定：Wave 5 先做，AI 整合接在後面

### 模型分工定案

| 節點 | 硬體 | 模型 | 角色 |
|------|------|------|------|
| 醫療/收容組 | Pi 500（8GB） | Gemma 4 E2B（Q4, ~1.5GB）— 結構化輸出待優化 | 語音 → 結構化欄位填寫（矛盾偵測 Phase 2b 重新評估） |
| 前進/安全組 Field Node | Pi Zero 2W（512MB） | **錄音為主**；Whisper Tiny 草稿 STT（**V1-01 待驗證**：戰術用語 CER 需 < 15%，醫療中文已確認失敗） | 錄製原始音檔 + Tiny 草稿，上傳 Console；STT 正式稿由 Console 重推 |
| 指揮部 Console | N100 或替代（32GB） | Whisper Large-v3 + Llama 3 8B 或 Gemma 4 26B MoE | Field Node 正式文字稿、情勢合成、TTX 後果引擎、AAR |

**Phase 2 實測結論**（2026-04）：
- Gemma 4 E2B 結構化輸出準確率 93.5%（通過 85% 門檻），但延遲 40-50s（門檻 15s）未過；矛盾偵測 0%（門檻 60%）未過
- Whisper Tiny/Small/Medium/Large 在醫療繁中術語 CER ~45%，Pi 500 記憶體頻寬上限 4.2 tok/s 是硬天花板
- **架構轉向**：Field Node 改為「啞錄音節點」，Console 統一做 STT；Whisper Tiny 在 Field Node 上的**戰術用語**表現仍待 V1-01 驗證
- Phase 2b 待執行：Gemma3 4B / 1B、SmolLM3 3B、Phi-4-mini 3.8B 在 Pi 500 上的小模型評估

---

## C0：後端重構 + 資料基礎層（先於所有 Phase）

**定位**：零功能變更的架構重構，同時建立演練資料護城河的完整 schema 基礎。不先做好這層，後面所有 Phase 都要重來。

### 為什麼是「護城河」

演練資料的五個用途決定 schema 設計：

| 用途 | 缺什麼（C0 前） |
|------|--------------|
| AAR 事後檢討 | 事件無關閉時間、無處置單位、無結案說明 |
| 跨場次比較 | 無統一分類法（event_type），無每場 KPI |
| AI 訓練 | 無 state→action→outcome 三元組結構 |
| 外部呈報 | 無場次 metadata（地點、人數、主辦單位） |
| 研究用途 | 無 exercise_id，多場資料全部混在一起 |

### 戰略定位（2026-04-23 確認）

- **TAK**：第一等需求，EOC 互通標準，不是「Wave 7 以後再說」
- **AI**：第一等需求，核心差異化，不是 Phase 2 評估後再定
- **斷網**：架構前提，所有功能必須離線可用
- **法規合規**：以個人資料保護法為最低基本標準，醫療資料存取稽核，不過度收集

### C0 新增 Schema

**`exercises` 表**（整個場次概念，目前不存在）：
```sql
id, name, date, location, type(real|ttx),
scenario_summary, weather, participant_count, organizing_body,
status(setup|active|archived), started_at, ended_at
```

**`event_types` 表**（taxonomy，讓跨場次比較有意義）：
```sql
id, code, name_zh, category, default_severity
```

**`resource_snapshots` 表**（正規化 pi_received_batches 為時間序列）：
```sql
id, exercise_id, unit_type, snapshot_at,
total_beds, occupied_beds, light_count, medium_count, severe_count, deceased_count, source
```

**`aar_entries` 表**：
```sql
id, exercise_id, category(well|improve|recommend), content, created_by, created_at
```

**`exercise_kpis` 表**（計算後存起來，供 AI 訓練和跨場次比較）：
```sql
exercise_id, kpi_key, kpi_value, computed_at
```

**`ai_recommendations` 表**（人機互動閉環，同時是法律紀錄）：
```sql
id, exercise_id, made_at, recommendation_type, content, confidence,
accepted(bool), related_decision_id, outcome_notes
```

### 既有表補欄位

**`events`**：`+ exercise_id, event_type_id, assigned_unit, acknowledged_at, resolved_at, resolution_notes`

**`decisions`**：補完定義 `+ exercise_id, rationale, affected_units, outcome_at, outcome_notes`

**所有主要資料表**：`+ exercise_id FK`（讓資料可按場次隔離和匯出）

### AI 訓練資料結構

每個訓練樣本 = `(state, action, outcome)`：
- `state`：當下 resource_snapshot + 進行中 events + 距演練開始時間
- `action`：decision 內容
- `outcome`：T+15min 後的 resource_snapshot 變化 + events 解決率

三個表都需要 `exercise_id + timestamp` 才能重建時間軸。

### AI 服務抽象層

- **目前驗證**：Breeze（台灣本土 LLM，Ollama 部署，OpenAI-compatible API）
- **設計原則**：`ai_service.py` 依賴注入 LLM client，底層模型可換，router 不感知
- **本地優先**：即時建議必須離線可用；雲端是 config 選項，非預設

### C0 模組結構（完整）

```
repositories/   exercise_repo / cop_repo / event_repo（補欄位）/ decision_repo（補完）
                resource_snapshot_repo / aar_repo / ai_repo(stub)
                snapshot_repo / audit_repo / account_repo / sync_repo / manual_repo

services/       exercise_service / cop_service / pi_push_service
                dashboard_service / sync_service / ai_service(stub, Breeze 抽象)

routers/        exercises / cop(Wave6 stub) / tak(Wave7 stub, 正確 CoT 欄位)
                ai(即時建議 + 演練後分析 stub) / ... 其他路由
```

### C5 前向相容（C0 一起做，避免屆時重改）

| 項目 | C0 做什麼 | C5 做什麼 |
|------|----------|----------|
| Inject 簽章 | `ttx_injects` 加 `signature TEXT NULL` | Orchestrator 簽署，PWA 驗簽 |
| Session mutex | `exercise_service.set_active()` 加互斥檢查 | Orchestrator 呼叫此 API 開始/結束場次 |
| Orchestrator 認證 | RBAC 加 `TTX_ORCHESTRATOR` role（read-only scope） | Orchestrator 用此 role 的 token 讀狀態 |
| API client 標注 | 設計文件標注 Orchestrator 為預期 client（影響 CORS/auth） | Orchestrator 直接呼叫，不需額外改 |

> 規則：C0 是「加欄位 + 加邏輯 + 加 role」；C5 是「加服務 + 加實作」。C5 不動 C0 的程式碼。

---

## Phase 0：Bug 修復 + 基礎準備

**目標**：清技術債，為 TTX 和 AI 打地基。可與 Wave 5 同時進行。
**實作參考**：AI_reference.md 第二部分 §1.4（Bug 清單）、§3.1（session_type schema）

### 0-1. shelter sw.js CACHE_UPDATE 錯誤檔名
- `shelter-pwa/public/sw.js:89` → `cache.add('./shelter_pwa_v2.1.html')` 改為 `cache.add('./shelter_pwa.html')`
- bump sw.js CACHE_NAME + PWA_VERSION

### 0-2. role 三方不一致
- 後端 `accounts.role`（指揮官/操作員）、醫療前端（5 種）、收容前端（2 種）全部不一致
- 修正：accounts 加 `role_detail TEXT`，`role` 保留粗分，TTX 角色分離用 `role_detail`
- 檔案：`db.py`、兩個 `admin.html`

### 0-3. 所有主要表加 `session_type`
- 隔離演練/實戰資料，TTX 前提
- 改動表：`snapshots`、`events`、`decisions`、`audit_log`、`manual_records`、`predictions`
- 值：`real`（預設）/ `exercise`
- 所有 SELECT 加 `WHERE session_type = ?`
- 檔案：`db.py`、`main.py`（所有 endpoint）

---

## Phase 1：Wave 5 UI 收尾

**實作參考**：project_status.md Wave 5 待做項目、指揮部儀表板設計規格 §10-12

| # | 項目 | 檔案 |
|---|------|------|
| 1 | 重設 deadline 後端 API | `main.py`：`PATCH /api/events/{id}/deadline` |
| 2 | 決策主題合併卡片 | `commander_dashboard.html`：`_zoneDecisionsTab()` group by `primary_event_id` |
| 3 | 物資 burn rate 預測線 | `commander_dashboard.html`：`drawSparkline()` 加虛線延伸到 Y=0 |
| 4 | 地圖流向箭頭 | `commander_dashboard.html`：`renderFlows()` 讀 flows 資料，動態粗度 |

---

## Phase 2：Gemma 4 E2B 評估（與 Phase 1 平行）

**目標**：驗證 E2B 在 Pi 500 上跑繁中民防術語的可行性。不阻塞其他開發。

### 環境
- Pi 500 + llama.cpp server mode（GGUF Q4_K_M）
- Gemma 4 E2B（2.3B 有效參數）

### 測試項目與通過標準

| 測試 | 輸入 | 通過標準 | **實測結果** |
|------|------|---------|------------|
| STT 準確率（Whisper Tiny） | 10 段演練錄音（15-30 秒，含 CMIST/ISBAR/START 術語） | CER < 15% | ❌ **CER ~45%**（醫療繁中術語全部失敗） |
| 結構化輸出（E2B） | 同上 → JSON（性別/年齡/分級/主訴） | 欄位準確率 > 85% | ✅ **93.5%**（準確率過關） |
| 矛盾偵測（E2B） | 5 段刻意矛盾錄音 | 偵測率 > 60% | ❌ **0%**（完全未偵測） |
| 推論延遲（E2B） | 30 秒音訊 → 完整 JSON | < 15 秒 | ❌ **40-50s**（Pi 500 記憶體頻寬瓶頸 4.2 tok/s） |
| 記憶體 | 推論中 + WS server 同時運行 | 無 OOM，RSS < 6GB | ✅ 通過（無 OOM） |

**根因**：Pi 500 BCM2712 記憶體頻寬 34 GB/s 是硬天花板，即使 Q4_K_M 也無法在 15s 內完成推論。Whisper 各 size 在醫療中文術語均超出可用範圍。

### 實測結論與架構轉向

| 項目 | 結論 |
|------|------|
| Whisper（Pi 500 本機） | Pi 500 不做 STT，改由 Console Whisper Large-v3 集中處理 |
| E2B 結構化輸出 | 準確率可用，但延遲需優化（prompt 精簡 / 批次推論 / 換小模型） |
| E2B 矛盾偵測 | 需重設計 prompt 或改用規則引擎輔助 |
| 整體架構 | Field Node 降級為「啞錄音節點」，音訊集中上傳 Console 做 STT |

### Phase 2b（待執行，Pi 500 上）

目標：找更快的小模型解決延遲問題，候選：

| 模型 | 大小（Q4） | 預估速度 | 優先 |
|------|-----------|---------|------|
| Gemma3 4B | ~2.5GB | 未知 | 🔴 優先 |
| Gemma3 1B | ~0.7GB | 未知 | 🔴 次優先 |
| SmolLM3 3B | ~1.8GB | 未知 | 🟡 |
| Phi-4-mini 3.8B | ~2.3GB | 未知 | 🟡 |

測試重點：同樣的結構化輸出 prompt → 延遲是否 < 15s；矛盾偵測重新設計 prompt 後再試。

### Fallback（更新後）
- Whisper Pi 500 本機 STT → **已棄用**，改 Console 集中
- E2B 延遲問題 → Phase 2b 小模型評估（進行中）
- 若所有小模型延遲仍 > 15s → 降為「手動確認 + 批次離線推論」，不做即時 AI 填表

### 產出
- ✅ 評估報告：`command-dashboard/tests/phase2_e2b/BENCHMARK_REPORT.md`（branch: phase2/e2b-evaluation）
- ✅ Prompt template + JSON output schema（同目錄）
- 🔲 Phase 2b 小模型報告（待執行）

---

## Phase 3：TTX 骨架 + Field Node MVP

**目標**：數位化兵推框架 + 前進/安全組進入系統。兩者都不需要 AI。

**實作參考（TTX）**：AI_reference.md 第二部分 §3.2（完整 CREATE TABLE）、§3.4（API endpoint 設計）、§3.5（scenario_designer.html + PWA TTX mode）
**實作參考（Field Node）**：民防感知規格書 v1.4 §2-3（系統架構 + 軟體元件）、§6（硬體接線 GPIO pin）、§8（檔案結構 + 同步協議）；民防感知測試計畫 v1.4 §F1-F2（驗收標準）

### TTX 部分

**3-1. 資料表**
- `ttx_sessions`（id, session_name, facilitator, status, started_at, ended_at）
- `ttx_injects`（id, session_id, inject_seq, target_unit, title, description, image_path, payload JSON, status）

**3-2. API**
```
POST /api/ttx/sessions                           — 建立演練
POST /api/ttx/sessions/{id}/start|pause|end      — 控制演練狀態
POST /api/ttx/sessions/{id}/injects              — 上傳 inject 卡
POST /api/ttx/sessions/{id}/inject/{iid}/push    — 推送到 PWA
GET  /api/ttx/sessions/{id}/timeline             — 即時決策時間軸
```

**3-3. 情境設計器 + 主持人控制台** → 新增 `scenario_designer.html`（同時作為 Dashboard 驗證工具和 TTX 主持人控制台）

**角色**：Phase 3 先作為 Dashboard 驗證工具，Phase 5 擴充為 TTX 主持人控制台（加 AI 後果審核）。

**核心概念**：不用事先寫死 JSON，用參數 + 公式即時生成 inject 序列，透過 TTX API live 注入系統。

**敘事主軸 preset**（可選預設或全自訂）：

| preset | 核心壓力 | 說明 |
|--------|---------|------|
| 🏠 收容壓力 | bed 使用率逼近 100% | shelter 主角，其他穩定 |
| 🏥 醫療緊急 | 紅傷湧入 + 物資耗盡 | medical 主角，shelter 轉介 |
| 📡 通訊中斷 | 某組斷線 N 分鐘 | gap 時間、影響組別可調 |
| ⚠️ 複合壓力 | 多組同時受壓 | 所有 slider 拉高 |
| 📉 壓力緩解 | 從高峰下降 | 起始值高，下降速率可調 |
| 🎯 五縱多點滲透 | 同時多地點事件 | 來源：第一場 INC-02+03+04（事件群），測試偵測延遲 |
| 🔫 指揮中斷與接場 | 指揮官倒底 + 空窗 + 接場 | 來源：第二場 II-A，測試指揮延續性 |
| 🏴 主線敘事弧 | 多階段連續情境 | 來源：第三場 VIP 被俘→談判→救回，測試跨組協調 |
| 📋 P1 驗證：醫療通報延遲 | 傷患事件產生但不推播 | 驗證自動提醒機制（AAR P1 惡化問題） |
| 🔧 自訂 | 全部手動 | 全部 slider 自由調整 |

**可調參數（sliders）**：

收容組：
- 床位：初始使用率% → 目標使用率%，湧入速度
- SRT 紅旗比例，pending_intake
- **當班人數**：N 人，異動時間點（T+Xmin ±N 人）→ 自動算 staff_ratio
- **物資**：毛毯（初始/最大 + 消耗速率）、飲用水（初始/最大 + 消耗速率）

醫療組：
- 紅傷：初始 → 目標，黃/綠/黑比例
- **物資**：IV / 氧氣 / 止血帶（初始/最大 + 消耗速率）
- 後送積壓速度
- **當班人數**：N 人，異動時間點

前進組：
- Alpha / Bravo：hazard type、傷亡人數、vehicle_needed

安全組：
- 哨位異常、隔離人數、QRF 可用人數

時間軸：
- 模擬時長（分鐘）、注入間隔（分鐘）、即時壓縮（秒）

事件觸發（門檻自動觸發）：
- ☑ 容量警告（shelter > 80%）
- ☑ IV 危急（IV < 20%）
- ☑ 人員不足警告（staff_ratio > 10）
- ☑ 物資即將耗盡（blanket 或 water < 15%）
- ☐ 安全威脅
- ☑ 待裁示（IV 補給 / 啟動備用收容點）

**資料路徑**（兩條並行，驗證 Dashboard 所有面板）：
- `snapshot` inject type → `POST /api/snapshots` → 頂部數字、burn rate、escalation
- `pi_push` inject type（新增）→ `POST /api/pi-push/{unit_id}` → L3/L4 鑽探、Pi 連線燈、趨勢線

`pi_push` payload 含個別傷患/住民記錄，模擬 PWA 實際產生的資料：
```json
{"unit_id": "medical", "records": [
  {"table_name": "patients", "record": {"id":"P001", "display_id":"M001-MA", "triage_color":"red", ...}},
  {"table_name": "resources", "record": {"id":"R001", "name":"IV 輸液", "current_qty":15, ...}}
]}
```

**操作流程**：
1. 選 preset → sliders 自動調到預設值
2. 手動微調任何參數
3. 按「預覽」→ 下方顯示 inject 時間軸
4. 按「注入」→ 自動建 TTX session + live push
5. 另一個 tab 開 Dashboard 演練模式 → 即時看數字變化
6. 注入完畢 → 按「結束」

**生成邏輯**：純前端 JS（線性插值 + 隨機擾動 + 門檻觸發），不需 AI、不需新後端 API。

**現有 10 情境 JSON 的角色**：變成 presets 的參數範本，頁面可載入後調整。

**檔案**：`command-dashboard/static/scenario_designer.html`（~800-1200 行）

**Phase 5 擴充**：加 AI 後果審核面板、inject 卡上傳（照片）、全局態勢監看。

**3-4. PWA TTX 模式** → `medical_pwa.html`、`shelter_pwa.html`
- `sessionStorage` 存 `ttx_session_id`，有值即為演練模式
- 頂部橙色 banner「演練模式」
- 收到 inject → 顯示情境卡（圖片 + 說明）
- 所有 POST 帶 `session_type: 'exercise'`

**3-5. 指揮部 TTX 模式** → `commander_dashboard.html`
- 加 TTX 模式切換（過濾 `session_type='exercise'`）

> **里程碑**：此時可跑人工兵推——主持人手動 inject → 各組在真實系統操作 → audit_log 記錄完整。

---

### Field Node MVP 部分

**來源**：民防感知系統規格書 v1.4（Sprint 0-3 精簡版）
**硬體**：Pi Zero 2W（未到貨），開發期間 Mac 模擬

**3-6. Field Node 軟體（Pi Zero 2W 端）**

| 元件 | 規格 | 驗收標準（來源：測試計畫 v1.4） |
|------|------|------|
| PTT 偵測 | GPIO 4 監聽 Kenwood 2.5mm Ring pin | 觸發延遲 < 0.2 秒，100 次零誤觸發 |
| 錄音 | PyAudio + FFmpeg → `/pending/` | 音檔完整、metadata 正確 |
| Whisper Tiny | int8 本機推論 | 30 秒音訊 < 5 秒（avg）/ < 8 秒（max） |
| Metadata | device UUID、operator ID、channel、UTC 時戳、PTT 秒數、SHA-256 | 欄位齊全 |
| 同步 | 每 30 秒 heartbeat + HTTP POST 上傳 | 成功 → `/uploaded/`（72hr 保留）、失敗 → `/failed/`（重試 5 次） |
| LED | GPIO 17（電源）、27（網路）、22（錄音） | 低電量 1Hz 紅閃、低磁碟 2Hz 紅閃 |
| Mac 模擬 | Python script 鍵盤觸發 + Whisper Tiny + HTTP upload | 端對端可驗證 |

**3-7. Command 接收端**

- `POST /api/field-nodes/upload`：Bearer token 驗證（複用 `pi_nodes` api_key 機制）、SHA-256 hash 去重
- 上傳內容：原始音檔（multipart）+ Whisper Tiny 草稿 + metadata JSON
- 新增表 `field_node_media`：id, field_node_id, operator_id, channel, ptt_duration, audio_path, draft_transcript, formal_transcript, uploaded_at, session_type
- 上傳成功 → 寫入 `field_node_media` → 可透過 `POST /api/events` 產生事件（source='field_node'）
- 檔案：`db.py`、`main.py`

**3-8. Field Node 管理 UI**
- 指揮部設定面板加 Field Node 區塊（複用 pi_nodes UI 模式）
- 顯示：裝置 ID、操作員、最後心跳、上傳狀態
- 檔案：`commander_dashboard.html`

> **里程碑**：前進/安全組語音記錄可上傳指揮部，有草稿文字（Whisper Tiny）。正式文字稿和 AI 分析在 Phase 5。

---

## Phase 4：語音輸入整合（依 Phase 2b 結果）

**前提**：Phase 2b 小模型評估至少一個模型通過（結構化輸出準確率 > 85%，延遲 < 15 秒）。
Phase 2（E2B）已確認 Pi 500 不適合跑 Gemma4 E2B（延遲 40-50s，硬天花板 4.2 tok/s），Phase 4 架構改為下列雙軌：

**架構選項（Phase 2b 結束後二選一）：**

| 選項 | 條件 | 架構 |
|------|------|------|
| A. Pi 本機小模型 | Phase 2b 至少一個模型通過 | Pi 500 跑 Gemma3 4B / Phi-4-mini，Ollama 本機推論 |
| B. 雲端 API | Phase 2b 全部失敗 | PWA 錄音 → 送 Gemini 2.5 Flash → 結構化 JSON 回傳（需網路） |

**實作參考**：AI_reference.md 第二部分 §4（部署 + 可追溯性設計）

**4-1. Pi 端 AI 推論服務**（選項 A）
- Ollama server mode（`127.0.0.1:11434`）作為獨立 process，跑 Phase 2b 通過的小模型
- `server/sync.js`（或新增 `server/ai_client.js`）透過 HTTP 呼叫本機 Ollama
- 不修改 WS 協議，AI 結果作為 delta 欄位發出

**4-1b. 雲端 API 服務**（選項 B）
- PWA 直接呼叫 Gemini 2.5 Flash API（音訊 → JSON，一步到位）
- API key 由 Pi admin 設定頁管理
- 離線 fallback：降級為手動輸入，顯示「AI 暫不可用」提示

**4-2. PWA 語音輸入 UI** → `medical_pwa.html`、`shelter_pwa.html`
- 檢傷頁加麥克風按鈕 → `MediaRecorder` API 錄音
- 錄完 → POST 到本機 Ollama（選項 A）或 Gemini API（選項 B）→ 回傳結構化 JSON
- **人工確認再寫入**：AI 填好欄位，使用者確認或修改，按「確認」才 submit

**4-3. 矛盾偵測**（規則引擎，不依賴 LLM）
- Phase 2 確認 Gemma4 E2B 矛盾偵測率 0%，改用確定性規則引擎實作
- 規則範例：GCS ≤ 8 但分級為綠/黃、血氧 < 90% 但未標記呼吸道問題、年齡 < 15 但使用成人劑量
- PWA 顯示黃色警告框，使用者可忽略或修正

---

## Phase 5：Console AI 統一部署（依硬體決定）

**前提**：AI 推論硬體確定（N100 或替代方案）。
**一台機器，兩個職責**：民防感知 Console（Field Node 音檔 → 正式文字稿）+ ICS_DMAS AI（情勢合成 + TTX 後果）。
**實作參考**：AI_reference.md 第二部分 §3.3（ai_engine.py 三函式設計）、§3.4（API + BackgroundTasks）、§4（模型部署）、§5（TTX 完整流程）；AI_reference.md 第一部分 §伍（TTX 後果引擎邏輯）、§玖（風險對策）；民防感知規格書 v1.4 §3（Console 軟體棧）、§5（AI 雙引擎）；民防感知開發計畫 v1.4 Sprint 4（Whisper Large + Llama 3 部署）

### 模型方案比較（硬體到位後實測決定）

| | 方案 A：原規格 | 方案 B：Gemma 4 |
|---|---|---|
| STT | Whisper Large-v3 int8 | Gemma 4 26B MoE（原生音訊） |
| 摘要/推論 | Llama 3 8B Q4 | 同一個 Gemma 4 26B |
| 模型數 | 2 個 | 1 個 |
| 優勢 | Whisper STT 成熟穩定 | 單模型、原生 function calling、agentic |
| 風險 | 雙模型資源競爭 | 繁中民防術語表現未驗證 |
| 通過標準 | 10×30 秒音檔 < 20 秒、無 OOM | 同左 + 結構化輸出準確率 > 85% |

**5-1. Field Node 正式文字稿**
- Console 收到原始音檔 → 大模型重新推論 → 寫入 `field_node_media.formal_transcript`
- 取代 Whisper Tiny 草稿成為正式記錄

**5-2. `ai_engine.py`（新建）**
- `synthesize_situation()` — calc_engine 輸出 + pi_received_batches + field_node_media → 自然語言情勢摘要
- `generate_decision_options()` — 為事件生成 `decisions.suggested_action_a/b`（欄位已存在，直接寫入）
- `generate_ttx_consequence()` — TTX 後果引擎
- **純函式**，不直接讀 DB，由 main.py 傳入

**5-3. `ai_insights` 表 + API**
- id, generated_at, insight_type, content, structured JSON, confidence, human_reviewed, session_type
- `GET /api/ai/insights/latest`、`POST /api/ai/synthesize`
- FastAPI `BackgroundTasks` 非同步（不阻塞 dashboard 輪詢）

**5-4. 指揮部 AI 面板** → `commander_dashboard.html`
- AI 情勢摘要區塊：時間、信心等級、摘要、依據連結
- `[已審閱]` → `ai_insights.human_reviewed = 1` + audit_log

**5-5. TTX 後果引擎**
- `ttx_consequences` 表（trigger_inject_id, trigger_decision_id, consequence_desc, facilitator_approved）
- 流程：指揮官決策 → AI 生成後果 → 主持人審核 → 核准後推送
- **facilitator_approved = 人工把關**，AI 後果不直接進系統

**5-6. Field Node 文字稿儀表板**
- 指揮部加 Field Node 文字稿瀏覽區（依 unit/channel 分群）
- 即時文字流 + 歷史搜尋（關鍵字、時間、單位篩選）
- 來源：`field_node_media` 表

**5-7. 事件分群與關聯偵測（Event Clustering）**
- 多起事件可能源自同一根因，目前事件列表是平的，指揮官需自行判斷關聯
- `ai_engine.py` 新增 `cluster_events()` — 分析事件的時間、位置（MGRS 鄰近）、類型，自動標記「可能相關」群組
- 範例：區域 B 的「疑似感染」+「隔離需求」+「物資短缺」→ AI 標記為同一群，提示可能是感染擴散
- `ai_insights` 表新增 `insight_type='event_cluster'`，structured JSON 存群組 event_id 列表
- Dashboard 事件面板顯示群組標記（相同顏色 tag 或連結線），點擊展開關聯事件
- **純建議**：AI 標記關聯，不自動合併或升級，指揮官決定後續處置

**5-8. 對話式查詢介面（Conversational Query）**
- 指揮官在高壓環境下可能無暇操作觸控 UI，自然語言查詢可壓縮認知處理時間
- Dashboard 新增查詢輸入框（文字先行，Phase 4 Whisper 整合後可擴充語音）
- `ai_engine.py` 新增 `answer_query()` — 接收自然語言問題，查詢 dashboard API 資料，回傳結構化回答
- 範例：「醫療組目前紅色傷患幾人？」→ AI 查 `/api/dashboard` → 回答「目前紅色傷患 3 人，其中 1 人等待後送」
- 支援的查詢範圍：各組人數/床位/物資現況、事件狀態、Pi 節點連線、趨勢摘要
- `GET /api/ai/query?q=...` — 回傳 `{ answer, sources[], confidence }`
- **不可執行寫入操作**：查詢介面僅讀取，不能建立事件、做裁示或修改任何資料

---

## Phase 6：AAR Pipeline

**實作參考**：AI_reference.md 第二部分 §3.3（aar_engine.py 四函式設計）、§6（AAR 三層分析 + 指揮官審閱追蹤）；AI_reference.md 第一部分 §陸（資料飛輪 + Ground Truth 格式）

**6-1. `aar_engine.py`（新建）**
- `build_timeline()` — audit_log → 決策時間軸（含 inject → 決策延遲）
- `analyze_decision_patterns()` — 跨 session 分析同一人的決策模式
- `compare_to_ground_truth()` — 需要人工建立的因果知識庫
- `generate_report()` — AI 生成 Markdown AAR 報告

**6-2. `aar_reports` 表 + API**
- `POST /api/ttx/sessions/{id}/aar` — 生成 AAR
- `GET /api/aar/reports/{id}` — 讀取報告

**6-3. Ground Truth 知識庫**

**種子資料來源**：`docs/0411-0412_ExcerciseData.md`（福和會三場演習 AAR 草稿 v1）

已有的因果關係（取自真實演習）：

| 決定/狀況 | 後果 | 基準值 | 目標 |
|-----------|------|--------|------|
| 指揮部知道傷患但未主動推播 | 醫療通報延遲 25→32 分（惡化） | 25-32 min | < 2 min |
| 收容/機動橫向不垂直上報 | 指揮部感知被動，< 20% 事件進入體系 | < 20% | > 60% |
| 嫌犯移交無 SOP | 第一、二場失敗，第三場成功 | 0→0→100% | 100%（維持） |
| 靜態威脅偵測無主動巡查 | 第一場平均 64 分延遲 | 64 min → 即時 | < 10 min（已達） |
| 裝備遺失不進指揮體系 | 連續兩場無追蹤無結案 | 0% 通報率 | 100% 強制通報 |
| 國軍失聯無備案程序 | 1 小時+ 無升級應對 | 無 SOP | 30 分觸發升級 |

量測指標（`compare_to_ground_truth()` 的輸入）：
```json
[
  {"metric": "醫療垂直通報延遲", "baseline_min": [25, null, 32], "target_min": 2, "trend": "worsening"},
  {"metric": "收容區垂直通報率", "baseline_pct": [20, 20, 20], "target_pct": 60, "trend": "no_change"},
  {"metric": "靜態威脅偵測延遲", "baseline_min": [64, 33, 2], "target_min": 10, "trend": "improving"},
  {"metric": "嫌犯移交成功率", "baseline_pct": [0, 0, 100], "target_pct": 100, "trend": "improving"},
  {"metric": "全組記錄完整率", "baseline_pct": [50, 50, 100], "target_pct": 100, "trend": "improving"},
  {"metric": "真實意外暫停時間", "baseline_min": [null, 11, 4], "target_min": 3, "trend": "improving"}
]
```

**DMAS 應直接支援的功能**（AAR 文件明確提到）：
- 傷患事件自動提醒 → Phase 5 `ai_engine.synthesize_situation()` 沉默警報
- 持續事件 vs 已結案分類 → events.status 狀態機（已有 open/in_progress/resolved）
- 追蹤執行緒管理 → 新增 event 標記：`tracking_thread: true`（長時間持續追蹤）

---

## Phase 7：安全硬化（部署前）

**實作參考**：安全與網路架構規格 v1.2 §4-5（TLS + LUKS + WireGuard）；民防感知規格書 v1.4 §4（USB Ignition + Panic Wipe 三層）、§5（YubiKey FIDO2）、§9（備份三層）；民防感知開發計畫 v1.4 Sprint 1（Console 加密層）、Sprint 5（YubiKey + Panic Wipe UI）

| 項目 | 範圍 | 規格來源 |
|------|------|---------|
| HTTPS/WSS（mkcert） | 所有節點通訊 | 安全規格 §4 |
| LUKS 全碟加密 | Pi 500 Data 分區、Console OS+Data Cartridge | 安全規格 §5、民防感知 §4.2 |
| WireGuard | 情境 1B 行動網路 | 安全規格 §4.3 |
| YubiKey FIDO2 | 組長高權限、Console 簽章、Panic Wipe 授權 | 民防感知 §4.3 |
| USB Ignition Key | Console 開機需 USB key | 民防感知 §4.1 |
| Panic Wipe（三層） | Console: UI 保護蓋 → 文字確認 → YubiKey；Field Node: GPIO 5 長按 5 秒 | 民防感知 §4.2 |
| 備份（三層） | WAL 即時 + 每小時 Cartridge 備份 + 任務後離線備份 | 民防感知 §9 |
| ICS-214 PDF + 數位簽章 | WeasyPrint + RSA hash footer | 民防感知 §7 |

---

## 依賴圖

```
Phase 0 (bug fix + session_type)
   │
   ├──→ Phase 1 (Wave 5 UI)
   │         │
   │         ↓
   │    Phase 3 (TTX 骨架 + Field Node MVP)
   │         │
   │         ├──→ Phase 4 (醫療/收容語音輸入) [依 Phase 2b 小模型評估]
   │         │         │
   │         │         ↓
   │         └──→ Phase 5 (Console AI 統一部署) [依硬體決定]
   │                   │
   │                   ↓
   │              Phase 6 (AAR)
   │                   │
   │                   ↓
   │              Phase 7 (安全硬化)
   │
   └──→ Phase 2 (E2B 評估，結案) ──→ Phase 2b (小模型) ──→ Phase 4
        （E2B 已完成，2b 待執行）
```

---

## 關鍵檔案清單

| 檔案 | Phase |
|------|-------|
| `command-dashboard/src/db.py` | 0, 1, 3, 5, 6 |
| `command-dashboard/src/main.py` | 0, 1, 3, 5, 6 |
| `command-dashboard/src/calc_engine.py` | 5 |
| `command-dashboard/src/ai_engine.py`（新建） | 5（含 5-7 cluster_events、5-8 answer_query） |
| `command-dashboard/src/aar_engine.py`（新建） | 6 |
| `command-dashboard/static/commander_dashboard.html` | 1, 3, 5 |
| `command-dashboard/static/scenario_designer.html`（新建） | 3, 5 |
| `server/`（index.js / ws_handler.js / sync.js） | 4 |
| `medical-pwa/public/medical_pwa.html` | 0, 3, 4 |
| `medical-pwa/public/sw.js` | 0 |
| `shelter-pwa/public/shelter_pwa.html` | 0, 3, 4 |
| `shelter-pwa/public/sw.js` | 0 |
| Field Node Python 軟體（新建目錄） | 3 |

## 驗證方式

| Phase | 驗證 |
|-------|------|
| 0 | 刪 `data/ics.db` 重建 → session_type 存在、role_detail 可寫入；shelter SW 更新不再靜默失敗 |
| 1 | 啟動 dashboard → deadline reset、決策合併、burn rate 線、流向箭頭正常 |
| 2 | ✅ Pi 500 + llama.cpp + E2B → 量化報告完成（見 BENCHMARK_REPORT.md）；2b 小模型評估待執行 |
| 3 | scenario_designer.html 建 session → inject 推送 → PWA 收到情境卡 → audit_log 完整；Field Node Mac 模擬 → 錄音 → upload → Command 收到 |
| 4 | 醫療 PWA 按麥克風 → 說話 → AI 填欄位 → 確認寫入 |
| 5 | AI 面板顯示情勢摘要；Field Node 正式文字稿生成；TTX 後果生成 → 主持人審核 → 推送；事件分群標記正確；對話式查詢回答正確且僅讀取 |
| 6 | 演練結束 → AAR 生成 → 時間軸 + 決策分析可讀 |
| 7 | mkcert 憑證安裝 → HTTPS/WSS 連線成功；LUKS 加密 → Panic Wipe < 0.5 秒 |

---

## 風險與對策

| 風險 | 對策 |
|------|------|
| Gemma 4 繁中民防術語表現未驗證 | Phase 2 獨立評估，有明確 fallback |
| 26B 硬體方案未定 | Phase 0-4 不依賴 26B，先做能做的 |
| Pi Zero 2W 未到貨 | Mac 模擬開發，到貨後移植 |
| AI 信任校準（過度信任/不信任） | UI 強制顯示信心依據 + TTX 定期注入「AI 錯誤」情境 |
| AI 過度依賴（系統停擺時志工更脆弱） | TTX 加入「AI 全停」情境，測試無 AI 決策能力 |
| Ground Truth 知識庫缺失 | AAR 後果引擎需要人工建立因果知識庫，程式碼無法替代 |

---

*整合來源：[AI_reference.md 第一部分](AI_reference.md)（AI 藍圖 v1.0, 2026-04-11）、[AI_reference.md 第二部分](AI_reference.md)（AI 技術報告 v1.0, 2026-04-11）、民防感知規格書 v1.4 (2026-03-30)、民防感知開發計畫 v1.4 (2026-03-04)、民防感知測試計畫 v1.4 (2026-03-04)、project_status.md*
