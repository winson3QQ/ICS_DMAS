---
name: 開發與 Debug 紀律
description: 實作前先查平台/語言規格，debug 靠 log 不靠猜，版本流水號，重要突破要 commit & push
type: feedback
---

## 規則

### 1. 先查規格，再實作或推論
- 實作前：先了解目標軟硬體平台（Raspberry Pi、iOS、Node.js、FastAPI 等）及使用語言的規格與特性，不得逕行推理。
- 參考業界規則（RFC、MDN、官方文件）後再開發。
- Debug 時：**不猜**。先把 debug level 做好，確認執行路徑後，結合平台/語言規格推理可能原因。

**Why:** 避免因平台差異（例如 iOS WebSocket 行為、Node.js TLS 驗證）產生錯誤假設，浪費時間在猜測上。

**How to apply:** 每次遇到 bug 或新功能，先問「這個平台/語言在這個情境下的規格是什麼？」，找到規格依據後再推論原因或選擇實作方式。

---

### 2. 雙層版本號 + Milestone 才 commit & push

**雙層版本號：**
| 層 | 用途 | 格式 | 說明 |
|----|------|------|------|
| Debug | 地端追蹤執行路徑 | `YYYY-MM-DD-vN` | 隨時改，不 commit，N 每次 debug 遞增 |
| Milestone | 正式 commit & push 的版號 | `v001`, `v002`, ... | 功能/修復完成後統一更新，從 v001 開始 |

**Commit 前 checklist（三個必須一致才 commit）：**
1. `SERVER_VERSION`（shelter_ws_server.js）更新為 milestone 版號
2. `PWA_VERSION`（shelter_pwa.html）同步
3. `CACHE_NAME`（sw.js）只要 PWA 資產有改就 +0.1（觸發 iOS/Safari 強制更新快取）

**Why:** Debug 版號是工具，不是歷史；milestone 版號才是 source of truth。地端開發時版號隨意，commit 時對齊，避免版號混亂。

**How to apply:** 完成里程碑時提醒使用者對齊三個版本常數再 commit & push，並給出建議的下一個版號（vNNN+1）。

---

### 3. 歡迎提升開發/debug 效率的建議
- 任何可增進開發或 debug 效率的工具、做法、架構改善，都可以主動提出。

**Why:** 使用者明確表示開放這類建議，不需要等被問。

**How to apply:** 在 code review、debug、實作討論中，若發現可改善效率的做法，主動說出來。
