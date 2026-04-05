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
| 3 | Escalation/De-escalation 升降級 + 地圖流向箭頭動畫 + 規格缺口補齊 | cmd-v0.4.x | 🔧 進行中 |
| 4 | Operator Fatigue 操作者疲勞偵測（需改 PWA） | cmd-v0.5.0 | 待做 |
| 5 | Pi Read-Only API + L3/L4 地圖鑽探 | cmd-v0.6.0 | 待做 |

## Wave 3 進度明細

### ✅ v0.4.0 已完成（未 commit）
- calc_engine `escalation_check()` — 5 升級 + 5 降級規則
- 地圖流向箭頭 SVG + 動畫框架（renderFlows，map_config flows:[] 結構已有，缺實際資料）
- 新鮮度四色圓點（地圖 marker 右上角）
- 通訊健康圓點（Zone A，只收容+醫療兩組，14px + 標籤）
- Decision 完整生命週期 UI（升級/結案按鈕 + 已裁示頁籤）
- Decision chain grouping（按 primary_event_id 分組）
- 事件地圖 marker（open_events_on_map）
- 事件類型對齊 PWA（shelter 23種 / medical 7種）
- events 表加 location_zone_id
- 容量倒數改用 server calc
- HTML rename → commander_dashboard.html
- gen_test_snapshots.py 新增 forward + security 快照

### ✅ v0.4.1 已完成（未 commit）
- 據點專屬 modal（L3 鑽探 — 頁籤：📊 數據 / 📋 事件 / ⚖ 裁示）
- 收容/醫療 → 預設「數據」頁籤；其他 → 預設「事件」頁籤
- 非 node_type 據點也可雙擊開 modal

### ✅ v0.4.2 已完成（未 commit）
- 版號統一管理：head 第 6 行 `CMD_VERSION` 常數，對齊 shelter/medical 的 PWA_VERSION 做法
- 通訊圓點加大 14px + 文字標籤（收容/醫療）
- 「收容34人 / 醫療11人」加單位
- Sparkline 展開字體全面放大（title 14px, value 16px, legend 11px, 軸標 11px）
- 事件頁籤對齊 shelter PWA 處置模式（處置紀錄列表 + 追加紀錄 + 結案前須有紀錄）
- 後端 events 表加 notes JSON + assigned_to + POST /api/events/{id}/notes API
- Modal icon 繼承據點 SVG icon

### 🔲 v0.4.3 待做
- **事件 marker 自動建 DB**：編輯模式新增非收容/醫療 marker 時，自動 POST /api/events 建一筆事件
- **事件編號**：`EV-MMDD-NNN` 格式（DB 用 UUID PK + event_code 顯示欄位）
- **事件處置 modal**：雙擊事件 marker 直接開處置 modal（不走 zone modal），對齊 PWA 的 openIncidentModal
- **倒數計時**：每個事件有 response_deadline_min（依嚴重度：critical=10分/warning=30分/info=60分），超時 icon 閃紅 + Zone C 提示
- **Zone C 事件追蹤**：顯示所有 open/in_progress 事件列表，有編號可點
- **結案 → marker 消失**：event status=resolved 時，地圖 marker 移除

### 🔲 Wave 3 剩餘（v0.4.x 後續 PATCH）
- 物資 burn rate 預測線（展開 sparkline 時疊加虛線到 Y=0）
- 斷線空洞圖表標注（灰色半透明區段）
- 前端/後端計算統一（移除前端 rate()/slope() 重複）
- 地圖流向箭頭填入實際 flows 資料 + 動態粗度
- 決策主題合併卡片（同 primary_event_id 的多筆 decision 合併為一張卡片展開歷程）

## 四層資訊架構（地圖鑽探）

| 層 | 用途 | 資料來源 | 狀態 |
|---|------|---------|------|
| L1 | Zone A 態勢速讀（0.5s 掃一眼） | calc_engine 聚合 | Wave 1 建立 |
| L2 | Zone B 地圖 + sparkline 趨勢 | 快照歷史 100 筆 | Wave 1 建立 |
| L3 | 點擊據點 → 詳情 modal + Pi 查詢 | 快照 + Pi API | v0.4.1 部分實作（指揮部 DB 資料），Pi API 留 Wave 5 |
| L4 | modal 中點擊個別記錄 → 完整資料 | Pi API | Wave 5 |

## Wave 3 升降級規則（已實作在 calc_engine.escalation_check）

| 升級信號 | 降級信號 |
|---------|---------|
| 收容率 > 80% 持續 30 分鐘 | 收容率 < 50% 持續 1 小時 |
| Red 傷患佔比突然上升 | 無新 Red 傷患超過 45 分鐘 |
| 未結事件 > 5 且持續增加 | 未結事件歸零 |
| staff_ratio > 8（超載） | staff_ratio < 3（有餘裕） |
| 物資 burn rate 暗示 2 小時內耗盡 | 物資充足，消耗穩定 |

## 事件地圖生命週期（v0.4.3 設計）

```
編輯模式放 marker（非收容/醫療類）
  → 自動建 event（EV-MMDD-NNN）+ 綁 location_zone_id
  → 地圖顯示 ⚠️ marker + 倒數計時
  → 雙擊 → 處置 modal（紀錄、狀態、結案）
  → 結案 → marker 消失 → 歸檔
```

## 技術備忘
- HTML 檔名固定 `commander_dashboard.html`，不再開新檔（見 feedback_no_new_html_files.md）
- 版號統一由 `<script>const CMD_VERSION='vX.Y.Z';</script>` 控制（head 第 6 行）
- 啟動指令：`cd command-dashboard && set PYTHONPATH=src && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`（Windows CMD）
- 測試資料：`python tests/gen_test_snapshots.py --batch`
- DB 有 schema 變更時需先 `del data\ics.db`

**Why:** 路線圖在先前對話中規劃，多次補充後需完整記錄避免遺失。
**How to apply:** 開發指揮部儀表板時，依此文件確認進度和待做項目。
