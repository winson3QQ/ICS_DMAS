# ICS_DMAS AI 整合開發 Roadmap

**唯一主文件** — 整合來源：Wave 5 待辦、AI 藍圖 v1.0、AI 技術報告 v1.0、民防感知系統規格書/開發計畫/測試計畫 v1.4
原始文件降為參考資料，不需要日常查閱。

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
| 醫療/收容組 | Pi 500（8GB） | Gemma 4 E2B（Q4, ~1.5GB） | 語音 → 結構化欄位填寫 + 矛盾偵測 |
| 前進/安全組 Field Node | Pi Zero 2W（512MB） | **Whisper Tiny**（int8, ~75MB） | 本機草稿 STT，上傳原始音檔至 Console |
| 指揮部 Console | N100 或替代（32GB） | Gemma 4 26B MoE 或 Whisper Large + Llama 3 8B | Field Node 正式文字稿、情勢合成、TTX 後果引擎、AAR |

**Field Node 為什麼不用 Gemma 4**：Pi Zero 2W 只有 512MB RAM，E2B Q4 需 1.5GB，載不進去。且 Field Node 上傳**原始音檔**，Console 用大模型重新推論——Whisper Tiny 草稿品質不影響 Console AI「幕僚」和「演練夥伴」能力。

---

## Phase 0：Bug 修復 + 基礎準備

**目標**：清技術債，為 TTX 和 AI 打地基。可與 Wave 5 同時進行。
**實作參考**：AI 技術報告 §1.4（Bug 清單）、§3.1（session_type schema）

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
| 測試 | 輸入 | 通過 |
|------|------|------|
| STT 準確率 | 10 段演練錄音（15-30 秒，含 CMIST/ISBAR/START 術語） | 字元錯誤率 < 15% |
| 結構化輸出 | 同上 → JSON（性別/年齡/分級/主訴） | 欄位準確率 > 85% |
| 矛盾偵測 | 5 段刻意矛盾錄音 | 偵測率 > 60% |
| 推論延遲 | 30 秒音訊 → 完整 JSON | < 15 秒 |
| 記憶體 | 推論中 + WS server 同時運行 | 無 OOM，RSS < 6GB |

### Fallback
- 全不通過 → 維持手動輸入，不整合語音 AI
- STT 過但結構化不過 → 只做 STT（Whisper Tiny 替代），不做結構化

### 產出
- 評估報告 + prompt template + JSON output schema

---

## Phase 3：TTX 骨架 + Field Node MVP

**目標**：數位化兵推框架 + 前進/安全組進入系統。兩者都不需要 AI。

**實作參考（TTX）**：AI 技術報告 §3.2（完整 CREATE TABLE）、§3.4（API endpoint 設計）、§3.5（facilitator.html + PWA TTX mode）
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

**3-3. 主持人控制台** → 新增 `facilitator.html`
- 建立/管理 session、上傳 inject 卡（照片 + 說明 + 目標組）
- 全局態勢監看（唯讀）、推送 inject、即時時間軸
- Phase 5 再加 AI 後果審核介面

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

## Phase 4：語音輸入整合（依 Phase 2 結果）

**前提**：Phase 2 E2B 評估通過。針對醫療/收容組 Pi 500。
**實作參考**：AI 藍圖 §肆（各組 AI 整合細節）、AI 技術報告 §4（Gemma 4 部署 + 可追溯性設計）

**4-1. Pi 端 AI 推論服務**
- llama.cpp server mode（`127.0.0.1:8090`）作為獨立 process
- `ics_ws_server.js` 透過 HTTP 呼叫本機 llama.cpp
- 不修改 WS 協議，AI 結果作為 delta 欄位發出

**4-2. PWA 語音輸入 UI** → `medical_pwa.html`、`shelter_pwa.html`
- 檢傷頁加麥克風按鈕 → `MediaRecorder` API 錄音
- 錄完 → POST 到 Pi 本機 AI endpoint → 回傳結構化 JSON
- **人工確認再寫入**：AI 填好欄位，使用者確認或修改，按「確認」才 submit

**4-3. 矛盾偵測**
- AI 回傳 `warnings[]`（如「血壓偏低但分在綠區」）
- PWA 顯示黃色警告框，使用者可忽略或修正

---

## Phase 5：Console AI 統一部署（依硬體決定）

**前提**：AI 推論硬體確定（N100 或替代方案）。
**一台機器，兩個職責**：民防感知 Console（Field Node 音檔 → 正式文字稿）+ ICS_DMAS AI（情勢合成 + TTX 後果）。
**實作參考**：AI 技術報告 §3.3（ai_engine.py 三函式設計）、§3.4（API + BackgroundTasks）、§4（模型部署）、§5（TTX 完整流程）；AI 藍圖 §伍（TTX 後果引擎邏輯）、§玖（風險對策）；民防感知規格書 v1.4 §3（Console 軟體棧）、§5（AI 雙引擎）；民防感知開發計畫 v1.4 Sprint 4（Whisper Large + Llama 3 部署）

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

---

## Phase 6：AAR Pipeline

**實作參考**：AI 技術報告 §3.3（aar_engine.py 四函式設計）、§6（AAR 三層分析 + 指揮官審閱追蹤）；AI 藍圖 §陸（資料飛輪 + Ground Truth 格式）

**6-1. `aar_engine.py`（新建）**
- `build_timeline()` — audit_log → 決策時間軸（含 inject → 決策延遲）
- `analyze_decision_patterns()` — 跨 session 分析同一人的決策模式
- `compare_to_ground_truth()` — 需要人工建立的因果知識庫
- `generate_report()` — AI 生成 Markdown AAR 報告

**6-2. `aar_reports` 表 + API**
- `POST /api/ttx/sessions/{id}/aar` — 生成 AAR
- `GET /api/aar/reports/{id}` — 讀取報告

**6-3. Ground Truth 知識庫（非技術）**
- 需要有經驗的指揮官整理「什麼決定 → 什麼後果」因果關係
- JSON 格式：scenario, decision, consequence, alternative, lesson
- 程式碼解決不了，人必須先建

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
   │         ├──→ Phase 4 (醫療/收容語音輸入) [依 E2B 評估]
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
   └──→ Phase 2 (E2B 評估) ──→ Phase 4
        （與 Phase 1 平行）
```

---

## 關鍵檔案清單

| 檔案 | Phase |
|------|-------|
| `command-dashboard/src/db.py` | 0, 1, 3, 5, 6 |
| `command-dashboard/src/main.py` | 0, 1, 3, 5, 6 |
| `command-dashboard/src/calc_engine.py` | 5 |
| `command-dashboard/src/ai_engine.py`（新建） | 5 |
| `command-dashboard/src/aar_engine.py`（新建） | 6 |
| `command-dashboard/static/commander_dashboard.html` | 1, 3, 5 |
| `command-dashboard/static/facilitator.html`（新建） | 3, 5 |
| `ics_ws_server.js` | 4 |
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
| 2 | Pi 500 + llama.cpp + E2B → 餵演練錄音 → 量化報告 |
| 3 | facilitator.html 建 session → inject 推送 → PWA 收到情境卡 → audit_log 完整；Field Node Mac 模擬 → 錄音 → upload → Command 收到 |
| 4 | 醫療 PWA 按麥克風 → 說話 → AI 填欄位 → 確認寫入 |
| 5 | AI 面板顯示情勢摘要；Field Node 正式文字稿生成；TTX 後果生成 → 主持人審核 → 推送 |
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

*整合來源：AI 藍圖 v1.0 (2026-04-11)、AI 技術報告 v1.0 (2026-04-11)、民防感知規格書 v1.4 (2026-03-30)、民防感知開發計畫 v1.4 (2026-03-04)、民防感知測試計畫 v1.4 (2026-03-04)、project_status.md*
