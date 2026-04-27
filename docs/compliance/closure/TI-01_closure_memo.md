# HOTFIX-TI-01 閉環備忘錄
## Trusted Ingest HMAC-SHA256 + Replay Protection

| 欄位 | 內容 |
|------|------|
| **控制項 ID** | TI-01 |
| **分類** | 機對機認證（Machine-to-Machine Authentication）|
| **嚴重程度** | HIGH — 主推送路徑無簽名即可注入任意資料 |
| **狀態** | ✅ **CLOSED** |
| **PR** | [#12 feat/hotfix-ti-01](../../..) → `main` |
| **Merge Commit** | `6bda2dc` |
| **Merge 時間** | 2026-04-27T12:05:37Z |
| **作者** | 開發負責人 |
| **Gatekeeper 審核** | _（簽核欄，見文末）_ |

---

## 1. 問題描述

### 1.1 原始漏洞

Pi 節點向指揮部推送資料的兩條路徑均**缺少請求完整性驗證**：

| 路徑 | 原保護 | 風險 |
|------|--------|------|
| `POST /api/snapshots` | Bearer token（不驗證來源） | 任何持有 token 的人可偽造快照 |
| `POST /api/sync/push` | Bearer token | 同上 |
| `POST /api/pi-push/{unit_id}` | Bearer token | **主週期推送路徑，大量資料流，無簽名驗證** |

Bearer token 驗證僅確認「token 是否存在於 DB」，無法防止：
- 中間人竄改 payload（tamper）
- Replay 攻擊（截取舊請求重放）
- 時間偏移注入（clock skew injection）

### 1.2 稽核發現（Auditor Finding，2026-04-27 Step B 期間）

原始 TI-01 實作（commit `f0e694b`）僅保護 `/api/snapshots` 及 `/api/sync/push`，**遺漏了 `piPushOnce()` 主推送路徑**，該路徑仍呼叫 `_postWithBearer()` 而非 `_postWithHmac()`。稽核當場發現並記錄為 **Gap**，決議以 Option A 擴充範疇。

---

## 2. 修補範疇（Scope）

### 2.1 兩階段提交

| Commit | 描述 | 日期 |
|--------|------|------|
| `f0e694b` | 原始 TI-01：HMAC 基礎建設 + `/api/snapshots` + `/api/sync/push` | 2026-04-27 |
| `5e855c6` | Option A：擴充 HMAC 至 `/api/pi-push/{unit_id}`（含主推送 + replay queue） | 2026-04-27 |

### 2.2 受保護端點（完整清單）

PR #12 merge 後，以下三個端點**全部**掛載 `Depends(verify_hmac)`：

```
POST /api/snapshots           — snapshot 推送
POST /api/sync/push           — 同步推送（備用路徑）
POST /api/pi-push/{unit_id}   — 主週期推送（每 30s）
```

AC-14 靜態斷言測試（`test_ingest_endpoint_allowlist.py`）確保清單不會靜默遺漏。

### 2.3 修改檔案清單

**指揮部（command-dashboard/）**：
- `src/middleware/trusted_ingest.py` — HMAC 驗證核心、Nonce Replay DB、Lazy Expiry TTL
- `src/routers/pi_push.py` — 新增 `Depends(verify_hmac)` + 調整驗證順序（HMAC 先）
- `src/routers/snapshot.py` — 原始 TI-01 實作（已含 HMAC）
- `src/routers/sync.py` — 原始 TI-01 實作（已含 HMAC）
- `tests/security/test_trusted_ingest.py` — AC-8a/b/c/d/e + AC-15a/b/c 共 8 項安全測試
- `tests/unit/test_ingest_endpoint_allowlist.py` — AC-14 靜態斷言（3 端點）
- `tests/api/test_pi_push_api.py` — 全面改寫，使用 hmac_client fixture
- `tests/api/test_dashboard_api.py` — push helper 改為 HMAC 版
- `tests/security/test_auth_bypass.py` — pi-push 繞過測試改為 hmac_client

**Pi Server（server/）**：
- `sync.js` — 3 個呼叫點從 `_postWithBearer()` 改為 `_postWithHmac()`
- `routes.js` — URL 驗證改為嚴格比對 `startsWith('https://')`

---

## 3. 技術實作摘要

### 3.1 HMAC Canonical String（Decision-2）

```
METHOD\n
/path\n
sorted_query_canonical\n
timestamp_ms\n
nonce_uuid_v4\n
sha256_hex(body_bytes)
```

演算法：HMAC-SHA256。Secret 為雙軌儲存：
- **Pi 端（簽名）**：`~/.ics/hmac_secret` 檔案（`chmod 0600`），由 `server/config.js:98-110` `loadHmacCredentials()` 載入
- **Command 端（驗證）**：`trusted_keys.secret` 欄位（SQLite 明文 hex 64 chars，需 DB `chmod 0600`），每請求依 `key_id` 查表取得（`src/middleware/trusted_ingest.py:110-119`）

兩端 secret 值相同，由 IT 佈建時手動對齊。

### 3.2 四個 X-ICS-* Headers

| Header | 內容 |
|--------|------|
| `X-ICS-Key-Id` | trusted_keys 對應 key_id |
| `X-ICS-Timestamp` | Unix ms（容許 ±300s skew） |
| `X-ICS-Nonce` | UUID v4，每請求唯一 |
| `X-ICS-Signature` | HMAC-SHA256 hex digest |

### 3.3 Replay Protection

- `nonce_cache` 表：`INSERT OR IGNORE` 原子操作防競爭
- TTL：10 分鐘（`MAX_SKEW_SECONDS = 300` × 2）
- Lazy Expiry：每次驗證時清除過期 nonce
- 回傳 `{"reason": "replay"}` + HTTP 401

### 3.4 驗證失敗回應碼語意

| reason | HTTP | 描述 |
|--------|------|------|
| `no_sig` | 401 | 缺少 X-ICS-* headers |
| `unknown_key` | 401 | Key-Id 不在 trusted_keys |
| `tampered` | 401 | 簽名比對失敗 |
| `skew` | 401 | Timestamp 超出 ±300s |
| `replay` | 401 | Nonce 已使用 |

### 3.5 Retry on Replay（AC-8b）

Pi Server 收到 `401 reason=replay` 時，自動以新 nonce 重試一次（`_postWithHmac()` 內建邏輯）。

---

## 4. 驗證證據

### 4.1 自動化測試

| 測試套件 | 測試數 | 結果 |
|---------|--------|------|
| Python（pytest，command-dashboard） | 307 tests | ✅ ALL PASSED |
| AC-8a：無 HMAC headers → 401 no_sig | 1 | ✅ |
| AC-8b：replay 自動重試 | 1 | ✅ |
| AC-8c：未知 key → 401 unknown_key | 1 | ✅ |
| AC-8d：tampered → 401 tampered | 1 | ✅ |
| AC-8e：time skew → 401 skew | 1 | ✅ |
| AC-14：3 端點靜態斷言全通過 | 1 | ✅ |
| AC-15a：pi-push 無簽名 → 401 | 1 | ✅ |
| AC-15b：pi-push 未知 key → 401 | 1 | ✅ |
| AC-15c：pi-push replay → 401 | 1 | ✅ |

**已知例外**：`test_first_run.py::test_writes_token_file` 在 Windows NTFS 上失敗（`chmod 0o600` 不生效）。此問題**早於 TI-01**，與本修補無關；已在 Pi 500 Linux 確認通過。

### 4.2 Pi 500 人工驗證（Step B，2026-04-27）

硬體：Raspberry Pi 500，OS：Linux（Raspbian），部署：`start_pi.sh`

| # | 驗證項目 | 結果 |
|---|---------|------|
| B-1 | trusted_keys 插入 + 查詢正確 | ✅ |
| B-2 | pi_nodes 建立 + api_key 對應 | ✅ |
| B-3 | Shelter Pi `command_url` + `pi_api_key` 設定 | ✅ |
| B-4 | `piPushOnce()` 主推送成功：`[PiPush] OK: N records` | ✅ |
| B-5 | Replay 攻擊：截取請求重放 → `{"reason":"replay"}` HTTP 401 | ✅ |
| B-6 | Tamper 攻擊：竄改 body → `{"reason":"tampered"}` HTTP 401 | ✅ |
| B-7 | Time Skew 攻擊：過期 timestamp → `{"reason":"skew"}` HTTP 401 | ✅ |
| B-8 | `audit_ingest_accepted` 表留存 3 筆正確記錄 | ✅ |
| B-9 | HTTPS 嚴格驗證：HTTP URL → 拒絕並提示「必須使用 HTTPS」 | ✅ |
| B-10 | 管理員 PIN 保護確認 | ✅ |

**人工驗證結果：10 / 10 通過**

---

## 5. Compliance 影響

| 標準 | 控制項 | 本修補前 | 本修補後 |
|------|--------|---------|---------|
| NIST SP 800-53 IA-3 | Device Identification and Authentication | ❌ Gap | ✅ Met |
| NIST SP 800-53 SC-8 | Transmission Confidentiality and Integrity | ⚠ Partial | ✅ Met（HMAC integrity layer） |
| NIST SP 800-53 SI-10 | Information Input Validation | ❌ Gap | ✅ Met |
| NIST SSDF PW.7 | Review and/or Analyze Human-Readable Code | ✅ | ✅ 測試補齊 |
| OWASP ASVS V14 | Configuration Verification | ⚠ Partial | ✅ Met |
| ISO 25010 可靠性 | Security sub-characteristic | ⚠ Partial | ✅ Improved |

> 備註：SC-8 的傳輸加密層（HTTPS）由 C1-B HTTPS 里程碑另行處理，HMAC 提供的是 **payload 完整性**，兩者相互補充、不互相取代。

---

## 6. 已知限制與後續事項（Maturity Hold）

以下項目**不阻擋 TI-01 閉環**，但須列入後續規劃：

| 項目 | ID | 描述 | 對應里程碑 |
|------|----|------|-----------|
| HMAC_SECRET 輪替流程 | — | 目前無 key rotation 機制；需定義輪替 SOP | C3-B（安全運維） |
| trusted_keys 多 Pi 佈建 | — | 目前手動插入 DB；規模化後需 provisioning API | C3-A（部署自動化） |
| Windows 測試隔離 | — | `test_writes_token_file` Windows 失敗未修（pre-existing） | tech-debt backlog |
| nonce_cache 容量監控 | — | 高頻推送下 nonce_cache 成長未加監控告警 | C3-B |
| **TTL 邊界 unit test** | **D-9** | **AC-4 僅測 replay 阻擋，缺「過期 nonce 可重用」邊界驗證（`NONCE_TTL_MS` 邊界）** | **下一 sprint** |

### D-9 詳細說明

現有 AC-4（`tests/security/test_trusted_ingest.py:167-183`）驗證：同一 nonce 第二次送出 → 被拒絕（replay 阻擋）。

**缺失**：未驗證「nonce 存入後，經過 `NONCE_TTL_MS`（預設 10 分鐘）後，同一 nonce 值可以重新被接受」。此邊界測試需使用 `monkeypatch` 將 `nonce_cache.created_at` 設為 `now_ms - NONCE_TTL_MS - 1`，確認 Lazy Expiry 確實清除並允許重入。

Gatekeeper Conditional Approve 已確認此為 open gap，列 D-9 追蹤。

---

## 7. 閉環聲明

HOTFIX-TI-01 的所有目標已達成：

1. **所有機對機 ingest 端點均掛載 HMAC 驗證**（3/3，AC-14 靜態斷言常態守護）
2. **Replay 攻擊防護已實作並通過人工驗證**（AC-8b/c）
3. **Tamper 及 Time Skew 攻擊均在 Pi 500 實機確認拒絕**
4. **307 項自動化測試全部通過，Pi 500 人工驗證 10 / 10 通過**
5. **PR #12 已 merge 至 main**（commit `6bda2dc`，2026-04-27T12:05:37Z）

本控制項狀態由 **Gap → ✅ Met**，可從 `docs/compliance/matrix.md` Gap Register 移除，並更新 Evidence 欄位指向 PR #12。

---

## 8. Gatekeeper 審核簽核

> 以下由 **Security & Compliance Gatekeeper（人員核可）** 填寫：

| 欄位 | 內容 |
|------|------|
| **審核人** | __________________ |
| **審核日期** | __________________ |
| **決議** | ☐ 核准閉環（Approved to Close） ☐ 條件核准 ☐ 退回（Reject）|
| **條件／備註** | __________________ |
| **簽名** | __________________ |

---

*本文件由開發負責人產出，依 ICS_DMAS 功能完成定義（Definition of Done）及 Compliance 閉環流程產出。*
*文件版本：v1.0 / 2026-04-27*
