---
name: medical PWA 待處理問題清單（2026-04-01 更新至 v0.3.53）
description: medical_pwa.html 已知問題、優先順序、修改方向，演習前必修 P1/P7/P8
type: project
---

## ✅ 已完成（v0.3.34–v0.3.53）

- **P2 ID 重複**：nextDisplayId 改從 DB max 取序號，格式 M007-MA（含性別年齡代碼）
- **治療評估 modal 重繪**：選傷型改為 show/hide，不重新 render，文字不消失，儲存鈕永遠可見（v0.3.41）
- **移區 triage_color 同步**：moveZone 同步更新燈號並寫 retriage 記錄（v0.3.42/v0.3.46）
- **安全威脅後送提醒**：交接完成時若有未結案安全威脅，寫入提醒記錄，事件卡顯示橘色警示（v0.3.43）
- **傷患詳情欄位重排**：來源→安檢狀態→外觀特徵→建檔者→傷型→主訴→生命徵象→目前區域→處置（v0.3.44/v0.3.45）
- **取消後送**：待後送卡加「✕ 取消」按鈕（cancelTransfer），v0.3.46
- **不可逆操作確認對話**：建檔/後送交接/事件結案三處加確認 modal（v0.3.47）
- **通報事件直開詳情**：createIncident 後直接開 openIncidentDetail（v0.3.48）
- **title 動態帶入版號**：`<title>` 改由 JS 從 PWA_VERSION 設定（v0.3.49）
- **START grid 改直排**：2×2 改單欄，避免手機裁切（v0.3.50）
- **ISBAR 補填外觀特徵**：外觀特徵為空時顯示警示框+補填欄，交接時存回 DB（v0.3.50）
- **登入頁改臂章圖**：logo 改為 Taiwan Civil Defense 臂章（v0.3.52）
- **內頁 banner 改紅十字 SVG**：取代臂章，flex 對齊（v0.3.52/v0.3.53）
- **PIN 提示統一**：全部統一為「4-6 位數字」，移除「僅限數字」冗餘文字（v0.3.52/v0.3.53）

---

## 演習前必修（🔴）

### P1 — 缺少「非前進組送入」C 來源表單
- 按鈕標籤「🚶 自行抵達」語意不完整，應改為「🙋 非前進組送入」
- 選 C 後沒有表單區塊：需加入送入方式、性別（觀察）、年齡段（觀察）、來源描述、主要傷況（觀察）
- submitIntake() 需讀取對應欄位，detail 中已有 source_sex/source_age 欄位

### P7 — 建檔後需產生醫療組腕帶 QR
- 前進組 QR 掃描後任務結束，醫療組需產生新 QR 綁腕帶
- 建檔成功後（含確認 modal 關閉後）開啟 openWristbandModal()
- QR payload：{ id, color, issued_at }（僅識別資訊）
- qrcode.js 已在 `<script>` 載入，直接可用
- 注意：建檔現在有確認 modal，QR 在 doSubmitIntake() 成功後觸發

### P8 — 全域掃碼查詢傷患
- Header 右側加 📷 掃碼按鈕（登出前）
- _state.scanMode: null | 'lookup'
- handleQrResult() 依 scanMode 分流

---

## 演習前需決定（🟡）

### P3 — getRedSlotsFree() 永遠回傳 999
- 紅區滿載警報永遠不觸發
- 方案 A：固定常數 RED_ZONE_CAPACITY = 5（最快）
- 方案 B：從 config 表讀取，管理員可設定
- **尚未決定方案**

### P4 — MIST 現場生命徵象 vs START 到院生命徵象混用
- patient card 顯示的是現場 MIST-S 數值，需分兩行顯示現場/到院
- **尚未實作**

### Badge 定義
- 接收 tab badge → 建議移除
- 分區 tab badge → 建議改為「待評估 + 逾時合計」
- **尚未決定**

---

## 演習後再做（🟢）

- P5：WebSocket IP 設定化（hardcode）
- P6：handleWsMsg() 實作（目前空函式）
- P9：語音快速建檔（Pi 5 faster-whisper）

---

## 修改優先順序速查

| 優先 | 項目 | 狀態 |
|------|------|------|
| 🔴 | P1 C 來源表單 | **待做** |
| 🔴 | P7 腕帶 QR | **待做** |
| 🔴 | P8 全域掃碼 | **待做** |
| ✅ | P2 ID 重複 | 已修 |
| 🟡 | P3 紅區容量 | 待決定方案 |
| 🟡 | P4 生命徵象分開 | 待做 |
| 🟡 | Badge 定義 | 待決定 |
| 🟢 | P5/P6/P9 | 演習後 |

**Why:** v0.3.53 完成大規模 UX 優化，演習前剩 P1/P7/P8 三項核心功能待補。
**How to apply:** 開始 medical PWA session 時先讀此記憶，確認哪些已修完、哪些仍待做。
