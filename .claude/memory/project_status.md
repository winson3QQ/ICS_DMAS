---
name: 專案狀態總覽
description: 醫療 PWA 進度、指揮部路線圖、硬體資訊、Pi 設定步驟
type: project
originSessionId: 543daa3e-1ccf-42d0-95b2-51722f37c565
---
## 上次做到哪裡（2026-04-25，Compliance Phase 0 完成 + cmd-v2.0.6 hotfix）

### Compliance Phase 0 完成項目（2026-04-25）

| 項目 | 內容 |
|------|------|
| **Session A** | Auth/Transport/Schema audit；NIST AC/IA/SC/AU + 800-63-3 + ASVS V2-V4-V9；31 個 gap |
| **Session B** | PII/Audit/Frontend audit；3 組件並行掃描；28 gap + 1 fix（B-FIX-01 isAuthed bug）+ 6 亮點 |
| **Session C** | Quality/Deploy/Ops audit；SSDF + ISO 25010/5055 + SAMM + SLSA + CIS Controls + DORA；30 gap + 8 亮點 |
| **Session D** | NIMS/ICS 508/Taiwan 法規 + 整合；20 gap + 6 亮點 |
| **累計** | 88 gap + 14 亮點，全進現有 Cx 範圍（無新 Cx 需加） |

### 文件交付（commit ad9d837 / 2417a52 等系列）

- `docs/compliance/README.md` — 入口 + session 計劃
- `docs/compliance/matrix.md` — 主對照表（13 大標準節區 + Gap Register + Evidence Index + 「可主張 compliance」master 清單）
- `docs/compliance/threat_model.md` — STRIDE 骨架
- `docs/compliance/security_policies.md` — 6 政策骨架
- `SECURITY.md` — 漏洞通報政策（含 PDPC 72h）
- `.github/PULL_REQUEST_TEMPLATE.md` — DoD checklist
- `docs/ROADMAP.md` — v2.1.0 Critical Path 6 波依賴順序

### Decision Sets（重要架構決策）

詳見 `architecture_decisions.md`：
- **Decision A**：IP 策略 — Open Core
- **Decision B**：DB 並發 — SQLite + retry（短期）/ PG（長期）
- **Decision Set C**（Session A 4 議題）：Session 雙層 timeout + IP/UA 漸層綁定 + Soft delete + Rate limit SQLite
- **Decision Set D**（Session B 5 議題）+ D0 實作優先策略：command 優先 / Pi/PWA 影響 command 也優先；C1-F 提前；audit hash chain 設計 + PII redaction by role；P-C1-E 擴大；B-FIX-01 併入 P-C1-G
- **Decision E**：功能與 License 解耦（v2.1.0 階段所有 Cx 寫成 license 無感；C4 才接 license file）

### cmd-v2.0.6 hotfix + cleanup（commit 46edd17 / dd2a554 / ec42894 / 4a95eba）

| 項目 | 內容 |
|------|------|
| **TOCTOU mutex hotfix** ✅ | `exercise_repo.update_exercise_status` 改原子 UPDATE+NOT EXISTS；test_concurrent xfail → passed |
| **Legacy dead code 清除** ✅ | 刪 `src/db.py`（65KB）+ `src/main_legacy.py`（66KB）；setup.sh 改用 `core.database.init_db` |
| **SECURITY.md** ✅ | 漏洞通報政策（含 PDPC 72h、SLA、scope） |
| **PR template** ✅ | `.github/PULL_REQUEST_TEMPLATE.md` 含 DoD checklist |
| **Hooks 跨平台** ✅ | `.githooks/post-merge` + `post-checkout` 改 python3（解 Windows UTF-8 sed bug） |
| **CLAUDE.md DoD** ✅ | 加「功能完成定義」章節（缺測不算完成）|

### 下一步：v2.1.0 Critical Path 第 1 波

依 ROADMAP「v2.1.0 Critical Path」起手三選一：
1. **C3-D 自動備份**（建議優先；30 分鐘可有最低版本，6 月演練前最關鍵，不擋其他 Cx）
2. **C1-F 模組化**（C1-A Phase 2 RBAC 的硬前提）
3. **C1-A Phase 4 政策文件**（IR plan + PDPC 程序）

---

## 上次做到哪裡（2026-04-24，C2-C/D + C1-E，cmd-v2.0.5）

### cmd-v2.0.5 完成項目

| 項目 | 內容 |
|------|------|
| **C2-C** ✅ | ruff linter（E/F/I/UP/B）+ pre-commit + detect-secrets；140 處自動修正 + 11 處 B904 手動修正 |
| **C2-D** ✅ | Admin PIN 鎖定（5次/30分）；前端顯示剩餘次數、本地時間解鎖提示 |
| **C1-E** ✅ | `schema_migrations` 表版本追蹤（M001-M005）；`GET /api/admin/schema-migrations`；Admin 面板「系統」tab |
| **Admin PIN 首次設定修正** ✅ | 移除預設 1234，改隨機 PIN 寫 `~/.ics/admin_pin_token`；未設定時 503 |
| **Pi server P-Cx roadmap** ✅ | 列出 P-C1-A/D/E、P-C2-C 待做項目 |
| 測試 | 269 passed + 1 xfailed（+18 新測試） |
| PRs | #1 C2-C / #2 C2-D / #3 C1-E → 全 merge 進 main |

### 下一步

| 優先 | 項目 |
|------|------|
| 🔴 | C1-A Phase 2：RBAC（指揮官 role 直接進 Admin 面板，解決兩套密碼問題）|
| 🟡 | C1-D：Append-only 稽核 hash chain |
| 🟡 | P-C1-A：Pi server Admin PIN 鎖定 |

---

## 上次做到哪裡（2026-04-24，外部 bundle 整合，cmd-v2.0.4）

### 測試擴充狀態（cmd-v2.0.4）

| 項目 | 狀態 |
|------|------|
| 外部生成 9 個 strict bundle 評估：7 個有值、2 個（admin_auth、auth_api）全重複丟棄 | ✅ |
| 去重後淨增 10 個測試（251 total = 250 passed + 1 xfailed） | ✅ |
| 新增：`TestLoginLockoutReset`（lockout reset DB 驗證）| ✅ |
| 新增：`TestSessionStrictBoundary`（heartbeat remaining、expired heartbeat→401）| ✅ |
| 新增：`TestExercisesStrict`（exact ID、exact 409、archive 404）| ✅ |
| 新增：`TestEventsStrict`（exact ID、status 4xx、notes 404）| ✅ |
| 新增：`TestWithinPayloadDuplicate`（sync payload 內重複 ID → last wins=UPDATE）| ✅ |
| **Production bug fix**：`do_archive` router 未做存在性檢查，靜默 200 → 改 404 | ✅ |
| TEST_CATALOG.md 更新（251 total） | ✅ |

### 測試擴充狀態（cmd-v2.0.3，舊）

| 項目 | 狀態 |
|------|------|
| Smoke v2（51 個）：replay、session edge、concurrent mutex、auth bypass、payload fuzzing | ✅ |
| Smoke v3（38 個）：admin gate、sync extended、session config、firstrun config | ✅ |
| 合計 241 tests（240 passed + 1 xfailed TOCTOU） | ✅ |
| Coverage 44%（排除 legacy dead code） | ✅ |
| 已知風險：exercise mutex TOCTOU（xfailed，C2 修正） | ⚠️ |
| TEST_CATALOG.md、ROADMAP.md、commercialization_plan_v1.md 全更新 | ✅ |
| 報告：`tests/reports/smoke_v3_20260424_144713.html` | ✅ |

---

## 上次做到哪裡（2026-04-24，C1-A Phase 1 完成）

### C1-A Phase 1 完成狀態（cmd-v2.0.2）

| 項目 | 狀態 |
|------|------|
| accounts schema：`failed_login_count` + `locked_until` + `is_default_pin` | ✅ |
| `verify_login()` 改 tuple 回傳 `(account, reason)` | ✅ |
| 5 fails / 15 min account lockout | ✅ |
| `unlock_account()` 管理員手動解鎖 | ✅ |
| `auth/rate_limit.py` middleware（10 req / IP / min for `/api/auth/login`） | ✅ |
| 423 Locked / 429 Too Many Requests responses | ✅ |
| `ensure_initial_admin_token()` 產隨機 6 位數 PIN（取代舊的 1234）| ✅ |
| PIN 印 console + 寫 `~/.ics/first_run_token`（chmod 600） | ✅ |
| login API 回傳 `must_change_pin` flag | ✅ |
| 改 PIN 後 `clear_default_pin_flag()` | ✅ |
| `first_run_gate_middleware` 423 Locked + whitelist | ✅ |
| 19 個新測試（`tests/security/test_login_lockout.py` + `test_first_run.py`） | ✅ |
| 152 unit tests 全綠（原 133 + 19）| ✅ |

**C1-A 後續 Phase（待後續 session）**：
- Phase 2：RBAC OBSERVER 角色 + 對齊 SYSTEM_ADMIN/COMMANDER 英文 role（影響面大，需 DB migration 決策）
- Phase 3：TOTP MFA + 備援碼（新依賴 pyotp + qrcode，需先確認供應鏈）
- Phase 4：CISO 文件範本（純 markdown）

**關鍵架構決策**：
- Lockout 用 accounts 表加欄位（不開新表，避免 join cost）
- Rate limit in-memory（單機 N100 足夠；水平擴展才需 Redis）
- First-run gate whitelist：login / change-pin / health / static / docs
- conftest.py 新增 `_reset_rate_limit` autouse fixture + `client` fixture 清 `is_default_pin` flag

---
## 上次做到哪裡（2026-04-24，C1-B 全面加密傳輸完成）

### C1-B 完成狀態（cmd-v2.0.1 / server-v1.3.0）

| 項目 | 狀態 |
|------|------|
| FastAPI CORS env 白名單（`ALLOWED_ORIGINS`）| ✅ |
| FastAPI CSP middleware（report-only + `/api/security/csp-report`）| ✅ |
| nginx 模組化反代（HTTP/2 + TLS 1.2/1.3 + HSTS + 安全標頭）| ✅ |
| step-ca 內網 PKI（init / start / trust / issue / renew / uninstall 腳本）| ✅ |
| Pi server `STRICT_TLS=true` env（沒憑證 fail-fast）| ✅ |
| `start_mac_https.sh`（C1-B 完整 stack 啟動）| ✅ |
| `deploy/demo-tls-capture.sh`（HTTP vs HTTPS Wireshark 對照）| ✅ |
| Tier 1-3 + Wireshark 對照組驗證 | ✅ 全綠 |
| PKI 管理政策（deploy/README.md §PKI 管理政策）| ✅ |
| 133 unit tests | ✅ |

**待後續 cX 處理**：
- CSP enforce mode（觀察 1-2 週後切；本輪 report-only）
- C1-A MFA + 登入鎖定 + OBSERVER 角色
- C1-F 前端模組化後升級 strict CSP（nonce-based）
- C3-B install.sh：systemd unit 設 `STRICT_TLS=true`、ACME renew timer、雙軌 CA 選項

**研究結論（政府採購 PKI）**：
- 附表十資通系統防護基準對加密只規範「演算法強度 + 金鑰管理 SOP」，**未指定 CA 來源**
- GTLSCA 為對外服務官方推薦，內網系統非強制
- ICS_DMAS 採雙軌設計：step-ca（預設）/ GTLSCA / BYO，C3-B install.sh `--cert-source=` 支援

**關鍵架構**：
- 鏈路加密：① 瀏覽器↔Command HTTPS、② iPad↔Pi HTTPS+WSS、③ nginx↔FastAPI loopback HTTP（零風險）、④ Pi push HTTPS
- iPad 不直連 Command（hub-and-spoke），所有 PWA 經由 Pi 中介
- 22 縣市 per-customer step-ca 獨立 instance（CA 私鑰外洩只影響該客戶）

詳見 [c1b_https_decisions.md](c1b_https_decisions.md)。

---
## 上次做到哪裡（2026-04-23，C0 後端重構完成）

### C0 重構完成狀態（cmd-v2.0.1，refactor/c0-command-backend branch）

| 項目 | 狀態 |
|------|------|
| 後端分層（routers/services/repositories/auth/core） | ✅ |
| Pi 端分層（server-v1.2.0） | ✅ |
| main.py ≤ 80 行（74 行） | ✅ |
| 133 個測試 + CI 全綠 | ✅ |
| 演練資料基礎 Schema（6 張表） | ✅ |
| AI / TAK stub | ✅ |
| C5 前向相容（4 件） | ✅ |
| PWA API 路徑對齊 | ✅ |
| 前端模組化（.js + esbuild） | 移至 C1-F |
| admin PIN 初始化（ensure_default_admin_pin） | ✅ |
| 臂章替換為台灣曙豐防災自訓團 | ✅ |

**下一步**：confirm CI 全綠後 merge refactor/c0-command-backend → main，然後開 C1 分支。

---

## 上次做到哪裡（2026-04-22，shelter-v2.2.49～v2.2.53）

### 本輪修復的核心問題：床位數在 Command 顯示錯誤且持續累加

**根本原因鏈**：
1. `seedDefaultBeds()` 沒有呼叫 `AuditManager.stamp()`，beds 沒有 `updated_at`
2. `pushRecoveryData` 過濾條件是 `updated_at >= last_sync_ts`，空床全被過濾
3. Dexie `clear()` 不重置 auto-increment，每次 reseed beds ID 持續累加（197→224→234…）
4. Pi 用 UPSERT（record_id PK），舊 ID 永遠不被刪，Command 端床數一直疊加

**修復方案**：
- `seedDefaultBeds()` 加入 `AuditManager.stamp()`（beds 有 updated_at）
- `pushRecoveryData()` 支援 `opts.fullSyncTables`，發送前帶 `full_sync_tables:['beds']`
- Pi server（v1.1.2）收到 `sync_push` 後，對 `full_sync_tables` 中的 table 先 DELETE 再 INSERT（原子操作）
- 消除 `sendClearTable` + `pushRecoveryData` 的 race condition（合併為單一 WS 訊息）

### 床位設定改版（shelter-v2.2.52）
- 「各區床位數量」改為逐區輸入（`data-zone` input），直接控制每區床數
- `saveConfig()` 偵測 `zonesChanged` 後自動呼叫 `confirmReseedBeds(true)`（不再彈確認）
- 新增 `_syncCapacityToPi()`：beds_meta `{_id:'capacity', capacity_max:N}` 推 Pi
- Command `_pi_batch_to_snapshot()` 讀 beds_meta → 用 `capacity_max` 作為 `bed_total`

### 床位頁合計列（shelter-v2.2.53）
- `.bed-legend` 右側新增 `<span id="bed-total-stats">`
- `renderBeds()` 計算所有區合計（空/佔/共），每次渲染更新右側合計文字

### 收容組事件 vs 指揮部事件追蹤（釐清）
- 收容組 incidents → Pi → Command `pi_received_batches` → 顯示於收容所節點詳情「組內事件」tab
- 指揮部「事件追蹤」列（EV-XXX）只包含 Command `/api/events` 建立的正式 ICS 事件
- 兩者刻意分開；若需升報可加「升報至指揮部」按鈕（尚未實作）

### 待確認（下次回來）
- Pi server 是否已重啟至 v1.1.2（需看 Pi logs：`[sync_push] full_sync clear: beds, deleted X rows`）
- Command server 是否已重啟（beds_meta capacity_max 修復才會生效）
- Wave 5 剩餘：burn rate 預測線、決策合併卡片

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

> Wave 進度與版本里程碑見 [docs/ROADMAP.md](../../docs/ROADMAP.md)

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

> 詳細清單見 [docs/ROADMAP.md § Wave 5 → v0.13.0](../../docs/ROADMAP.md)
>
> 剩餘：決策主題合併卡片、物資 burn rate 預測線

---

### Wave 7：TAK 整合

> 細節待定。前進組／安全組使用 ATAK，需與 Command Console 整合。
> 前進組可能與軍方對接，地圖需支援 MIL-STD-2525 軍用符號渲染。
> TAK CoT `type` 欄位本身即為 MIL-STD-2525 代碼（如 `a-f-G-U-C`），TAK 整合與符號渲染為同一 Wave。
> **注意**：ATAK 裝置每幾秒推送 GPS 位置，動態 marker 更新是 TAK 整合的前提條件（Wave 5 先打好基礎）。

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

- HTML 固定 `commander_dashboard.html`，版號由 `CMD_VERSION` 常數控制（目前 `v0.12.14`）
- Pi server 版號 `SERVER_VERSION`（目前 `v1.1.2`）、FastAPI 版號 `1.2.0`
- Shelter PWA 版號 `v2.2.53`、Medical PWA 版號 `v0.6.7-alpha`
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
