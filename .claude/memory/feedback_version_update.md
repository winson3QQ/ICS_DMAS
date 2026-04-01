---
name: 版本編號規則
description: PWA 版本編號格式與 milestone 進版規則
type: feedback
---

每次改動後直接遞增末位版號（x.x.NN），不詢問使用者。

版本格式：`x.x.NN`（如 v0.3.08、v0.3.09…）

**Why:** 在確認進入 milestone 前，版號停在 x.x.NN 格式持續累積。只有使用者明確說「進版」或確認 milestone 完成，才升級到 x.(N+1).0。

**How to apply:** 改任何程式後直接 bump 末位數字。不要因為功能完整就自行升主版號。等使用者提醒。同步更新 sw.js 的 CACHE_NAME。
