---
name: debug 紀律規則
description: 加 log 時必須同步更新版號，讓使用者能確認跑的是新版
type: feedback
---

每次加 log 或修改後，必須同步遞增 PWA_VERSION（或 SERVER_VERSION），並更新 sw.js CACHE_NAME。

**Why:** 若版號沒更新，使用者無法確認瀏覽器跑的是新版還是快取舊版，debug 會對錯目標。
**How to apply:** 任何改動 → 先改版號 → 再 commit。版號改動是必要步驟，不是可選步驟。
