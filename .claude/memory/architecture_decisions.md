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

---

## Compliance 程式架構決策（2026-04-25 決策）

### 決策
建立正式 compliance 程式，產出可用於投標 / 行銷 / 稽核的文件體系。

### 涵蓋標準（鎖定後不變）

**資安**：NIST SP 800-53 Rev.5（Moderate baseline）+ SP 800-63-3 + CSF 2.0 + SP 800-218 SSDF + FEMA NIMS/ICS 508
**軟體品質**：ISO/IEC 25010:2023 + ISO/IEC 5055:2021 + CNS 25010 + OWASP ASVS 4.0 L2 + CIS Controls v8
**流程成熟度**：OWASP SAMM 2.0 + SLSA v1.0 + DORA metrics
**Taiwan**：資安法 + 附表十 + 個資法 PDPA + 災害防救法 + 政府資通安全整體防護計畫 12 項

**不納入**：ISO 27001 外部驗證（C6）/ FedRAMP / HIPAA / CMMI

### 文件結構（3 新 + 既有擴充）

**新增（`docs/compliance/`）**：
- `matrix.md` — 主 deliverable，控制項 × 組件 × 狀態對照
- `threat_model.md` — STRIDE + 信任邊界
- `security_policies.md` — 6 policies 一檔（800-53 xx-1 family 要求）

**擴充既有**：
- `docs/ROADMAP.md` 每個 Cx 標註適用標準 + 新 Cx（C2-E/C2-F/W-Cx/擴充 P-Cx）
- `docs/commercialization_plan_v1.md` Session D 補 compliance 章節（投標用）
- `CLAUDE.md` 入口指引

### 執行方式（4 段式 Audit）

Session A（Auth/Transport/Schema）→ B（PII/Audit/Frontend）→ C（Quality/Deploy/Ops）→ D（NIMS + 整合）

每個 session 在 matrix.md「Session Log」區塊更新進度，避免換 session 失憶。

### 關鍵原則
1. 架構層級對照，不做 line-by-line code review
2. 寧可少說不誇大 — 未完成項目明確標示「規劃中」
3. 新增 Cx 最小化（已新增：C2-E / C2-F / W-Cx prefix + 擴充 P-Cx）
4. 跨組件協議統一（C1-D 擴大為涵蓋 command + pi + pwa 三組件的 logging + audit 協議）

### 對 Roadmap 的影響
- **C1-A Phase 2 範圍擴大**：原 RBAC OBSERVER + 對齊英文 role → 改為 4-role（含系統管理員）+ role_detail ICS 職稱 + operational_periods + Transfer of Command + duty_log + Unity of Command 偵測
- **C1-D 範圍擴大**：原純 audit hash chain → 擴大為跨組件可觀察性 + audit 協議 + 8 個優先埋 log 位置明細
- **C1-C 範圍擴大**：原 Fernet 欄位加密 → 三層加密策略（Fernet / SQLCipher / LUKS）
- **新 Cx**：C1-G（WebSocket 安全）、C2-E（供應鏈 / SSDF）、C2-F（生產韌性 + DB 並發 + dev/prod debug）、C3-F（Docker + Binary IP 保護）、C3-G（客戶自助支援）、C5-E（AI 資安）
- **C2-C 擴充**：加 GitHub Security suite（CodeQL / Dependabot / secret scanning）
- **C3-B 擴充**：加 NTP / chrony、WAL mode、LUKS 全碟加密
- **Wave 6 擴充**：COP 事件自動分類 + AI 推薦自動排序 + QR Code 5 分鐘快照
- **Wave 7 拆分**：7a TAK 整合 + 7b MANET 前進組網路
- **新 Cx prefix**：W-Cx（PWA 同步項，先前未獨立追蹤），對應新增 W-C1-G
- **v2.1.0 標的**：Compliance audit 完成後重估時程

---

## Decision A：IP 策略 — Open Core（2026-04-25 決策）

### 決策
採 **Open Core** 模式（商業化 v1.8 既定方向的具體落實）。

### 分層策略

| 層 | 模式 | 包含 | 發布方式 |
|---|---|---|---|
| **閉源核心** | Binary compiled（Cython 或 Nuitka）| `services/ai_service.py`、TTX Orchestrator、`calc_engine` 核心邏輯、AI prompt templates、licensing (`C4`) | Docker image 私有 registry |
| **開源外殼** | 原始碼公開 | schemas、routers、auth middleware、UI、PWA、部分 services、migration 框架 | GitHub public repo |
| **部署** | Docker 容器化 | 所有組件（command-dashboard / pi-server / nginx / step-ca）打包 | `docker compose pull && up -d` |

### 對 Roadmap 影響
- 新 **C3-F Docker + Binary IP 保護**
- 相依 C4（Tier licensing）
- 影響開發流程：需建 CI build pipeline（Binary 編譯 → image push）

### 參考
- 商業化計畫 v1.8 §IP 策略章節
- Red Hat / Elastic / MongoDB 等 Open Core 先例

---

## Decision Set C：Session A audit 4 議題（2026-04-25 決策）

Session A audit 揭露的 4 個跨 session 議題的最終設計決策。

### C1：Session 雙層 timeout（NIST AC-12 / ASVS V3.3.2/V3.3.3）

- **Idle timeout 30 分鐘**：超過閒置自動登出（無 API 呼叫即視為 idle）
- **絕對 timeout 14 小時**：對應指揮官 12 小時班 + 2 小時交班緩衝（取代現有 8 小時）
- **28 分鐘警告**：UI 彈警示「2 分鐘後將登出，按一下續期」
- 對應 **C1-A Phase 2** 範圍

### C2：Session 漸層綁定（IP + UA family）（ASVS V3.7 / NIST SC-23）

不採嚴格 IP 綁定（演練切網會打斷指揮）；改漸層判斷：

| 變化情境 | 處置 |
|---|---|
| 全不變 | 通過 |
| IP 變但網段（/24）不變 | 通過 + audit「IP shifted within network」|
| UA family 同、網段變 | 通過 + 要求 PIN lightweight re-auth + audit |
| UA family 變 | 強制完整重登入 |
| UA family + 網段都變 | 強制重登 + audit SEVERITY=HIGH |

**UA family 規則**：解析 UA 字串只取大類（`Safari-iOS` / `Chrome-Win` 等），不存完整 UA（避免 OS 更新就 mismatch）。

**配套 5 道防線**（與綁定一起構成深度防禦）：
1. Idle timeout（C1）
2. TLS 1.2+ 強制（已有）
3. Token rotation：敏感操作（改 role / 刪帳號 / Transfer of Command）後發新 token
4. Audit 記所有 session 變化（IP shift / network change / UA mismatch）
5. 「上次登入 IP / 時間」UI 提示（使用者自己察覺異常）

對應 **C1-A Phase 2** 範圍。

### C3：Soft delete（AC-2(3) / 個資法稽核可追溯）

- `delete_account()` 改為 `UPDATE accounts SET status='archived', deleted_at=now()`
- 新增欄位：`deleted_at TEXT`（migration M006 一併加）
- UI 預設不顯示 archived 帳號；admin 可選看
- 真正物理刪除：個資法資料主體要求時才走獨立流程（留 `deletion_log`）
- audit_log operator 字串保留歷史（join archived 帳號還能查到 display_name）

對應 **C1-A Phase 2** 範圍。

### C4：Rate limit 持久化 — 純 SQLite（NIST AC-7 / CIS §6.3）

- in-memory dict → SQLite `rate_limit_buckets` 表
- schema：`(scope, key, timestamp)` — scope=「login」/「admin_pin」/ 未來其他；key=IP；timestamp=每次嘗試時間
- 查詢時 `DELETE` 過期的 + `COUNT` 視窗內的
- restart 不清零

**選 SQLite 而非 Redis 的 compliance 理由**：
- SSDF / SLSA 不加 supply chain dep
- SBOM（CycloneDX）不增元件
- 客戶維運：不需多裝一個 service
- Policies §5 recovery：一個 DB 集中備份

對應 **C2-F** 範圍（與生產韌性 + DB 並發 retry 同步實作）。

---

## Decision E：功能與 License 解耦（2026-04-25 決策）

### 原則

v2.1.0 階段（C1-C5 各 Cx 實作期間），**所有功能寫成「license 無感」**。License 機制由 C4（v2.2.0）統一接入。

### 三條規則

#### 規則 1：法規 / 安全合規功能 — **絕對不能**用 license 關

下列項目**全 tier 必須開啟**，不接受 license 控制：

- **NIST 800-53 AC-7 / CIS §6.3** 登入 lockout / rate limit
- **NIST 800-53 AU-2/9** audit log + 完整性保護（hash chain）
- **NIST 800-53 SC-8** TLS 1.2+ 強制
- **NIST 800-53 IA-5** PIN hash + 強度檢查
- **個資法 §27** 安全維護義務（含至少應用層 PII 加密）
- **個資法 §12** 72h PDPC 通報程序
- **附表十防護基準**全 12 項基線
- **OWASP ASVS L2** 認證 / 存取 / 加密 / data protection 必要項

理由：tier 是商業價格分層；法規是法律底線。**降低底線 = 違法**，不是省錢。

License 控制範圍**僅限 feature / capability**（哪些模組開、AI 是否啟用、Pi 節點上限、外部 API 是否開放等）。

#### 規則 2：License 須支援彈性發行模式

License 機制必須能滿足以下情境而**不需改程式**：

- **三層標準 SKU**：Tier 1 / Tier 2 / Tier 3（template 一鍵套用）
- **客製化 SKU**：單一客戶特殊組合（例：Tier 2 + AI 但不要 voice）
- **試用 license**：時限性全開，過期後自動降級（`expires_at` + fallback tier）
- **Promo / 季節 license**：限時加開特定 feature（例：演練前 1 個月免費開 TTX）
- **A/B test license**：兩組客戶不同 feature 組合，比較採購率
- **降級**：客戶不續約 → 自動回 Tier 1 baseline，不直接停服務

### 規則 3：解耦的具體作法

#### 程式碼層（C1-C5 階段）

**所有 feature gate 透過 `License` dependency**：

```python
# C1-A Phase 2 階段就這樣寫
@router.post("/api/admin/accounts")
def create_account(
    body: CreateAccount,
    license: License = Depends(get_license),
):
    if body.role == "觀察員" and not license.has_feature("observer_role"):
        raise HTTPException(403, "Observer role 需對應 license feature")
    ...
```

**禁止**寫法（會造成日後重工）：
```python
# ❌ 直接判斷 tier 字串
if config.tier == "tier1": ...
# ❌ 在功能模組裡硬編 license 邏輯
if not check_paid_customer(...): ...
```

#### License 服務層（C4 才實作）

```python
class License(Protocol):
    customer: str
    issued_at: datetime
    expires_at: datetime | None
    features: dict[str, Any]   # feature flag 字典
    limits: dict[str, int]     # 數量上限（max_pi_nodes 等）

    def has_feature(self, name: str) -> bool: ...
    def get_limit(self, name: str) -> int: ...
    def is_valid(self) -> bool: ...   # 含 expires_at 檢查
```

#### Stub 階段（C1-C5 實作期間，C4 完成前）

提供「全開 stub license」：
```python
def get_license() -> License:
    """C4 完成前用，實作後換成 license file 解析"""
    return StubLicense(features={"observer_role": True, "ttx_module": True, ...})
```

C4 落地時換掉 `get_license()` 一個函式，**所有 feature gate 自動接上**真實 license。**零重工**。

#### Feature flag 命名 convention

- 模組類：`{module}_module`（例：`shelter_module`、`medical_module`、`ttx_module`）
- 能力類：`{capability}`（例：`observer_role`、`ai_prediction`、`voice_input`、`field_node_upload`、`physical_security`）
- 上限類：放 `limits` 不放 `features`（例：`limits.max_pi_nodes = 10`）

### 對 Roadmap 的影響

- **v2.1.0 階段**所有 Cx 實作要遵守此原則 — 寫 `Depends(get_license)` 注入點，不寫 tier hardcode
- **C4（v2.2.0）**只實作 license file 解析 + 簽章驗證 + `get_license()` 真實版
- **C1-A Phase 2 / C1-C / C5-A/B/C/D** 等需要 feature gate 的 Cx，**現在**就要把 `Depends(get_license)` 寫進 router

### 違反此原則的偵測

- Code review 抓 `tier == "tier1"` 字串比對 → 退件
- ruff 自定義規則（C2-C 擴充時加）：grep `tier ==` 警告
- PR template DoD 加一條：「無 hardcoded tier 判斷」

---

## Decision Set D：Session B audit 5 議題 + 實作策略（2026-04-25 決策）

### D0：實作優先順序總原則（橫貫所有 Cx）

> **原則**：command-dashboard 優先實作；Pi server / PWA 改動若**影響 command 行為**也視為優先；其餘 Pi / PWA 改動延後。

落地規則：
- 設計必須跨組件思考（不能 design 完才發現 Pi 不能配合）
- 實作排程 command 先，Pi / PWA 後續 wave 補
- 例外：Pi / PWA 的改動如果**會改 command 收到的資料 / 行為**（例：correlation ID 在 Pi 端產生、WS 訊息簽章 Pi 端要送），那部分要跟 command 同步推進

### D1：C1-F 模組化提前

`commander_dashboard.html` 376KB monolithic（10,000+ 行 inline JS）是後續所有功能的硬阻礙：
- C1-A Phase 2 RBAC：前端 role-based UI 隱藏需 module 化才好寫
- C1-D correlation ID：前端發 request 需中介 module
- W-C1-A PWA 對齊：前後端模組化 pattern 一致才好維護

**決策**：**C1-F 提前到 C1-A Phase 2 之前**（或前 2 週併行起步）。

實際拆解：
1. **C1-F 第一波**：抽出 module skeleton（ES modules + esbuild bundle 設定）+ 取出 auth / session module
2. **C1-A Phase 2**：在 C1-F 第一波基礎上實作 RBAC（後端 require_role + 前端 role-based render）
3. **C1-F 第二波**：CSP 升 enforce + nonce-based + 其他 module 收尾

### D2：跨組件 audit hash chain — 設計跨組件，command 先實作

跨組件 correlation ID + hash chain 設計原則：

**Correlation ID（事件追蹤）**：
- 起源於最早接收 user action 的組件（PWA 或 command browser）
- 格式：UUID v4
- 跨組件傳遞：
  - PWA → Pi：WS msg payload 帶 `corr_id`
  - Pi → command：HTTP push body / Bearer header 都帶 `corr_id`
  - Command 內部：FastAPI middleware 自動 propagate to log + audit
- 落地階段：
  - **第一階段**：command 內部 correlation ID（middleware + structlog + audit_log 欄位）
  - **第二階段**：Pi 端接收 + 轉發
  - **第三階段**：PWA 端產生 + 上傳

**Audit hash chain**：
- 設計：每筆 audit_log 含 `prev_hash` + 自身內容 → SHA-256 → `cur_hash`
- 跨組件：每組件各自維護一條 chain（command / pi / pwa 各一）；command 端再做「meta-chain」串接 Pi 推送的批次 hash
- 校驗：定期 / 啟動時 verify 整條 chain
- 落地階段：
  - **第一階段**：command audit_log 加 `prev_hash` + `cur_hash` 欄位 + verify 邏輯
  - **第二階段**：Pi audit_log 加同樣欄位
  - **第三階段**：PWA audit_log 加 + 上傳時帶 chain 簽章

對應 **C1-D**（command）+ **P-C1-D**（pi）+ **W-C1-D**（pwa）。

### D3：PII redaction by role — 必須合規

> 個資法 §6 + §27：特種個資（醫療）必要範圍才能蒐集 / 處理 / 利用。觀察員 role 沒有業務必要性看完整病患姓名 / 過敏 / 用藥。

**決策**：實作 role-based PII redaction：

| Role | 病患資料可見範圍 |
|---|---|
| 系統管理員 | 完整（包含姓名、年齡、性別、症狀、過敏、用藥）|
| 指揮官 | 完整 |
| 操作員 | 依職責（醫療相關職務 = 完整；其他 = 僅 display_id + 傷情等級）|
| **觀察員** | **匿名化**：只顯示 display_id（例：M-001）+ 傷情等級色（紅 / 黃 / 綠 / 黑）+ 後送狀態；不顯示姓名 / 年齡 / 症狀細節 |

**實作位置**：
- 後端 redact layer：`services/pii_filter.py` — 依 session role 過濾 response payload
- 套用點：所有 endpoint 回 patient / person 資料時 middleware 過濾
- audit log：observer 看了什麼匿名化資料也要 audit（PT-7 要求）

**收容組（persons）對應**：
- 觀察員看：床位佔用率 + 入站數，不看姓名

對應 **C1-A Phase 2**（role gate）+ **C1-C**（PII filter）。

### D4：P-C1-E 範圍擴大確認

P-C1-E 從原本「Schema version API + GUI 顯示」擴大為：
- Pi 端建立 **正式 `schema_migrations` 版本表**（取代現有 ad-hoc CREATE IF NOT EXISTS）
- 引入 migration runner 邏輯（對齊 command 的 `_MIGRATIONS` list pattern）
- 提供 `GET /admin/schema-version` API
- shelter + medical PWA admin 介面顯示 Pi 當前 schema version

對應 **P-C1-E**。

### D5：B-FIX-01 isAuthed bug → 併入 P-C1-G

`server/ws_handler.js` 的 `clear_table` 檢查 `ws.isAuthed`（永遠 false 的 dead-deny）：
- 不 hotfix（按實作策略 D0：Pi-side 不直接影響 command 當前行為）
- 併入 **P-C1-G**（Pi WS 安全與可靠性）：
  - 修正 isAuthed flag（auth 成功時 set）
  - 或刪除 clear_table msg type（如不需要）
  - 同時補 WS 訊息簽章 + 重放防護 + heartbeat 完整管理

對應 **P-C1-G**。

---

## Decision B：DB 並發 — SQLite + retry（短期）/ PG（長期）（2026-04-25 決策）

### 問題
Pi 500 + 多 Pi Zero 2W 同時 PTT 推送 → SQLite 單寫者限制 → `database is locked` 錯誤。

### 決策
- **短期（6 月演練前必做）**：SQLite + connection pool + exponential backoff retry + **序列化 writer queue**
- **中期（Wave 7 後評估）**：視實際併發壓力決定是否升 PostgreSQL
- **長期（多客戶 SaaS 階段）**：混合架構 — Pi 端 SQLite（本地小規模）+ command-dashboard PG（多 Pi 彙總）

### 選擇 A（短期）的理由
- 演練規模 5-10 個 Pi Zero 2W，SQLite + WAL + 正確 retry 足夠（實測 10-20 writes/sec 上限）
- 工作量小（純應用層），不動 schema 或部署架構
- PG 升級工作量大（migration、部署複雜度、記憶體 + SSD 成本），不該在 6 月前做
- 保留升級路徑：repository 層抽象化後，未來換 PG 只改 `core/database.py`

### 實作位置
- C2-F 範圍內（生產韌性）
- 具體：`core/database.py` 加 retry decorator；寫入類 service 用序列化 writer queue

### 量測標準
- 模擬 10 Pi 同時 push 30 秒，錯誤率 <1%
- 需在 C2-A security tests 加 concurrent write test

---

---

## C1-A 首次啟動 PIN 交付——C3-B 解決（2026-04-24 決策）

### 問題
首次啟動產生的隨機 PIN 目前只印在 console 和寫入 `~/.ics/first_run_token`。
部署到 Pi 後台服務（systemd）時，部署者看不到 console，token 檔也需要 SSH 才能讀。

### 決策
**現在的做法是過渡方案**，C3-B（一鍵安裝腳本）實作時解決：
- 安裝腳本最後一步要求部署者設定初始 PIN（部署者一定在場）
- 或印出隨機 PIN 並要求確認後才結束腳本

### 業界參考
- 方案 A（安裝時設定）：Enterprise 軟體主流，`bash install.sh --initial-pin XXXXXX`
- 方案 B（本機限定首次設定）：pfSense / Proxmox / Grafana 做法，初始狀態只允許 localhost 訪問
- 方案 C（硬體衍生密碼）：路由器做法，從 Pi serial number 衍生 PIN，貼紙印在機器上

**選定：方案 A**（安裝腳本設定），搭配方案 B（首次設定前只開 localhost）作為保險。

### 不動 C1-A 現有程式碼
現有的 `ensure_initial_admin_token()` 邏輯不變，C3-B 的安裝腳本在啟動服務前先呼叫 CLI 設定初始 PIN，不進入 first-run 流程。
