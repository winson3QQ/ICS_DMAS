# ICS_DMAS 統一路線圖

> **唯一入口**。Wave（功能）與 cX（工程品質/商業化）合併於此。
> 細節見：[商業化計劃](commercialization_plan_v1.md) · [指揮部規格書](../command-dashboard/docs/指揮部儀表板設計規格.md) · [Compliance](compliance/README.md)
>
> **Cx 命名前綴**：
> - `C-` / 無前綴：command-dashboard
> - `P-C*`：Pi server 對應項
> - `W-C*`：PWA（shelter + medical）對應項

---

## 現在位置（2026-04-25）

| 項目 | 狀態 |
|------|------|
| 程式版號 | `cmd-v2.0.5` / `server-v1.3.0` |
| Wave 進度 | Wave 5 尾端（剩 1 項）|
| cX 進度 | C0 ✅ / **C1-B ✅**（程式碼）/ **C1-A Phase 1 ✅** / **C1-E ✅** / **C2-C ✅** / **C2-D ✅** / C1-A Phase 2 RBAC 待做（擴大範圍）/ Compliance Audit 待做 |
| 下一個里程碑 | `v0.13.0` Wave 5 完成 |
| 下一個商業里程碑 | `v2.1.0` 第一個可投標版本（Compliance audit 完成後重估）|
| **Compliance 程式** | ⏸ Phase 0 Audit 未開始（Session A→B→C→D 未開始）。見 [compliance/](compliance/README.md) |

---

## 版本里程碑總覽

| 版本 | Feature（Wave）| Engineering（cX）| 目標 | 商業意義 | 狀態 |
|------|----------------|------------------|------|---------|------|
| ~~v0.12.x~~ | ~~Wave 1–4++ 完成~~ | ~~C0 後端重構完成~~ | ~~2026-04~~ | ~~架構基礎~~ | ✅ |
| **v0.13.0** | Wave 5 完成 | — | 2026-05 | UI 收尾，演訓可用 | 🔄 |
| **v2.1.0** | Wave 6 COP 基礎 | C1 安全合規 + C2 工程品質 | 2026-06 | **第一個可投標版本** | 🔲 |
| **v2.2.0** | Wave 6–7 | C3 部署維運 + C4 產品授權 | 2026-Q3 | **第一個可銷售版本** | 🔲 |
| **v3.0.0** | Wave 7–8 | C5-A TTX + C5-B AAR | 2026-Q4 | **護城河，TTX+AAR 商品化** | 🔲 |
| **v3.1.0** | Wave 8–9 | C5-C AI 預測 + C5-D 語音 | 2027-Q1 | AI 差異化，Tier 3 可賣 | 🔲 |
| **v3.2.0** | Wave 9 | C6 合規認證 | 2027-Q2 | ISO 認證，旗艦標案 | 🔲 |

---

## Wave 5 → v0.13.0（🔄 進行中）

### Feature

| 項目 | 狀態 | 說明 |
|------|------|------|
| 重設 deadline API | ✅ | `PATCH /api/events/{id}/deadline` 前後端均完成 |
| 動態 marker 聯動 calc_engine | ✅ | 三態 RAG：ok/warn/crit 顏色＋badge＋閃爍 |
| 縮短 push/polling 間隔（5s）| ✅ | Pi push 60s → 5s，最壞延遲 ~10s |
| 地圖流向箭頭（Leaflet）| ✅ | SVG overlay 已移除，統一 Leaflet |
| UI 狀態 Ctrl+Shift+R 還原 | ✅ | 5 個 sessionStorage key 全部持久化 |
| 量能圖資料＋語意修正 | ✅ | sBt→sBu；床位→量能；傷患後送→入站 |
| **物資 burn rate 預測線** | 🔲 | `chart_utils.js` 加 `projectToZero` 虛線延伸 |
| ~~決策主題合併卡片~~ | ⏸ 暫緩 | COP 資訊架構重設計後一起實作，避免在錯誤佈局上建功能 |

### Engineering（C0 遺留）

| 項目 | 狀態 |
|------|------|
| Session SQLite 持久化 | ✅ cmd-v0.12.13 |
| 前端模組化（移至 C1-F）| 🔲 |

---

## Wave 6 + C1 + C2 → v2.1.0（🔲 第一個可投標版本）

### Feature — Wave 6：COP 完整實作

> ⚠️ **前置條件**：Wave 6 實作前需完成 **COP 資訊架構 design sprint**（見 architecture_decisions.md）。
> 現有三欄佈局有結構性問題（決策佇列優先序、左 panel 對象不一致、地圖與事件列表脫節），
> 在錯誤架構上疊加功能只會增加技術債。

| 項目 | 說明 |
|------|------|
| **COP 資訊架構重設計** | Design sprint 產出：線框圖 + 聯動規格 + 更新設計規格書 |
| 熱圖（Heatmap）| 事件/人員密度疊加於地圖 |
| 叢集化（Clustering）| 大量 marker 自動群組 |
| 過濾搜尋 | 事件/資源/人員全域搜尋 |
| 時間軸回放 | 從 `resource_snapshots` 表重建歷史狀態 |
| 3D 地形 | 依硬體評估（N100 目標平台）|
| **COP 事件自動分類** 🆕 | PTT 語音 / TAK / PWA 輸入進系統後立即自動分類、計算優先序，直接顯示地圖與決策佇列 |
| **決策佇列 + AI 推薦自動排序** 🆕 | 依嚴重度 + 緊急度自動排序；AI 推薦卡片每 30 秒自動更新推送 |
| **QR Code 快照 5 分鐘自動產生** 🆕 | 最新 COP 狀態轉 QR Code，極端斷網時 PWA 仍可同步（W-C1-G 衝突解析策略配套）|

### Engineering — C1：安全性與法規合規

| 子項 | 內容 | 說明 |
|------|------|------|
| 子項 | 內容 | 適用標準 | 說明 |
|------|------|---------|------|
| **C1-A** ⚠️ Phase 1 完成 | 認證強化 | NIST 800-63-3 AAL2 / 800-53 IA / CIS §6 | ✅ Phase 1（登入鎖定 + 首次強制設定）；🔲 **Phase 2：RBAC 4-role + 作業期間 + Transfer of Command**（範圍擴大，見下註）；🔲 Phase 3 TOTP MFA；🔲 Phase 4 CISO 政策文件（→ security_policies.md 升正式版）|
| **C1-B** ✅ 程式碼 | 全面加密傳輸 | NIST 800-53 SC-8/12/13 / ASVS V9 | nginx HTTPS（TLS 1.2+）、HSTS、CSP report-only、CORS 收斂、step-ca 內網 PKI；待 step-ca/nginx 安裝實測；strict CSP 留 C1-F 後做 |
| **C1-C** | 個資保護 + 靜態資料加密 | 個資法 PDPA / NIST Privacy Framework / 800-53 PT / SC-28 | **三層加密策略**：① 應用層 Fernet 敏感欄位加密 ② DB 層 SQLCipher（評估導入）③ OS 層 LUKS 全碟加密（Pi 部署時設定）；`pii_access_log`、72h PDPC 通報流程、資料分類表 |
| **C1-D** | 可觀察性 + 稽核 | NIST 800-53 AU / ASVS V7 / CSF DETECT | **範圍擴大**：跨組件 correlation ID + structlog JSON + append-only audit + hash chain + 6 個月保存（command/pi/pwa 三組件協議統一）；**8 個優先埋 log 位置**：(1) WS 連線/推送 (2) 事件產生與分類 (3) DB 寫入 (4) SDR/無線電錄音 (5) STT 轉錄+CER (6) AI 推薦+採納/拒絕 (7) 登入/權限檢查 (8) calc_engine 計算 |
| **C1-E** ✅ | Schema 版本追蹤 | NIST 800-53 CM-3 / CM-6 | `schema_migrations` 表，append-only，正式追蹤所有 DB 變更 |
| **C1-F** | 前端模組化 + 前端安全 | ASVS V14 / CSP3 / 800-53 SC | 抽出 `.js` 模組、esbuild bundle、vitest 前端測試、**CSP enforce 切換**（從 report-only）|
| **C1-G** 🆕 | WebSocket 安全與可靠性 | ASVS V9 / NIST 800-53 SC-8/23 / CIS §13 | ConnectionManager（heartbeat + reconnect backoff + message queue）、WS token 驗證（獨立於 HTTP session）、WS mTLS（Tier 3）、message signing（可選，高安全版本）、DoS 防護（連線數限制 + rate limit per-connection）|

> **註**：C1-A Phase 2 範圍擴大 — 4-role RBAC（系統管理員 / 指揮官 / 操作員 / 觀察員）+ role_detail（ICS 標準職稱下拉）+ `require_role()` gate + operational_periods 表 + Transfer of Command API + duty_log 表 + Unity of Command 偵測 + break-glass admin PIN 收斂。詳細設計見 compliance/ 與 architecture_decisions.md。

### Engineering — C2：工程品質

| 子項 | 內容 | 適用標準 | 說明 |
|------|------|---------|------|
| **C2-A** | 測試補完 | ASVS L2 / ISO 25010 可靠性 / CIS §16 | security/ 測試（auth bypass、SQL injection、rate limit）+ ASVS L2 完整驗證 |
| **C2-B** | CI/CD 強化 + 品質度量 | DORA / ISO 25010 / SSDF PW.7 | mypy strict、coverage ≥70%、js-quality（eslint + vitest）、DORA metrics 追蹤 |
| **C2-C** ✅ 擴充 | 程式碼品質工具 + GitHub Security | SSDF PW.4 / CIS §16.11 | ruff、pre-commit hooks、detect-secrets；**擴充**：GitHub CodeQL 啟用、Dependabot alerts、secret scanning、SAST 報告 fail-build 政策 |
| **C2-D** ✅ | Admin PIN 鎖定 | NIST 800-63-3 / CIS §6.3 | 5次失敗/鎖定30分鐘，前端顯示剩餘次數與解鎖時間 |
| **C2-E** 🆕 | 供應鏈與 SSDF | SLSA L2 / SSDF PS / NIST SR / CycloneDX | pip-audit + npm audit CI、**SBOM（CycloneDX）** 生成、vulnerability disclosure 政策、SLSA L2 產製流程 |
| **C2-F** 🆕 | 生產部署韌性 | ASVS V14.3 / 800-53 SI / CIS §8 | 統一 exception handler + 錯誤訊息資訊不揭露（生產模式 debug off）+ payload size 限制 + 全域 rate limit（非只 /login）+ OWASP Top 10 覆蓋檢查；**dev/prod debug 模式切換機制**；**DB 並發韌性**（connection pool + exponential backoff retry + 序列化 writer queue，解 `database is locked`；6 月演練前必做，詳見 architecture_decisions.md Decision B）|

### Engineering — Pi Server 同步（C1/C2 適用項目）

> Pi server（Node.js）與 command dashboard 共享相同的安全與工程品質目標。
> 以下為 command dashboard Cx 項目在 Pi server 的對應工作。

| 子項 | 對應 | 內容 | 狀態 |
|------|------|------|------|
| **P-C1-A** | C1-A / C2-D | Admin PIN 鎖定 + 首次強制設定（確認 Pi server 無預設 admin PIN 漏洞）| 🔲 |
| **P-C1-B** 🆕 | C1-B | Pi 端 TLS 憑證管理 + STRICT_TLS 強制 + 憑證到期監控 | 🔲 |
| **P-C1-D** | C1-D | Audit log hash chain + correlation ID（與 command 跨組件串連）| 🔲 |
| **P-C1-E** | C1-E | Schema version API + shelter/medical GUI 顯示（`server/migrations.js` 已有邏輯，缺 API）| 🔲 |
| **P-C1-G** 🆕 | C1-G | Pi 端 WS 連線管理（heartbeat + reconnect）+ WS token 驗證 + DoS 防護 | 🔲 |
| **P-C2-C** | C2-C | ESLint + prettier + detect-secrets + GitHub CodeQL（Node.js 等效） | 🔲 |
| **P-C2-F** 🆕 | C2-F | Pi 端錯誤處理 + 生產 debug off + payload 限制 + Pi 端全域 rate limit + Pi 端 DB 並發 retry | 🔲 |

### Engineering — PWA 同步（W-Cx，新增前綴家族）

> PWA（shelter + medical）的安全與品質項目，先前未獨立追蹤。
> 以下為 command Cx 項目在 PWA 的對應工作，shelter 與 medical 共用同一份 Cx（實作可能略有差異）。

| 子項 | 對應 | 內容 | 狀態 |
|------|------|------|------|
| **W-C1-A** 🆕 | C1-A | PWA 端 RBAC + session 機制（目前 PWA 登入是 PIN，無 role 概念）| 🔲 |
| **W-C1-C** 🆕 | C1-C | PWA 端 PII 處理（IndexedDB 存病患資料，目前明文；Dexie 加密 / 欄位分級）| 🔲 |
| **W-C1-D** 🆕 | C1-D | PWA 端使用者操作 audit log + correlation ID（上傳至 Pi → 串入系統 audit chain）| 🔲 |
| **W-C1-F** 🆕 | C1-F | PWA CSP + XSS 防護 + Service Worker 安全（含 SW 劫持防護）| 🔲 |
| **W-C1-G** 🆕 | C1-G | PWA 端 WS client 可靠性（reconnect backoff、離線佇列、同步衝突解析策略）| 🔲 |
| **W-C2-A** 🆕 | C2-A | PWA 端 vitest / playwright 測試 | 🔲 |
| **W-C2-F** 🆕 | C2-F | PWA 端錯誤處理 + 前端 error → 後端回拋機制 | 🔲 |

### Engineering — Compliance Audit（新增：貫穿所有 Cx 的合規程式）

| 子項 | 內容 | 狀態 |
|------|------|------|
| **Compliance Phase 0** 🆕 | Audit 全系統 × NIST 800-53/63/218/CSF × ISO 25010/5055 × NIMS/ICS 508 × Taiwan 法規 → 產出 matrix + gap analysis + threat model + policies | ⏸ 未開始（Session A→B→C→D）|
| 持續追蹤 | 每次 Cx 項目完成，同步更新 compliance matrix evidence 欄位 | 持續 |

> ⚠️ **v2.1.0 的關鍵路徑**：C1-B（HTTPS）是最優先——沒有 HTTPS 就不是可投標的安全系統。
> 6月底演練是壓力節點，目標在演練前完成 C1-B + C1-A 核心部分。

---

## Wave 7 + C3 + C4 → v2.2.0（🔲 第一個可銷售版本）

### Feature — Wave 7：TAK 整合 + MANET

#### 7a：TAK 整合
| 項目 | 說明 |
|------|------|
| FreeTAKServer ↔ ICS_DMAS | CoT（Cursor on Target）XML 雙向橋接 |
| MIL-STD-2525 符號渲染 | CoT `type` 欄位即為符號代碼，同一 Wave 實作 |
| 動態 GPS marker | ATAK 裝置每幾秒推送位置，Wave 5 動態 marker 為基礎 |
| CoT 訊息自動分類 | 進入後自動轉 marker + 事件，自動計算優先序 |

#### 7b：MANET（前進組網路）🆕
| 項目 | 說明 |
|------|------|
| Pi Zero 2W Mesh 自動加入 | 開機後自動加入 Mesh、自動選擇最佳路徑 |
| 訊號強度監控 | 連線品質即時回傳指揮部 |
| 零設定原則 | 平地 / 城市環境下幾乎零設定即可使用 |

### Engineering — C3：部署與維運

| 子項 | 內容 | 適用標準 |
|------|------|---------|
| **C3-A** | 設定外部化：`/etc/ics/command.env`，不進 git | CM-6 / CIS §4 |
| **C3-B** | 一鍵安裝腳本：建立 `ics` 系統使用者、權限、key 產生、systemd、**NTP / chrony 設定**、**WAL mode 啟用**、**LUKS 全碟加密** | CM-2 / SC-12 / SI-16 |
| **C3-C** | 健康檢查 `/health` + Prometheus `/metrics` + OpenTelemetry traces（跨組件）| CSF DETECT / 800-53 AU-6 / ISO 25010 可靠性 |
| **C3-D** | 自動備份三層：WAL（即時）/ daily gzip（30天）/ NAS rsync（可選）+ **Recovery drill 每 6 個月** | CP-9 / CP-10 |
| **C3-F** 🆕 | Docker 化 + Binary IP 保護（**Open Core 策略**）| — |
| **C3-G** 🆕 | 客戶支援自助化 | — |

**C3-F 詳細**（Open Core 模式，見 architecture_decisions.md Decision A）：
- Dockerfile + docker-compose.yml：command-dashboard / pi-server / nginx / step-ca 各自容器化
- **閉源核心** binary compile（Cython 或 Nuitka）：`services/ai_service.py` / TTX Orchestrator / calc_engine 核心邏輯
- **開源** 其他層：schemas / routers / auth middleware / UI
- 私有 Docker registry（自建或 GHCR private）
- Image 版本標籤（如 `ics-dmas:2.1.3`）+ 舊 image 保留供回滾
- 客戶部署流程：`docker compose pull && docker compose up -d`

**C3-G 詳細**：
- `collect_debug.sh`：一鍵打包 log / 系統狀態 / config（去敏後）成 zip
- 客戶 FAQ + troubleshooting playbook（繁中）
- 自助診斷：`docker compose ps` / `docker logs` / 健康檢查 endpoint
- 目標：70-80% 問題客戶自助解決

### Engineering — C4：產品分層與授權機制

| 子項 | 內容 |
|------|------|
| **C4** | 授權檔（JSON，RSA 簽章）控制 Tier 1/2/3 功能開關 |
| **C4** | Tier 1 基礎版 / Tier 2 演訓版 / Tier 3 旗艦版 定義 |

---

## Wave 8 + C5-A/B → v3.0.0（🔲 護城河開始）

### Feature — Wave 8：EOC/NIMS 標準對齊

| 項目 | 說明 |
|------|------|
| ICS 201/214 表單輸出 | 事件概況表 + 工作日誌，PDF/列印友善 HTML |
| 資源請求工作流程 | PWA 提交 → 指揮部審核 → 狀態回報（ICS 213RR）|
| 單位間訊息 | 結構化文字訊息，綁定事件 ID |
| 廣播通知 | 全組/特定組廣播，PWA banner + 音效 |
| 狀況報告（SitRep）| 自動產生純文字摘要，指揮官確認後鎖定 |
| AAR 自動組裝 | 演習結束後從 DB 組裝事件時間軸、決策紀錄、資源消耗 |

### Engineering — C5-A：TTX 場景資料庫

- 場景庫 CRUD API + 指揮部 UI
- Inject 簽章（`ttx_injects.signature`，C0 已預留欄位）
- MSEL 格式 export（HSEEP 標準）
- **商業路徑**：TTX 先賣 → 跑 N 場 → 升級 ICS_DMAS，資料無縫帶入

### Engineering — C5-B：AAR 報告引擎

- `aar_entries` 表（C0 已建）
- 自動生成 PDF / JSON（機器可讀，AI 訓練用）
- 跨場次 KPI 比較（`exercise_kpis` 表）

---

## Wave 9 + C5-C/D → v3.1.0（🔲 AI 差異化）

### Feature — Wave 9：Silent Scribe 整合

| 項目 | 狀態 | 說明 |
|------|------|------|
| Pi 500 本地 STT | ❌ 不可行 | Whisper CER 45%，中文醫療術語全錯 |
| N100 推論 | 🔲 待硬體 | Pi 錄音 → N100 推論，延遲可接受 |
| 雲端 API（Gemini Flash）| 🔲 評估中 | 音檔→JSON 一步到位，需確認法規 |
| LLM ICS-214 自動填表 | 🔲 | Breeze 本地（93.5% 結構化準確率，延遲 40–50s）|
| Panic Wipe | 🔲 | 物理觸發資料清除機制 |

### Engineering — C5-C：AI 預測層

- `ai_service.py` 抽象介面（C0 stub 已建）
- `ai_recommendations` 表（法律紀錄 + 訓練資料閉環）
- 即時建議：`POST /api/ai/recommend`（讀當下 COP 狀態）
- 演練後分析：`GET /api/ai/report/{exercise_id}`
- 本地優先（Breeze on N100），雲端為 fallback

### Engineering — C5-D：語音輸入

- STT 路線待定（見 Wave 9 上方）
- `SQLCipher` 資料庫加密（靜態加密，Tier 3；與 C1-C 的三層加密策略對應）

### Engineering — C5-E 🆕：AI 資安

| 子項 | 內容 | 適用標準 |
|------|------|---------|
| **Prompt injection 防護** | Input validation + prompt template 隔離 + output sanitization | OWASP LLM Top 10（2025 版）/ NIST AI RMF |
| **Output sandbox** | AI 輸出先經規則引擎驗證（不可提議實體行動、不可觸發其他 API）再呈現 | NIST AI RMF GOVERN-AI |
| **Model weight 簽章** | 本地模型權重檔 SHA-256 + 簽章驗證（啟動前檢查）| SLSA v1.0 / SSDF PS.2 |
| **AI-specific audit log** | 所有 prompt + response + 指揮官採納/否決紀錄（C5-C `ai_recommendations` 表擴充）| AU-2 / 個資法（AI 不得洩漏個資）|
| **無出境保證** | 雲端 AI 僅接受匿名化資料（個資 tagger 前置過濾）| 個資法 §21 |

---

## C6 → v3.2.0（🔲 ISO 認證版本）

- ISO 27001 / CNS 27001 資安管理認證準備
- 外部滲透測試、弱點掃描報告
- 旗艦標案用（政府機關最高採購門檻）

---

## 參考文件

| 文件 | 用途 |
|------|------|
| [commercialization_plan_v1.md](commercialization_plan_v1.md) | C1–C5 各子項實作細節、授權機制設計、法規合規規格 |
| [AI_integration_roadmap.md](AI_integration_roadmap.md) | AI Phase 0–7 技術路線圖 |
| [指揮部儀表板設計規格.md](../command-dashboard/docs/指揮部儀表板設計規格.md) | 前端 UI/UX 規格，Wave 對應功能細節 |
| [project_status.md](../.claude/memory/project_status.md) | 技術備忘、版本歷史、Pi 部署步驟 |
