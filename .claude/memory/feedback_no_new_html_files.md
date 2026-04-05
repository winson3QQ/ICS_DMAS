---
name: HTML 不開新檔，原地改版
description: 儀表板 HTML 不要每次生新檔案（v13→v14→v15），用版號常數區分版本
type: feedback
---

HTML 不要每次開新檔案（staff_v12.html → staff_v13.html → staff_v14.html），直接在原檔改版，用 JS 常數（如 `cmd-v0.4.0`）和 git commit 區分版本。跟 medical_pwa.html、shelter_pwa.html 做法一致。

**Why:** 每次開新檔會造成檔案膨脹，舊檔案堆積。PWA 從來不這樣做。
**How to apply:** 指揮部儀表板固定用 `staff_v14.html`（或未來重新命名），版號用 title + `.h-ver` 常數控制。
