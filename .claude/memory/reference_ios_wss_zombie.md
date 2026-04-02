---
name: iOS WSS Happy Eyeballs zombie 參考
description: iOS Safari WSS 雙連線 zombie 的根因、已排除假設、設計決策，避免重複踩坑
type: reference
---

## 根本原因（pcap 確認）

iOS URLSession Happy Eyeballs 同時開兩條 TCP/WSS 連線（間隔 27-31ms）：
- 第一條（zombie）：TLS Finished 和 HTTP Upgrade 分開送
- 第二條（success）：Finished+Upgrade 同一個 packet
- iOS 在第一條 HTTP 101 到達前已選第二條；第一條 TCP 保持但 JS onopen 永不觸發

## 設計決策（仍在程式碼中生效）

| 決策 | 原因 |
|------|------|
| zombie 只 log 不 close/terminate | terminate(RST) 破壞整個 connection group → 無限 retry；close(Close frame) 破壞飛航恢復自動重連 |
| CONNECT_TIMEOUT 2s | 讓 zombie 自然被 client timeout 清除 |
| visibilitychange delay 100ms | 給 iOS 時間完成 TLS，不打斷 CONNECTING |
| `_connectedAt` < 2s skip | 防止 reload 後 visibilitychange 誤判為需要重連 |
| switchRole 不 reload | soft logout 保持 WS 連線，避免觸發 zombie |

## 已排除假設（不要再試）

1. OCSP revocation check — 不是原因
2. serviceWorker.register 阻塞 — 不是原因
3. CONNECT_TIMEOUT 太短（舊的「12-22s TLS」是誤判，實際是 zombie 累積）
4. perMessageDeflate — ws 預設即 false
5. visibilitychange 打斷 CONNECTING — 已用 delay 解決
6. ws.terminate() 清 zombie — 破壞 Happy Eyeballs
7. ws.close() 清 zombie — 破壞飛航恢復

## 未解限制

飛航/背景回來有時較慢，iOS visibilitychange/online 事件觸發時機不穩定，使用者有時仍需刷螢幕。
