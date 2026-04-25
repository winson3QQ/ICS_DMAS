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
| A | C0 + C1-A + C1-B + C1-E（Auth/Transport/Schema） | 🔄 進行中 | 2026-04-25 | Architecture-level audit 完成；詳下 |
| B | C1-C + C1-D + C1-F + W-C1-* + P-C1-*（PII/Audit/Frontend） | ⏸ 未開始 | — | — |
| C | C2 + C3 + P-C2-* + W-C2-*（Quality/Deploy/Ops） | ⏸ 未開始 | — | — |
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

**Session B/C/D 可能需要補讀（本 session 未深讀）**：
- `command-dashboard/src/routers/events.py` / `decisions.py` / `snapshots.py` — 寫入類 endpoints（Session B 配 C1-D correlation ID）
- `server/auth.js`, `server/ws_handler.js`, `server/middleware.js` — Pi server auth（Session B 配 P-C1-G）
- `command-dashboard/static/commander_dashboard.html` — 前端 role gate（Session B 配 W-C1-A 審）
- `shelter-pwa/`, `medical-pwa/` — PWA 原始碼（Session B 必讀）
- `.github/workflows/*.yml` — CI 設定（Session C 必讀）

### 未決定 / 待追問（cross-session issue）

**Session A 4 議題 — 已決議**（2026-04-25，詳見 architecture_decisions.md Decision Set C）：

1. ✅ **Session 雙層 timeout**：30 min idle + 14 hr 絕對 + 28 min 警告（C1-A Phase 2）
2. ✅ **Session 漸層綁定 IP + UA family + 5 道配套防線**（C1-A Phase 2）
3. ✅ **Soft delete**：status='archived' + deleted_at 欄位，物理刪走獨立流程（C1-A Phase 2，M006 一併加欄位）
4. ✅ **Rate limit 純 SQLite 持久化**：選 A，不用 Redis（C2-F）

**Session cookie vs header**：保留 X-Session-Token header（抗 CSRF），不改 cookie。

**新生議題（Session B 處理）**：
- 暫無

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

_Session C 填入：SI-2/3/4/7/10/11/16_

### 1.6 CM — Configuration Management

_Session C 填入：CM-2/3/6/7/8_

### 1.7 CP — Contingency Planning

_Session C 填入：CP-2/4/9/10_

### 1.8 IR — Incident Response

_Session C 填入：IR-4/5/6/8_

### 1.9 PL — Planning

_Session D 填入：PL-2/8_

### 1.10 RA — Risk Assessment

_Session D 填入：RA-3/5（含 threat_model）_

### 1.11 SA — System and Services Acquisition

_Session C 填入：SA-8/11/15（SSDF 相關）_

### 1.12 SR — Supply Chain Risk Management

_Session C 填入：SR-3/5/11（SBOM / SLSA 相關）_

### 1.13 MP / PE / PS / AT

_Session D 評估：本系統多為組織流程層（訓練、實體安全、人員管理），部分 N/A_

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

_Session C 填入：資產清單、風險評估、供應鏈_

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

#### PR.DS — Data Security（部分）

| ID | 子能力 | Status | 對應 |
|---|---|:---:|---|
| PR.DS-01 | Data-at-rest 保護 | ❌ | SC-28；C1-C 三層加密待做 |
| PR.DS-02 | Data-in-transit 保護 | ✅ | SC-8；TLS 完整 |
| PR.DS-10 | Data-in-use 保護 | N/A | 單機處理 |

### 3.4 DETECT

_Session C 填入：異常事件、持續監控_

### 3.5 RESPOND

_Session C 填入：事件應變、分析、溝通_

### 3.6 RECOVER

_Session C 填入：恢復計畫、改善_

---

## 4. NIST SP 800-218 SSDF（Secure Software Development Framework）

> 原文：https://csrc.nist.gov/Projects/ssdf

### 4.1 PO — Prepare the Organization

_Session C 填入：PO.1/2/3/4/5_

### 4.2 PS — Protect the Software

_Session C 填入：PS.1/2/3_

### 4.3 PW — Produce Well-Secured Software

_Session C 填入：PW.1-9_

### 4.4 RV — Respond to Vulnerabilities

_Session C 填入：RV.1/2/3_

---

## 5. ISO/IEC 25010:2023（軟體品質 8 特性）

> 原文：ISO/IEC 25010:2023 Systems and software engineering - Systems and software quality models

### 5.1 Functional Suitability（功能性）

_Session C 填入_

### 5.2 Performance Efficiency（效能效率）

_Session C 填入_

### 5.3 Compatibility（相容性）

_Session C 填入_

### 5.4 Interaction Capability（使用性）

_Session C 填入_

### 5.5 Reliability（可靠性）

_Session C 填入_

### 5.6 Security（資訊安全）

_交互 reference NIST + OWASP ASVS；Session A/B/C 貢獻_

### 5.7 Maintainability（可維護性）

_Session C 填入，與 C0 分層架構對照_

### 5.8 Portability（可攜性）

_Session C 填入_

### 5.9 Flexibility（彈性，2023 新增）

_Session C 填入_

### 5.10 Safety（安全，2023 新增）

_Session D 填入（涉及事件操作的生命安全）_

---

## 6. ISO/IEC 5055:2021（CWE-based 軟體量測）

> 原文：ISO/IEC 5055:2021 Information technology - Software measurement - Software quality measurement

### 6.1 Reliability

_Session C 填入：CWE 依 ASVS / CIS 輔以測試_

### 6.2 Security

_Session C 填入_

### 6.3 Performance Efficiency

_Session C 填入_

### 6.4 Maintainability

_Session C 填入_

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
| V9.1.1 TLS for all inbound connections | ✅ | nginx 終端 TLS 1.2+；loopback 到 FastAPI 是明文但同主機 |
| V9.1.2 Modern TLS configuration | ✅ | Mozilla Intermediate 2024-09 |
| V9.1.3 Insecure protocols 禁用 | ✅ | TLS 1.0/1.1 禁用 |
| V9.2.1 Outbound connections 驗證憑證 | ⚠️ | Python requests / urllib 預設 verify=True；待驗證是否有 verify=False 的地方 |
| V9.2.2 Encrypted communications with backend components | ⚠️ | Pi↔Command HTTPS + Bearer；**缺 mTLS**（C1-G）|
| V9.2.3 Authenticated connections with backend | ✅ | Bearer token 驗 |
| V9.2.4 Certificates validated against trust chain | ✅ | step-ca CA 掛到系統 trust store（trust-root-mac.sh）|

---

## 8. CIS Controls v8

> 原文：https://www.cisecurity.org/controls/

### 18 CIS controls

_Session A/B/C 分工填入（Control 1-18），每個 control 的 Safeguard level IG1/IG2_

---

## 9. OWASP SAMM 2.0

> 原文：https://owaspsamm.org/

### 5 Business Functions × 3 Practices × 3 Maturity Levels

_Session C 填入：目標 Level 2（Governance / Design / Implementation / Verification / Operations）_

---

## 10. SLSA v1.0（Supply Chain Integrity）

> 原文：https://slsa.dev/spec/v1.0/

### Build Levels 1-4

_Session C 填入：目標 L2（short-term），L3（long-term, C2-E）_

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

_Session B 填入：個資欄位清單 / 蒐集目的 / 存取稽核 / 72h 通報_

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

### Session B/C/D 索引（待補）

_（後續 session 執行時追加，預期會覆蓋 audit hash chain、PII 加密、CI/CD、NIMS 對應）_

---

## 主張 compliance 的清單（供投標 / 行銷引用）

> 完成 session A/B/C/D 後，此區列出「可對外主張已 comply」的標準 / 控制項清單，搭配實作證據。
>
> **原則**：寧可少說，不誇大。未完成的標記「規劃中（target Cx-X）」，不隱瞞。

_（Session D 結束時填入）_
