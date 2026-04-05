---
name: 指揮部儀表板 Wave 路線圖
description: command-dashboard 五個 Wave 的開發路線圖及各 Wave 版號對應
type: project
---

指揮部儀表板開發分 5 個 Wave：

| Wave | 內容 | 版號 | 狀態 |
|------|------|------|------|
| 1 | 三區佈局 + 雙地圖(站內/站外 tab) + calc_engine 基礎智慧(burn rate, comm health, output monitor) | cmd-v0.2.0 | ✅ 完成 (commit 2d17802) |
| 2 | 互動地圖事件輸入(23種類型) + Decision Countdown + DCI + staff API | cmd-v0.3.0 | ✅ 完成 (commit 8db0fe6) |
| 3 | Escalation/De-escalation 升降級 + 地圖流向箭頭動畫 + 規格缺口補齊 + 事件地圖生命週期 + 佈局重構 | cmd-v0.4.0~v0.5.x | 🔧 進行中 |
| 4 | Operator Fatigue 操作者疲勞偵測（需改 PWA） | cmd-v0.6.0 | 待做 |
| 5 | Pi Read-Only API + L3/L4 地圖鑽探 | cmd-v0.7.0 | 待做 |

## Wave 3 已完成版本

### ✅ v0.4.0~v0.4.2 (commit 5d084f8)
- calc_engine `escalation_check()` — 5 升級 + 5 降級規則
- 新鮮度四色圓點、通訊健康圓點（收容+醫療）
- Decision 完整生命週期 UI（升級/結案 + 已裁示頁籤 + chain grouping）
- 事件類型對齊 PWA、events 表加 location_zone_id
- 據點專屬 modal（L3 鑽探：📊 數據 / 📋 事件 / ⚖ 裁示）
- 事件處置對齊 shelter PWA（處置紀錄 + 追加 + 結案須有紀錄）
- events 表加 notes JSON + assigned_to + POST /api/events/{id}/notes
- 版號統一管理 CMD_VERSION、HTML rename → commander_dashboard.html

### ✅ v0.4.3~v0.4.9 (commit b8566ad)
- 事件 marker 自動建 DB（編輯模式新增非收容/醫療 marker → POST /api/events）
- 事件編號 EV-MMDD-NNN（db.py _generate_event_code）
- response_deadline 依嚴重度（critical=10分/warning=30分/info=60分）
- 處置 modal（編號 + severity + 倒數 + 紀錄 + 追加 + 結案）
- Zone C 事件追蹤區塊
- 結案 marker 灰色半透明（不消失）
- 單/雙擊衝突修正、重複渲染移除

### ✅ v0.5.0 (commit 8d7da77)
- 佈局重構：左側 3+2 切換（態勢/資源）+ 右側事件追蹤 60% + 待裁示 40%
- Zone C 精簡（物資/容量/人力倒數 + 升降級）

### ✅ v0.5.1~v0.5.7（未 commit）
- edit-bar 重設計：提示移除、5 組按鈕（前進/安全/收容/醫療/指揮部）+ 事件下拉
- 放置流程：選組別→選事件→點地圖（3 click 零打字）+ 放完自動儲存關閉
- SVG icon 重繪：event（三角 currentColor）+ threat（人形 currentColor）+ pin（灰色據點）
- 事件 marker 顏色動態：evt-new(黃) → evt-warn(橘) → evt-overdue(紅閃) → evt-resolved(灰)
- 各組按鈕專屬色（前進橘/安全藍/收容黃/醫療紅/指揮部綠），未選中等亮度、選取全亮
- EVENT_CATEGORIES 五組事件歸納（forward 5 + security 5 + shelter 6 + medical 6 + command 4）
- 處置 modal：追加/處理中/結案 同一排、⏱可點擊重設 deadline
- ⚙ 齒輪移到底欄最右

## 🔲 v0.5.x 待做（下次 session 繼續）

### UX 改善
- 事件/裁示面板展開 5:5（點右側面板向左展開覆蓋地圖一半）
- 結案事件灰色仍可點擊查看歷程（目前 evt-resolved CSS 有，但 marker 是否可點待驗）
- ⏱ 重設 deadline 後端 API（目前只追加 notes，沒有實際更新 DB 的 response_deadline）
- 組別按鈕顏色微調（使用者反饋顏色不對，需對照實際螢幕確認）

### 功能補完
- 地圖流向箭頭填入實際 flows 資料 + 動態粗度
- 物資 burn rate 預測線（展開 sparkline 疊加虛線到 Y=0）
- 斷線空洞圖表標注（灰色半透明區段）
- 前端/後端計算統一（移除前端 rate()/slope() 重複）
- 決策主題合併卡片（同 primary_event_id 合併）

## 四層資訊架構（地圖鑽探）

| 層 | 用途 | 資料來源 | 狀態 |
|---|------|---------|------|
| L1 | Zone A 態勢速讀（0.5s 掃一眼） | calc_engine 聚合 | Wave 1 建立 |
| L2 | Zone B 地圖 + sparkline 趨勢 | 快照歷史 100 筆 | Wave 1 建立 |
| L3 | 點擊據點 → 詳情 modal + Pi 查詢 | 快照 + Pi API | v0.4.1 部分實作，Pi API 留 Wave 5 |
| L4 | modal 中點擊個別記錄 → 完整資料 | Pi API | Wave 5 |

## Wave 3 升降級規則（已實作在 calc_engine.escalation_check）

| 升級信號 | 降級信號 |
|---------|---------|
| 收容率 > 80% 持續 30 分鐘 | 收容率 < 50% 持續 1 小時 |
| Red 傷患佔比突然上升 | 無新 Red 傷患超過 45 分鐘 |
| 未結事件 > 5 且持續增加 | 未結事件歸零 |
| staff_ratio > 8（超載） | staff_ratio < 3（有餘裕） |
| 物資 burn rate 暗示 2 小時內耗盡 | 物資充足，消耗穩定 |

## 事件放置流程（v0.5.1+ 設計）

```
底欄常駐：[前進][安全][收容][醫療][指揮部] [事件▾]  ── [⚙]
  1. 點組別按鈕（亮起）→ 事件下拉啟用
  2. 選事件類型 → 游標變十字
  3. 點地圖 → marker 放置 + 自動建 DB 事件 + 自動儲存 + 自動退出放置模式
```

## 技術備忘
- HTML 檔名固定 `commander_dashboard.html`（見 feedback_no_new_html_files.md）
- 版號由 `<script>const CMD_VERSION='vX.Y.Z';</script>` 控制（head 第 6 行）
- 啟動：`cd command-dashboard && set PYTHONPATH=src && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
- 測試資料：`python tests/gen_test_snapshots.py --batch`
- DB schema 變更需 `del data\ics.db`

**Why:** 路線圖在多次對話中演進，需完整記錄避免遺失。
**How to apply:** 開發指揮部儀表板時，依此文件確認進度和待做項目。
