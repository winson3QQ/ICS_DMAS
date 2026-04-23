# ICS_DMAS 商業化大改版計劃 v1.3

> 狀態：草稿（初步規劃）
> 基準版本：shelter-v2.2.53 / server-v1.2.0 / cmd-v0.12.13
> v1.1 更新：整合 AI_integration_roadmap、project_status、Silent Scribe v1.4 規格
> v1.2 更新：法規同步（資安法/個資法 2025 修正）、競品動態（WebEOC Nexus + JAI）、標準更新（NIST 5.2.0）
> v1.3 更新：C0 Pi 端重構完成（server-v1.2.0）、PMTiles range request 修正
> 最後 review：2026-04-23

---

## Review 機制

### 觸發條件（任一發生即 review，不等排程）

- 新的政府採購案開始評估本系統
- 競品有重大更新（WebEOC、D4H、EMIC 2.x）
- 台灣法規修正：資安法、個資法、政府採購作業指引
- 技術環境重大變化（FastAPI 大版本、Pi 新硬體、AI 模型突破）
- 任一 Phase 完成後，評估後續 Phase 是否需要調整
- 距上次 review 超過 **6 個月**

### 定期排程

每 6 個月由 Claude 自動執行：
- Web search 競品動態、台灣法規更新、EOC 市場趨勢
- 比對現有計劃，標記需要更新的項目
- 輸出 review 摘要，由使用者決定是否更新文件

### Review 歷史

| 日期 | 版本 | 主要變動 | 觸發原因 |
|------|------|---------|---------|
| 2026-04-23 | v1.1 | 整合 AI roadmap、Silent Scribe、Wave 6-9 | 初版建立 |
| 2026-04-23 | v1.2 | 資安法/個資法 2025 修正同步；WebEOC Nexus+JAI 競品更新；NIST 5.2.0；ISO 27001 版本確認 | 定期排程 review（6 個月） |

---

## 目錄

1. [現況診斷](#一現況診斷)
2. [與現有技術路線圖的關係](#二與現有技術路線圖的關係)
3. [設計原則](#三設計原則)
4. [目標架構藍圖](#四目標架構藍圖)
5. [C0：基礎重構](#c0基礎重構唯一串行前提)
6. [C1：安全性與法規合規](#c1安全性與法規合規)
7. [C2：可測試性與工程品質](#c2可測試性與工程品質)
8. [C3：部署與維運](#c3部署與維運)
9. [C4：產品分層與授權機制](#c4產品分層與授權機制)
10. [C5：護城河功能建立](#c5護城河功能建立)
11. [C6：合規認證](#c6合規認證)
12. [執行順序與版本里程碑](#執行順序與版本里程碑)
13. [商業模式](#商業模式)
14. [護城河策略](#護城河策略)
15. [Silent Scribe 戰術版產品線](#silent-scribe-戰術版產品線)
16. [長期產品演進 Wave 6–9](#長期產品演進-wave-69)
17. [附錄：關鍵法規依據](#附錄關鍵法規依據)

---

## 一、現況診斷

### 工程品質評分

| 面向 | 評分 | 狀態 | 主要問題 |
|------|------|------|---------|
| 軟體架構分層 | 45% | 🔴 不合格 | 3 個 God files，無 router/service/repo 分層 |
| 安全性 | 55% | 🔴 不合格 | 預設 PIN 1234、CORS 全開、無 MFA、敏感欄位明文 |
| 可測試性 | 15% | 🔴 不合格 | 無測試框架；分層不做，測試也寫不了 |
| 可維護性 | 45% | 🔴 不合格 | 無 linter/type check；文件充分但救不了結構 |
| 部署維運 | 50% | ⚠️ 部分合格 | systemd 良好；缺健康檢查/metrics/備份 |
| 商業化指標 | 60% | ⚠️ 部分合格 | 功能完整；缺認證/壓測/WCAG |

**加權總分：約 45/100（科研/演訓可接受；商業化不合格）**

### 現有 God Files

| 檔案 | 行數 | 問題 |
|------|------|------|
| `medical-pwa/public/medical_pwa.html` | 4,854 | UI/WebSocket/IndexedDB/PIN 全混 |
| `shelter-pwa/public/shelter_pwa.html` | 3,264 | 同上 |
| `command-dashboard/src/db.py` | 1,594 | CRUD/migration/sync/audit 全混 |
| `command-dashboard/src/main.py` | 1,577 | 64 個路由 + models + 認證 + tile 全混 |
| `server/`（8 模組）| ~900（分散） | ✅ C0 已重構：logger/config/db/auth/audit/sync/ws_handler/routes |

### 台灣政府採購合規缺口

| 要求 | 法源 | 現況 |
|------|------|------|
| Log 保存 ≥ 6 個月 | 資通系統防護基準 | 🔴 無持久化 |
| 廠商 ISO 27001 或書面承諾 | 採購契約範本 | 🔴 缺乏 |
| 弱掃 + 滲透測試報告 | 資安法 B 級機關 | 🔴 從未執行 |
| 個資適當安全措施 | 個資法第 27 條 | 🔴 敏感欄位未加密 |
| MFA（管理後台 AAL2） | 共通資安基本要求 | 🔴 缺失 |
| WCAG 2.0 AA | 數位部規範 | 🔴 未評估 |
| SBOM 軟體物料清單 | 採購作業指引 | 🔴 缺乏 |
| 全程傳輸加密 | 防護基準附表十 | ⚠️ Pi 端有 WSS；指揮部仍 HTTP |

---

## 二、與現有技術路線圖的關係

> 本節是 v1.1 新增的核心整合章節。讀者若已熟悉 `AI_integration_roadmap.md` 和 `project_status.md`，請從這裡開始理解兩份計劃的關係。

### Phase 命名對照表

商業化計劃使用前綴 **C**（Commercial）區分，避免與 AI 路線圖的 Phase 0–7 混用。

| 商業化計劃（本文） | AI 路線圖（AI_integration_roadmap.md） | 關係 |
|------------------|--------------------------------------|------|
| **C0** 基礎重構 | ——（AI 路線圖無對應；其 Phase 0 是 bug fix，已完成） | 新增工作 |
| **C1** 安全合規 | **Phase 7**（安全硬化：HTTPS/WSS、LUKS、YubiKey） | **互補合併**（見下方說明） |
| **C2** 可測試性 | ——（無對應） | 新增工作 |
| **C3** 部署維運 | Phase 7 備份三層、systemd | 部分重疊，C3 更完整 |
| **C4** 產品分層 | ——（無對應，商業決策） | 新增工作 |
| **C5** 護城河 | **Phase 3**（TTX）、**Phase 5**（Console AI）、**Phase 6**（AAR） | **直接對應**（見下方說明） |
| **C6** 合規認證 | ——（無對應） | 新增工作 |

### 安全性兩層架構（C1 ＋ Phase 7）

兩份計劃的安全性工作針對不同威脅模型，**必須同時做，不能互相替代**：

| | C1（軟體合規資安） | AI roadmap Phase 7（物理/軍規資安） |
|---|---|---|
| **威脅假設** | 網路攻擊、合規稽查 | 實體入侵、設備被奪、資料外洩 |
| **適用產品層** | 所有層（基礎版以上） | Tier 3 旗艦版 / Silent Scribe 戰術版 |
| **技術項目** | MFA、CORS、個資加密、audit trail、HTTPS | LUKS 全碟加密、YubiKey FIDO2、Panic Wipe、USB 點火鑰匙、SQLCipher |
| **驗收標準** | 政府採購資安稽查 | 野戰驗收、實體銷毀測試 |

**實作原則**：C1 是全產品線基礎，所有版本都要做。Phase 7 的物理資安功能作為 Tier 3 功能，由授權開啟。

### 護城河功能與 AI 路線圖的對應

C5 的護城河功能不是從零開始，而是**在現有 AI 路線圖基礎上加商業化包裝**：

| C5 護城河項目 | AI 路線圖對應 | 現況 |
|--------------|-------------|------|
| 5-A TTX 場景資料庫 | Phase 3（已建 10 個場景 + scenario_designer.html） | ✅ 基礎已有，需加商業化結構 |
| 5-B AAR 報告引擎 | Phase 6（aar_engine.py 四函式設計） | 🔲 尚未實作，需照 Phase 6 規格做 |
| 5-C AI 預測層 | Phase 5（Console AI：情勢合成、決策選項、事件分群、對話查詢） | ⚠️ 依硬體（N100）到位時間 |
| 5-D 語音輸入 | Phase 4（Pi 本機小模型 或 Gemini API） | ⚠️ 依 Phase 2b 小模型評估結果 |
| 5-E 外部整合 | Wave 7 TAK、Wave 8 NIMS | 🔲 長期，見 Wave 6-9 章節 |

### Wave 5 與商業化計劃的關係

**Wave 5（UI 收尾，當前進行中）應繼續獨立推進，不被商業化計劃打斷。**

Wave 5 剩餘項目：
- 決策主題合併卡片（`_zoneDecisionsTab()` group by）
- 物資 burn rate 預測線（`drawSparkline()` 加虛線延伸）

這兩項不影響 C0 架構重構的優先序，可平行進行。

### Silent Scribe 的定位

`security & forward/` 目錄下的 C2-Intelligence (Silent Scribe) 是**獨立但相關的產品線**：

- **不是** ICS_DMAS 的一個功能模組
- **是** 以 ICS_DMAS 指揮部為後端，加上 Field Node + N100 Console + 軍規資安的**戰術版產品**
- 目標市場：民防團體、準軍事組織（比 ICS_DMAS 主線更敏感的客群）
- 機密等級：CONFIDENTIAL（主線 ICS_DMAS 為公開產品）
- 詳見本文 [Silent Scribe 戰術版產品線](#silent-scribe-戰術版產品線) 章節

---

## 三、設計原則

每個技術決策都必須能回答以下四個問題，四個都不是則不做：

1. **這個改動讓我們更容易通過政府採購驗收嗎？**
2. **這個改動讓客戶更難換掉我們嗎？**
3. **這個改動讓下一個功能更容易加嗎？**
4. **這個改動讓系統在斷網時仍有基本功能嗎？**

第四個問題對應兩個核心架構原則：
- **擴充性**：新單位（前進組、安全組）加入時，schema 不需要重寫，COP 資料模型對 unit_type 保持參數化而非寫死
- **韌性**：每個節點必須能獨立運作，COP 是最終一致的（eventually consistent），不依賴單一集中點；斷網時各單位繼續收資料，連線後同步

---

## 四、目標架構藍圖

### 後端（Python / FastAPI）

```
command-dashboard/src/
├── main.py                    # ≤80 行：init + middleware + include_router
├── core/
│   ├── config.py              # Pydantic BaseSettings，從 .env 讀取
│   ├── database.py            # SQLite init、WAL、connection factory
│   ├── migrations.py          # 版本化 migration（schema_version 表）
│   ├── logging.py             # structlog 結構化 JSON log
│   └── license.py             # 授權檔驗證（Ed25519 簽名）
├── auth/
│   ├── session.py             # X-Session-Token 驗證（FastAPI Depends）
│   ├── pi_key.py              # Bearer API Key 驗證（Pi 推送用）
│   ├── password.py            # PBKDF2、首次強制修改、密碼政策
│   ├── mfa.py                 # TOTP（pyotp）、QR code、備援回復碼
│   └── rbac.py                # 角色：SYSTEM_ADMIN/COMMANDER/OBSERVER/PI_NODE
├── repositories/              # 純 SQL，零業務邏輯，可獨立測試
│   ├── base.py                # get_db()、transaction context manager
│   ├── events_repo.py
│   ├── decisions_repo.py
│   ├── snapshots_repo.py
│   ├── accounts_repo.py
│   ├── audit_repo.py          # append-only，無 DELETE/UPDATE 方法
│   └── ttx_repo.py
├── services/                  # 業務邏輯，依賴 repositories，可 mock 測試
│   ├── snapshot_sync.py       # 三 Pass 對齊（從 db.py 搬）
│   ├── decision_flow.py       # 決策狀態機
│   ├── ttx_engine.py          # TTX 場景推進、事件注入（整合現有 10 情境）
│   ├── aar_generator.py       # AAR 報告（對應 AI roadmap Phase 6）
│   └── prediction.py          # 資源預測（對應 AI roadmap Phase 5，依硬體）
├── routers/
│   ├── events.py
│   ├── decisions.py
│   ├── snapshots.py
│   ├── admin.py               # 使用者、Pi Key、MFA 設定
│   ├── tiles.py               # Leaflet tile proxy
│   ├── ttx.py                 # 含 scenario_designer 後端 API
│   ├── aar.py
│   ├── field_nodes.py         # Field Node 上傳端點（AI roadmap 3-7）
│   └── system.py              # /health、/metrics、/version
├── models/                    # Pydantic request/response models
│   ├── event.py
│   ├── decision.py
│   ├── snapshot.py
│   ├── ttx.py
│   └── field_node.py
└── calc_engine.py             # 現有，不動（已是純函式）
```

> **注意**：`ai_engine.py`（AI roadmap Phase 5）和 `aar_engine.py`（Phase 6）在 C5 護城河階段才實作，不在 C0 重構範圍。

### Pi 端（Node.js）

```
shelter-pwa/server/            # medical-pwa/server/ 同結構
├── index.js                   # createServer + listen，≤50 行
├── config.js                  # 環境變數讀取，startup 時 validate
├── db.js                      # SQLite 封裝，WAL，connection singleton
├── auth.js                    # PIN 驗證、登入鎖定、session token
├── ws_handler.js              # WebSocket message router
├── http_handler.js            # Admin HTTP endpoints
├── push_client.js             # 推送至指揮部（retry + exponential backoff）
├── audit.js                   # append-only audit log
└── migrations.js              # 版本化 DB migration
```

### 前端（PWA）

PWA 離線優先架構保留單檔部署，但引入建置流程：

```
開發目錄（有模組邊界）：
shelter-pwa/src/
├── js/
│   ├── auth.js
│   ├── sync.js       # WsManager + pushRecoveryData
│   ├── ui.js
│   ├── ttx.js        # TTX 模式（session_type='exercise'，橙色 banner）
│   └── audit.js
└── index.html

建置輸出（esbuild bundle，離線可用）：
shelter-pwa/public/shelter_pwa.html
```

---

## C0：基礎重構（唯一串行前提）

> 所有後續 Phase 的前提。C0 完成前，其他工作在沙堆上蓋房子。
> **與 AI roadmap 的關係**：AI roadmap Phase 0 的 bug fix 已完成，C0 是完全不同的工作（架構搬遷），不要混淆。

### 目標

把現有功能原封不動搬進新結構。零功能變更，只改架構。

### 工作項目

- [ ] **後端分層**：`main.py`（1,577 行）+ `db.py`（1,594 行）拆進 `routers/` + `services/` + `repositories/` + `auth/` + `core/`
- [x] **Pi 端分層**：`ics_ws_server.js`（1,159 行）拆進 `server/` 子目錄（server-v1.2.0，2026-04-23）
- [ ] **前端模組化**：抽出 `.js` 模組 + 加入 esbuild 建置步驟
- [ ] **Smoke test**：用 httpx TestClient 打每個端點，確認無功能回歸
- [ ] **session_type 完整性**：確認 AI roadmap Phase 0-3 的 session_type 欄位在新架構中正確傳遞

### 完成標準

- `main.py` ≤ 80 行
- 現有 64 個路由全部可運作
- `npm run build` 產出的 PWA 功能與現在完全相同
- Wave 5 剩餘項目（burn rate 預測線、決策合併卡片）可在新架構中繼續實作

---

## C1：安全性與法規合規

> 目標：通過政府採購驗收的資安稽查，取得投標資格。
> **與 AI roadmap 的關係**：本章節覆蓋軟體合規資安。AI roadmap Phase 7 的物理資安（LUKS、YubiKey、Panic Wipe）作為 Tier 3 功能，詳見 C4 授權機制和 Silent Scribe 章節。

### C1-A 認證強化

**首次強制設定（移除預設 PIN 1234）**
- 部署後第一次打開指揮部 → 強制進入設定頁面
- 管理員密碼政策：≥12 字元、英數混合（NIST SP 800-63B）
- 設定完成前所有 API 回傳 `423 Locked`
- Pi 端同樣：首次啟動產生隨機臨時 PIN，印出至 console，強制首次修改

**管理後台 MFA（TOTP，AAL2）**
- 啟用流程：產生 secret → 顯示 QR code → 驗證首次 OTP → 啟用
- 登入流程：密碼 OK → 要求 OTP → 核發 session token
- 提供 10 組一次性備援回復碼
- 適用範圍：`SYSTEM_ADMIN` 角色必須，`COMMANDER` 角色可選

**RBAC 角色權限**

| 角色 | 權限 | 適用層 |
|------|------|-------|
| `SYSTEM_ADMIN` | 管理使用者、設定、MFA、Pi Key | Tier 1+ |
| `COMMANDER` | 下決策、查全部資料、啟動 TTX | Tier 1+ |
| `OBSERVER` | 唯讀（供外部稽查人員使用） | Tier 2+ |
| `PI_NODE` | 推送專用，無 UI 存取權 | 所有層 |

**登入鎖定**
- 失敗 5 次 → 鎖定 15 分鐘
- 每 IP 每分鐘 ≤ 10 次認證請求
- 鎖定事件寫入 audit log

**CISO 指定要求（2025 資安法修正新增）**
- 資通安全管理法 2025 修正後，廠商合約須明定資安責任，政府機關需指派 CISO 及全職資安人員
- 銷售合約範本應包含：資安聯絡人（廠商端）、事件通報 SLA、資安演練配合義務
- 提供客戶機關的 CISO 指派輔助文件（範本）

### C1-B 全面加密傳輸

- 指揮部加入 nginx reverse proxy，啟用 HTTPS（TLS 1.2+，建議 TLS 1.3）
- Security headers：HSTS、X-Frame-Options DENY、CSP、X-Content-Type-Options
- CORS 收斂：`allow_origins=["*"]` 改為環境變數設定（預設內網網段）
- Pi 端 WSS：確認所有部署環境啟用，自動拒絕非 TLS 連線

> 注意：AI roadmap Phase 7 的 mTLS（nginx 雙向憑證）和 WireGuard 是 Tier 3 功能，在 C4 授權機制中控制開啟。

### C1-C 個資保護

**敏感欄位應用層加密**
- 加密欄位：身分證號、健康狀況、聯絡電話
- 金鑰：`/etc/ics/field.key`（部署時產生，Fernet AES-128-CBC + HMAC-SHA256）
- 不進 git，不進備份 tarball（備份只備資料，不備金鑰）

**個資存取記錄**
- 每次讀取含個資記錄 → 寫入 `pii_access_log`（操作者、時間、記錄 ID、原因）

**資料洩露通報機制（2025 個資法修正新增）**
- 個資法 2025 修正後設立獨立監管機關**個人資料保護委員會（PDPC）**
- 發生洩露事件時：
  - 72 小時內通報 PDPC（類 GDPR Article 33 要求）
  - 洩露影響當事人時需另行通知受影響者
- 系統需備有：洩露事件偵測機制、通報流程 SOP、客戶機關的通報輔助文件
- 部署合約應明定廠商協助通報責任（修正後個資法要求）

**API 設計**
- `/api/snapshots/stats`：統計用，自動去識別
- `/api/snapshots/detail`：需 COMMANDER + 觸發 pii_access_log

### C1-D Append-only 稽核軌跡

**DB trigger 防竄改**
```sql
CREATE TRIGGER protect_audit_log
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;
```

**雜湊鏈完整性**
- 每筆 `entry_hash = hash(prev_hash + timestamp + content)`
- 可程式驗證稽核軌跡未被竄改

**6 個月保存（systemd timer）**
- 每月壓縮備份 audit_log 至 `/var/lib/ics/archive/`
- 可選：rsync 至外部 NAS

**結構化 Log（可接 SIEM）**
- structlog，JSON 格式輸出
- 台灣政府 IT 部門常要求接入 Splunk / ELK

### C1-E Schema 版本追蹤

```python
MIGRATIONS = [
    (1, "initial_schema", "..."),
    (2, "add_audit_hash_chain", "..."),
    (3, "add_pii_access_log", "..."),
    (4, "add_session_type_all_tables", "..."),  # AI roadmap Phase 0-3 已做，在此正式追蹤
    # append-only，舊項目永不修改
]
```

---

## C2：可測試性與工程品質

> 目標：覆蓋率 ≥ 70%，可輸出報告給驗收方；CI/CD 自動把關。
> **前提**：C0 完成後才能有效寫單元測試（repository 層可 mock）。

### C2-A 測試框架

```
tests/
├── conftest.py
├── unit/
│   ├── test_calc_engine.py        # 純函式，目標 100%
│   ├── test_snapshot_sync.py      # 三 Pass 對齊
│   ├── test_auth_password.py
│   ├── test_field_encryption.py
│   ├── test_migrations.py
│   └── test_audit_hash_chain.py
├── integration/
│   ├── test_events_api.py
│   ├── test_auth_flow.py          # 登入→MFA→session 完整流程
│   ├── test_pi_push.py            # 模擬 Pi 推送 + 三 Pass 對齊
│   ├── test_ttx_flow.py           # 場景注入→決策→session_type 隔離
│   └── test_field_node_upload.py  # Field Node 音檔上傳流程
└── security/
    ├── test_auth_bypass.py
    ├── test_sql_injection.py
    └── test_rate_limit.py
```

前端：加入 Vitest，覆蓋每個 js 模組的核心邏輯。

### C2-B CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
jobs:
  python-quality:
    - ruff check / format
    - mypy（strict mode）
    - pytest --cov=src --cov-fail-under=70

  js-quality:
    - eslint
    - vitest --coverage

  security-scan:
    - pip-audit（Python CVE）
    - npm audit（Node CVE）
    - bandit（Python 靜態安全分析）

  build-pwa:
    - esbuild bundle
    - lighthouse-ci（WCAG AA + 效能基準）
```

### C2-C 程式碼品質工具

- **Python**：ruff（lint + format）、mypy strict、bandit
- **Node.js**：eslint（含 security rules）
- **Pre-commit hooks**：ruff、mypy、eslint、detect-secrets（防 secret 進 git）
- **設定檔**：`pyproject.toml`、`.eslintrc.json`、`.pre-commit-config.yaml`

---

## C3：部署與維運

> 目標：沒有參與開發的工程師能在 4 小時內完成部署，維運 6 個月不需上門。

### C3-A 設定外部化

所有路徑、密鑰、設定從 `/etc/ics/command.env` 讀取，不進 git：

```
DB_PATH=/var/lib/ics/data/ics.db
LOG_LEVEL=info
LOG_FORMAT=json
CERT_PATH=/etc/ics/certs/command.crt
KEY_PATH=/etc/ics/certs/command.key
FIELD_KEY_PATH=/etc/ics/field.key
ALLOWED_ORIGINS=https://192.168.100.1
LICENSE_PATH=/etc/ics/license.json
PI_PUSH_INTERVAL=5
```

### C3-B 一鍵安裝腳本

`install.sh` 涵蓋：
- 建立 `ics` 系統使用者（非 root）
- 建立目錄結構、設定正確檔案權限（`/etc/ics/` 為 0700）
- 產生 field encryption key
- 產生首次設定 token（僅顯示一次）
- 安裝依賴、複製 systemd service 檔、啟動服務

### C3-C 健康檢查與可觀測性

**`/health` 端點**
```json
{"status": "ok", "checks": {"db": "ok"}, "version": "2.1.0"}
```

**`/metrics` 端點（Prometheus 格式）追蹤：**
- `ics_pi_push_total`（依 node_id、status）
- `ics_pi_push_latency_seconds`
- `ics_ws_connections`
- `ics_db_write_latency_seconds`
- `ics_auth_failures_total`
- `ics_ttx_sessions_active`（演訓模式感知）

### C3-D 自動備份

三層備份策略（與 AI roadmap Phase 7 備份三層對齊）：
- **L1（即時）**：SQLite WAL 日誌（現有）
- **L2（每日）**：`ics-backup.timer` 每日凌晨 2 點，sqlite3 online backup + gzip，保留 30 天
- **L3（離線）**：rsync 至外部 NAS（`BACKUP_NAS_PATH` 環境變數，可選）

> Tier 3 / Silent Scribe 額外加：每小時資料彈匣備份（AI roadmap Phase 7 / Silent Scribe Sprint 1）

---

## C4：產品分層與授權機制

> 目標：技術層面支援三個定價層，用授權檔控制功能開關。

### 授權檔設計

```json
{
  "customer": "台中市政府消防局",
  "issued": "2026-01-01",
  "expires": "2027-12-31",
  "tier": "full",
  "features": {
    "shelter_module": true,
    "medical_module": true,
    "ttx_module": true,
    "ttx_scenario_library": true,
    "aar_export": true,
    "ai_prediction": false,
    "voice_input": false,
    "field_node_upload": false,
    "physical_security": false,
    "max_pi_nodes": 10,
    "max_concurrent_users": 50
  },
  "signature": "..."
}
```

簽名：Ed25519（廠商私鑰簽，公鑰內嵌於程式）。

### 三層產品定義

| 功能 | 基礎版 | 全功能版 | 旗艦版 |
|------|:------:|:--------:|:------:|
| 指揮部模組 | ✅ | ✅ | ✅ |
| 收容所模組 | 擇一 | ✅ | ✅ |
| 醫療組模組 | 擇一 | ✅ | ✅ |
| 基本稽核軌跡 | ✅ | ✅ | ✅ |
| Health / Metrics | ✅ | ✅ | ✅ |
| TTX 演訓模組 | ❌ | ✅ | ✅ |
| TTX 場景庫（10+ 情境） | ❌ | ✅ | ✅ |
| AAR 報告匯出 | ❌ | ✅ | ✅ |
| 語音輸入（AI 填表） | ❌ | ❌ | ✅ |
| AI 情勢合成 / 預測 | ❌ | ❌ | ✅ |
| Field Node 上傳端點 | ❌ | ❌ | ✅ |
| 物理資安（LUKS、Panic Wipe） | ❌ | ❌ | ✅ |
| 外部 API 開放 | ❌ | ❌ | ✅ |
| Pi 節點上限 | 4 | 10 | 無限 |
| 參考定價（一次性）| NT$35–50 萬 | NT$60–90 萬 | NT$150 萬+ |
| 年度維護 | NT$8 萬 | NT$15 萬 | NT$25 萬 |

> **Tier 3 旗艦版**即為將 AI roadmap Phase 4–7 的功能商業化的產品形態。

---

## C5：護城河功能建立

> 目標：讓競爭者即使做出相同架構，也搶不走客戶。
> **注意**：C5 各項目均有對應的 AI roadmap 基礎，不是從零實作。

### C5-A TTX 場景資料庫（最高優先護城河）

**現有基礎**（AI roadmap Phase 3，已完成）：
- 10 個情境 JSON（`scenarios/` 目錄）
- `scenario_designer.html`（參數化生成 + live 注入）
- TTX session / inject 資料表與 API

**近期真實演練資料積累（2026 年）**：
- **第 11 個場景**：2026-05-31 無線電演練 → 演練後手工填 TTX 場景 JSON（disaster_type、scale、key_decision_points）；session log 匯出為第 1 筆 AAR 原始資料
- **第 12 個場景**：2026-06 月底/07 月初 中型演練 → 第 2 筆 AAR 資料；場景規模升至 medium
- **第 13 個場景**：2026-08-30 無線電演練 → 第 3 筆 AAR session log

**需要加入的商業化結構**：

```python
class TTXScenario:
    """
    新增欄位（在現有 JSON 結構上擴充）：
    - disaster_type: 颱風/地震/複合型/工業意外
    - terrain: 山地/平原/沿海/都市
    - scale: small/medium/large
    - difficulty: basic/advanced/stress_test
    - key_decision_points: [決策點清單]
    - effectiveness_score: 演訓後填寫，衡量場景是否達到訓練目標
    - real_incident_reference: 若源自真實事件，記錄事件 ID
    """
```

**場景效果追蹤**（每次演訓後自動記錄）：
- 哪些注入事件造成最大決策壓力
- 哪些決策點被跳過或延遲
- 客戶弱點 → 下次演訓自動推薦針對性場景

**護城河價值**：現有 10 個情境 + 每次 TTX 服務積累 → 3 年後 50+ 個驗證過的台灣本土場景，是別人花錢買不到的核心 IP。

### C5-B AAR 報告引擎（資料鎖定護城河）

> **對應**：AI roadmap Phase 6（aar_engine.py 四函式設計）。以下為商業化實作規格，技術細節見 AI roadmap。

從 audit_log 自動產生：

- **事件時間軸**：甘特圖格式，含 inject 觸發 → 決策延遲分析
- **決策分析**：時機、依據、結果，跨 session 比較
- **資源使用圖**：收容所/醫療資源時序變化
- **SOP 偏差**：與標準程序的差異（Ground Truth 知識庫，seed 來自 `docs/0411-0412_ExcerciseData.md`）
- **改善建議**：與歷史相似場景對比

輸出格式：
- PDF（繁體中文，含圖表，適合呈報長官）
- JSON（機器可讀，AI 訓練用，見 C5-C）

**護城河價值**：政府機關演訓都要出 AAR 報告。客戶資料越積越多，換系統就要放棄所有歷史對比基準。

### C5-C AI 預測層（台灣本土差異化）

> **對應**：AI roadmap Phase 5（Console AI），依 N100 硬體到位時間。
> **等待條件**：≥ 20 次真實演訓/事件的 AAR JSON + N100 或同等硬體。

AI roadmap Phase 5 已定義：
- `synthesize_situation()`：情勢合成
- `generate_decision_options()`：決策選項
- `generate_ttx_consequence()`：TTX 後果引擎
- `cluster_events()`：事件分群與關聯偵測
- `answer_query()`：對話式查詢（僅讀取）

商業化包裝：
- 全部作為 Tier 3 授權功能（`ai_prediction: true`）
- Console AI 的推論硬體成本（N100 Mini PC）納入 Tier 3 報價

**訓練資料來源**：
- 本系統 AAR JSON（自有，每次演訓積累）
- 消防署公開災害報告（解析結構化）
- 氣象署颱風路徑 API（實時特徵）

**護城河價值**：無任何海外競爭者有台灣颱風 + 地震 + 山地複合災害訓練資料。

**與 WebEOC JAI 的差異化定位（2026 競品更新後補充）**：
WebEOC Nexus 已推出 AI 助手 JAI（Juvare AI），定位為雲端作戰預測。本系統 AI 的核心差異在於：
- **全程離線**：N100 本機推論，網路斷線後 AI 仍可運作（WebEOC JAI 需連線）
- **台灣本土訓練資料**：颱風、地震、山地複合型災害場景，JAI 無此資料集
- **台灣法規合規**：本機運算不涉及個資上傳雲端，符合個資法 + 資安法要求

### C5-D 語音輸入（AI roadmap Phase 4）

> **對應**：AI roadmap Phase 4，依 Phase 2b 小模型評估結果。

兩條路線（Phase 2b 評估後擇一）：
- **路線 A**：Pi 本機小模型（Gemma3 4B / Phi-4-mini，Phase 2b 通過標準：延遲 < 15s）
- **路線 B**：雲端 Gemini 2.5 Flash（音檔 → JSON 一步到位，需網路）

矛盾偵測改用規則引擎（Phase 2 已確認 LLM 矛盾偵測率 0%）：

商業化包裝：作為 Tier 3 授權功能（`voice_input: true`）。

### C5-E 外部系統整合（平台護城河，Tier 3）

- **EMIC 2.0 整合**：從中央系統接收災情，匯入本地指揮（互補定位）
- **中央氣象署 API**：颱風路徑疊加 Leaflet 地圖
- **HXL 匯出**：供 NGO / 國際人道組織使用
- **TAK 整合**：FreeTAKServer + CoT（Wave 7，見長期演進章節）
- **開放 API（v1）**：RESTful + OpenAPI，供 Tier 3 客戶自行整合

---

## C6：合規認證

> 目標：取得正式認證資格，進入大型政府標案。

### C6-A ISO 27001 準備

> **版本說明（2025 更新）**：ISO/IEC 27001:2013 → 2022 版移轉期限已於 2025-10-31 截止，所有新申請及認證更新一律採用 **ISO/IEC 27001:2022**。Amendment 1:2024（氣候行動）新增極端氣象對資安的風險評估要求，台灣消防局作業環境（颱風、地震）直接相關，ISMS 文件需納入氣候韌性評估段落。

先書面化，後取得認證（取得認證費時 6–12 個月）：

ISMS 文件集：
- 資訊安全政策
- 存取控制政策
- 密碼管理政策
- 事件回應程序（含通報 NICS SOP）
- 業務持續計畫（BCP）
  - RTO：指揮部 ≤ 4 小時；Pi 節點 ≤ 1 小時（離線韌性）
  - MTPD：72 小時
- 供應商安全管理（含陸資禁令聲明）
- 風險評估報告（每年更新）

### C6-B 滲透測試

委託 DEVCORE 或 CHT Security 執行完整 Web App 滲透測試：

測試範圍：
- OWASP Top 10（含 WebSocket-specific）
- 認證繞過測試
- 個資存取控制測試
- Pi 節點端點安全
- 局域網橫向移動測試

報告作為驗收文件附件，B 級機關要求每 2 年 1 次。

### C6-C WCAG 2.0 AA

- CI 自動跑 Lighthouse-CI（失敗阻擋 merge）
- 手動修繕：鍵盤導航、色彩對比、ARIA label
- 三端 PWA（收容所/醫療組/指揮部）均需達標

### C6-D SBOM（軟體物料清單）

```bash
pip-licenses --format=json > sbom-python.json
npm list --json > sbom-node.json
```

- 每季更新，納入交付文件包
- CI 加陸資套件自動檢查步驟

---

## 執行順序與版本里程碑

### 執行順序

```
Wave 5 收尾（獨立進行，不阻塞後續）
        │
        ↓（可平行開始）
C0 基礎重構（唯一串行前提）
        │
        ├── C1 安全合規 ─┐ 可平行
        └── C4 產品分層 ─┘
                │
                ├── C2 可測試性 ─┐ 可平行
                └── C3 部署維運 ─┘
                        │
                        C5 護城河
                        │  ├── C5-A TTX 場景庫（Phase 3 基礎已有）
                        │  ├── C5-B AAR 引擎（= AI Phase 6）
                        │  ├── C5-C AI 預測（= AI Phase 5，依硬體）
                        │  └── C5-D 語音輸入（= AI Phase 4，依 Phase 2b）
                        │
                        C6 合規認證
```

### 版本里程碑

| 里程碑 | 版本 | 商業意義 | 對應 AI roadmap |
|--------|------|---------|----------------|
| Wave 5 完成 | `cmd-v0.13.0` | UI 收尾，演訓可用 | Phase 1 完成 |
| C0 Pi 端完成 | `server-v1.2.0` | Pi server 模組化，對外功能不變 | — |
| C1 + C2 完成 | `v2.1.0` | **第一個可投標版本** | — |
| C3 + C4 完成 | `v2.2.0` | **第一個可銷售版本** | — |
| C5-A + C5-B 完成 | `v3.0.0` | **護城河開始，TTX+AAR 商品化** | Phase 6 完成 |
| C5-C + C5-D 完成 | `v3.1.0` | **AI 差異化功能，Tier 3 可賣** | Phase 4+5 完成 |
| C6 完成 | `v3.2.0` | **ISO 認證版本，旗艦標案用** | Phase 7 完成 |
| Silent Scribe MVP | `ss-v1.0.0` | **戰術版獨立產品線上線** | Silent Scribe Sprint 6 |

---

## 商業模式

### 目標市場

| 市場 | 說明 | 特性 |
|------|------|------|
| **A：台灣公部門** | 22 個縣市消防局、災防辦、消防署 | 最大最穩定；採購週期 12–18 個月 |
| **B：台灣 NGO/準公部門** | 紅十字會、慈濟、企業 BCP | 決策快；預算小 |
| **C：民防/準軍事組織** | 民防團體（Silent Scribe 客群） | 高度敏感；需戰術版 |
| **D：國際（長遠）** | 東南亞災防、國際人道組織 | 需 HXL 格式；難度最高 |

### 商業模式：硬體捆綁 + 年度授權 + 服務收入

**一次性收入**

| 產品 | 定價 |
|------|------|
| 基礎版：軟體授權 + Pi 套件 + 安裝 + 訓練 | NT$35–50 萬 |
| 全功能版：全套 + 安裝 + 訓練 + 1 次 TTX | NT$60–90 萬 |
| 旗艦版（含 AI + 語音 + Field Node 上傳） | NT$150 萬+ |
| Silent Scribe 戰術版（另議） | NT$200 萬+ |

**重複收入（Recurring Revenue）**

| 服務 | 定價 |
|------|------|
| 年度維護合約 | NT$8–25 萬/年 |
| TTX 演訓服務 | NT$5–10 萬/次 |
| 訓練課程 | NT$3–5 萬/梯次 |
| AAR 分析報告服務 | NT$2–3 萬/份（非 DIY 客戶） |

### 差異化定位

> EMIC 是平時的「回報系統」。ICS_DMAS 是災時的「作戰系統」。
> 網路斷了，EMIC 也斷了。ICS_DMAS 繼續跑。

EMIC 定位為互補，推動「EMIC + ICS_DMAS 雙系統」採購。

---

## 護城河策略

### 技術護城河

> **競品動態補充（2026-04）**：WebEOC 已推出 WebEOC Nexus 雲端版，含 AI 助手 JAI。競品 AI 功能屬雲端推論，在台灣法規（個資法、資安法）及離線作業情境下有先天劣勢。差異化應強調「離線韌性 + 台灣本土場景 + 無個資上傳」，而非單純功能比拼。

| 護城河 | 建法 | 難以複製的原因 |
|--------|------|--------------|
| TTX 場景資料庫 | 每次服務副產品（已有 10 個種子） | 場景效果評分是領域知識，非工程問題 |
| AAR 報告資料 | 客戶使用累積 | 換系統失去所有歷史對比基準 |
| AI 預測模型 | 台灣本土訓練資料 | 無海外競爭者有此資料集；本機推論符合個資法，WebEOC JAI 雲端不符 |
| 離線同步協議與韌性架構 | 三 Pass 對齊為種子，演進至各節點維護本地 COP 副本的聯邦式同步；申請技術專利 | 災害現場網路必然不穩定；WebEOC/D4H 依賴雲端連線，本系統斷網仍可運作；未來 front/security 單位加入不需重寫 COP 架構 |
| 硬體套件 | 預裝 OS image + 認證套件 | 換系統需要換掉實體設備 |

### 商業護城河

| 護城河 | 建法 | 預期效果 |
|--------|------|---------|
| 政府規格制定者 | 與消防署合作草擬 EOC 系統建置規範 | 競爭者必須符合你的設計 |
| 操作人員訓練網絡 | 「ICS_DMAS 認證操作員」課程 | 受訓人員成為內部推廣者 |
| 政府框架合約 | 申請共同供應契約 | 22 縣市可直接叫貨 |
| 合作夥伴生態 | 與災防顧問、系統整合商合作 | 分銷網絡難以複製 |

### 護城河建立時間軸

```
Year 1：先挖壕溝
  ├── TTX 場景資料庫開始正式積累（種子：現有 10 個情境）
  │     ├── 2026-05-31 無線電演練 → 場景 #11 + 第 1 筆 AAR session log
  │     ├── 2026-06底/07初 中型演練 → 場景 #12 + 第 2 筆 AAR session log
  │     └── 2026-08-30 無線電演練 → 場景 #13 + 第 3 筆 AAR session log
  ├── 硬體套件定型（Pi OS image + 認證套件）
  ├── AAR 報告引擎上線（C5-B）
  └── 第一個縣市政府案例

Year 2：建城牆
  ├── 與消防署合作參與規範制定
  ├── 認證操作員課程，目標 100 人受訓
  ├── 申請離線同步協議專利
  └── 共同供應契約申請

Year 3：護城河注水
  ├── AI 預測模型（訓練資料積累夠了）
  ├── 50+ TTX 場景庫
  ├── 3–5 個縣市參考案例
  └── 框架合約上架，被動入單
```

---

## Silent Scribe 戰術版產品線

> **機密等級**：本產品線文件標記 CONFIDENTIAL，不對一般客戶公開。
> **完整規格**：`security & forward/docs/民防輔助感知系統_規格書_v1_4.md`

### 定位

Silent Scribe（C2-Intelligence）是以 ICS_DMAS 指揮部為後端，加上 Field Node + N100 Console + 軍規物理資安的**戰術版產品**。適用於比一般政府採購更高威脅等級的場景。

**與 ICS_DMAS 主線的關係**：
- **共用**：指揮部後端（FastAPI）、WebSocket 同步協議、TTX 引擎、資料模型
- **差異**：Field Node 硬體（Pi Zero 2W + PTT 偵測）、N100 Console（Whisper Large + Llama 3）、物理資安層（LUKS + YubiKey + Panic Wipe）

### 硬體組成

| 元件 | 規格 | 費用（含多套） |
|------|------|--------------|
| Field Node（每人一台） | Pi Zero 2W + PTT 偵測電路 + Pelican 殼體 | 約 NT$4,300/套 |
| Console | N100 Mini PC（32GB）+ 外接 NVMe 主/備彈匣 | 約 NT$25,000–40,000 |
| 信任根 | USB 點火鑰匙 + YubiKey FIDO2 | 約 NT$3,000 |

### 關鍵功能（Tier 3 授權開啟）

| 功能 | 說明 |
|------|------|
| **零操作負擔錄音** | PTT 按下即錄，放開自動 STT + 上傳，操作員無需操作系統 |
| **雙層 Whisper** | Field Node：Tiny 草稿（< 5 秒）；Console：Large-v3 正式稿 |
| **YubiKey 簽署** | 關鍵操作（ICS-214 簽署、Panic Wipe）需 YubiKey FIDO2 授權 |
| **三層 Panic Wipe** | UI 保護蓋 → 文字確認 → YubiKey，0.5 秒內抹除資料 |
| **LUKS 全碟加密** | Console OS 碟 + 資料彈匣全部 LUKS2，拔除即撤離 |
| **GPS 授時** | Console 為時間主機，Field Node 每 5 分鐘對時，精度 < 1 秒 |
| **ICS-214 PDF** | LLM 自動填表 + WeasyPrint 輸出，含數位簽章 Hash |

### 開發狀態與路徑（對應 Silent Scribe Sprint 計劃）

| Sprint | 狀態 | 說明 |
|--------|------|------|
| Sprint 0：效能基準測試 | ✅ 完成 | Pi 500 E2B 評估完成（見 project_status.md Phase 2） |
| Sprint 1：Console 加密底層 | 🔲 待做 | LUKS2、USB 點火、GPS 授時、三層備份 |
| Sprint 2：容器化與資料分離 | 🔲 待做 | docker-compose + Field Node API |
| Sprint 3：Field Node 開發 | 🔲 待做 | Pi Zero 2W 未到貨，先用 Mac 模擬 |
| Sprint 4：AI 升級 | 🔲 待做 | 依 Phase 2b 小模型評估結果 |
| Sprint 5：實體認證與 PDF | 🔲 待做 | YubiKey + WeasyPrint |
| Sprint 6：野戰驗收 | 🔲 待做 | 戶外全系統驗收 |

### 定價（另議，CONFIDENTIAL）

- 軟體授權：NT$200 萬+（含 ICS_DMAS 旗艦版授權）
- Field Node 每套硬體套件
- Console 硬體套件
- 安裝 + 野戰訓練：NT$20–40 萬/次
- 年度支援合約：NT$30–50 萬/年

---

## 長期產品演進 Wave 6–9

> 以下為 `project_status.md` 指揮部路線圖 Wave 6–9，納入商業化計劃作為長期規劃參考。

| Wave | 內容 | 商業意義 | 狀態 |
|------|------|---------|------|
| **Wave 6** COP 完整實作 | 熱圖、叢集化、過濾搜尋、時間軸回放；**韌性架構前提：各節點維護本地 COP 副本，最終一致同步，無單點失敗** | 提升指揮部態勢感知；為 front/security 單位加入奠定聯邦式 COP 基礎 | 🔲 待做 |
| **Wave 7** TAK 整合 | FreeTAKServer + CoT ↔ ICS_DMAS、MIL-STD-2525 符號 | 打通前進組 ATAK 裝置，進入戰術市場 | 🔲 待做 |
| **Wave 8** EOC/NIMS 標準對齊 | ICS 201/214 表單、資源請求工作流程、單位間訊息、廣播、SitRep | 對標 WebEOC，進入正式 EOC 採購市場 | 🔲 待做 |
| **Wave 9** Silent Scribe 整合 | STT Breeze ASR 25（N100）、LLM ICS-214 自動填表、SQLCipher | ICS_DMAS 主線整合語音功能，Tier 3 完整實現 | 🔲 待做 |

### Wave 6-9 的商業化意義

- **Wave 7（TAK）**：台灣前進組普遍使用 ATAK，整合後 ICS_DMAS 成為台灣唯一可接 ATAK 的民用 EOC 系統
- **Wave 8（NIMS）**：ICS 201/214 表單輸出是政府採購驗收的常見要求（Wave 8 P1 項目），也是 ISO 22301 BCP 文件的一部分
- **Wave 9（Silent Scribe 整合）**：讓 Tier 3 產品的語音功能不需要額外部署，降低客戶維護成本

---

## 附錄：關鍵法規依據

| 法規/標準 | 來源 | 對本系統的強制要求 |
|-----------|------|-------------------|
| 資通安全管理法（2025 修正版） | 數位部 | 核心系統 Log ≥ 6 個月；年度弱掃；未通報罰款上限 NT$1,000 萬；CISO 強制指定；廠商合約須明定資安責任 |
| 資通安全責任等級分級辦法 | 數位部 | 消防局屬 B 級，核心系統需 ISO 27001 |
| 個人資料保護法（2025 修正版） | 個人資料保護委員會（PDPC） | 傷亡者個資需適當安全措施；洩露事件強制通報 PDPC（72 小時內）及當事人 |
| 政府資訊服務採購作業指引 | 數位部 + 工程會 | SBOM、陸資禁令、資安獨立預算 |
| 共通性資安基本要求（軟體） | 數位部 | MFA AAL2、SAST、滲透測試；Zero Trust Architecture 擴展實施中 |
| WCAG 2.0 AA | 數位部 | 政府系統新建/改版強制 |
| NIST SP 800-53 Rev. 5.2.0 | NIST（參考） | 稽核/存取控制/事件回應最佳實務；5.2.0 新增 SA-24 設計韌性、SI-02(07) 根因分析 |
| ISO 27001:2022（含 Amd 1:2024） | ISO（參考） | 資安管理體系；Amendment 1:2024 新增氣候韌性評估要求（颱風/地震場景相關） |
| ISO 22301:2019（含 Amd 1:2024） | ISO（參考） | BCP、RTO/MTPD 定義；Amendment 1:2024 新增氣候韌性 |
| FEMA CPG 101 v3.1 | FEMA（參考） | EOC 計畫書結構、多機關協同（2025-05 正式發布，最新版） |
| UN HXL / HDX | OCHA（參考） | NGO 客戶資料互通格式 |

---

*本文件為初步規劃草稿（v1.2），未設定時間點。各 Phase 的詳細工作拆解、工時估算，待確認執行優先序後另行制定。*
*v1.1 整合來源：AI_integration_roadmap.md、project_status.md、民防輔助感知系統規格書 / 開發計畫 v1.4*
*v1.2 法規更新來源：資安法 2025 修正（2025-09-24 總統公布）、個資法 2025 修正（2025-11-11 總統公布）；競品來源：Juvare WebEOC Nexus 官網、D4H 2025 Wrapped；標準來源：NIST CSRC SP 800-53 Rev 5.2.0（2025-08-27）、ISO 27001:2022/Amd 1:2024*
