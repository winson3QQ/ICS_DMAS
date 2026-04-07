---
name: Medical PWA 功能進度
description: 歷次用戶回饋 P 項完成狀態、目前版號、待辦
type: project
---

## 目前版號

- 程式：`medical-v0.6.3-alpha`（git tag）
- 規格書：`v0.6`（medical_pwa_spec_v0_5.md，已更新 header）

## 已完成 P 項

| 版號 | 項目 |
|------|------|
| v0.5.x | P0-10 後送流程拆分（治療區一鍵後送，目的地移至後送區 ISBAR） |
| v0.5.x | P0-12 ISBAR B 欄自動預填治療摘要 |
| v0.5.x | P1-4 待評估佇列改 display_id 排序 |
| v0.5.5 | P1-5 年齡改數字輸入，`_ageToCode()` 換算識別碼，`source_age` 存原始數字 |
| v0.5.6/v0.5.8/v0.5.9 | P1-6 姓名欄選填，卡片/詳情頁顯示，加性別/年齡欄位 |
| v0.5.7 | P1-7 重評預填前次生命徵象與主訴 |
| v0.6.0 | P2-8 創傷評估加 MOI + 用藥史 + 過敏史（`tr-` 前綴 ID 避免與非創衝突） |
| v0.6.0 | P2-9 非創 SAMPLE 順序改 A→M→S→P→L→E |
| v0.6.1 | P2-11 ISBAR 醫院選單近到遠排序，priority 院所置頂加 ★ |
| v0.6.1～v0.6.3 | P3-14 物資編輯/停用（軟刪除灰顯可恢復）/JSON 匯入 |

## 待辦 P 項

| 優先 | 項目 |
|------|------|
| ⏸ | P0-3 簡化登入：帳號快選晶片 + 保留完整 PIN 驗證，方案確認中 |
| 🔴 | P3 紅區容量：`getRedSlotsFree()` 永遠 999，從 config 讀 `red_capacity` |
| 🟡 | P4 生命徵象分開：現場 MIST-S vs 到院 START 混用 |
| 🟡 | Badge 定義：分區 badge 待決定 |
| 🟢 | P5/P6/P7/P8/P9：Pi URL config、WS 同步、腕帶 QR、全域掃碼、語音建檔 |

## 技術注意事項

- 創傷的用藥/過敏 ID 使用 `tr-allergy-*` / `tr-sample-a` / `tr-sample-m`（與非創的 `allergy-*` / `sample-a` / `sample-m` 分開，兩個 section 同時在 DOM 中）
- `_confirmInModal(title, msg, confirmFnStr, cancelFnStr)` 第三參數必須是**字串**，不可傳 function。需要 async callback 時用 `window._pendingXxxId` 暫存再用 `doXxx()` 函式字串
- 設定 tab 只有角色 `=== '組長'` 才顯示（`showApp()` 第 838 行控制），Demo 模式不走 `showApp()` 所以設定 tab 不會出現
- 物資停用：`db.resources.update(id, { disabled: true })`，渲染時 `activeItems = items.filter(r => !r.disabled)`
