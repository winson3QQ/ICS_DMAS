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

### 2. 版本號與 git commit 解耦

**原則：git commit 隨時 push，版號只在值得標記時才動。**

**版本號格式：SemVer** — `vMAJOR.MINOR.PATCH`（起點 `v0.1.0`）
- `PATCH` +1：bug fix 完成，行為有改變
- `MINOR` +1：一個功能完整可用
- `MAJOR` +1：介面或資料格式有破壞性變更（Pi ↔ 指揮部 API、DB schema 等）
- `MAJOR=0`：開發期，介面仍可能變動

**Debug 版號（地端，不 commit）：** `YYYY-MM-DD-vN`，隨時改，用來追蹤執行路徑。

**版號 bump checklist（缺一不可）：**
1. `SERVER_VERSION`（shelter_ws_server.js）
2. `PWA_VERSION`（shelter_pwa.html）
3. `CACHE_NAME`（sw.js，只要 PWA 資產有改就同步更新）
4. **規格書同步**：若有介面、資料格式、或功能行為變更，需更新對應規格文件
   - `docs/民防輔助感知系統__規格書_v1_3.docx`（系統總規格）
   - `docs/security_network_spec_v1.0.md`（安全與網路架構）
   - `shelter-pwa/docs/shelter_pwa_spec_v2_2.docx`（收容組 PWA 規格）
   - `command-dashboard/docs/指揮部儀表板設計規格_v1_1.docx`（指揮部儀表板規格）
   - `medical-pwa/docs/medical_pwa_spec_v0_2.docx`（醫療組 PWA 規格）

**版號 bump 流程：**
```bash
# 平常：隨時 commit & push，不改版本號
git commit -m "fix: ..."
git push

# 決定這個狀態值得一個版號時：
# 1. 完成上方 checklist（四項）
# 2. commit + tag
git commit -m "chore: bump vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

**Why:** 頻繁 push 保留進展，版號有語意（讓人知道這個版本的成熟度和變動幅度），git tag 讓版本可回溯。

**How to apply:** 使用者決定 bump 版號時，建議正確的 SemVer 版號，提醒對齊三個常數，並執行 tag。

---

### 3. 歡迎提升開發/debug 效率的建議
- 任何可增進開發或 debug 效率的工具、做法、架構改善，都可以主動提出。

**Why:** 使用者明確表示開放這類建議，不需要等被問。

**How to apply:** 在 code review、debug、實作討論中，若發現可改善效率的做法，主動說出來。
