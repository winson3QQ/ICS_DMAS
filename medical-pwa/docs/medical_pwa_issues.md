# medical_pwa.html — 問題清單與修改建議

> 版本：v0.3.48 / 規格 v0.4
> 整理日期：2026-03-31
> 原始清單基於 v0.2.0，持續更新中

---

## 背景說明

醫療組傷患來源分三種：

| 來源代碼 | 說明 | 資料狀況 |
|----------|------|---------|
| A | 前進組送入 | 有 MIST（QR 掃描或手動輸入） |
| B | 收容組轉介 | 已有登記資料 |
| C | 非前進組送入 | 可能有（自行走入）或完全沒有（他人抬入）資料 |

---

## ✅ 已完成

### P2 — `nextDisplayId()` 產生重複 ID（已修）
- 改為從 DB `orderBy('id').last()` 取最大序號，不再用 `_state.patients.length`
- ID 格式：`M007-MA`（含性別年齡代碼）

### 治療評估流程優化（v0.3.41）
- 選傷型改為 CSS show/hide，不重新 render
- 主訴/生命徵象文字不因選型別而消失
- 儲存鈕永遠可見，不需先選型別才出現

### 移區 triage_color 同步（v0.3.42）
- moveZone 同步更新 triage_color 並寫 retriage 記錄
- 移區 modal 顯示「→ 燈號同步更新」或「燈號不變」提示

### 安全威脅後送提醒（v0.3.43）
- 後送交接完成後，若有未結案安全威脅事件，寫入提醒記錄（patient_transferred_at、reminded_to）
- 事件卡與事件詳情均顯示橘色警示橫幅

### 傷患詳情欄位重排（v0.3.44–v0.3.45）
- 新順序：來源 → 安檢狀態 → 外觀特徵 → 建檔者 → 傷型 → 主訴 → 生命徵象 → 目前區域 → 處置 → 歷程

### UX 優化（v0.3.46–v0.3.48）
- 待後送卡加「✕ 取消後送」按鈕
- 刪除孤兒函式：openRetriage / saveRetriage / closeIncident
- 建檔、後送交接、事件結案三處加確認 modal（不可逆操作二次確認）
- 通報事件後直接開詳情，省去返回列表步驟

---

## 🔴 演習前必修

### ✅ P1 — 缺少「非前進組送入」的最少欄位表單（已完成）

**現況**
- 來源 C 按鈕標示為「🚶 自行抵達」，語意不完整
- 選 C 後沒有對應的表單區塊

**影響**
被他人抬入、無法溝通的傷患，沒有正確的建檔路徑。

**修改內容**

1. 按鈕改為「🙋 非前進組送入」
2. `renderIntakeForm()` 加入 C 來源區塊（送入方式、性別觀察、年齡段觀察、來源描述、主要傷況）
3. `doSubmitIntake()` 讀取 C 欄位（含 `arrival_mode`、`source_sex`、`source_age`）

> **【v0.5.0-alpha 已修】** `renderIntakeForm()` 的非B分支已包含安檢狀態、
> 性別/年齡觀察、外觀特徵描述，並直接進入 START 檢傷。
> C 來源建檔前強制填寫性別與年齡（行 1930 驗證）。

---

### P7 — 建檔後需產生醫療組腕帶 QR

**現況**
`doSubmitIntake()` 建檔成功後只顯示 toast 並返回儀表板，無 QR 產生步驟。

**影響**
後續移區、交班、後送時無法掃碼查詢傷患。

**修改內容**

1. `doSubmitIntake()` 成功後改呼叫 `openWristbandModal(displayId, color, qrPayload)`
2. QR payload：`{ id, color, issued_at }`（僅識別資訊）
3. `qrcode.js` 已在 `<script>` 載入，直接可用

```javascript
function openWristbandModal(displayId, color, qrPayload) {
  const colorLabel = { red:'🔴 紅', yellow:'🟡 黃', green:'🟢 綠', black:'⚫ 黑' };
  openModal('腕帶 QR Code',
    `<div style="text-align:center;padding:8px 0;">
      <div style="font-size:20px;font-weight:700;margin-bottom:4px;">${displayId}</div>
      <div style="font-size:14px;margin-bottom:16px;">${colorLabel[color]||color}</div>
      <div id="wristband-qr" style="display:inline-block;padding:12px;background:#fff;border-radius:8px;border:1px solid var(--border);"></div>
      <div style="font-size:12px;color:var(--text3);margin-top:10px;">列印或截圖後綁上傷患腕帶</div>
    </div>`,
    `<button class="btn btn-primary flex-1" onclick="closeModal();switchTab('dashboard')">✅ 完成，返回儀表板</button>`
  );
  setTimeout(() => {
    const el = document.getElementById('wristband-qr');
    if (el && window.QRCode)
      new QRCode(el, { text: qrPayload, width: 160, height: 160, correctLevel: QRCode.CorrectLevel.M });
  }, 50);
}
```

> **【演習不需要】** 腕帶識別採用顏色腕帶 + `display_id` 手寫方式。
> QR code 因折疊問題不適合腕帶，條碼腕帶需要熱感應印表機，演習前不具備此硬體。
> 護理員在 app 輸入 `display_id` 手動查詢傷患即可。

---

### P8 — 全域掃碼查詢傷患

**現況**
掃碼功能只在接收/檢傷流程中存在，無法在治療區或後送頁快速查詢傷患。

**修改內容**

1. Header 右側加 📷 掃碼按鈕（登出按鈕前）
2. `_state.scanMode` 新增（`null | 'lookup'`）
3. `handleQrResult()` 依 scanMode 分流：lookup 模式走 `handlePatientScanResult()`，intake 模式走原有 MIST 帶入
4. `handlePatientScanResult()` 從 DB 查 display_id，找到後呼叫 `openPatientDetail(patient.id)`

> **【演習不需要】** 全域掃碼查詢的前提是傷患身上有可掃描的識別碼。
> 演習採用 `display_id` 手動查詢，P8 與 P7 一同延後至硬體決定後再做。

---

## 🟡 演習前需決定

### P3 — `getRedSlotsFree()` 永遠回傳 999
- 紅區滿載警報永遠不觸發
- **決定方案**：從 config 讀取 `red_capacity`，預設值 5，管理員可在設定頁調整
- 非架構問題，一行修正即可

### P4 — 現場生命徵象 vs 到院生命徵象混用
- patient card 顯示的是現場 MIST-S 數值，非到院 START 數值
- 修正：DB 加 `arrival_vitals` 欄位，card 分兩行顯示
- **尚未實作**

### Badge 定義
- 接收 tab badge → 建議移除（無需提醒）
- 分區 tab badge → 建議改為「待評估 + 逾時合計」
- **尚未決定**

---

## 🟢 演習後再做

### P5 — WebSocket IP hardcode
- 第 616 行 `const piIp = '192.168.100.30'`，換場地需改程式碼
- 改為 config 表 + 管理員介面設定

### P6 — `handleWsMsg()` 是空函式
- 多裝置同步目前完全無效
- 最小實作：收 `patient_updated` 後 `loadPatients()` 再重繪

### P9 — 語音快速建檔（Pi 5 離線辨識）
- 架構：手機錄音 → WebSocket → Pi 5 faster-whisper → 回傳文字 → 規則解析填欄位
- P1–P8 完成後再做

---

## 修改優先順序速查

| 優先 | 項目 | 狀態 |
|------|------|------|
| ✅ | P2 ID 重複 | 已修 |
| ✅ | UX 優化（v0.3.41–v0.3.48） | 已完成 |
| ✅ | P1 C 來源表單 | 已完成（v0.5.0-alpha） |
| 🟢 | P7 腕帶 QR | 演習不需要，display_id 手寫即可 |
| 🟢 | P8 全域掃碼 | 演習不需要，同 P7 |
| 🔴 | P3 紅區容量 | 小修：從 config 讀 red_capacity |
| 🟡 | P4 生命徵象分開 | 待做 |
| 🟡 | Badge 定義 | 待決定 |
| 🟢 | P5 / P6 / P9 | 演習後 |
