---
name: 開發與 Debug 紀律
description: 實作前先查平台/語言規格，debug 靠 log 不靠猜，兩軌版本命名規則，重要突破要 commit & push
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

### 2. 兩軌版本命名規則

本專案使用兩套獨立的版本號，**不可混用**：

#### 軌道一：程式版本（SemVer）
格式：`vMAJOR.MINOR.PATCH`，起點 `v0.1.0`，以 git tag 標記。

| 位號 | 觸發條件 | 範例 |
|------|---------|------|
| PATCH +1 | bug fix 完成，行為有改變 | v0.1.1 |
| MINOR +1 | 一個功能完整可用 | v0.2.0 |
| MAJOR +1 | 介面或資料格式有破壞性變更（Pi ↔ 指揮部 API、DB schema） | v1.0.0 |
| MAJOR=0 | 開發期，介面仍可能變動 | — |

Debug 版號（地端，不 commit）：`YYYY-MM-DD-vN`，隨時改，只用來追蹤執行路徑。

#### 軌道二：規格書版本（vX.Y）
格式：`vX.Y`（無 PATCH），各文件獨立編號，不跟隨程式 SemVer。

| 位號 | 觸發條件 |
|------|---------|
| Y +1 | 規格內容新增、修正、或對應程式里程碑更新 |
| X +1 | 規格架構重大改版（例如整合另一份規格、業務流程重構） |

**兩軌的對應關係：**
- 規格書 header 的「對應程式版本」欄記錄此規格版本對齊的程式 SemVer milestone。
- 規格書 changelog 中每一列須標注對應的程式里程碑（若已有對應 tag）或「規格先行」。
- 程式 bump 版號時，若規格書有連動異動，規格書也要同步進版。

---

### 3. 程式版號 bump checklist（缺一不可）

1. `SERVER_VERSION`（shelter_ws_server.js）
2. `PWA_VERSION`（shelter_pwa.html）
3. `CACHE_NAME`（sw.js，只要 PWA 資產有改就同步更新）
4. **規格書同步**：若有介面、資料格式、或功能行為變更，需更新對應規格文件，並在 changelog 加注程式里程碑
   - `shelter-pwa/docs/shelter_pwa_spec_v2_3.md`（收容組 PWA 規格，當前版本）
   - `command-dashboard/docs/指揮部儀表板設計規格_v1_1.md`（指揮部儀表板規格，當前版本）
   - `medical-pwa/docs/medical_pwa_spec_v0_3.md`（醫療組 PWA 規格，當前版本）
   - `medical-pwa/docs/醫療組SOP_20260323.md`（醫療組 SOP，當前版本）

**版號 bump 流程：**
```bash
# 平常：隨時 commit & push，不改版本號
git commit -m "fix: ..."
git push

# 決定這個狀態值得一個版號時：
# 1. 完成上方 checklist
# 2. commit + tag
git commit -m "chore: bump vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

**Why:** 兩軌版本分開，讓規格書可以在程式開發前先進版（規格先行），也讓程式里程碑能精確對應到當時生效的規格版本，方便跨機器換手與事後審計。

**How to apply:** 程式 bump 版號時，建議正確的 SemVer；規格書進版時，確認 changelog 有標注對應程式里程碑或「規格先行」。

---

### 4. Memory 更新必須同步 repo

寫入或修改任何 memory 檔案後，**立即**同步至 repo 的 `.claude/memory/`，並 commit & push。

```bash
cp ~/.claude/projects/-Users-3qq-Desktop-ICS-DMAS/memory/<檔名>.md \
   /Users/3qq/Desktop/ICS_DMAS/.claude/memory/<檔名>.md
git add .claude/memory/ && git commit -m "chore: 同步 memory — ..."
git push
```

**Why:** CLAUDE.md 明確規定 memory 存在 repo，不 push 則其他機器拿不到更新。只更新本機 `~/.claude/` 等於沒做。

**How to apply:** 每次呼叫 Write 或 Edit 寫 memory 檔案，下一步就是 cp + commit + push，不等使用者提醒。

---

### 5. 歡迎提升開發/debug 效率的建議
- 任何可增進開發或 debug 效率的工具、做法、架構改善，都可以主動提出。

**Why:** 使用者明確表示開放這類建議，不需要等被問。

**How to apply:** 在 code review、debug、實作討論中，若發現可改善效率的做法，主動說出來。
