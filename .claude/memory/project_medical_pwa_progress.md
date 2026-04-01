---
name: medical PWA 開發進度（2026-04-01，v0.3.53）
description: medical-pwa 目前架構狀態、版本、關鍵函式、待處理事項快速參考
type: project
---

## 目前版本：v0.3.53

- 檔案：`medical-pwa/public/medical_pwa.html`（單一檔案，CSS/HTML/JS 全 inline）
- SW：`medical-pwa/public/sw.js`，CACHE_NAME = `medical-pwa-v0.3.49`（需隨版號更新）
- 預覽：`python3 -m http.server 8001`，目錄 `medical-pwa/public/`

---

## 架構重點

- **DB version 4**：patients 表含 `source_sex`, `source_age`, `care_status`, `triage_color`, `current_zone`
- **care_status**：`'triaged'` → `'assessed'` → `'pending_transfer'`
- **State 欄位**：`intakeSecurity`, `intakeSex`, `intakeAge`, `intakeDraftId`, `_treatState`, `_pendingHandoff`, `_pendingIncidentClose`
- **triage lock**：`canPickTriageColor()` 三重鎖 → `renderTriageColorPicker()` 局部重繪
- **modal 系統**：`#modal-overlay`（hidden/visible），`_confirmInModal()` 替換 modal 內容做確認對話
- **idle timer**：`IDLE_WARN_S=90s`, `IDLE_LOCK_S=30s`

---

## 已完成功能摘要（截至 v0.3.53）

| 版本區間 | 重點 |
|----------|------|
| v0.3.0–v0.3.3 | Intake 強化、ID 格式、START lock、治療評估 modal bug 修正 |
| v0.3.41 | 治療評估 show/hide，不重繪 modal |
| v0.3.42–v0.3.46 | moveZone 同步燈號、安全威脅後送提醒、傷患詳情欄位重排、取消後送 |
| v0.3.47–v0.3.48 | 不可逆操作確認 modal、事件建立直開詳情 |
| v0.3.49 | title 動態帶入 PWA_VERSION |
| v0.3.50 | START 改直排、ISBAR 外觀特徵補填 |
| v0.3.52–v0.3.53 | 登入頁臂章、內頁紅十字 SVG banner、PIN 提示統一 |

---

## 演習前待做（P1/P7/P8）

- **P1**：C 來源表單（「非前進組送入」選項下加表單欄位）
- **P7**：建檔後開 openWristbandModal()，產生腕帶 QR（qrcode.js 已載入）
- **P8**：Header 加 📷 掃碼按鈕，_state.scanMode 分流查詢

**Why:** 跨機器作業快速恢復用。開始 session 前先 git pull 確認版號，再繼續 P1/P7/P8。
**How to apply:** 版號改動必須同步更新 PWA_VERSION 常數 + sw.js CACHE_NAME，兩者缺一不可。
