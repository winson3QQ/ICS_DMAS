---
name: 架構設計決策
description: COP 架構、模組命名、依賴注入、C0 資料模型、AI/TAK 整合策略等已確認的設計決策
type: project
originSessionId: 09a1a831-5017-4e49-aeb3-29cf3cb75611
---
## COP GUI 資訊架構——待重設計（2026-04-24 決策）

### 決策
Wave 6 COP 功能實作前，**必須先完成 COP 資訊架構重設計（design sprint）**，不得在現有佈局上直接疊加新功能。

### 問題診斷
現有三欄佈局（左：態勢/資源、中：地圖、右：事件追蹤）有三個結構性問題：
1. **左 panel 對象不一致**：量能（收＋醫合計）、傷患入站（僅醫療）、事件（指揮部層級），三個 card 回答不同組、不同層次的問題
2. **決策佇列被埋**：待裁示（最高優先）與已結案事件同列，Commander 最需要看的東西優先序不明確
3. **地圖與事件列表未整合**：點擊事件不 highlight 地圖 marker，地理脈絡與事件列表脫節

### 對 Roadmap 的影響
- **決策主題合併卡片**（原 Wave 5 尾項）：**暫緩**，設計後一起實作，避免在錯誤架構上建功能
- **物資 burn rate 預測線**（原 Wave 5 尾項）：**照做**，chart_utils.js 計算，與佈局無關
- **Wave 6 功能**（熱圖、叢集化等）：建在新 COP 架構上，不在舊架構上疊加

### Design Sprint 產出（實作 Wave 6 前必須完成）
1. 資訊層次定義（Commander 第一眼看什麼）
2. 佈局線框圖（三欄重新分工，地圖與 panel 關係）
3. 地圖 ↔ 事件列表聯動規則
4. Per-role 視角規格（指揮官 vs 幕僚）
5. 更新設計規格書（成為 Wave 6 實作依據）

---

## COP（共同圖像）後端架構原則

已確認的設計方向：

- **聯邦式、最終一致**：各節點（Pi + Command）各自維護本地 COP 副本，斷網仍可運作，復線後同步
- **無單點失敗**：Command dashboard 離線時，Pi 端 PWA 仍可操作
- **多來源正規化層**：Pi push / TAK CoT / 手動輸入 → 統一進 `cop_service`，不各自寫進不同 table
- **時間軸支援**：`cop_repo` 需存快照，Wave 6 時間軸回放用
- **參數化 unit_type**：新單位（front/security）加入時 schema 不重寫，COP 資料模型對 unit_type 保持參數化

## C5 前向相容（C0 一起做，避免屆時重改）

| 項目 | C0 做 | C5 用 |
|------|-------|-------|
| `ttx_injects.signature TEXT NULL` | C0 加欄位 | C5 Orchestrator 填入簽章值 |
| `exercise_service.set_active()` mutex | C0 加邏輯 | C5 Orchestrator 呼叫 |
| `TTX_ORCHESTRATOR` RBAC role | C0 加 role | C5 Orchestrator 用此 token |
| API 設計標注 Orchestrator 為 client | C0 設計時考慮 | C5 直接呼叫，不改 |

**規則**：C5 只加服務和實作，不動 C0 程式碼。

## TTX Orchestrator（C5-A，獨立服務）

- **定位**：Land-and-expand 前鋒產品，可單賣，不捆綁完整 ICS_DMAS
- **架構**：獨立服務 + lite backend（exercises/ttx_injects/aar_entries），讀狀態用 Command read-only API
- **資料**：仍存 Command DB，Orchestrator 無自己的完整 DB
- **進場路徑**：客戶先買 TTX → 跑 N 場 → 升級 ICS_DMAS，資料無縫帶入
- **標準**：無業界軟體標準，流程層面對齊 HSEEP（MSEL 格式、AAR 模板）
- **資安關鍵**：Inject 簽章（最高風險防線）、session mutex、read-only token

## TAK 整合（Wave 7）— 第一等需求，非 stub

- **定位**：EOC 互通標準，競爭差異化，不是「以後再說的 stub」
- 協議：CoT（Cursor on Target）XML，規格必須相容，不能自創格式
- 進入點：`routers/tak.py` + `services/tak_service.py`
- stub 的 schema 欄位必須是真實 CoT 欄位（type, uid, time, stale, lat, lon, hae, ce, le 等）
- TAK 資料正規化後進同一個 COP 層，不開新 table
- 與 MIL-STD-2525 符號渲染同一 Wave（CoT type 欄位即為 MIL-STD-2525 代碼）

## AI 整合架構（第一等需求，非 Phase 2 評估）

### 兩種模式

| 模式 | 觸發時機 | 延遲要求 | 執行位置 |
|------|---------|---------|---------|
| 即時決策支援 | 演練進行中 | 低延遲 | 本地優先（Pi 500 / N100） |
| 演練後分析 | 演練結束後 | 可較慢 | 可走雲端 |

### 抽象介面設計

- `ai_service.py` 用依賴注入，底層 LLM client 可換，router 不感知
- 目前驗證中：**Breeze**（台灣本土 LLM，Ollama 部署，OpenAI-compatible API）
- 未來：未定，介面不鎖定特定模型
- 本地優先原則：斷網仍可提供即時建議；雲端是 fallback，由 config 控制，非預設

### 護城河閉環（ai_recommendations 表）

```
AI 建議 → 指揮官採納/否決 → 結果記錄 → 下次 AI 更準
```

`ai_recommendations` 是法律紀錄 + 訓練資料，不是 nice-to-have：
```
id, exercise_id, made_at, recommendation_type,
content, confidence,
accepted(bool), related_decision_id, outcome_notes
```

### AI 法律責任原則

- AI 建議必須標記「僅供參考」
- 指揮官永遠有 override 權，系統設計不得限制
- 全程稽核：`accepted(bool)` + `related_decision_id` 必須完整

### AI API Endpoints（ai.py router）

```
POST /api/ai/recommend          ← 即時建議（讀當下 COP 狀態）
GET  /api/ai/report/{exercise_id}  ← 演練後分析
GET  /api/ai/export/{exercise_id}  ← ML 訓練資料（state/action/outcome 格式）
GET  /api/ai/compare            ← 跨場次 KPI 比較
```

## 演練資料護城河（C0 資料模型核心）

### 戰略定位

演練資料是「護城河」（competitive moat），不是功能。五個用途：
1. AAR 事後檢討
2. 跨場次比較（進步量化）
3. AI 訓練（state→action→outcome）
4. 外部呈報（消防局、縣市政府）
5. 研究用途

### C0 必須建立的新 Schema

**`exercises` 表**（合併原 `ttx_sessions`，場次 metadata）：
```
id, name, date, location, type(real|ttx),
scenario_summary, weather, participant_count,
organizing_body, status(setup|active|archived),
started_at, ended_at,
-- TTX 專屬欄位（type='real' 時為 NULL）
facilitator, scenario_id
```

> 決策：`ttx_sessions` 表**合併進** `exercises`（Option B）。
> `ttx_injects.session_id` → 改為 `exercise_id` FK → `exercises.id`。
> 原 `ttx_sessions` 表在 C0 migration 後廢棄。
> 理由：TTX 場次本質上是一種演練，統一管理讓 exercise_id 在所有表一致。

**`event_types` 表**（taxonomy，跨場次比較用）：
```
id, code, name_zh, category, default_severity
```

**`resource_snapshots` 表**（正規化時間序列，from pi_received_batches）：
```
id, exercise_id, unit_type, snapshot_at,
total_beds, occupied_beds,
light_count, medium_count, severe_count, deceased_count, source
```

**`aar_entries` 表**：
```
id, exercise_id, category(well|improve|recommend),
content, created_by, created_at
```

**`exercise_kpis` 表**（計算後存起來，AI 訓練和跨場次比較用）：
```
exercise_id, kpi_key, kpi_value, computed_at
```

**`ai_recommendations` 表**（見上方 AI 整合架構）

### 既有表的必要欄位補充

**`events` 表補**：
- `exercise_id` FK
- `event_type_id` FK（接 taxonomy）
- `assigned_unit`
- `acknowledged_at`
- `resolved_at`（AAR 和 AI 訓練都需要）
- `resolution_notes`

**`decisions` 表補完定義**：
```
id, exercise_id, made_by, made_at, decision_type,
content, rationale, affected_units,
outcome_at, outcome_notes
```

### AI 訓練資料結構

每個訓練樣本 = `(state, action, outcome)`：
```
state:   { 當下 resource_snapshot, 進行中 events, 距演練開始幾分鐘 }
action:  { decision 內容 }
outcome: { T+15min 後的 resource_snapshot 變化, events 解決率 }
```

三個表都需要 `exercise_id + timestamp` 才能重建時間軸。

## 法規合規基線

- **個人資料保護法**：醫療病患欄位加存取稽核，不過度收集，purpose limitation
- 演練資料不傳出境：雲端 AI 只能用匿名化資料
- 資料主權：全部本地存，sync 是選項不是必要
- schema 設計不得有「必須連線才能寫入」的欄位

## 命令後端模組結構（C0，完整版）

```
command-dashboard/src/
├── main.py              ≤80 行
├── core/config.py       環境變數、路徑
├── core/database.py     get_conn、init_db、Depends(get_db)
├── schemas/             Pydantic models（跨 router 共用）
├── auth/service.py      hash_pin、verify_login、session
├── auth/middleware.py   auth_middleware、validate_session
├── repositories/        DB CRUD，使用 Depends(get_db)
│   ├── exercise_repo.py     場次管理（新增）
│   ├── cop_repo.py          COP 快照（時間軸）
│   ├── event_repo.py        補 exercise_id / resolved_at
│   ├── decision_repo.py     補完定義
│   ├── resource_snapshot_repo.py  正規化 Pi push（新增）
│   ├── aar_repo.py          AAR 條目（新增）
│   ├── ai_repo.py           AI 建議紀錄 stub（新增）
│   ├── snapshot_repo.py
│   ├── audit_repo.py
│   ├── account_repo.py
│   ├── sync_repo.py
│   └── manual_repo.py
├── services/
│   ├── exercise_service.py  場次管理（新增）
│   ├── cop_service.py       多來源 → COP 正規化
│   ├── pi_push_service.py   Pi 來源 → cop_service
│   ├── dashboard_service.py COP → 前端顯示
│   ├── sync_service.py      三 Pass 對齊協議
│   └── ai_service.py        Breeze 抽象層 stub（新增）
└── routers/
    ├── exercises.py    場次管理（新增）
    ├── cop.py          Wave 6 stub
    ├── tak.py          Wave 7 stub（CoT 欄位正確）
    ├── ai.py           AI stub（新增，即時 + 演練後）
    └── ...其他路由
```

## Pi Server 模組結構（已完成 server-v1.2.0）

- `server/sync.js` 用 `setBroadcast()` 依賴注入解循環依賴
- sync.js 未來擴充 TAK 時加 `tak_client.js`，不動現有結構
- `getCommandUrl()`/`setCommandUrl()` 封裝可變狀態，供 admin API 動態更新

## 韌性設計原則（第 4 條）

斷網仍有基本功能：
- 每個 Pi 節點獨立可用
- Command dashboard 有本地資料副本
- 復線後自動補送（push_queue）
- AI 即時建議：本地模型優先，雲端是 fallback
