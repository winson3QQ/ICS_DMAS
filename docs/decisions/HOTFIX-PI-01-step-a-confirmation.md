# HOTFIX-PI-01 Step A Confirmation

**Date:** 2026-04-26  
**Task:** HOTFIX-PI-01 — Remove Pi server default PIN 1234, enforce first-run token  
**Stage:** §10 Step A — Dependency Check 人工批准  
**Confirmed by:** User（2026-04-26）  
**Implementation status:** ✅ 完成，所有 test green，等待 git commit 指令

---

## Confirmation Items

### #1 `grep -rn "1234" server/` 結果

**Status: ✅ 確認（含一項偏差說明）**

| | 說明 |
|---|---|
| Task card §3 預期 | `db.js:40, 47`（2 處）|
| Dependency check 實際找到 | `db.js:40, 44, 47`（3 處）|
| 偏差原因 | L44 為 `log.info('[Seed] 預設管理員 PIN 已設定（1234）')` 的 log message，task card 未列入預期 |
| Post-fix grep 結果 | 只剩 `db.js:38` 的 comment 字串（非功能性）|
| §6 acceptance criteria | ✅「結果為空（測試的 negative case 除外）」達成 |

**移除的行（git diff 確認）：**
```diff
-    crypto.pbkdf2('1234', Buffer.from(salt, 'hex'), 200000, 32, 'sha256', (err, key) => {
-      log.info('[Seed] 預設管理員 PIN 已設定（1234）');
-        crypto.pbkdf2('1234', Buffer.from(acctSalt, 'hex'), 200000, 32, 'sha256', (e2, k2) => {
+  // 不再 seed 預設 admin/1234；fresh DB 啟動由 first_run.js 產生一次性 token，
```

---

### #2 §3 Design Constraint Check 無 decision required 待解項目

**Status: ✅ 確認**

| 待確認項目 | 狀態 |
|---|---|
| D#1 Admin password / Operator PIN 強度 | ✅ Option C 批准（2026-04-26）|
| D#2 自動化測試範圍 | ✅ Option C 批准（Unit + 1 spawn + §8 manual）|
| D#3 Token 檔生命週期 | ✅ Option D 批准（3a + 權限檢查 + audit）|
| D#4 stdout 訊息格式 | ✅ Option B 批准（只印路徑，token 不進 log）|

所有 D#1–D#4 在實作開始前已取得明確批准，無 open question。

---

### #3 Files Actually Involved 與 §4 一致

**Status: ✅ 確認**

**修改（diff > 0）：**

| 檔案 | §4 列出 | 實際狀態 |
|---|---|---|
| `server/db.js` | ✅ | ✅ 已修改 |
| `server/routes.js` | ✅ | ✅ 已修改 |
| `server/ws_handler.js` | ✅ | ✅ 已修改 |
| `server/index.js` | ✅ | ✅ 已修改 |
| `server/config.js` | ✅ | ✅ 已修改 |
| `package.json` | ✅ | ✅ 已修改 |

**新增：**

| 檔案 | §4 列出 | 實際狀態 |
|---|---|---|
| `server/first_run.js` | ✅ | ✅ 已建立 |
| `server/__tests__/first_run.test.js` | ✅ | ✅ 已建立 |
| `server/__tests__/first_run_integration.test.js` | 未列（Decision #2 C 拆出）| ✅ 已建立（在批准範圍內）|

**不動（diff = 0 bytes，已驗證）：**

| 檔案 | §4 列出 | 實際狀態 |
|---|---|---|
| `server/middleware.js` | ✅ 不動 | ✅ 未變更 |
| `server/auth.js` | ✅ 不動 | ✅ 未變更 |
| `server/migrations.js` | ✅ 不動 | ✅ 未變更 |
| `server/sync.js` | ✅ 不動 | ✅ 未變更 |

---

### #4 Whitelist / WS message type 清單正確

**Status: ✅ 確認**

#### HTTP First-run Whitelist（`routes.js:22–29`）

| Method | Path | 放行理由 |
|---|---|---|
| `GET` | `/admin/status` | 狀態查詢，無敏感資料，無寫入 |
| `GET` | `/cert` | CA 憑證下載，無敏感資料 |
| `GET` | `/cert/install` | 憑證安裝說明頁，靜態內容 |
| `GET` | `/` | PWA / admin 入口頁，需可存取才能進行 setup |
| `POST` | `/admin/setup` | First-run setup endpoint，內部另驗 token + password |

靜態檔案（`express.static`）在 middleware 之前處理，自動繞過 gate ✅

#### WS Gate（`ws_handler.js:42–54`）

**_STATE_CHANGING（阻擋，回 `FIRST_RUN_REQUIRED`）：**

| Type | 說明 |
|---|---|
| `delta` | 寫入 delta_log + current_state |
| `sync_push` | 寫入 snapshots + delta_log |
| `session_restore` | 變更 clients map |
| `audit_event` | 寫入 audit_log |
| `clear_table` | 刪除 current_state 資料 |

**放行（不在 _STATE_CHANGING 集合內）：**

| Type | 說明 |
|---|---|
| `auth` | 帳號驗證（只讀 DB）|
| `debug_ping` | 無寫入 |
| `catchup_req` | 讀取 delta_log，無寫入 |
| `time_sync_req` | 回傳 pi_time，無寫入 |
| `ping` | 回傳 pong，無寫入 |

與 task card §3 dependency check / Decision Record §4/§e 完全一致 ✅

---

## Test Results

| Layer | 執行指令 | Pass | Fail |
|---|---|---|---|
| Unit（`first_run.test.js`）| `node --test server/__tests__/first_run.test.js` | 19 | 0 |
| Integration（`first_run_integration.test.js`）| `node --test server/__tests__/first_run_integration.test.js` | 1（含 15 scenarios）| 0 |

---

## Next Steps

- [ ] **Step B**（§10）：User 在 Pi 實機跑 §8 verification script 全綠
- [ ] **Step C**（§10）：User 決定何時更新 Matrix CAP-010 Status / ROADMAP P-C1-A

**Git commit 等待 user 指令。**
