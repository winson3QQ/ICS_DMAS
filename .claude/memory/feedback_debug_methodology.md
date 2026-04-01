---
name: debug 方法論
description: 根據 log/文件/公開資料再擬計畫；推論部分要明確標示，不能當事實陳述
type: feedback
---

debug 順序：先查平台規格與公開資料 → 再看 log → 再擬計畫。不能只看 log 就直接推斷原因。

**Why:** 平台本身的設計規則（iOS/Android/瀏覽器行為）比 log 更基礎。若基礎不清楚，log 解讀會方向錯誤。
**How to apply:** 回覆中推論要標示「推論：」，事實要有依據（規格書、MDN、公開 pcap）。不確定就說不確定，不填補猜測。
