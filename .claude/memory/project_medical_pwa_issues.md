---
name: medical PWA 待處理問題清單（2026-03-30 更新）
description: medical_pwa.html 的已知問題、優先順序、修改方向，演習前必修 P1/P7/P8
type: project
---

## 演習前必修（🔴）

### P1 — 缺少「非前進組送入」C 來源表單
- 按鈕標籤「🚶 自行抵達」語意不完整，應改為「🙋 非前進組送入」
- 選 C 後沒有表單區塊：需加入送入方式、性別（觀察）、年齡段（觀察）、來源描述、主要傷況（觀察）
- `submitIntake()` 需讀取 `c-arrival-mode`、`c-sex`、`c-age`、`c-source-desc`、`c-issue`
- **狀態：❌ 待做**

### P2 — `nextDisplayId()` 產生重複 ID ✅ 已修（v0.3.0）
- 問題：`_state.patients.length + 1` 只算活躍傷患，已後送者不計入，導致序號重複
- 修正：`generateDraftId()` async，從 DB `orderBy('id').last()` 取最大值
- ID 格式改為 `M007-FA`（含性別年齡代碼）
- DB 升至 version 4，patients 表加 `source_sex`、`source_age`
- 備注：`arrival_mode` 欄位是否需加入 DB 尚未確認（P1 完成後順帶確認）

### P7 — 建檔後需產生醫療組腕帶 QR
- 前進組 QR 掃描後任務結束，醫療組需產生新 QR 綁腕帶
- `submitIntake()` 建檔成功後改為開啟 `openWristbandModal()`
- QR payload：`{ id, color, issued_at }`（僅識別資訊，不含醫療資料）
- `qrcode.js` 已在第 365 行載入，直接可用
- **狀態：❌ 待做**

### P8 — 全域掃碼查詢傷患
- Header 右側加入 📷 掃碼按鈕（登出按鈕之前）
- `_state.scanMode` 新增欄位（null | 'lookup'）
- `handleQrResult()` 依 scanMode 分流：lookup 模式走 `handlePatientScanResult()`，原有模式走 MIST 帶入
- `handlePatientScanResult()` 從 DB 查 display_id，找到後呼叫 `openPatientDetail(patient.id)`
- **狀態：❌ 待做**

---

## 演習前需決定（🟡）

### P3 — `getRedSlotsFree()` 永遠回傳 999
- 紅區滿載警報永遠不觸發
- 方案 A：固定常數 `RED_ZONE_CAPACITY = 5`（最快）
- 方案 B：從 config 表讀取，管理員可設定
- **狀態：❌ 尚未決定方案**

### P4 — MIST 現場生命徵象 vs START 到院生命徵象混用
- patient card 顯示的是現場 MIST-S 數值，不是到院時 START 數值
- 修正：DB 加 `arrival_vitals` 欄位（可納入 P1 的 migration），patient card 分兩行顯示
- **狀態：❌ 待做（時間允許）**

### Badge 定義（未收錄於 issues.md）
- 接收 tab badge → 建議移除（檢傷官自己建單不需提醒）
- 分區 tab badge → 建議改為「待評估 + 逾時合計」
- 分區看板「全部待評估」篩選 tab → 待確認是否需要
- **狀態：❌ 尚未決定**

### 治療評估 modal 重繪 ✅ 已修（v0.3.2）
- 原問題：`renderTreatmentModal` 用 `document.getElementById('modal-body')` 判斷（always true）
- 修正：改為檢查 `modal-overlay.classList.contains('hidden')`

---

## 演習後再做（🟢）

### P5 — WebSocket IP hardcode
- 第 616 行 `const piIp = '192.168.100.30'` 需換場地就改程式碼
- 改為從 config 表讀取，管理員介面可設定

### P6 — `handleWsMsg()` 是空函式
- 多裝置同步目前完全無效
- 最小實作：收到 `patient_updated` 時 `loadPatients()` 再重繪

### P7b — QR snapshot、交班、物資管理
- 功能未動，維持原樣

### P9 — 語音快速建檔（Pi 5 離線辨識）
- 架構：手機錄音 → WebSocket 傳 Pi 5 → faster-whisper base 辨識 → 回傳文字 → 規則解析填欄位
- **P1–P8 完成後再做**

---

## 修改優先順序速查

| 優先 | 項目 | 狀態 | 時間點 |
|------|------|------|--------|
| 🔴 | P1 C 來源表單 | ❌ 待做 | 演習前 |
| 🔴 | P7 腕帶 QR 產生 | ❌ 待做 | 演習前 |
| 🔴 | P8 全域掃碼查詢 | ❌ 待做 | 演習前 |
| ✅ | P2 ID 重複 bug | 已修 v0.3.0 | — |
| 🟡 | P3 紅區容量 | 待決定方案 | 演習前確認 |
| 🟡 | P4 到院生命徵象 | ❌ 待做 | 演習前（時間允許） |
| 🟡 | Badge 定義 | 待決定 | 演習前確認 |
| ✅ | 治療評估 modal 重繪 | 已修 v0.3.2 | — |
| 🟢 | P5/P6/P9 | 待做 | 演習後 |

**Why:** 演習前開發的主要依據。
**How to apply:** 開始 medical PWA session 時先讀此記憶，確認哪些已修完、哪些仍待做。
