# ICS_DMAS 統一路線圖

> **唯一入口**。Wave（功能）與 cX（工程品質/商業化）合併於此。
> 細節見：[商業化計劃](commercialization_plan_v1.md) · [指揮部規格書](../command-dashboard/docs/指揮部儀表板設計規格.md)

---

## 現在位置（2026-04-24）

| 項目 | 狀態 |
|------|------|
| 程式版號 | `cmd-v2.0.4` / `server-v1.3.0` |
| Wave 進度 | Wave 5 尾端（剩 2 項）|
| cX 進度 | C0 ✅ / **C1-B ✅** / **C1-A Phase 1 ✅**（鎖定 + rate limit + 首次強制設定；Phase 2 RBAC + Phase 3 MFA 待做）/ C1 其餘待做 / C2 部分完成 |
| 下一個里程碑 | `v0.13.0` Wave 5 完成 |
| 下一個商業里程碑 | `v2.1.0` 第一個可投標版本 |

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

### Engineering — C1：安全性與法規合規

| 子項 | 內容 | 說明 |
|------|------|------|
| **C1-A** ⚠️ Phase 1 完成 | 認證強化 | ✅ 登入鎖定 5次/15min + IP rate limit 10/min + 首次強制設定（移除預設 PIN 1234）；🔲 RBAC OBSERVER；🔲 TOTP MFA AAL2 |
| **C1-B** ✅ 程式碼 | 全面加密傳輸 | nginx HTTPS（TLS 1.2+）、HSTS、CSP report-only、CORS 收斂、step-ca 內網 PKI；待 step-ca/nginx 安裝實測；strict CSP 留 C1-F 後做 |
| **C1-C** | 個資保護 | 敏感欄位 Fernet 加密、`pii_access_log`、72h PDPC 通報流程 |
| **C1-D** | Append-only 稽核軌跡 | DB trigger 防竄改、雜湊鏈、6 個月保存、structlog JSON |
| **C1-E** | Schema 版本追蹤 | `migrations` 表，append-only，正式追蹤所有 DB 變更 |
| **C1-F** | 前端模組化 | 抽出 `.js` 模組、esbuild bundle、vitest 前端測試 |

### Engineering — C2：工程品質

| 子項 | 內容 | 說明 |
|------|------|------|
| **C2-A** | 測試補完 | security/ 測試（auth bypass、SQL injection、rate limit）|
| **C2-B** | CI/CD 強化 | mypy strict、coverage ≥70%、js-quality（eslint + vitest）|
| **C2-C** | 程式碼品質工具 | ruff、pre-commit hooks、detect-secrets |

> ⚠️ **v2.1.0 的關鍵路徑**：C1-B（HTTPS）是最優先——沒有 HTTPS 就不是可投標的安全系統。
> 6月底演練是壓力節點，目標在演練前完成 C1-B + C1-A 核心部分。

---

## Wave 7 + C3 + C4 → v2.2.0（🔲 第一個可銷售版本）

### Feature — Wave 7：TAK 整合

| 項目 | 說明 |
|------|------|
| FreeTAKServer ↔ ICS_DMAS | CoT（Cursor on Target）XML 雙向橋接 |
| MIL-STD-2525 符號渲染 | CoT `type` 欄位即為符號代碼，同一 Wave 實作 |
| 動態 GPS marker | ATAK 裝置每幾秒推送位置，Wave 5 動態 marker 為基礎 |

### Engineering — C3：部署與維運

| 子項 | 內容 |
|------|------|
| **C3-A** | 設定外部化：`/etc/ics/command.env`，不進 git |
| **C3-B** | 一鍵安裝腳本：建立 `ics` 系統使用者、權限、key 產生、systemd |
| **C3-C** | 健康檢查 `/health` + Prometheus `/metrics` 端點 |
| **C3-D** | 自動備份三層：WAL（即時）/ daily gzip（30天）/ NAS rsync（可選）|

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
- `SQLCipher` 資料庫加密（靜態加密，Tier 3）

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
