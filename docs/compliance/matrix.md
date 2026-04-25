# ICS_DMAS Compliance Matrix

> **主 deliverable**：控制項 × 組件 × 狀態對照表。投標 / 稽核 / 行銷主要依據。
> **最後更新**：2026-04-25（骨架建立，Session A/B/C/D 填入內容）
> **審查原則**：架構層級對照，非 line-by-line code review。
>
> 狀態代號：✅ 符合 / ⚠️ 部分符合 / ❌ 未實作 / N/A 不適用（附理由）

---

## Session Log（給下一個 session 的 context）

> **重要**：每個 session 結束前必須更新此區。切換 session 讀此區就能延續工作。

### 整體進度

| Session | 範圍 | 狀態 | 完成日期 | Context 要點 |
|:---:|---|:---:|---|---|
| A | C0 + C1-A + C1-B + C1-E（Auth/Transport/Schema） | ✅ 完成 | 2026-04-25 | 31 個 gap，Decision Set C 4 議題決議 |
| B | C1-C + C1-D + C1-F + W-C1-* + P-C1-*（PII/Audit/Frontend） | ✅ 完成 | 2026-04-25 | 28 個 gap + 1 個 immediate fix（B-FIX-01 isAuthed bug）+ 6 個亮點 |
| C | C2 + C3 + P-C2-* + W-C2-*（Quality/Deploy/Ops） | ✅ 完成 | 2026-04-25 | 30 個 gap + 8 個亮點；SSDF L2 候選；SAMM L1.5；SLSA L1；DORA 低成熟度；備份/DR 全失 |
| D | Wave 功能 + NIMS + ICS 508 + 整合 | ⏸ 未開始 | — | — |

### Session A 執行狀況（2026-04-25）

**完成**：NIST AC / IA / SC / AU 主要控制項對照；800-63-3 AAL/IAL；ASVS V2/V3/V4 主要要求；CSF PROTECT-PR.AA / PR.DS（部分）；12 大重大 gap 列入 Gap Register。

**Session A 用 Explore agent 架構層審視的結論**（10 大事實 + 12 大 gap，見下節區）：
- ✅ PBKDF2-SHA256 (100k iter, 16-byte salt) 帳號 hash
- ✅ Session header-based (X-Session-Token, UUID v4, 8hr timeout, SQLite 持久化)
- ✅ 登入 lockout 持久化（5x15min）; Admin PIN lockout 持久化（5x30min）
- ✅ First-run gate 完整（whitelist + 423 擋阻）
- ✅ TLS 1.2/1.3 + Mozilla Intermediate cipher + HSTS 1yr + Security headers 完整
- ✅ Pi push Bearer token 驗證
- ✅ Schema migration append-only 追蹤
- ✅ 登入錯誤訊息不洩漏帳號存在性
- ✅ Header-based session 天生抗 CSRF
- ✅ 核心 auth 邏輯分層清晰（auth/service, middleware, rate_limit, first_run_gate）

**重大 gap**（下 Gap Register 詳列）：
- ❌ 後端無 role-based endpoint gate（C1-A Phase 2 核心 target）
- ❌ 無 Separation of Duties / 最小權限（Admin PIN 是 all-or-nothing）
- ❌ Soft delete 未真實施（`delete_account()` 是 hard DELETE）
- ⚠️ Rate limit in-memory，server restart 清零
- ⚠️ Audit log 無 hash chain、無保存 / 清除策略（C1-D 範圍）
- ⚠️ CSP 含 `unsafe-inline`（C1-F 升 nonce-based）
- ⚠️ No mTLS（Pi↔Command、WS 都 Bearer token only）
- ⚠️ 無 correlation ID 跨組件（C1-D 範圍）
- ⚠️ WebSocket 認證層模糊 —— Pi server 端 ws_handler 無明顯 token 檢查（待 Session B 或 C1-G 補）
- ⚠️ 無 session idle timeout（只有絕對 timeout）
- ⚠️ 無登入 banner（AC-8）
- ⚠️ PWA 無 MDM / device enrollment（AC-19）

### 讀過的檔案清單（避免 session 間重複讀）

**Session A 已掃 / 已映射**（架構層）：
- `command-dashboard/src/db.py` (1594 行) — schema / audit_log / migration
- `command-dashboard/src/auth/service.py` — session 管理
- `command-dashboard/src/auth/middleware.py` — 全域 auth middleware
- `command-dashboard/src/auth/first_run_gate.py` — 首次設定閘
- `command-dashboard/src/auth/rate_limit.py` — 登入 rate limit
- `command-dashboard/src/repositories/account_repo.py` — 帳號 CRUD + lockout
- `command-dashboard/src/routers/admin.py` — Admin PIN + 帳號管理 router
- `command-dashboard/src/routers/auth.py` — login/logout router
- `command-dashboard/src/core/security_headers.py` — CSP middleware
- `command-dashboard/src/core/database.py` — migration 框架
- `command-dashboard/src/core/config.py` — 環境變數 / 豁免清單
- `deploy/nginx/conf.d/security-headers.conf` — nginx security headers
- `deploy/nginx/conf.d/ssl-common.conf` — TLS config
- `command-dashboard/src/services/pi_push_service.py` — Pi push 驗證
- `deploy/step-ca/README.md` — PKI 架構說明

**Session B 已掃 / 已映射**（架構層）：
- `server/index.js` / `routes.js` / `auth.js` / `middleware.js` / `audit.js` / `migrations.js` / `db.js` / `sync.js` / `ws_handler.js` / `config.js` / `logger.js`（全 Pi server）
- `shelter-pwa/public/shelter_pwa.html`（3264 行 monolithic）+ `sw.js` + `manifest.json`
- `medical-pwa/public/medical_pwa.html` + `sw.js` + `manifest.json`
- `command-dashboard/static/commander_dashboard.html`（376 KB monolithic）

**Session C/D 可能需要補讀**：
- `.github/workflows/*.yml` — CI 設定（Session C 必讀）
- `command-dashboard/tests/**` — 測試覆蓋率分析（Session C）
- `command-dashboard/pyproject.toml` / `requirements.txt` — 依賴清單（Session C SBOM 用）
- `package.json` 系列 — Node.js 依賴（Session C）

### 未決定 / 待追問（cross-session issue）

**Session A 4 議題 — 已決議**（2026-04-25，詳見 architecture_decisions.md Decision Set C）：

1. ✅ **Session 雙層 timeout**：30 min idle + 14 hr 絕對 + 28 min 警告（C1-A Phase 2）
2. ✅ **Session 漸層綁定 IP + UA family + 5 道配套防線**（C1-A Phase 2）
3. ✅ **Soft delete**：status='archived' + deleted_at 欄位，物理刪走獨立流程（C1-A Phase 2，M006 一併加欄位）
4. ✅ **Rate limit 純 SQLite 持久化**：選 A，不用 Redis（C2-F）

**Session cookie vs header**：保留 X-Session-Token header（抗 CSRF），不改 cookie。

**Session B 5 議題 — 已決議**（2026-04-25，詳見 architecture_decisions.md Decision Set D）：

1. ✅ **B-FIX-01 isAuthed bug**：併入 P-C1-G（按實作策略 D0：Pi-side 不影響 command 當前行為，不 hotfix）
2. ✅ **C1-F 提前**：移到 C1-A Phase 2 之前或併行（376KB monolithic 是 RBAC 硬阻礙）
3. ✅ **跨組件 audit hash chain 設計定案**：每組件各維護一條 chain + command 端 meta-chain；correlation ID 跨組件 propagate；command 先實作（C1-D）/ Pi 跟進（P-C1-D）/ PWA 跟進（W-C1-D）
4. ✅ **P-C1-E 範圍擴大**：Pi 建正式 `schema_migrations` 表 + runner + API + PWA GUI
5. ✅ **PII redaction by role**：觀察員只看 display_id + 傷情等級色；姓名 / 症狀 / 過敏 / 用藥不顯（個資法 §6 §27 必合規）；redact layer 在 command service 層（C1-A Phase 2 + C1-C）

**實作策略總原則（Decision D0）**：command 優先；Pi/PWA 改動若影響 command 行為視為優先；其餘 Pi/PWA 改動 wave 後補。

---

### Session C 揭露的議題（待 Session D 收 / 你決定）

#### 立即可動（已完成於本 commit）
- ✅ **G-C10 SECURITY.md**：`SECURITY.md` 已建（含 PDPC 72h 通報流程、SLA、scope）
- ✅ **G-C15 legacy dead code**：`src/db.py` + `src/main_legacy.py` 已刪；`setup.sh` 改用 `core.database.init_db`；`pyproject.toml` 移除排除清單
- ❌ **G-C19**：driving driving false positive（`.gitignore` 已涵蓋 `*.db`），實際無此問題
- ✅ **G-C28 PR template**：`.github/PULL_REQUEST_TEMPLATE.md` 已建（含 DoD checklist + compliance 欄位）

#### 已知 bug 待修
- **G-C05 TOCTOU mutex**：演練 concurrent activate xfail 標記在 test_concurrent.py — 不是新 Cx，是要修的 known bug

#### 商業 / 資源決策題
- **G-C01 + G-C02 + G-C03 備份 / DR**：6 月演練前**必須**做。要我把它升 Critical Cx priority 還是 timeline 重排？
- **G-C04 IR plan + 72h 通報**：個資法 §12 + IR-6 + IR-8 三個都依賴；要排哪個 Cx？
- **G-C06 TLS hardcode + renewal**：C3-A（config 外部化）+ C3-B（install 擴）共同處理

### 重大架構發現（觸發 ROADMAP 或 architecture_decisions 更新的）

**無新 Cx 需加**。 Session A 所有發現都能落入既有 Cx：
- Role-based endpoint gate → **C1-A Phase 2**（已規劃範圍）
- Rate limit 持久化 → 建議併入 **C1-A Phase 2**（同 auth 範疇）
- Hard delete → 建議併入 **C1-A Phase 2**
- Audit log hash chain / 保存 / 清除策略 → **C1-D**（已規劃）
- CSP unsafe-inline → **C1-F**（已規劃）
- mTLS → **C1-G**（已規劃）
- Correlation ID → **C1-D**（已規劃）
- WS 認證層細節 → **C1-G**（已規劃）
- Session idle timeout → **C1-A Phase 2**（建議併入）
- Login banner (AC-8) → **C1-A Phase 2**（小項，低優先）

**唯一可能需要 architecture_decisions 新記的**：Rate limit 持久化做法（in-memory + SQLite fallback, or 純 SQLite, or Redis）。**暫標 Session B 再定**（因影響 audit log 協議，會跟 C1-D 一起討論）。

---

## Meta：Scope 與基線確認

### 標的系統
- `command-dashboard/`（FastAPI + SQLite，Python 3.11+）
- `server/`（Node.js Pi server，原 `ics_ws_server.js`）
- `shelter-pwa/`（Progressive Web App，Dexie + WebSocket）
- `medical-pwa/`（Progressive Web App，Dexie + WebSocket）
- 部署基礎：`deploy/nginx/` + `deploy/step-ca/`

### 標準基線鎖定
詳見 [README.md § 涵蓋標準](README.md#涵蓋標準已鎖定)。關鍵選擇：
- **NIST 800-53 Moderate**（非 Low，因系統儲存個資 / 醫療資料）
- **SBOM 格式：CycloneDX**
- **Policy 語言**：繁中為主 + 術語英文（NIST 原文 reference）

### 評估方法
- 架構層級對照（design / data flow / 責任歸屬），**不做** line-by-line code review
- 證據（evidence）欄位標示「file:line」或「doc:section」指向確實存在的實作
- 無實作但規劃中 → 狀態 ⚠️ + gap 欄位描述 + target Cx
- 完全不做 → N/A + 說明理由（例：HIPAA 不適用台灣）

---

## 對照表使用說明

每個標準自成一節。節內格式：

```
| Control ID | 要求摘要 | Command | Pi | PWA | Cx owner | Priority | Evidence | Gap |
```

- **Command / Pi / PWA**：三組件獨立狀態
- **Cx owner**：負責此項的 Cx 編號（含 P-Cx、W-Cx）
- **Priority**：🔴 critical / 🟡 high / 🟠 medium / ⚪ low
- **Evidence**：file:line / PR#/ doc:section
- **Gap**：⚠️ 或 ❌ 時說明缺口

Gap 過長時移到最下方「Gap Register」section，matrix 只留編號。

---

## 1. NIST SP 800-53 Rev. 5（Moderate Baseline）

> 標準原文：https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
> Moderate baseline 涉及約 260 個 control，本節按 family 分列本系統相關項。

### 1.1 AC — Access Control

**表欄**：C = Command / P = Pi server / W = PWA；Pri 🔴 critical / 🟡 high / 🟠 medium / ⚪ low

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| AC-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🟡 | `security_policies.md §2` 骨架；Session D 完稿正式版 |
| AC-2 | Account Management | ⚠️ | ❌ | ❌ | C1-A Phase 2 / P-C1-A / W-C1-A | 🔴 | `account_repo.py` 完整 CRUD + lockout；**gap**：無年度 review 機制；`delete_account()` 是 hard DELETE；Pi / PWA 無對應帳號管理 |
| AC-2(1) | Automated Account Management | ❌ | ❌ | ❌ | C1-A Phase 2 | 🟠 | 無自動化 review / disable 機制 |
| AC-2(3) | Disable Accounts | ⚠️ | ❌ | ❌ | C1-A Phase 2 | 🟡 | `accounts.status` 欄位存在（active/suspended）；無 inactivity 自動停用 |
| AC-2(13) | Disable for High-Risk | ❌ | ❌ | ❌ | C1-A Phase 2 | 🟠 | 無 risk-based disable |
| AC-3 | Access Enforcement | ⚠️ | ⚠️ | N/A | **C1-A Phase 2** | 🔴 | Admin PIN 閘口 + 粗分 role 有；**後端無 endpoint-level RBAC gate** (核心 gap)；C1-A Phase 2 `require_role()` 補 |
| AC-4 | Information Flow Enforcement | N/A | N/A | N/A | — | — | 單體系統，無跨域資料流（TAK Wave 7 再評估）|
| AC-5 | Separation of Duties | ❌ | ❌ | ❌ | C1-A Phase 2 | 🔴 | 無 role 分離（Admin PIN 是 all-or-nothing）；**C1-A Phase 2 4-role 解決** |
| AC-6 | Least Privilege | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 2 | 🔴 | 非最小權限原則；Admin PIN 全權；C1-A Phase 2 分級解決 |
| AC-6(1) | Authorize Access to Security Functions | ❌ | ❌ | ❌ | C1-A Phase 2 | 🔴 | 需 require_role(系統管理員) 守門 admin 端點 |
| AC-6(5) | Privileged Accounts | ❌ | ❌ | ❌ | C1-A Phase 2 | 🔴 | 無明確特權帳號（Admin PIN 匿名）；系統管理員 role 解決 |
| AC-6(9)(10) | Log / Prohibit privileged use | ⚠️ | ❌ | N/A | C1-A Phase 2 + C1-D | 🟡 | audit_log 記 admin PIN 操作；缺 hash chain（C1-D）|
| AC-7 | Unsuccessful Logon Attempts | ✅ | ❌ | ❌ | 已完成 / P-C1-A / W-C1-A | 🟡 | Command: 5x15min 帳號鎖定 + 10/min IP rate limit + Admin PIN 5x30min；**Pi / PWA 未對應** |
| AC-8 | System Use Notification | ❌ | ❌ | ❌ | C1-A Phase 2（併入） | ⚪ | 無登入 banner（法規不強制，但 Moderate baseline 列；加一行容易）|
| AC-10 | Concurrent Session Control | ❌ | ❌ | ❌ | C1-A Phase 2 | 🟡 | 同一帳號可多 session 同時登入；建議上限 N=2（電腦+手機） |
| AC-11 | Device Lock | ⚠️ | N/A | ⚠️ | C1-A Phase 2（併入） | 🟠 | 靠 session timeout (8hr) 絕對終結；**無 idle lock 觸發畫面鎖定** |
| AC-12 | Session Termination | ⚠️ | N/A | ⚠️ | C1-A Phase 2（併入） | 🟡 | 有絕對 timeout；**無 idle timeout**；logout 確實刪 session |
| AC-14 | Permitted Actions Without Auth | ✅ | ✅ | N/A | — | — | `config.py PUBLIC_PATHS`: /health, /docs, /static 明確定義 |
| AC-17 | Remote Access | ✅ | ✅ | ✅ | — | 🟡 | TLS 1.2+ 強制（STRICT_TLS env）；HSTS 1yr；**gap**：無 remote access policy 文件 → security_policies.md §2 補 |
| AC-17(2) | Protection of Confidentiality | ⚠️ | ⚠️ | ⚠️ | C1-G + C1-B | 🟡 | nginx TLS ✅；**mTLS 未啟用**（Tier 3 才做）；WS 層認證模糊 |
| AC-18 | Wireless Access | ⚠️ | ⚠️ | ⚠️ | Wave 7 MANET | 🟡 | Pi 500 WiFi 用；**無 WPA3 policy / access point hardening 規範** |
| AC-19 | Mobile Device Control | ❌ | N/A | ⚠️ | W-C1-A / Wave 7 | 🟠 | PWA 在 iPad/Android；**無 MDM / device enrollment**；靠 iOS/Android OS 保護 |
| AC-20 | Use of External Systems | N/A | N/A | N/A | — | — | 本地優先架構；TAK 整合（Wave 7）屬外部，屆時補政策 |
| AC-22 | Publicly Accessible Content | ✅ | ✅ | N/A | — | — | /health, /docs 明確公開；內容不含敏感資料 |

### 1.2 AU — Audit and Accountability

> Session A 列出現況（架構層）；**hash chain / 保存策略 / 跨組件 correlation 深入細節 Session B 配合 C1-D 詳填**。

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| AU-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🟡 | `security_policies.md §3` 骨架 |
| AU-2 | Event Logging | ⚠️ | ⚠️ | ❌ | C1-D | 🔴 | `audit_log` 表 19+ 事件類型（`db.py`）；**gap**：PWA 使用者操作未回拋 audit；Pi 有 audit 但未與 command 串連 |
| AU-3 | Content of Audit Records | ⚠️ | ⚠️ | N/A | C1-D | 🟡 | 欄位：operator / device_id / action_type / target / detail / exercise_id / created_at；**缺 correlation ID 跨組件**；**缺 source IP / user agent**（AU-3(1) 要求）|
| AU-4 | Audit Log Storage Capacity | ⚠️ | ⚠️ | N/A | C1-D / C3-D | 🟠 | SQLite 單表；**無大小監控 / 輪替**；長期演練會無限膨脹 |
| AU-5 | Response to Log Failures | ❌ | ❌ | N/A | C1-D | 🟡 | log 失敗目前 silent（寫入 fail 不阻斷業務；若 audit fail 應告警）|
| AU-6 | Audit Review / Analysis | ⚠️ | ❌ | N/A | C1-D + C3-C | 🟠 | `/api/admin/audit-log` 有查詢 endpoint；**無告警規則 / 異常偵測** |
| AU-8 | Time Stamps | ⚠️ | ⚠️ | ⚠️ | C3-B 擴充（NTP） | 🔴 | `strftime('%Y-%m-%dT%H:%M:%SZ','now')` 依賴系統時鐘；**Pi 無 NTP 強制保障**；時間不可信 → ICS 214 時間戳沒法律效力 |
| AU-9 | Protection of Audit Info | ⚠️ | ⚠️ | N/A | C1-D | 🔴 | INSERT-only（程式約定非 DB 約束，可繞）；**無 hash chain / 簽章**；admin PIN 保護查詢 |
| AU-9(3) | Cryptographic Protection | ❌ | ❌ | N/A | C1-D | 🔴 | **無簽章機制**；hash chain 是 C1-D 核心項 |
| AU-11 | Audit Record Retention | ❌ | ❌ | N/A | C1-D / C3-D | 🟡 | **無保存 / 清除策略**；security_policies.md §3 規劃 6 個月 |
| AU-12 | Audit Generation | ⚠️ | ⚠️ | ❌ | C1-D | 🟡 | 寫入類動作多有 audit，但**非 100% 覆蓋**（需 middleware 層強制，而非 service 層選擇性）|

#### Session B 補充：跨組件 audit 細節

**Pi server audit_log schema**（`server/migrations.js`）：
```sql
audit_log(id TEXT PK, action, operator_name, device_id, session_id, timestamp, detail JSON)
```

**Pi audit 寫入點**（顯式呼叫，非 middleware）：
- `ws_handler.js`：login_success / login_failed / network_recovery_push / audit_event（PWA 上傳）
- `routes.js`：admin_pin_setup / account_created / account_status_changed / pin_reset / account_deleted / account_role_changed

**PWA audit_log（IndexedDB）**：
- shelter：person_exited / full_data_destroy / snapshot_exported / network_recovery_push
- medical：patient_intake / patient_triage / transfer_initiated / export_completed
- 經 `SyncManager.sendAuditEvent()` 上傳 Pi（無強制；非 middleware 層）

**Session B 確認的 audit gap**：
- ❌ 三組件 **無 correlation ID** 串連（同一個操作在三邊各自有獨立 ID）
- ❌ 三組件 **無 hash chain**（Pi audit_log 也只是 INSERT-only 程式約定）
- ❌ Pi audit_event msg type 接收**無驗證**（PWA 可送任意 audit）
- ❌ 三組件 audit log **無 cleanup / 保存政策**
- ⚠️ Pi 寫 audit **失敗 silent**（try/catch 吞掉不告警）
- ⚠️ audit detail JSON 可能含 PII（待 C1-C 加 PII tagger 過濾）

### 1.3 IA — Identification and Authentication

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| IA-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🟡 | `security_policies.md §2` 骨架 |
| IA-2 | Identification and Authentication (Users) | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 2 / W-C1-A | 🟡 | 單因素 PIN（NIST AAL1）；**Phase 3 TOTP 達 AAL2** |
| IA-2(1) | MFA for Privileged | ❌ | ❌ | ❌ | C1-A Phase 3 | 🔴 | **無 MFA**；Phase 3 規劃 TOTP |
| IA-2(2) | MFA for Non-Privileged | ❌ | ❌ | ❌ | C1-A Phase 3 | 🟡 | 同上 |
| IA-2(8) | Replay-Resistant Auth | ✅ | ✅ | ✅ | — | — | HTTPS + session token 機制抗 replay |
| IA-2(12) | Acceptance of PIV Credentials | N/A | N/A | N/A | — | — | 非美國聯邦系統；對應 Taiwan 自然人憑證可未來評估（Wave 8+）|
| IA-3 | Device Identification | ⚠️ | ✅ | ⚠️ | P-C1-A | 🟡 | Pi 端 `pi_nodes.api_key` 為 device credential；PWA 無 device ID |
| IA-4 | Identifier Management | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 2 | 🟡 | `username` UNIQUE；**無 reuse 禁止期**；Phase 2 補政策 |
| IA-5 | Authenticator Management | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 2/3 | 🟡 | PBKDF2 + salt 已有；**PIN 強度 4-6 位**；缺密碼複雜度檢查（無連號 / 無重複）|
| IA-5(1) | Password-Based Auth | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 2 | 🟡 | PBKDF2-SHA256, 100k iter, 16-byte salt ✅；**4 碼 PIN 太弱**（Moderate baseline 建議 8+ char） |
| IA-5(2) | PKI-Based Auth | N/A | ⚠️ | N/A | C1-B / C1-G mTLS | 🟠 | step-ca PKI 基礎有；mTLS 是未來項 |
| IA-5(6) | Protection of Authenticators | ⚠️ | ⚠️ | ⚠️ | C1-C | 🟡 | PIN hash 存 DB；Admin PIN 寫 `~/.ics/first_run_token` chmod 600 ✅；**無定期強制換 PIN 機制** |
| IA-5(13) | Expiration of Cached Authenticators | N/A | N/A | N/A | — | — | 無 cache auth |
| IA-6 | Authenticator Feedback | ✅ | ✅ | ✅ | — | — | 登入失敗訊息通用（不洩漏帳號存在性） |
| IA-7 | Cryptographic Module Authentication | ✅ | ✅ | ✅ | — | — | Python `hashlib` + TLS via nginx（經 FIPS-approved algos）|
| IA-8 | Identification of Non-Organizational Users | N/A | N/A | N/A | — | — | 封閉系統，非自然人皆組織內 |
| IA-11 | Re-authentication | ❌ | N/A | ❌ | C1-A Phase 2 | 🟡 | 敏感操作（改 role / 刪帳號）應強制重認證；**目前只靠 admin PIN** |
| IA-12 | Identity Proofing | N/A | N/A | N/A | — | — | 自我聲明 IAL1；無 proof 流程 |

### 1.4 SC — System and Communications Protection

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| SC-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🟡 | `security_policies.md` 系列 |
| SC-5 | Denial of Service Protection | ⚠️ | ⚠️ | N/A | C2-F | 🔴 | 登入 rate limit 有；**其他 endpoint 無全域 rate limit**；無 payload size limit；`push_queue` 有 24h 清除但未驗證壓測 |
| SC-7 | Boundary Protection | ✅ | ⚠️ | N/A | C1-B / C3-B | 🟡 | nginx 反向代理 + loopback HTTP 內網隔離；**Pi WiFi AP 邊界**（Wave 7 MANET 相關）|
| SC-8 | Transmission Confidentiality | ✅ | ✅ | ✅ | 已完成 / P-C1-B | 🟡 | TLS 1.2/1.3 強制（`STRICT_TLS`）；HSTS 1yr；Pi push 含 HTTPS |
| SC-8(1) | Cryptographic Protection | ✅ | ✅ | ✅ | — | — | Mozilla Intermediate 2024-09 cipher suites（ECDHE-*-GCM / CHACHA20-POLY1305）|
| SC-10 | Network Disconnect | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 2 / C1-G | 🟡 | session timeout 8hr；**WS 無 heartbeat / reconnect 正式管理**（C1-G 範圍）|
| SC-12 | Cryptographic Key Management | ⚠️ | ⚠️ | N/A | C1-B 收尾 / C3-B | 🟡 | step-ca PKI 架構有；**憑證到期監控 / 自動 renew timer 待驗證**；金鑰輪替政策待補 |
| SC-13 | Cryptographic Protection | ✅ | ✅ | N/A | — | — | TLS 1.2+ / PBKDF2-SHA256 / Fernet（C1-C 範圍）都是 NIST-approved |
| SC-17 | PKI Certificates | ⚠️ | ⚠️ | N/A | C1-B 收尾 | 🟡 | step-ca per-customer 架構良好；**實機 PKI 部署 / renew timer / OCSP stapling 待實測** |
| SC-18 | Mobile Code | N/A | N/A | ⚠️ | W-C1-F | 🟠 | PWA JS 執行於客戶端；靠 CSP 防 XSS（目前 `unsafe-inline`，C1-F 收緊）|
| SC-23 | Session Authenticity | ✅ | ✅ | ✅ | — | 🟡 | UUID v4 session token + TLS 封裝；**gap**：無 session binding to IP / user agent（偷 token 即可用） |
| SC-28 | Protection of Info at Rest | ❌ | ❌ | ❌ | **C1-C 擴大** | 🔴 | **應用層 Fernet 未實施**；**DB 層 SQLCipher 未實施**；**OS 層 LUKS 未實施**；三層加密策略是 C1-C 擴充範圍 |
| SC-28(1) | Cryptographic Protection | ❌ | ❌ | ❌ | C1-C | 🔴 | 同上 — 無靜態加密 |
| SC-8(2) | Pre / Post Transmission Handling | N/A | N/A | N/A | — | — | TLS 自動處理 |

### 1.5 SI — System and Information Integrity

> Session B 部分填入（與 audit / WS 安全相關）；其餘 Session C 補。

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| SI-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🟡 | security_policies.md 骨架 |
| SI-4 | System Monitoring | ⚠️ | ❌ | N/A | C1-D + C3-C | 🟡 | command 有 audit_log 查詢；Pi 無告警 / 監控；缺 anomaly detection |
| SI-7 | Software / Firmware Integrity | ❌ | ❌ | ❌ | C2-E + C3-F | 🟡 | 無 binary 簽章驗證；C3-F Docker image signing 計畫處理 |
| SI-7(15) | AI Model Integrity | N/A | N/A | N/A | C5-E（未來）| ⚪ | 待 AI 部署時加 model weight 簽章（C5-E 範圍）|
| SI-10 | Information Input Validation | ⚠️ | ⚠️ | ⚠️ | C2-F | 🟡 | Pydantic schema 驗 command；Pi `express.json()` **預設 100kb 上限**；PWA 客端驗無服務端配套 |
| SI-11 | Error Handling | ⚠️ | ❌ | N/A | C2-F | 🟡 | command HTTPException 不洩 stack；**Pi 無全域 exception handler**；sync.js 有 `catch(err)` 但吞掉不 log |
| SI-16 | Memory Protection | N/A | N/A | N/A | — | — | 應用層無相關（OS / runtime 提供）|

### 1.6 CM — Configuration Management

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| CM-1 | Policy and Procedures | ❌ | ❌ | ❌ | C1-A Phase 4 | 🟡 | security_policies.md 無 CM 章節（待補）|
| CM-2 | Baseline Configuration | ⚠️ | ⚠️ | ⚠️ | C3-A / C3-B | 🟡 | systemd units 即 baseline；schema_migrations 表追蹤 DB baseline；**無 nginx / step-ca config baseline 文件**；config 散在多檔（pyproject / .env / unit file）|
| CM-3 | Configuration Change Control | ❌ | ❌ | ❌ | C2-B + 流程 | 🟡 | 無 change request workflow；config 變更 audit_log 不記；系統管理員改 PIN / Pi key 有 audit ✅ 但 OS-level config 變更無 |
| CM-3(2) | Test / Validate Changes | ⚠️ | ❌ | N/A | C2-B | 🟠 | command 改動有 CI 測試；Pi config / nginx config 變更無 staging 驗證流程 |
| CM-6 | Configuration Settings | ⚠️ | ⚠️ | ⚠️ | C3-A 擴 | 🟡 | env var system 存在；**敏感路徑 hardcoded in systemd unit files**（cert/key path）；無 `/etc/ics/*.env` 集中模式 |
| CM-7 | Least Functionality | ⚠️ | ⚠️ | N/A | C3-B | 🟠 | systemd ExecStart 收緊；無系統強化基線（CIS Benchmark）|
| CM-8 | System Component Inventory | ❌ | ❌ | ❌ | C2-E | 🟡 | 無 SBOM（CycloneDX 規劃中）；無 asset registry |
| CM-11 | User-Installed Software | N/A | N/A | N/A | — | — | 封閉系統 |

### 1.7 CP — Contingency Planning

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| CP-1 | Policy and Procedures | ❌ | ❌ | ❌ | C1-A Phase 4 | 🔴 | `security_policies.md §5 Contingency Plan` 骨架；無詳細 playbook |
| CP-2 | Contingency Plan | ⚠️ | ⚠️ | ⚠️ | C3-D + policies §5 | 🔴 | RTO ≤ 4h / RPO ≤ 1h 已寫 commercialization plan；**未轉成可執行 playbook** |
| CP-4 | Contingency Plan Testing | ❌ | ❌ | ❌ | C3-D | 🔴 | **無 DR drill 紀錄**；要求每 6 個月一次 |
| CP-9 | System Backup | ❌ | ❌ | N/A | **C3-D 急迫** | 🔴 | **無自動備份腳本**；WAL mode ✅ 是基礎但不夠；無 daily gzip / NAS rsync；6 月演練前必補 |
| CP-9(1) | Test Backup Reliability | ❌ | ❌ | N/A | C3-D | 🔴 | 無還原測試 |
| CP-10 | System Recovery | ⚠️ | ⚠️ | ⚠️ | C3-D | 🔴 | QR Code 同步降級設計（Wave 5）；**無實機故障還原 playbook**；step-ca root CA 損毀僅文件描述，無 runbook |
| CP-10(2) | Transaction Recovery | ⚠️ | ⚠️ | N/A | C3-D + C1-D | 🟡 | WAL 提供 transaction durability；跨 component 一致性還原無流程 |

### 1.8 IR — Incident Response

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| IR-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🔴 | `security_policies.md §4 Incident Response` 骨架 |
| IR-4 | Incident Handling | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 + C3-C | 🔴 | audit_log 捕事件；**無 incident classification / triage 流程** |
| IR-5 | Incident Monitoring | ⚠️ | ❌ | ❌ | C3-C 擴 | 🟡 | command 有 audit query；**無 anomaly alerting** |
| IR-6 | Incident Reporting | ❌ | ❌ | ❌ | C1-A Phase 4 | 🔴 | **無內部通報流程；無 PDPC 72h 通報程序**（個資法 §12）|
| IR-7 | Incident Response Assistance | N/A | N/A | N/A | — | — | 組織層面 |
| IR-8 | Incident Response Plan | ❌ | ❌ | ❌ | C1-A Phase 4 | 🔴 | **無 IR plan 文件**；security_policies §4 待擴 |

### 1.9 PL — Planning

_Session D 填入：PL-2/8_

### 1.10 RA — Risk Assessment

_Session D 填入：RA-3/5（含 threat_model）_

### 1.11 SA — System and Services Acquisition

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| SA-8 | Security Engineering | ✅ | ⚠️ | ⚠️ | — | 🟡 | command 分層架構（C0）+ TLS stack（C1-B）；Pi / PWA 架構部分 |
| SA-11 | Developer Testing | ⚠️ | ❌ | ❌ | C2-A 擴 / W-C2-A / P-C2-* | 🟡 | command 269 測試 / 44% coverage；**Pi / PWA 無 test suite** |
| SA-11(1) | Static Code Analysis | ⚠️ | ❌ | ❌ | C2-C 擴 | 🟡 | command bandit 在 CI；**無 SAST for Pi / PWA**；CodeQL 待加 |
| SA-11(8) | Dynamic Code Analysis | ❌ | ❌ | ❌ | C2-A | 🟠 | 無 DAST / fuzzing-based runtime test |
| SA-15 | Development Process | ⚠️ | ⚠️ | ⚠️ | C2-E + C2-B | 🟡 | feature branch + PR ✅；**無 SBOM / SLSA L2** |

### 1.12 SR — Supply Chain Risk Management

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| SR-1 | Policy and Procedures | ❌ | ❌ | ❌ | C1-A Phase 4 | 🟡 | 待補 SR 章節（policies） |
| SR-3 | Supply Chain Controls | ⚠️ | ⚠️ | ⚠️ | C2-E | 🟡 | requirements.txt pinned；pip-audit 啟用；**npm 端無對應**；無正式 vendor 審查 |
| SR-4 | Provenance | ❌ | ❌ | ❌ | C2-E + C3-F | 🟡 | 無 SLSA provenance；C3-F Docker 簽章規劃中 |
| SR-5 | Acquisition Strategies | ⚠️ | ⚠️ | ⚠️ | CLAUDE.md（已有禁中國條款）| 🟢 | 已有「禁止中國供應鏈」規則；待形式化 vendor 評估 |
| SR-11 | Component Authenticity | ❌ | ❌ | ❌ | C2-E + C3-F | 🟡 | 無 binary 簽章；無 image signing；C3-F Open Core Binary 需簽章 |

### 1.13 MP — Media Protection

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| MP-1 | Policy and Procedures | ❌ | ❌ | ❌ | C1-A Phase 4 | 🟡 | security_policies.md §6 (Privacy) 部分涵蓋；應補 MP 章節 |
| MP-2 | Media Access | ❌ | ❌ | ❌ | C1-C 擴大 | 🔴 | **PWA IndexedDB 含病患 PII 明文**；Pi SQLite 含病患 PII 明文；Command SQLite 同；C1-C 三層加密解 |
| MP-4 | Media Storage | ❌ | ❌ | ❌ | C1-C 擴大 / C3-D | 🔴 | 同 MP-2；備份檔（C3-D）也明文 |
| MP-5 | Media Transport | N/A | N/A | N/A | — | — | 系統內部傳輸由 SC 控制 |
| MP-6 | Media Sanitization | ❌ | ❌ | ❌ | medical-pwa Phase 3 / C3-D | 🟡 | **Panic Wipe 未實施**（medical-pwa 規劃）；Pi / Command 退場 disk wipe 流程未文件化 |
| MP-7 | Media Use | ❌ | ❌ | ❌ | C1-C / W-C1-C | 🟡 | PWA 端 export（medical AES-256-GCM 加密 ✅，shelter snapshot 加密 ✅）；無 USB 政策 |

### 1.14 PT — Privacy（800-53 Privacy Controls）

| Control | 要求摘要 | C | P | W | Cx owner | Pri | Evidence / Gap |
|---|---|:---:|:---:|:---:|---|:---:|---|
| PT-1 | Policy and Procedures | ⚠️ | ⚠️ | ⚠️ | C1-A Phase 4 | 🔴 | security_policies.md §6 骨架；個資法明訂 |
| PT-2 | Authority to Process PII | ❌ | ❌ | ❌ | C1-C | 🔴 | **無 purpose limitation 文件化**（蒐集目的）；個資法 §5 要求 |
| PT-3 | PII Processing Purposes | ❌ | ❌ | ❌ | C1-C | 🟡 | 無告知當事人機制（演練前同意書是流程層，未在系統內）|
| PT-4 | Consent | ❌ | ❌ | ❌ | C1-C | 🟡 | 無系統內同意紀錄；應由演練表單收 |
| PT-5 | Privacy Notice | ❌ | ❌ | ❌ | C1-A Phase 4 | 🟡 | 無隱私權告知頁 |
| PT-6 | System of Records Notice | N/A | N/A | N/A | — | — | 美國聯邦特有（Privacy Act）|
| PT-7 | Specific Categories of PII | ⚠️ | ⚠️ | ⚠️ | C1-C | 🔴 | **病患醫療資料是個資法 §6 「特種個資」**；需明確記錄 + 加密 + 存取稽核 |

### 1.15 AT / PE / PS / SR

| 族 | 狀態 | 備註 |
|---|:---:|---|
| AT（教育訓練）| ❌ | C1-A Phase 4 規劃；security_policies.md 補 |
| PE（實體環境）| N/A | 由部署現場政策（Pi 鎖櫃、機房門禁）|
| PS（人員安全）| N/A | 由組織人事流程 |
| SR（供應鏈）| ⚠️ | C2-E 範圍（SBOM、SLSA L2、dep scan）|

---

## 2. NIST SP 800-63-3（Digital Identity）

> 原文：https://pages.nist.gov/800-63-3/

### 2.1 AAL（Authenticator Assurance Level）

| 現況 | 目標 | Gap |
|---|---|---|
| **AAL1**（單因素 memorized secret — 6 位 PIN）| **AAL2**（C1-A Phase 3 加 TOTP → 二因素）| TOTP + 備援碼；對應 IA-2(1)(2) |

**AAL1 符合性檢查**：
- ✅ Memorized secret 最低要求（NIST 規範 6 digits is marginal，且 PIN 非 alphanumeric；**建議 Phase 2 逐步升 8+ 位或改 alphanumeric**）
- ✅ Throttling（rate limit + lockout）
- ✅ Secret hashed with approved function (PBKDF2-SHA256, 100k iter)
- ⚠️ Salt 16 bytes（規範 ≥32-bit，16 bytes = 128 bits 足夠）

### 2.2 IAL（Identity Assurance Level）

**IAL1** — 自我聲明身份（no proofing）

- ✅ 符合本系統定位（EOC 封閉系統，現場部署，身份靠組織內部管理）
- 不追求 IAL2（需 in-person / remote 證件核對流程）

### 2.3 FAL（Federation Assurance Level）

**N/A** — 目前無聯邦身份識別（無 SSO / SAML / OIDC）。未來 TAK 整合（Wave 7）若涉及跨組織 SSO 再評估。

---

## 3. NIST CSF 2.0

> 原文：https://www.nist.gov/cyberframework

### 3.1 GOVERN

_Session D 填入：治理、風險策略、角色責任_

### 3.2 IDENTIFY

| Category | Status | Notes |
|---|:---:|---|
| ID.AM 資產管理 | ❌ | 無 SBOM / asset registry（C2-E）|
| ID.RA 風險評估 | ⚠️ | threat_model.md 骨架（Session D）|
| ID.SC 供應鏈 | ⚠️ | 「禁中國供應鏈」CLAUDE.md ✅；無正式評估 |
| ID.GV 治理 | ⚠️ | security_policies.md 骨架 |

### 3.3 PROTECT

> Session A 填 PR.AA（Identity Management & Access Control）；其餘 Session B/C 填。

#### PR.AA — Identity Management, Authentication and Access Control

| ID | 子能力 | Status | 對應 NIST 800-53 / Cx |
|---|---|:---:|---|
| PR.AA-01 | 身份建立與管理 | ⚠️ | AC-2 / IA-4；C1-A Phase 2 |
| PR.AA-02 | Identities are proofed and bound | N/A IAL1 | IA-12（不適用 EOC 內網）|
| PR.AA-03 | Users authenticated commensurate with risk | ⚠️ → ❌ | IA-2(1)(2) MFA 缺 → C1-A Phase 3 |
| PR.AA-04 | Identity assertions | N/A | 無 federation |
| PR.AA-05 | Access permissions enforced（含 least privilege）| ❌ | AC-3/5/6；**核心 gap**，C1-A Phase 2 |
| PR.AA-06 | Physical access | N/A 軟體 | 由部署現場政策（Pi 鎖櫃）|

#### PR.DS — Data Security（Session B 完整版）

| ID | 子能力 | Status | 對應 NIST / Cx |
|---|---|:---:|---|
| PR.DS-01 | Data-at-rest 保護 | ❌ | SC-28 / MP-2/4；**3 層 storage 全明文**（PWA IndexedDB / Pi SQLite / Command SQLite）；C1-C 三層加密 |
| PR.DS-02 | Data-in-transit 保護 | ⚠️ | SC-8；command ↔ user TLS ✅；Pi server 可 fallback ws://；C1-B 收尾 + P-C1-B |
| PR.DS-10 | Data-in-use 保護 | N/A | 單機處理 |
| PR.DS-11 | Data confidentiality（PII）| ❌ | MP-2 / PT-7；**特種個資（醫療）明文**；C1-C |
| PR.DS-13 | Software / hardware integrity | ⚠️ | SI-7；無 binary 簽章；C2-E + C3-F |

### 3.4 DETECT

| Category | Status | Notes |
|---|:---:|---|
| DE.AE Anomalies / Events | ⚠️ | audit_log 記錄；**無 anomaly detection / alerting**（C3-C 擴）|
| DE.CM Continuous Monitoring | ❌ | 無 Prometheus / Grafana；`/api/health` 基礎；C3-C 完整版 |
| DE.DP Detection Process | ❌ | 無 alert rule 文件；無 SOC playbook |

### 3.5 RESPOND

| Category | Status | Notes |
|---|:---:|---|
| RS.RP Response Planning | ❌ | 無 IR plan（C1-A Phase 4 + policies §4）|
| RS.CO Communications | ❌ | 無 stakeholder 通報流程（PDPC / 客戶 / 司法）|
| RS.AN Analysis | ❌ | 無 forensic 流程 |
| RS.MI Mitigation | ⚠️ | lockout / rate limit 是 reactive ✅；無 incident-driven mitigation |
| RS.IM Improvements | ⚠️ | architecture_decisions 記設計變更；無正式 lessons-learned 流程 |

### 3.6 RECOVER

| Category | Status | Notes |
|---|:---:|---|
| RC.RP Recovery Planning | ❌ | RTO/RPO 寫了未實作（C3-D 急迫）|
| RC.IM Improvements | ❌ | 無 recovery drill；無改善追蹤 |
| RC.CO Communications | ❌ | 無客戶通報程序 |

---

## 4. NIST SP 800-218 SSDF（Secure Software Development Framework）

> 原文：https://csrc.nist.gov/Projects/ssdf

### 4.1 PO — Prepare the Organization

| Practice | Status | Evidence / Gap |
|---|:---:|---|
| PO.1 軟體開發流程 | ✅ | CLAUDE.md feature branch + PR；DoD 章節 |
| PO.2 角色責任 | ⚠️ | role 區分有；**無 RACI 表**（policies §1）|
| PO.3 IT 環境隔離 | ⚠️ | tmp_db fixture 隔離測試；**無 dev/staging/prod 環境分離**；Mac dev / Pi prod 直接跳 |
| PO.4 標準應用 | ✅ | NIST/OWASP 對應（compliance/matrix）+ ruff 規則 |
| PO.5 Criteria 評估 | ⚠️ | DoD 隱含 release gate；**無形式化 release checklist** |

### 4.2 PS — Protect the Software

| Practice | Status | Evidence / Gap |
|---|:---:|---|
| PS.1 保護所有形式 code | ✅ | GitHub repo + branch protection（推論）|
| PS.2 驗證軟體完整性 | ❌ | **無 commit GPG 簽章要求**；Docker image 簽章規劃在 C3-F |
| PS.3 保留 artifact | ✅ | CI artifact retention 30 天 |

### 4.3 PW — Produce Well-Secured Software

| Practice | Status | Evidence / Gap |
|---|:---:|---|
| PW.1 設計安全 features | ✅ | First-run gate / login lockout / admin PIN / TLS 全做（C1-A/B）|
| PW.2 Design Review | ⚠️ | architecture_decisions.md 記重大設計；**無正式 design review process** |
| PW.3 重用 code 安全審查 | ⚠️ | pip-audit + bandit 有；**無 dep review log** |
| PW.4 Apply 安全函式 | ✅ | PBKDF2-SHA256 100k iter / Mozilla TLS / Fernet（規劃）|
| PW.5 避免 unsafe patterns | ✅ | 15 fuzzing tests（SQL injection / XSS / oversized）|
| PW.6 測試 unit/integration/api | ✅ | 269 tests, 4 layers; coverage 44% |
| PW.7 Code Review | ✅ | feature branch → PR → merge |
| PW.8 Test Executables | ❌ | 無 binary security testing；C3-F 後加 |
| PW.9 Default Config 安全 | ✅ | SESSION_TIMEOUT / CSP_MODE / first-run gate 預設安全 |

### 4.4 RV — Respond to Vulnerabilities

| Practice | Status | Evidence / Gap |
|---|:---:|---|
| RV.1 Identify Vulnerabilities | ⚠️ | pip-audit + bandit each push；**Pi npm 端無對應**；無 Dependabot |
| RV.2 Assess Vulnerabilities | ❌ | bandit 無 CVSS 輸出；無正式風險評估流程 |
| RV.3 Root Cause Analysis | ❌ | **無 SECURITY.md / 漏洞通報流程** |

---

## 5. ISO/IEC 25010:2023（軟體品質 8 特性）

> 原文：ISO/IEC 25010:2023 Systems and software engineering - Systems and software quality models

| 特性 | Status | Evidence / Gap |
|---|:---:|---|
| **5.1 Functional Suitability**（功能性）| ✅ | 269 tests 涵蓋 auth / event / exercise / dashboard 工作流 |
| **5.2 Performance Efficiency**（效能效率）| ❌ | **無 load / stress 測試**；無 profiling；Pi SQLite 並發限制（D Decision B 規劃 retry）|
| **5.3 Compatibility**（相容性）| ⚠️ | FastAPI 0.136.0 固定；CI 只跑 ubuntu-latest；無 multi-version matrix |
| **5.4 Interaction Capability**（使用性）| ⚠️ | UI 規格詳實（指揮部規格 + PWA spec）；**無 a11y 測試** |
| **5.5 Reliability**（可靠性）| ⚠️ | Session cleanup / DB isolation / WAL ✅；**無 chaos testing**；**TOCTOU mutex 已知 xfail** |
| **5.6 Security**（資訊安全）| ⚠️ | 詳見 NIST + ASVS 各節；C1 完成度 ~50% |
| **5.7 Maintainability**（可維護性）| ⚠️ | C0 分層架構 ✅；**legacy dead code 未清**（db.py 65KB / main_legacy.py 66KB）；**commander_dashboard.html monolithic 376KB**（C1-F 解）|
| **5.8 Portability**（可攜性）| ⚠️ | Mac dev / Pi prod 雙平台支援；**無 Windows ops 支援**（dev OK）|
| **5.9 Flexibility**（彈性，2023 新增）| ✅ | 設定外部化（env + config table）；FastAPI dependency injection |
| **5.10 Safety**（安全，2023 新增）| ⚠️ | 涉及生命安全（醫療 ISBAR / 後送）；**無 fail-safe mode 文件**（系統故障時 fallback 行為）|

---

## 6. ISO/IEC 5055:2021（CWE-based 軟體量測）

> 原文：ISO/IEC 5055:2021 Information technology - Software measurement - Software quality measurement

> ISO/IEC 5055 用 CWE 量測；本系統未做正式 CWE 量測，但下列 CWE 類別由現有測試 / 工具部分覆蓋：

| 維度 | CWE 覆蓋（部分）| Status |
|---|---|:---:|
| **6.1 Reliability** | CWE-415（double-free）/ CWE-401（memory leak）由 Python GC 緩解；CWE-672（resource exhaustion）`push_queue` 24h cleanup ✅ | ⚠️ |
| **6.2 Security** | CWE-89 SQL injection（fuzzing test ✅）/ CWE-79 XSS（CSP 待 enforce）/ CWE-307 brute force（lockout ✅）/ CWE-311 missing encryption（C1-C 待做）/ CWE-256 plaintext password storage（PBKDF2 ✅）| ⚠️ |
| **6.3 Performance Efficiency** | CWE-770（resource allocation 無限制）— payload size limit 缺（C2-F）；CWE-405（asymmetric resource）| ⚠️ |
| **6.4 Maintainability** | CWE-1126（declarative complexity）— commander_dashboard.html monolithic；CWE-1111（incomplete documentation）— 部分 ⚠️ | ⚠️ |

---

## 7. OWASP ASVS 4.0（Level 2）

> 原文：https://owasp.org/www-project-application-security-verification-standard/

### V1-V14 Level 2 requirements

> Session A 填 V2（Auth）/ V3（Session）/ V4（Access Control）/ V9（Comm）；其餘 Session B/C 填。

#### V2: Authentication

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V2.1.1 密碼長度 ≥12（或 alternative policy）| ⚠️ | 6 位 PIN + 強 hash + lockout；**ASVS 角度 PIN 不夠，但 EOC 場景用 PIN 合理**，補 TOTP (C1-A Phase 3) |
| V2.1.5 允許 paste | ⚠️ | 待驗證 PIN 欄位是否 `autocomplete=off` 阻 paste |
| V2.1.7 change password 強制驗證舊 PIN | ✅ | `/api/admin/accounts/{u}/pin` 需 admin PIN，非自助；Phase 2 自助改 PIN 需舊 PIN |
| V2.1.11 沒有密碼提示 | ✅ | 無 hint |
| V2.2.1 安全通知（新登入 / 新裝置通知）| ❌ | 未實施，C1-A Phase 2 可加 |
| V2.2.3 認證方式公開記錄 | ⚠️ | 程式碼注釋有，security_policies.md 補 |
| V2.3.1 system-generated initial secret | ✅ | `ensure_initial_admin_token()` 隨機 6 位 |
| V2.5 Credential recovery | ⚠️ | 忘記 PIN 靠 admin PIN 重置；**admin PIN 忘記的恢復政策未寫** |
| V2.7 OOB authenticators | N/A | 無 |
| V2.8 One-time authenticators | ❌ | C1-A Phase 3 TOTP |

#### V3: Session Management

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V3.1.1 Stateless tokens OR server-side | ✅ | Server-side（SQLite `sessions` 表）|
| V3.2.1 Token generation 隨機 ≥64 bits | ✅ | UUID v4 = 122 bits 熵 |
| V3.2.2 Token uniqueness | ✅ | UUID v4 |
| V3.3.1 Logout invalidates all sessions? | ⚠️ | 登出只刪當前 token；其他裝置 session 保留 → 非 ASVS 嚴格解讀；**Phase 2 可加「登出所有裝置」按鈕** |
| V3.3.2 Token idle timeout | ❌ | 只有絕對 timeout 8hr；**缺 idle timeout**（Phase 2 補） |
| V3.3.3 Absolute timeout | ✅ | 8 小時（SESSION_TIMEOUT） |
| V3.3.4 Re-auth for sensitive operations | ⚠️ | admin PIN 部分達成；帳號 role 變更尚未強制重認證 |
| V3.4 Cookie 屬性 | N/A | 非 cookie-based |
| V3.5 Token-based auth | ✅ | X-Session-Token header |
| V3.7 Defenses against token-based attacks | ⚠️ | 無 token rotation（每次重要動作換 token）；**replay 靠 TLS + token-in-header 防** |

#### V4: Access Control

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V4.1.1 Trusted enforcement server-side | ❌ | **後端無 role gate**（核心 gap，C1-A Phase 2）|
| V4.1.2 All URLs / resources 有授權檢查 | ⚠️ | auth middleware 有；**role 層面尚無**；admin PIN 閘口對 /api/admin/* 是有 |
| V4.1.3 principle of least privilege | ❌ | admin PIN 全權（C1-A Phase 2 改）|
| V4.1.5 Deny by default | ❌ | 目前是 allow all authenticated；**需改 deny by default + explicit allowlist** |
| V4.2.1 Sensitive data 和函式保護 | ⚠️ | PIN hash / audit log 受 admin PIN 保護；無細粒 |
| V4.3.1 Administrative interface 授權強 | ⚠️ | Admin PIN + 5x30min lockout ✅；**但匿名化（無法追究是誰用的 PIN）** |
| V4.3.2 Directory browsing 關閉 | ✅ | FastAPI 無 dir listing；nginx 靜態 root 設定無 `autoindex on`（待驗證）|

#### V9: Communications

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V9.1.1 TLS for all inbound connections | ⚠️ | command nginx ✅；**Pi server 預設可 fallback 到 ws://**（STRICT_TLS=false 時）；C1-B 收尾 + P-C1-B 解 |
| V9.1.2 Modern TLS configuration | ✅ | Mozilla Intermediate 2024-09 |
| V9.1.3 Insecure protocols 禁用 | ✅ | TLS 1.0/1.1 禁用 |
| V9.2.1 Outbound connections 驗證憑證 | ⚠️ | Python requests / urllib 預設 verify=True；Pi 端 fetch 行為待驗證 |
| V9.2.2 Encrypted communications with backend components | ⚠️ | Pi↔Command HTTPS + Bearer；**缺 mTLS**（C1-G）|
| V9.2.3 Authenticated connections with backend | ✅ | Bearer token 驗 |
| V9.2.4 Certificates validated against trust chain | ✅ | step-ca CA 掛到系統 trust store（trust-root-mac.sh）|

#### V7: Cryptography

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V7.1.1 主要金鑰由 OS / KMS 管理 | ⚠️ | TLS 私鑰存盤；step-ca 私鑰存盤；無 OS keyring / KMS（暫接受，C3-B 補 LUKS 後改善）|
| V7.1.2 不在程式碼 hardcode | ✅ | detect-secrets pre-commit；env / config 表 / file 三處取 |
| V7.1.3 隨機數源強度 | ✅ | command: `secrets.token_*` ✅；Pi: `crypto.randomBytes` ✅；PWA: `crypto.getRandomValues` ✅ |
| V7.2 演算法選用 | ✅ | PBKDF2-SHA256（100k iter）/ TLS 1.2+ / AES-256-GCM（PWA export）|
| V7.3 加密金鑰 lifecycle | ⚠️ | 無正式 key rotation 政策（PIN / TLS cert 都靠手動換） |

#### V8: Data Protection

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V8.1 一般資料保護 | ⚠️ | Memory cache 有；**無加密 at rest** |
| V8.1.1 敏感資料 logging 排除 | ⚠️ | command audit_log detail 可能含 PII（C1-C 加 tagger）；structlog 過濾規則未定 |
| V8.1.2 敏感資料 cache control 防護 | ⚠️ | nginx 靜態 Cache-Control 未針對敏感頁設 `no-store`（待 C1-F）|
| V8.2 client-side data protection | ❌ | **PWA IndexedDB 病患資料明文**（W-C1-C 三層加密）|
| V8.3 sensitive private data | ❌ | **病患 PII（姓名/年齡/性別/症狀/過敏）全明文** at rest（C1-C + W-C1-C）|

#### V14: Configuration（Frontend / 部署）

| Requirement | Status | Evidence / Gap |
|---|:---:|---|
| V14.1 Build / Deploy 流程 | ⚠️ | 有 GitHub Actions CI；**無 SBOM / SLSA**（C2-E）|
| V14.2 依賴管理 | ⚠️ | `requirements.txt` / `package.json` 鎖版本；**無自動 vuln scan in CI**（C2-C 擴充）|
| V14.3 Unintended security disclosure | ⚠️ | Pi server **無生產 / 開發模式區分**（NODE_ENV 不檢查）；C2-F 解 |
| V14.4 HTTP Security Headers | ⚠️ | command nginx ✅；**Pi server `/static/`（PWA HTML 來源）無 security headers**；W-C1-F 補 |
| V14.4(1) X-Content-Type-Options | ⚠️ | command ✅；Pi `/static/` ❌ |
| V14.4(3) Content-Security-Policy | ⚠️ | command ✅（report-only，待 enforce）；**PWA 完全無 CSP**（無 meta tag、無 header）|
| V14.4(5) Referrer-Policy | ⚠️ | command ✅；Pi `/static/` ❌ |
| V14.5 HTTP Request Header Validation | ⚠️ | FastAPI Pydantic 驗；Pi `express.json()` 預設 100kb limit；**無顯式 size limit / type 檢查** |

---

## 8. CIS Controls v8

> 原文：https://www.cisecurity.org/controls/

> 本系統定位為小型 EOC，目標 **IG1（基礎）+ 部分 IG2**（Implementation Group 1 = 自主小組織）。

| Control | 主題 | Status | Cx owner | Notes |
|---|---|:---:|---|---|
| 1 | Inventory and Control of Enterprise Assets | ⚠️ | C2-E | 無正式 asset registry；部署清單在 commercialization plan |
| 2 | Inventory and Control of Software Assets | ❌ | C2-E | 無 SBOM；client device 不在管控（PWA 在客戶 iPad）|
| 3 | Data Protection | ❌ | C1-C | 三層加密未做；資料分類待補 |
| 4 | Secure Configuration of Enterprise Assets and Software | ⚠️ | C3-A / C3-B | systemd / nginx 有 baseline；無 CIS Benchmark 驗證 |
| 5 | Account Management | ⚠️ | C1-A Phase 2 | RBAC 待做；Soft delete 待做 |
| 6 | Access Control Management | ⚠️ | C1-A Phase 2 | role-based gate 待做；least privilege 待做 |
| 7 | Continuous Vulnerability Management | ⚠️ | C2-C 擴 + C2-E | pip-audit + bandit ✅；無自動 patch；CodeQL 待加 |
| 8 | Audit Log Management | ⚠️ | C1-D | audit_log 表 ✅；hash chain / 保存政策 / 跨組件 correlation 待做 |
| 9 | Email and Web Browser Protections | N/A | — | 不適用（無 email 系統）|
| 10 | Malware Defenses | N/A | — | 客戶 OS 層責任 |
| 11 | Data Recovery | ❌ | **C3-D 急迫** | 無自動備份；無還原測試；CP-9/10 全失 |
| 12 | Network Infrastructure Management | ⚠️ | C3-B + Wave 7 MANET | 部分（nginx 反代）；無 firewall / WiFi AP 設定 |
| 13 | Network Monitoring and Defense | ❌ | C3-C | 無 IDS / 流量監控 |
| 14 | Security Awareness and Skills Training | N/A | 組織責任 | 客戶教育訓練（不在系統內）|
| 15 | Service Provider Management | ❌ | C2-E | 無 vendor 評估流程文件 |
| 16 | Application Software Security | ⚠️ | C2-A/C/E + C1-F | ruff / detect-secrets / 部分 testing ✅；ASVS L2 完成度 ~60% |
| 17 | Incident Response Management | ❌ | C1-A Phase 4 | 無 IR plan；security_policies §4 待擴 |
| 18 | Penetration Testing | ❌ | C6 | 規劃在 v3.2.0 ISO 認證階段 |

---

## 9. OWASP SAMM 2.0

> 原文：https://owaspsamm.org/

> 5 Business Functions × 3 Practices each = 15 Practices，每個有 3 Maturity Levels（1/2/3）。本系統目標 **Level 2 整體**。

| Function | Practice | Current Level | Notes |
|---|---|:---:|---|
| **Governance** | Strategy & Metrics | 1 | DoD 章節有，無 metrics dashboard |
|  | Policy & Compliance | 1→2 | security_policies.md 骨架；matrix.md 主體；目標 L2 達成 |
|  | Education & Guidance | 1 | CLAUDE.md + TEST_CATALOG.md；無 secure coding training |
| **Design** | Threat Assessment | 1→2 | threat_model.md 骨架（Session D 完稿）|
|  | Security Requirements | 2 | 散在規格書 + matrix；可主張 |
|  | Security Architecture | 2 | C0 分層 + architecture_decisions |
| **Implementation** | Secure Build | 1→2 | CI 有；SBOM / signing 缺（C2-E）|
|  | Secure Deployment | 1 | systemd 有；無 staging；C3 待做 |
|  | Defect Management | 1 | bug 散在 git issue；無 vulnerability tracker |
| **Verification** | Architecture Assessment | 2 | compliance audit 進行中（本程式）|
|  | Requirements-driven Testing | 2 | 269 tests + ASVS 對照 |
|  | Security Testing | 2 | bandit / detect-secrets / fuzzing；目標 L3（自動 DAST）|
| **Operations** | Incident Management | 1 | audit_log；無 IR plan（C1-A Phase 4）|
|  | Environment Management | 1 | 部分（systemd + nginx）；無 staging 環境 |
|  | Operational Management | 1 | 手動部署；DORA 低成熟度 |

**整體 SAMM Level**：**1.5**（多數 Practice L1，少數 L2）；**目標 L2** 在 v2.1.0 階段達成（C2-E + C3-D + C1-A Phase 4 補齊後）。

---

## 10. SLSA v1.0（Supply Chain Integrity）

> 原文：https://slsa.dev/spec/v1.0/

| Level | 要求 | Status | Gap |
|---|---|:---:|---|
| **L1** | Provenance（基礎追蹤）| ✅ | GitHub repo + CI 流程可追蹤；artifact retention 30 天 |
| **L2** | Hosted build platform | ⚠️ → 目標 | 用 GitHub Actions（hosted）✅；**無 SLSA provenance attestation**（C2-E 加 `slsa-github-generator`）|
| **L3** | Hardened builds | ❌ → C2-E 後 | 無 hermetic build；無 isolated builders |
| **L4** | Two-party review + reproducible | ❌ → C6 | 規劃 v3.2.0 ISO 階段 |

**目標**：v2.1.0 達 **L2**（C2-E 規劃中，需在 CI 加 SLSA provenance generator）；長期 L3。

---

## 11. FEMA NIMS / ICS Doctrine

> 原文：FEMA IS-700, IS-800, NIMS Implementation Plan

### 11.1 Incident Command System 結構

_Session D 填入：與本系統 role / operational period 對應_

### 11.2 Unity of Command

_Session D 填入：對照 C1-A Phase 2 commander of record 機制_

### 11.3 Operational Period / Planning P

_Session D 填入：對照 operational_periods 表設計_

### 11.4 Multi-Agency Coordination（MACS）

_Session D 填入：TAK 整合（Wave 7）_

### 11.5 Resource Management

_Session D 填入：對照 resource_requests + ICS 213RR_

### 11.6 Information Management / Public Information

_Session D 填入_

---

## 12. FEMA ICS 508 表單對應

> 原文：https://training.fema.gov/icsresource/icsforms.aspx

| 表單 | 用途 | 本系統欄位來源 | Status | Cx owner |
|---|---|---|:---:|---|
| ICS 201 | Incident Briefing | events / operational_periods / decisions | _Session D_ | Wave 8 |
| ICS 202 | Incident Objectives | iap_notes（operational_periods） | _Session D_ | Wave 8 |
| ICS 203 | Organization Assignment | accounts + duty_log | _Session D_ | Wave 8 |
| ICS 205 | Communications Plan | pi_nodes + network config | _Session D_ | Wave 8 |
| ICS 206 | Medical Plan | medical-pwa 的 ISBAR 資料 | _Session D_ | Wave 8 |
| ICS 209 | Status Summary | resource_snapshots + events 統計 | _Session D_ | Wave 8 |
| ICS 213RR | Resource Request | resource_requests（新表，Wave 8）| _Session D_ | Wave 8 |
| ICS 214 | Unit Log / Activity Log | duty_log + audit_log | _Session D_ | Wave 8 |
| ICS 215 | Operational Planning Worksheet | resource allocation records | _Session D_ | Wave 8 |
| ICS 215A | IAP Safety Analysis | safety officer notes（operational_periods）| _Session D_ | Wave 8 |

---

## 13. Taiwan 法規對應

### 13.1 資通安全管理法 + 附表十防護基準

_Session D 填入：12 項防護基準對應 NIST 800-53 控制項_

### 13.2 個資法 PDPA

#### PII 欄位清單（Session B 確認）

| 表 / 來源 | 欄位 | 個資類別 | 存放位置 | 加密狀態 |
|---|---|---|---|---|
| **medical-pwa: patients** | display_id, source_age, source_sex, injury_type, trauma_or_medical (含主訴 / 過敏 / 用藥), current_zone, disposition | **§6 特種個資（醫療）** | IndexedDB | ❌ 明文 |
| **medical-pwa: triages** | patient_id + triage 細節 | §6 特種個資 | IndexedDB | ❌ 明文 |
| **shelter-pwa: persons** | display_id, name, age, status, family_unit_id | §6 一般個資 | IndexedDB | ❌ 明文 |
| **Pi server: current_state / delta_log / snapshots** | 上述全部（透過 sync） | §6 一般 + 特種 | SQLite | ❌ 明文 |
| **command: pi_received_batches / snapshots** | 上述全部（透過 push） | §6 | SQLite | ❌ 明文 |
| **command: accounts** | username, display_name | §2 一般個資 | SQLite | hash（PIN）+ 明文（display） |
| **command: audit_log.detail** | 可能含 operator name / target | §2 一般 | SQLite | ❌ 明文 |

#### 個資法各條對應

| 條文 | 要求 | Status | 缺口 / 對應 Cx |
|---|---|:---:|---|
| §5 蒐集 — purpose limitation | 限於特定目的必要範圍 | ❌ | 系統內無 purpose 紀錄；演練表單收集流程未在系統內；C1-A Phase 4 補政策 + C1-C 標欄位 |
| §6 特種個資（醫療）| 原則禁止蒐集，例外要明文同意 + 法律依據 | ⚠️ | 災害防救法 §35 提供法律依據 ✅；**未在系統內紀錄當事人同意** |
| §8 告知義務 | 蒐集時告知當事人 | ❌ | 無系統內告知機制；演練前同意書是流程層 |
| §11 維護資料正確 | 資料不正確應刪除 / 更正 | ⚠️ | medical PWA 有 transfer / disposition；無公開的「請求更正」流程 |
| §12 資料外洩通報 | 72h 內通報 PDPC + 當事人 | ❌ | **無 incident response 流程文件化**；C1-A Phase 4 + security_policies.md §4 補 |
| §15 公務機關蒐集 | 法律依據 + 必要 + 安全維護措施 | ⚠️ | 災害防救法依據 ✅；**安全維護措施不足**（無加密 at rest）|
| §17 公開應由首長負責 | 設立資料保護標準 | ❌ | 需組織政策層；security_policies.md §6 |
| §18 個資處理人員管理 | 員工管理 / 教育訓練 | ❌ | C1-A Phase 4 + 組織政策 |
| §19 國際傳輸 | PDPC 限制 | ✅ | 本系統本地優先；雲端 AI 規劃匿名化（C5-E）|
| §27 / §41 安全維護義務 | 防止竊取 / 竄改 / 毀損 / 滅失 / 洩漏 | ❌ | 同 §15；**未達標**；C1-C + C1-D + C3-D 解 |
| §41 違反罰則 | 5 萬 ~500 萬 + 刑責 | — | 風險警示：未達 §27 標準會吃罰款 |

### 13.3 災害防救法

_Session D 填入：演練資料保存 / 應變中心運作 / 跨機關協調_

### 13.4 政府資通安全整體防護計畫（12 項）

_Session D 填入_

---

## Gap Register（統整所有 ⚠️/❌ 項目）

> 格式：`[Control-ID] Priority | Component | Gap | Target Cx | ETA`
> Session A/B/C 發現後彙整，Session D 排序 + 指派 Cx

### Session A 發現（2026-04-25）

#### 🔴 Critical（v2.1.0 投標前必補）

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-A01 | AC-3 / AC-5 / AC-6 / V4.1.1 / V4.1.5 | command + pi + pwa | **後端無 role-based endpoint gate**（核心 RBAC 缺）；deny-by-default 未實施 | C1-A Phase 2 |
| G-A02 | AC-6(1) / AC-6(5) | command | 無特權帳號分離（Admin PIN 匿名 + all-or-nothing）| C1-A Phase 2 |
| G-A03 | SC-28 / PR.DS-01 | command + pi + pwa | **靜態資料未加密**：應用層 Fernet / DB SQLCipher / OS LUKS 全缺 | C1-C 擴大 |
| G-A04 | AU-9(3) | command + pi | Audit log **無 hash chain / 簽章**（INSERT-only 是程式約定可繞）| C1-D |
| G-A05 | AU-8 | command + pi | **時間來源不可信**（系統時鐘無 NTP 強制）→ ICS 214 法律效力受質疑 | C3-B 擴充（NTP）|
| G-A06 | SC-5 / V14 | command + pi | 全域 rate limit 缺；**只有 /login 有限速**；無 payload size limit | C2-F |

#### 🟡 High（v2.1.0 強烈建議補）

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-A07 | AC-2 | command | `delete_account()` hard DELETE，**audit_log operator 會指向不存在的 user**；應改 soft delete | C1-A Phase 2 |
| G-A08 | AC-7 / IA-2 | pi + pwa | Pi 端 / PWA 端**無登入 lockout / rate limit** | P-C1-A / W-C1-A |
| G-A09 | AC-12 / V3.3.2 | command + pwa | 無 idle session timeout；只有絕對 timeout | C1-A Phase 2 |
| G-A10 | AC-17(2) / SC-23 | command + pi | session token **無 IP / UA binding**（偷 token 即可用）| C1-A Phase 2 |
| G-A11 | AU-2 / AU-12 | command + pi + pwa | 寫入 audit 散在 service 層（非 100% 覆蓋）；應改 middleware 強制 | C1-D |
| G-A12 | AU-3 | command + pi | audit_log 缺 source IP / user agent / **correlation ID** | C1-D |
| G-A13 | AU-11 | command + pi | 無 audit log 保存 / 清除策略 | C1-D + security_policies §3 |
| G-A14 | IA-2(1)(2) | command + pi + pwa | **無 MFA**（單因素 PIN）；達不到 AAL2 | C1-A Phase 3 |
| G-A15 | IA-5(1) | command + pi + pwa | 4 位 PIN 可受暴力（lockout 緩解，但不夠）；**無連號 / 重複防** | C1-A Phase 2 |
| G-A16 | SC-12 / SC-17 | command + pi | step-ca **實機部署 + renew timer 未實測**；OCSP stapling 在 dev 關閉 | C1-B 收尾 / P-C1-B |
| G-A17 | SC-10 / V3 | pi + pwa | WebSocket **無 heartbeat 管理 / 認證模糊**；auth token 層細節待 Session B 驗 | C1-G |
| G-A18 | AU-4 / AU-5 | command + pi | log 容量無監控；寫 fail silent | C1-D + C3-C |

#### 🟠 Medium

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-A19 | AC-2(1) / AC-2(13) | command | 無自動化帳號 review / risk-based disable | C1-A Phase 2 |
| G-A20 | AC-10 | command | 同帳號可多 session 同時登入（無上限）| C1-A Phase 2 |
| G-A21 | AC-11 | command + pwa | 無 UI idle lock 觸發畫面鎖 | C1-A Phase 2 |
| G-A22 | AC-19 | pwa | PWA 無 MDM / device enrollment | W-C1-A / Wave 7 |
| G-A23 | AU-6 | command | audit log 查詢有，**異常告警規則無** | C1-D + C3-C |
| G-A24 | IA-3 | pwa | PWA 無 device identifier | W-C1-A |
| G-A25 | IA-11 | command | 敏感操作（改 role / 刪帳號）無強制重認證 | C1-A Phase 2 |
| G-A26 | SC-18 | pwa | CSP `unsafe-inline`（600+ inline styles/handlers）| C1-F |
| G-A27 | V2.5 | command | admin PIN 忘記恢復政策未文件化 | C1-A Phase 4 / security_policies §2 |

#### ⚪ Low

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-A28 | AC-8 | command | 無登入 banner | C1-A Phase 2（小項，併入）|
| G-A29 | V2.1.5 | command + pwa | PIN 欄位 paste 行為未驗（autocomplete=off？）| C1-A Phase 2 |
| G-A30 | V3.7 | command | 無 token rotation（敏感動作後換 token）| C1-A Phase 2（可選）|
| G-A31 | V3.3.1 | command | 登出未終結所有裝置 session | C1-A Phase 2 |

### Session B 發現（2026-04-25）

#### 🚨 Immediate fix（程式碼 bug，非 compliance gap）

| ID | 問題 | 檔案 | 說明 |
|---|---|---|---|
| **B-FIX-01** | `ws.isAuthed` 從未被 set | `server/ws_handler.js` `clear_table` 處 | 檢查 `if (!ws.isAuthed) reject` 永遠 reject（dead code 變相 deny-all）；要嘛刪 dead path、要嘛實作正確的 isAuthed flag；併入 P-C1-G |

#### 🔴 Critical（v2.1.0 投標前必補）

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-B01 | MP-2 / SC-28 / PT-7 / 個資法§27 | pwa | **病患特種個資 + 收容人員個資 IndexedDB 全明文** | W-C1-C |
| G-B02 | MP-2 / SC-28 | pi | Pi SQLite **整 DB 明文**（current_state / delta_log / snapshots 全帶 PII）| C1-C 擴大（P-C1-C 新項）|
| G-B03 | SC-28 | command | command SQLite 同（pi_received_batches / snapshots）| C1-C |
| G-B04 | V14.4(3) | pwa | **PWA 完全無 CSP**（無 meta，無 header，因 Pi 是 Express 不送 security headers）| W-C1-F |
| G-B05 | SC-23 / V9.2.2 | pi | WebSocket 訊息 **無簽章 / 無 HMAC / 無重放防護** | C1-G + P-C1-G |
| G-B06 | SC-8 | command + pi | **WS / Pi push 可 fallback 到 ws:// / http://**（STRICT_TLS=false 時）| C1-B 收尾 + P-C1-B |
| G-B07 | AC-7 | pi | **Pi server admin PIN 無 lockout**（command 有，Pi 沒對齊）| P-C1-A |
| G-B08 | PT-2 / 個資法§5,§6,§8 | command + pi + pwa | **無 purpose limitation 紀錄 + 無告知 + 無同意紀錄**（系統內）| C1-A Phase 4 + C1-C |
| G-B09 | 個資法§12 / IR-6 | command + pi + pwa | **無 72h PDPC 通報流程文件化** | security_policies.md §4 + C1-A Phase 4 |
| G-B10 | AU-12 / AU-3 | command + pi + pwa | **跨組件無 correlation ID**；同操作三邊 audit 無法串連 | C1-D |

#### 🟡 High（v2.1.0 強烈建議補）

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-B11 | AC-3 / SC-7 | pi | **WS broadcast 無 record-level 過濾**：所有 PWA 收所有 delta（包含 PII）| C1-G + W-C1-A |
| G-B12 | AU-3 | pi + pwa | PWA 上傳的 `audit_event` msg type **無服務端驗證**（任何人可送任意 audit）| P-C1-G |
| G-B13 | SI-11 / V14.3 | pi | **Pi 無全域 exception handler**；無 NODE_ENV 區分；錯誤可能洩漏 | P-C2-F |
| G-B14 | V8.1.1 | command + pi | audit_log `detail` JSON **可能含 PII**（無 tagger 過濾）| C1-C + C1-D |
| G-B15 | AC-2 / 個資法§11 | pi | Pi `accounts` 表帳號管理流程 **與 command 不同步**（雙端維護同帳號）| W-C1-A / P-C1-A 設計 |
| G-B16 | SC-5 | pi | **Pi server 無 rate limit**（任何層）；`express.json()` 預設 100kb | P-C2-F |
| G-B17 | AU-11 / 個資法§11 | command + pi + pwa | 三組件 audit_log 無 cleanup 政策；長期累積 | C1-D + security_policies §3 |
| G-B18 | V14.4 | pi | Pi `/static/` (PWA HTML 來源) **無 security headers**（X-Content-Type-Options / Referrer-Policy 等）| W-C1-F |
| G-B19 | AU-5 | pi | Pi audit 寫入失敗 silent swallow（try/catch 吞）| P-C1-G + C1-D |
| G-B20 | AC-3 / V4.1 | command | **commander_dashboard.html 376KB monolithic**（10,000+ 行 inline JS）| **C1-F 急迫**；前端模組化是 RBAC 前置 |
| G-B21 | SC-18 | pwa | shelter PWA 43× innerHTML / medical PWA 31× innerHTML | W-C1-F |
| G-B22 | CM-3 | pi | Pi 無 schema_migrations 版本表（migrations.js 是 ad-hoc CREATE IF NOT EXISTS）| P-C1-E |

#### 🟠 Medium

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-B23 | SI-7 | pi + pwa | sw.js cache HTML **無 origin 嚴格驗證**；可能 cache 跨版本髒資料 | W-C1-F |
| G-B24 | V8.1.2 | command | nginx 靜態 `/static/` 對敏感頁無 `Cache-Control: no-store` | C1-F |
| G-B25 | V7.3 | command + pi | 無正式 key rotation 政策（PIN / TLS / API key 都靠手動）| C1-A Phase 4 + C3-B |
| G-B26 | MP-6 | pwa + pi | 退場 disk wipe 流程未文件化 | C3-D + medical Phase 3 (Panic Wipe) |
| G-B27 | PT-3 / PT-4 | command + pwa | 無系統內隱私權告知 + 同意紀錄 | C1-A Phase 4 |
| G-B28 | V8.3 PII redaction by role | command | 觀察員 role 預期能看 dashboard 但**不該看完整病患 PII**；目前無 role-based PII redaction | C1-A Phase 2 + C1-C |

### Session C 發現（2026-04-25）

#### 🔴 Critical（v2.1.0 投標前必補）

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-C01 | CP-9 / CIS §11 / 個資法§27 | command + pi | **無自動備份腳本**（WAL 不夠；無 daily gzip / NAS rsync）| **C3-D 急迫** |
| G-C02 | CP-10 / CSF RC.RP | command + pi + pwa | **無實機故障還原 playbook**（commercialization 寫了 RTO 4h 但無 runbook）| C3-D + policies §5 |
| G-C03 | CP-4 | command + pi | **無 DR drill 紀錄 / 流程**（要求每 6 個月）| C3-D + policies §5 |
| G-C04 | IR-6 / IR-8 / 個資法§12 | command + pi + pwa | **無 IR plan + 無 PDPC 72h 通報程序文件** | C1-A Phase 4 + policies §4 |
| G-C05 | CIS §16 | command | **TOCTOU mutex bug 已知未修**（演練 concurrent activate xfail）| C2-A 急迫修復（不是新 Cx，是 known issue） |
| G-C06 | CM-3 / CM-6 | command + pi | **TLS 憑證路徑 hardcoded in systemd unit files**（cert/key 路徑）；renewal / drift 無監控 | C3-A + C3-B 擴 |

#### 🟡 High（v2.1.0 強烈建議補）

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-C07 | SI-4 / DE.CM | command + pi | **無 Prometheus `/metrics`**；`/api/health` 基礎（不查 DB / 子服務）| C3-C 擴 |
| G-C08 | SI-4 / DE.AE | command + pi | **無異常告警**；audit log 查詢有，無 alert rule | C3-C |
| G-C09 | RV.1 / CIS §7 | command + pi | **Dependabot / npm audit 無 CI 整合**；npm 端供應鏈不掃 | C2-C 擴 + C2-E |
| G-C10 | RV.3 / 公開貢獻 | meta | **無 SECURITY.md 漏洞通報流程文件** | 立即可補（policies §4 + repo root SECURITY.md） |
| G-C11 | CM-8 / SR-4 / SLSA L2 | command | **無 SBOM**（CycloneDX）；無 SLSA provenance | C2-E |
| G-C12 | PS.2 / SR-11 | command | **無 commit / artifact 簽章**（無 GPG / cosign）| C2-E + C3-F |
| G-C13 | SA-11 / 25010 Reliability | command | **覆蓋率 44%** — sync_repo 9% / ttx_repo 22% / map 29% / admin 37% | C2-A 擴 |
| G-C14 | SA-11 | pi + pwa | **Pi 0 測試 / PWA 0 測試**（CI 無對應 job）| P-C2-* / W-C2-A |
| G-C15 | 25010 Maintainability | command | **legacy dead code 未清**（db.py 65KB + main_legacy.py 66KB，0% coverage 占用）| 立即可清（清廢碼，不必 Cx） |
| G-C16 | 25010 Performance / SC-5 | command + pi | **無 load / stress 測試**；無 profiling 記錄 | C2-A 擴 + DB 並發決策 B 落實 |
| G-C17 | CM-3 / SR-1 | command | **無 mypy 型別檢查**（runtime 型別錯誤風險）| C2-B 擴 |
| G-C18 | DE.CM | command + pi | log 寫 `/tmp/ics_*.log`（**ephemeral, 重啟消失**）；無集中化 | C3-C + C1-D |
| ~~G-C19~~ | CP-9 | command | ~~DB 在 git repo~~ → **驗證為 false positive**：`.gitignore` 已有 `*.db`；audit agent 誤判 | ✅ 不需修 |

#### 🟠 Medium

| ID | Control | Component | Gap | Target Cx |
|---|---|---|---|---|
| G-C20 | CM-2 | command + pi | nginx / step-ca config 無 baseline 文件；散在多檔 | C3-A |
| G-C21 | MA-4 | command + pi | SSH 遠端維護無 bastion / VPN 文件 | policies + C3-B |
| G-C22 | CIS §12 | pi | Pi WiFi AP 設定無 IaC（手動）；無 firewall 規則 | C3-B + Wave 7 |
| G-C23 | 25010 Compatibility | ci | **CI 只跑 ubuntu-latest**；無 multi-OS / multi-Python matrix | C2-B |
| G-C24 | RV.2 | ci | bandit 無 CVSS / 無 artifact 存檔（只 stdout）| C2-C 擴 |
| G-C25 | CIS §15 | meta | **無 vendor 評估流程文件**（雖有「禁中國」原則）| policies + C2-E |
| G-C26 | 25010 Safety | command + pwa | **無 fail-safe mode 文件**（系統故障時 fallback 行為，涉及生命安全）| 規格書 + C3-D |
| G-C27 | 25010 Portability | command | 無 Windows ops 支援（dev OK）| 文件層（不必修） |
| G-C28 | PR template | meta | 無 PR template 強制 review 規則 | 立即可補（`.github/PULL_REQUEST_TEMPLATE.md`）|

#### ⚪ Low / Quick wins

| ID | 項目 | 說明 |
|---|---|---|
| G-C29 | `.github/CONTRIBUTING.md` 缺 | 開源 Open Core 後需要 |
| G-C30 | Code of Conduct 缺 | 開源 Open Core 後需要 |

#### ✅ Session C 確認的亮點

| 項目 | 證據 |
|---|---|
| 測試體系成熟 | 269 tests / 4 layers / 129 security tests |
| 安全測試覆蓋 | login lockout 9 / first-run 10 / admin gate 10 / payload fuzzing 15 / token forging 5 |
| Code quality 工具 | ruff（E/F/I/UP/B）+ ruff-format + detect-secrets + pre-commit |
| CI 自動化 | ci-backend.yml 每 push 跑 pytest + pip-audit + bandit + coverage |
| systemd units 結構 | 3 個 service + 依賴 + restart policy + 階梯式 RestartSec |
| 依賴 pinned | requirements.txt + requirements-test.txt 全 == |
| Branch 策略文件化 | CLAUDE.md feature branch + PR + DoD |
| `.secrets.baseline` 已 commit | detect-secrets V1.5.0 設計 |

#### ✅ Session B 確認的亮點（已 comply 項目）

| 項目 | 證據 |
|---|---|
| Medical PWA export 加密 | AES-256-GCM with PBKDF2 derived key（醫療 PWA `ExportCrypto`）|
| Shelter PWA snapshot 加密 export | 同上 |
| WS heartbeat ping | 25s ping，無回應 terminate（雖然不夠完整，但有基本機制）|
| push_queue 24h cleanup | `MAX_QUEUE_AGE_MS=24h` 自動清過期未送資料 |
| PIN client-side hash | shelter / medical PWA 都用 PBKDF2-SHA256 100k iter（client-side hash before send）|
| WAL mode | Pi SQLite + command SQLite 都啟 WAL |

---

## Evidence Index（關鍵 control 的實作位置）

> 用途：稽核時快速對應「我們符合 AC-X，請看這些檔案」。
> 命名：`<NIST/ASVS ID> → <檔案路徑>:<line> → <說明>`

### Session A 索引（auth/transport/schema 族）

#### 認證（IA / V2 / V3）
- `IA-2 / V2.1.7 / V3` → `command-dashboard/src/auth/service.py` → Session 建立 / 驗證 / timeout
- `IA-5 / V2.1.1 / IA-5(1)` → `command-dashboard/src/repositories/account_repo.py` → PBKDF2-SHA256 100k iter, 16-byte salt
- `IA-2(8) / V3.5` → `command-dashboard/src/auth/middleware.py` → X-Session-Token header 驗證
- `AC-7 / V2` → `command-dashboard/src/auth/rate_limit.py` → 10 req/min/IP login rate limit
- `AC-7 / V2 lockout` → `command-dashboard/src/repositories/account_repo.py` → 5x15min 帳號鎖定（持久化）
- `AC-7 admin PIN lockout` → `command-dashboard/src/repositories/config_repo.py` → 5x30min admin PIN 鎖定（持久化）
- `IA-5(1) initial secret` → `command-dashboard/src/repositories/config_repo.py::ensure_initial_admin_token()` → 隨機 6 位 PIN
- `IA-2 first-run gate` → `command-dashboard/src/auth/first_run_gate.py` → 423 擋阻 + whitelist

#### 存取控制（AC / V4）
- `AC-3 admin PIN gate` → `command-dashboard/src/routers/admin.py::_check_admin_pin()` → /api/admin/* 全閘
- `AC-14 PUBLIC_PATHS` → `command-dashboard/src/core/config.py` → /health, /docs, /static 豁免清單
- `AC-3 粗分 role check` → `command-dashboard/src/routers/config_router.py:21` → `if sess["role"] != "指揮官"`（範例）

#### 稽核（AU）
- `AU-2 / AU-3 audit_log` → `command-dashboard/src/db.py` → audit_log table schema + INSERT-only 程式約定
- `AU-6 audit query` → `command-dashboard/src/routers/admin.py:216` → /api/admin/audit-log endpoint

#### 加密傳輸（SC / V9）
- `SC-8 TLS config` → `deploy/nginx/conf.d/ssl-common.conf` → TLS 1.2/1.3, Mozilla Intermediate
- `SC-7 / SC-8 security headers` → `deploy/nginx/conf.d/security-headers.conf` → HSTS, X-Frame-Options, etc.
- `SC-7 CSP` → `command-dashboard/src/core/security_headers.py` → CSP middleware (report-only)
- `SC-17 PKI` → `deploy/step-ca/` → per-customer step-ca + issue/renew/uninstall scripts
- `SC-8 Pi push auth` → `command-dashboard/src/services/pi_push_service.py::validate_pi_push()` → Bearer token

#### Schema 管理（CM-3 / CM-6）
- `CM-3 migrations` → `command-dashboard/src/core/database.py` → _MIGRATIONS list M001-M005, idempotent
- `CM-6 schema_migrations` → `command-dashboard/src/db.py` → schema_migrations 追蹤表

### Session B 索引（PII / Audit 跨組件 / Frontend）

#### Pi server
- `AC-7 / IA-2 Pi auth` → `server/auth.js` → PBKDF2 PIN + login_failures 表（30min/5x lockout 帳號層）
- `IA-2 Pi WS auth` → `server/ws_handler.js` → WS 連線後 `auth` msg + PBKDF2 驗證
- `AU-2 Pi audit write` → `server/audit.js::writeAuditLog()` → `audit_log` 表 INSERT
- `AU-2 Pi audit events` → `server/ws_handler.js` + `server/routes.js` → 顯式呼叫各 event
- `SC-8 Pi TLS load` → `server/config.js:62-84` → CERT_PATH / KEY_PATH / STRICT_TLS 邏輯
- `SC-8 Pi push to command` → `server/sync.js:144-145` → POST `/api/pi-push/{unit}` + Bearer token
- `AC-3 Pi admin gate` → `server/middleware.js::adminAuth` → x-admin-pin 比對

#### Shelter PWA
- `IA-2 PWA login` → `shelter-pwa/public/shelter_pwa.html` → PIN + PBKDF2-SHA256 100k iter（client-side hash）
- `MP-2 / SC-28 IndexedDB` → `shelter-pwa/public/shelter_pwa.html` → Dexie schema v3（persons / beds / incidents / shifts / audit_log / snapshots / config）
- `SC-18 frontend` → `shelter-pwa/public/shelter_pwa.html` → 43× innerHTML
- `SI-7 service worker` → `shelter-pwa/public/sw.js` → Cache-First 策略 + 無 origin 嚴格驗證
- `MP-7 export` → `shelter-pwa/public/shelter_pwa.html::ExportCrypto` → AES-256-GCM with PBKDF2 key

#### Medical PWA
- `IA-2 PWA login` → `medical-pwa/public/medical_pwa.html` → 同 shelter
- `MP-2 / PT-7 / SC-28 IndexedDB` → `medical-pwa/public/medical_pwa.html` → Dexie schema v5（**patients 表含特種個資**：source_age / source_sex / injury_type / trauma_or_medical）
- `MP-7 export` → `medical-pwa/public/medical_pwa.html::ExportCrypto` → AES-256-GCM
- `SC-18 frontend` → `medical-pwa/public/medical_pwa.html` → 31× innerHTML

#### Cross-component
- `AU-3 跨組件 audit 缺串連` → 三組件無 correlation ID（gap）
- `SC-8 PWA → Pi → Command 資料流` → `server/ws_handler.js` broadcasts deltas → `server/sync.js` 推 command（PII 全程明文）

### Session C 索引（Quality / Deploy / Ops）

#### CI / 測試 / 工具
- `PW.6 / SA-11 / CIS §16` → `command-dashboard/tests/` → 269 tests, 4 layers
- `PW.6 test catalog` → `command-dashboard/tests/TEST_CATALOG.md` → 完整測試型錄 + 覆蓋率分析
- `PO.1 / CI` → `.github/workflows/ci-backend.yml` → pytest + pip-audit + bandit
- `PW.4 / CIS §16.11` → `command-dashboard/.pre-commit-config.yaml` → ruff + detect-secrets + 基礎檢查
- `PW.5 / V14.1` → `command-dashboard/pyproject.toml` → ruff 規則 E/F/I/UP/B
- `PS.3 / CI artifact` → `.github/workflows/ci-backend.yml` retention 30 days

#### 部署 / Ops
- `CM-2 / MA-2` → `command-dashboard/setup.sh` → 開發環境初始化（idempotent）
- `MA-2 / CM-3` → `update_pi.sh` → git pull + 條件式 deps reinstall + systemctl restart
- `MA-2` → `start_pi.sh` / `start_mac_https.sh` → 多服務啟動順序 + health check
- `CM-7 / MA-2` → `command-dashboard/systemd/*.service` → 3 個 service + 依賴 + restart 策略
- `IR-5 / DE.CM` → `command-dashboard/src/routers/dashboard.py:40-42` → `/api/health`（基礎）

#### 配置
- `CM-6` → `command-dashboard/src/core/config.py` → env var + 預設值
- `CM-2` → `deploy/nginx/conf.d/*.conf` → nginx baseline + sed runtime substitution
- `SC-12` → `deploy/step-ca/` → PKI scripts（init / issue / renew）

### Session D 索引（待補）

_（Session D 執行時追加，預期會覆蓋 NIMS / ICS 508 / Taiwan 法規 / 整合）_

---

## 主張 compliance 的清單（供投標 / 行銷引用）

> 完成 session A/B/C/D 後，此區列出「可對外主張已 comply」的標準 / 控制項清單，搭配實作證據。
>
> **原則**：寧可少說，不誇大。未完成的標記「規劃中（target Cx-X）」，不隱瞞。

_（Session D 結束時填入）_
