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
| 3 | Escalation/De-escalation 升降級 + 地圖流向箭頭動畫 | cmd-v0.4.0 | 待做 |
| 4 | Operator Fatigue 操作者疲勞偵測（需改 PWA） | cmd-v0.5.0 | 待做 |
| 5 | Pi Read-Only API + L3/L4 地圖鑽探 | cmd-v0.6.0 | 待做 |

**Wave 2 待補：** 事件類型尚未對齊 PWA 的 INCIDENT_LABELS（shelter 23種 / medical 7種）

**Wave 3 追加項目（規格缺口盤點後歸入）：**
- 新鮮度四色圓點視覺化（§5）
- Decision 完整生命週期 UI（revision/escalation/closure）（§9）
- 已裁示歸檔 UI（驗收 #7）
- 決策主題合併卡片（驗收 #8）
- 通訊健康視覺化（七大指標補完）
- 物資 burn rate 趨勢圖（七大指標補完）
- 斷線空洞圖表標注（驗收 #13）
- 事件地圖生命週期（動態 marker + 右鍵歷程 + 結案歸檔）
- 前端/後端計算統一（移除前端 rate()/slope() 重複）

## 四層資訊架構（地圖鑽探）

| 層 | 用途 | 資料來源 | 狀態 |
|---|------|---------|------|
| L1 | Zone A 態勢速讀（0.5s 掃一眼） | calc_engine 聚合 | Wave 1 建立 |
| L2 | Zone B 地圖 + sparkline 趨勢 | 快照歷史 100 筆 | Wave 1 建立 |
| L3 | 點擊據點 → 詳情 modal + Pi 查詢 | 快照 + Pi API | Wave 5 |
| L4 | modal 中點擊個別記錄 → 完整資料 | Pi API | Wave 5 |

L3/L4 是 Wave 5「Pi Read-Only API + L3/L4 地圖鑽探」的核心內容。

## Wave 3 升降級規則（原始定義）

| 升級信號 | 降級信號 |
|---------|---------|
| 收容率 > 80% 持續 30 分鐘 | 收容率 < 50% 持續 1 小時 |
| Red 傷患佔比突然上升 | 無新 Red 傷患超過 45 分鐘 |
| 未結事件 > 5 且持續增加 | 未結事件歸零 |
| staff_ratio > 8（超載） | staff_ratio < 3（有餘裕） |
| 物資 burn rate 暗示 2 小時內耗盡 | 物資充足，消耗穩定 |

**Why:** 路線圖在先前對話中規劃，但未存入 memory 導致遺失。
**How to apply:** 開發指揮部儀表板時，依 Wave 順序推進，不跳號。
