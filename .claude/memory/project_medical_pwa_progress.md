---
name: medical PWA 開發進度（2026-03-30）
description: medical-pwa 目前架構狀態、已完成工作、待處理事項
type: project
---

## 目前版本：v0.3.3（最後 commit：b646a5a）

分支：`feat/medical-pwa-ui-redesign`（worktree：`.claude/worktrees/charming-neumann`）
預覽伺服器：`python -m http.server 8001`，目錄 `medical-pwa/public/`

---

## 本 session 完成（v0.3.0 → v0.3.3）

### v0.3.0 — Intake 頁面功能強化

#### 倒數計時可見（Item 0）
- `updateIdleHdr()` 原本將倒數文字設為白色（白字白底看不見）
- 修正為 `#999`（正常）/ `#C62828`（最後 30 秒警急紅色）

#### 安檢預設「未完成」+ 鎖定分色（Item 1）
- `intakeSecurity` 預設 `'incomplete'`
- 安檢未改變時，`renderTriageColorPicker()` 鎖定（opacity 0.4, pointer-events none）並顯示警告
- `onSecurityChange()` 更新 state 並局部重繪 `#triage-section`

#### 個人特徵（性別/年齡）+ Draft ID（Item 2）
- `_state.intakeSex`, `_state.intakeAge`, `_state.intakeDraftId` 新增至 state
- DB 升至 version 4，patients 表加 `source_sex`, `source_age`
- `onPersonChanged()` 更新 state，呼叫 `generateDraftId(sex, age)`
- `generateDraftId()` async，從 `db.patients.orderBy('id').last()` 取序號，格式 `M001-FA`
- Draft ID 預覽區塊（`#patient-id-preview`）常駐 DOM，`display:none` 控制顯示
- 性別 / 年齡其中一個恢復「—」→ draft ID 收回（`display:none`）

#### START walk 未選鎖定分色（Item 3）
- `canPickTriageColor()` 三重鎖：`intakeSecurity !== 'incomplete'` + `intakeSex && intakeAge` + `start-walk` 已選
- 鎖定原因訊息依序判斷，顯示最前面未滿足的條件

### v0.3.1 — Source 按鈕對齊（patch）
- `.source-btns` padding 從 `12px 14px` 改為 `12px 28px`
- 與「掃描 QR」/ 「手動輸入」按鈕左右邊距對齊（用 `getBoundingClientRect()` 驗證，差距 < 0.01px）

### v0.3.2 — Bug 修正

1. **個人特徵未填仍可分色**：`canPickTriageColor()` 加入 sex/age 雙重判斷
2. **Draft ID 收回**：`onPersonChanged()` 偵測到 sex 或 age 為空時隱藏預覽 div
3. **評估按鈕無效（zones 分區 ▶ 評估）**：
   - 原因：`renderTreatmentModal()` 檢查 `document.getElementById('modal-body')` 存在性（always true）
   - 修正：改為檢查 `modal-overlay.classList.contains('hidden')`，未開啟時才呼叫 `openModal()`

### v0.3.3 — 三項改善

1. **移除「確認分色」按鈕**：`renderTriageColorPicker()` 移除 `#triage-confirm` 區塊，`setTriageColor()` 移除對應邏輯，`confirmTriageColor()` 函式刪除
2. **非創評估加臨床參考值**：`renderSampleOpqrst()` 全面改寫，所有欄位改用 `mist-combo` 模式（select 快選 + input 補充）。ABC 加正常值提示，SAMPLE 加常見選項，OPQRST 加警示（R 放射部位標注心臟/主動脈模式）
3. **傷患詳情加安檢狀態**：`openPatientDetail()` 加入 `security_cleared` 欄位顯示

---

## 架構重點（給下次繼續的快速參考）

- **單一檔案**：`medical-pwa/public/medical_pwa.html`，所有 CSS/HTML/JS inline
- **DB version 4**：patients 表含 `source_sex`, `source_age`
- **State 相關欄位**：`intakeSecurity`（'incomplete'|'yes'|'pending'）、`intakeSex`、`intakeAge`、`intakeDraftId`
- **triage lock 機制**：`canPickTriageColor()` 三重鎖 → `renderTriageColorPicker()` 局部重繪 `#triage-section`
- **modal 系統**：`#modal-overlay`（hidden/visible）、`#modal-body`（always in DOM）
- **idle timer**：`IDLE_WARN_S=90s`, `IDLE_LOCK_S=30s`，`clearIdleTimers()` + `startIdleTimer()`

---

## 待處理（issues.md 對照）

| 項目 | 狀態 | 說明 |
|------|------|------|
| P1 — C 來源表單 | ❌ 待做 | 演習前必修 |
| P2 — ID 重複 bug | ✅ 完成 | DB v4、格式 M001-FA、async 序號，`arrival_mode` 欄位待確認 |
| P3 — 紅區容量 | ❌ 待決定方案 | — |
| P4 — 到院生命徵象 | ❌ 待做 | — |
| P7 — 腕帶 QR 產生 | ❌ 待做 | 演習前必修 |
| P8 — 全域掃碼查詢 | ❌ 待做 | 演習前必修 |
| Badge 定義 | ❌ 待決定 | — |
| 治療評估 modal 重繪 | ✅ 已修 | v0.3.2 修復（評估按鈕無效 bug） |

**Why:** 跨機器作業，此 memory 是 medical PWA session 的快速恢復依據。
**How to apply:** 開始 medical PWA session 時先讀此 memory，確認版本號與 git branch，再繼續 P1/P7/P8。
