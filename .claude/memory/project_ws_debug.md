---
name: WSS 連線 debug 狀態（shelter PWA）
description: iOS zombie 連線問題，已排除假設，下一步：URL query string 追蹤 source
type: project
---

## 問題描述
Shelter PWA WebSocket 連線在 iOS 背景後回來時出現 zombie 狀態（連線看似存在但無回應）。

## 已排除假設
- 不是 server 端 keepalive 問題
- 不是 SSL 憑證問題

## 下一步
用 URL query string 區分連線來源（`?source=ios-fg`、`?source=ios-bg`），在 server log 追蹤哪個連線是 zombie。

**Why:** iOS 背景處理與桌面瀏覽器行為不同，需要明確識別連線來源才能定位問題。
**How to apply:** shelter PWA WebSocket debug 繼續時，先從 URL query string 追蹤方向切入。
