---
name: medical PWA 開發進度（2026-03-30）
description: medical-pwa 目前架構狀態、已完成工作、待處理事項
type: project
---

## 已完成（本次 session）

### 架構重構：以傷患狀態為中心
- **DB version 3**：patients 表新增 `care_status` 索引欄位
- `care_status` 值：`'triaged'`（已建檔待評估）→ `'assessed'`（治療評估完成）→ `'pending_transfer'`（待後送）
- 同時儲存 `assessed_by`、`assessed_at` 於 patient 記錄，供卡片顯示履歷用

### 接收流程（檢傷官）
- Intake 表單順序：安全檢查（安檢+收容組登記並排）→ START 四格 → 確認分色 → 「完成檢傷 → 建檔」
- 提交按鈕緊接在「確認分色」按鈕正下方（`triage-submit` div）
- **不再要求填傷型**，建檔即存，`care_status='triaged'`，儀表板立即更新

### 分區看板（治療官）
- 傷患卡片直接顯示三步驟進度條：`✓ 檢傷 ｜ ○ 治療評估 ｜ ○ 後送`
- 醫療履歷：`建檔 陳一・15:37` / `評估 王二・15:45`（或「⬜ 治療評估待接手」）
- 「▶ 評估」快捷按鈕：care_status='triaged' 的傷患才顯示
- 點「▶ 評估」→ `openTreatmentAssessment(id)` → modal 選傷型 + XABCDE/SAMPLE → 儲存 → care_status='assessed'

### 角色導向初始 tab
登入後根據角色自動跳頁：
- 檢傷官 → 接收 tab
- 治療官 / 機動人員 → 分區 tab
- 後送官 → 後送 tab
- 其他（組長等）→ 儀表板

### Tab Badge
- **分區**：再評估逾時人數（`reassess_due_at` 過期）
- **接收**：care_status='triaged' 待評估人數（**待討論是否移到分區**）
- **後送**：disposition='後送' 待後送人數
- 三個 badge 在每次 `renderCurrentTab()` 時統一由 `updateTabBadges()` 更新

### 儀表板燈號 bug 修正
- 原本 emoji + CSS dot 重疊顯示兩顆，已改為純 CSS dot + 中文狀態文字

---

## 待決定 / 待實作

### Badge 定義討論（未完成）
用戶確認 badge 定義有點模糊，下次繼續：
1. 接收 tab badge → 建議移除（檢傷官自己建單，不需提醒）
2. 分區 tab badge → 建議改為「待評估 + 逾時合計」（治療官主要關注點）
3. 分區看板「全部待評估」篩選 tab → 待確認是否需要

### 其他已識別但未處理
- `setInjury` 函式和 `confirmTriageColor` 的 console.log 還在（偵錯用，正式版可移除）
- 治療評估 modal 的 `renderTreatmentModal` 使用 `existing = document.getElementById('modal-body')` 判斷是否已開啟，需驗證切換傷型時是否正常重繪
- QR snapshot、交班、物資管理功能未動，維持原樣

---

## 關鍵檔案
- `medical-pwa/public/medical_pwa.html`（所有邏輯在此單一檔案）
- `medical-pwa/public/sw.js`（Service Worker，改完要 Cmd+Shift+R 強制重整）
- `medical-pwa/docs/醫療組SOP_20260323.md`（流程設計依據）
- `medical-pwa/docs/medical_pwa_spec_v0_4.md`（規格書）

**Why:** 跨機器作業，此機器處理 medical PWA，另一台機器處理 shelter PWA，不可混用記憶。
**How to apply:** 下次繼續時先確認 badge 定義方向，再實作分區看板「待評估」篩選。
