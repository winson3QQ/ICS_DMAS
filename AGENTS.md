# AGENTS.md — ICS_DMAS Agent Operating Rules

> **目的**：所有 AI agent（Matrix Steward、Security Review、Close Verdict、Implementation Auditor、Claude Code）在此文件定義的規則下運作。
> **最高原則**：GitHub Issue 是執行記錄。Matrix Tab 2 是技術映射真相。ROADMAP.md 是人類視角（Tab 1 鏡像）。

---

## 命名慣例（Naming Convention）

### 三層架構 — 對外只用這三種東西

| 層級 | 名稱 | 格式 | 範例 |
|------|------|------|------|
| 1 | Edition | 英文名稱 | Demo · Exercise Pro · GovOps · Tactical |
| 2 | Release | SemVer | `v2.1.0` |
| 3 | Item | GitHub Issue# + 短標題 | `#8 Fix — WS pre-auth gate` |

Item 類型：
- **Fix** — 安全修補、bug fix、gap 解除（有 P0/P1/P2 label）
- **Feature** — 新功能、新能力
- Claims 是 Release 的**輸出**，不是 Item。由 Matrix Steward 在 Issue 關閉後從 matrix 衍生。

### 所有內部複雜性住在 Matrix Tab 2
CAP、GAP、NIST、Cx、Wave、GP、maturity level 等技術細節全在 matrix.md Tab 2。
Agent 讀 matrix，Human 看 ROADMAP.md（Tab 1 鏡像）。
**任何對外文件、PR title、Issue title 只使用三層架構，不出現 CAP/GAP/Cx 等術語。**

### Issue 標題格式
```
[Fix|Feature] — [短標題] · [Edition] / [Release]
範例：Fix — WebSocket pre-auth gate · Exercise Pro / v2.1.0
```

### Branch 命名
```
fix/issue-NN-short-title      （Fix 類 Issue）
feat/issue-NN-short-title     （Feature 類 Issue）
docs/issue-NN-short-title     （純文件更新）
```
範例：`fix/issue-8-ws-preauth`、`feat/issue-12-cop-heatmap`

### Priority Labels（GitHub Issue Labels）
- `priority:P0` — 阻擋 Edition gate，當前 sprint 必須先做
- `priority:P1` — Edition 強烈建議
- `priority:P2` — Quality hardening

---

## Source of Truth

| 真相類型 | 來源 |
|---------|------|
| Capability 狀態、maturity、edition gate | **Matrix Tab 2**（matrix.md） |
| 執行記錄、approval、verdict、evidence | **GitHub Issues + PRs** |
| 人類可讀的 Release 計劃 | **ROADMAP.md**（Tab 1 鏡像，由 Steward 同步） |
| 實作事實 | **Repo code + tests** |
| README | 非 maturity 權威，僅導航用途 |

---

## 工作流（完整步驟）

### 觸發
Human 在 chat 說明優先級（如「下一個 P0 Fix」）。後續 Step 1–3 可在同一對話連續執行，到 Gate A 自動停。

### Step 1 — Matrix Steward：建立 Issue + Context

**執行**：
1. 讀 matrix.md Tab 2，找到對應 CAP row 與開放 GAP
2. 用 `gh` CLI 建立 GitHub Issue（空 body，正確標題格式和 labels）
3. 在 Issue 貼第一則 comment：Context summary

**Context comment 格式**：
```markdown
## Matrix Context

**Edition target**: Exercise Pro
**Release target**: v2.1.0
**Cause**: [從 GAP 描述取得——為什麼這個問題存在]
**Reason**: [從 CAP maturity 取得——為什麼這個 release 要修]
**Impact if skipped**: [從 edition gate 取得——不修會擋住什麼]

_Internal refs (agent use only)_: CAP-NNN · GAP-DOM-NN · NIST XX
```

**記錄位置**：GitHub Issue Comment #1，標籤 `role:steward`

### Step 2 — Security Review（Gatekeeper 角色，pre-task）

**執行**：
1. 讀 matrix Tab 2 + Step 1 context
2. 檢查 P0/P1 狀態、NIST controls、forbidden patterns
3. 在同一 Issue 貼 Security Review verdict

**Security Review comment 格式**：
```markdown
## Security Review

**Go / No-Go**: Go ✅ / No-Go ❌
**Conditions for implementation**:
- [實作必須滿足的安全條件]
**Forbidden patterns**:
- [明確禁止的實作方式]
**Out-of-scope boundary**:
- [本 Issue 明確不做的事]
```

**記錄位置**：GitHub Issue Comment #2，標籤 `role:security-review`

### Step 3 — Implementation Auditor：Task Card

**執行**：
1. 讀 matrix + Security Review
2. 產出完整 Task Card（§1–§10）
3. 用 `gh` CLI 編輯 Issue body，填入 Task Card
4. 在 Issue 留 comment 通知 Gate A 就緒

**Task Card Header**（Issue body 開頭）：
```
Edition  : Exercise Pro
Release  : v2.1.0
Issue    : #NN
Type     : Fix / Feature
Priority : P0 / P1 / P2
Cause    : [一句話——為什麼這個問題存在]
Reason   : [一句話——為什麼這個 release 要修]
Impact   : [一句話——不修會擋住什麼]
```

---

> ### Gate A — Human 批准範圍 ◆
>
> **Human 讀 Task Card，確認 scope、file list、design decisions。**
> 在 Issue 貼 comment：`Gate A: go` 或提出疑慮。
> Agent 看到 `Gate A: go` comment 才能繼續。
>
> _這是 coding 開始前的唯一人工決策點。_

---

### Step 4 — Claude Code：實作

**執行**：
1. 讀 GitHub Issue Task Card（§1–§10）
2. 執行 §3 Dependency Check，回報結果
3. 在 branch `fix/issue-NN-short-title` 實作
4. 寫 tests per §7
5. 用 `gh` CLI 開 PR，連結 Issue#，PR body 含 Known Limitations

**Claude Code 可以使用 `gh` CLI**：
- `gh issue create` — 建立 Issue（Step 1）
- `gh issue comment` — 貼 comment
- `gh issue edit` — 編輯 Issue body
- `gh pr create` — 開 PR
- 但**不可以** `git push` 到 main，不可自行 merge

**記錄位置**：GitHub PR（連結 Issue#）

### Step 5 — Implementation Auditor：PR Review

**執行**：
1. 讀 PR 變更 + Task Card
2. 逐條確認 §6 Acceptance Criteria pass/fail
3. 產出 §8 Human Verification Script（可直接 copy-paste 的 shell 指令）
4. 在 PR 貼 review comment

**記錄位置**：GitHub PR Review comment，標籤 `role:auditor`

---

> ### Gate B — Human 實機驗證 ◆
>
> **Human copy-paste §8 script，在 Pi 500 / N100 執行。**
> 把輸出貼到 PR comment：`Gate B: pass` + 關鍵輸出截圖或文字。
> 這個步驟需要實體硬體，無法由 agent 替代。

---

### Step 6 — Close Verdict（Gatekeeper 角色，post-task）

**執行**：
1. 讀 Gate B 結果 + PR
2. 發布最終 verdict
3. 在 Issue 貼 close comment

**Close Verdict comment 格式**：
```markdown
## Close Verdict

**Go / No-Go**: Go ✅ / No-Go ❌

### Allowed Claims（此 Issue 關閉後可宣稱）
- ✅ [可宣稱的事項]

### Forbidden Claims（仍禁止）
- ❌ [仍不可宣稱的事項]

### Matrix Update Required
- CAP-NNN: [Needs Hardening → Partial Hardened 等]
- Evidence: PR#NN, commit [hash]
```

**記錄位置**：GitHub Issue close comment，標籤 `role:close-verdict`

---

> ### Gate C — Human Merge + Close ◆
>
> **Human 在 GitHub merge PR，關閉 Issue。**
> 這是安全邊界——任何 agent 不得直接操作 main branch。
> Merge commit hash = 不可竄改的批准記錄。

---

### Step 7 — Matrix Steward：Matrix 更新

**執行**（在 chat 中，Steward 產出更新指令，human 貼入 matrix 或 Steward 直接 commit）：
1. 讀 Close Verdict + PR
2. 更新 matrix.md Tab 2：CAP maturity、Status、Evidence 欄（PR# + commit hash）
3. 更新 matrix.md Tab 1：Release Dashboard 的 Item 狀態、Claims
4. Commit message 格式：`matrix: update CAP-NNN after Issue #NN close`

**記錄位置**：matrix.md commit，commit message 引用 Issue# 和 PR#

---

## Task Card Format（§1–§10）

每個 GitHub Issue body 必須包含以下所有 section。Claude Code 在看到 `Gate A: go` 前不得開始實作。

### §0 Header（見 Step 3 格式）

### §1 Task
一段話。說明必須做什麼，完成後的系統狀態是什麼。不含設計決策（設計決策在 §6）。

### §2 Context
- Codebase 位置與 tech stack（語言、框架、關鍵 library、版本）
- 部署環境（OS、user、路徑、systemd unit）
- 目前損壞行為（含 file:line 證據）
- 權威來源參照（Matrix Tab 2 row、Security Review 條件）

### §3 Dependency Check
Claude Code 必須執行所有項目並回報，才能寫任何 code。Human 審閱回報後發 Gate A 批准。

必要 grep 項目：
- 相關 literal、function name、pattern 在受影響組件的位置
- 要修改行為的現有呼叫者、middleware、tests
- Schema 或 config 變更是否必要
- 所有 HTTP route（method + path）：新增、修改、作為 whitelist gate 的
- 所有 WebSocket message type：新增、修改、被 gate 的
- 部署環境假設（user、HOME、路徑、權限、systemd unit）
- Design Constraint Check — 對 §6 每條 AC 和 §7 每條 test，說明：
  ```
  §6 item N: [directly implementable | decision required: <question>]
  §7 test N: [unit | integration/spawn | human verification — reason: <why>]
  ```
  任何 `decision required` 項目必須在 Gate A 前與 human 確認，不得單方面決定。

### §4 Files Actually Involved
只列 §3 Dependency Check 確認的檔案。分三類：
- Will modify: 路徑 — 原因
- Will add: 路徑 — 原因
- Will not touch (explicit): 路徑 — 原因

若 §3 尚未跑完，此 section 必須寫「pending §3」。

### §5 Goal
以可觀察的行為描述實作完成後的系統狀態。不含實作細節（那在 §4 和 §6）。

### §6 Acceptance Criteria
checklist 格式。每條必須：
- **Observable**：可用 curl、log line、file check 或 test assertion 驗證
- **Unambiguous**：不需要設計決策才能解讀
- **Scoped**：不暗示 §9 Out of Scope 的工作

模糊條件必須在 Gate A 前改寫或移到 decision point。

### §7 Automated Tests
每條測試指定層別：
- **Unit** — 純函式，無 server、DB、filesystem（快，必要）
- **Integration/spawn** — 啟動真實 server process（慢，只在 middleware 掛載必要時用）
- **Human verification** — 由 §8 script 涵蓋，明確標示

規則：
- 不引入新 test framework，除非 §4 明確列出
- Node.js 組件：優先用 `node:test`（built-in）
- Python 組件：優先用 `pytest`
- Integration/spawn tests 必須處理：tmp DB（env var 控制路徑）、ephemeral port、SIGTERM cleanup、cross-platform binary 相容性（如 better-sqlite3）
- 每個 test name 對應 §6 的一條 AC（1-to-1）

### §8 Human Verification Script
在實際部署目標（非 CI）執行的 shell 指令，step-by-step。
- 每步驟必須包含預期輸出或 exit code
- 所有步驟可依序執行，中間不需手動介入
- 涵蓋從 fresh state 到 steady state 的完整 operator workflow

### §9 Out of Scope
明確列出不在本 Issue 範圍的相關工作：
```
- <item> — reason: belongs to Issue #NN / [release target]
```
若 in-scope 實作需要碰 out-of-scope 區域，Claude Code 必須停止並回報，不得自行決定。

### §10 Human Approval Gates
三個強制 gate。Claude Code 不得在 gate 確認前繼續。

**Gate A — 開始寫 code 前**：
- §3 Dependency Check 回報已提交
- §3.7 所有 `decision required` 項目已與 human 確認
- §4 Files 已由 human 確認
- Whitelist / gate / message-type 清單已由 human 確認

**Gate B — merge 前**：
- PR 已在 feature/fix branch 開啟（非 main）
- Human 已在部署目標執行 §8 script；所有步驟 green
- `npm test` / `pytest` 在 dev machine 和 Linux target 均通過
- 未新增 §4 未列出的 dependency

**Gate C — merge 後（human only）**：
Issue 必須在以下所有項目完成後才算 CLOSED：
- C-1. PR merge confirmed；merge commit hash 記錄在 Issue
- C-2. Close Verdict（Step 6）已貼為 Issue close comment
- C-3. Matrix Steward（Step 7）已更新 matrix Tab 2
- C-4. ROADMAP.md（Tab 1）已同步 Item 狀態

---

## Scope Control

- Coding agent 只能執行有 `Gate A: go` comment 的 Issue task card
- 不展開 scope
- 不建立相鄰功能
- 若 dependency 缺失，停止並回報，不重新設計

---

## Code Change Rules

- 只在 `fix/issue-NN-*` 或 `feat/issue-NN-*` branch 工作
- 不 commit、push、tag、開 PR，除非明確指示
- 可用 `gh` CLI 操作 GitHub Issue（create、comment、edit body）
- 可用 `gh pr create` 開 PR
- 不可直接操作 main branch
- 新增或更新 regression tests（可行時）
- 無法跑 tests 時，精確說明原因

---

## Documentation Rules

- 不建立新的長文件
- Fix Issue 完成後，只回報 matrix update suggestion
- Human owner 決定 matrix 和 ROADMAP 的最終更新
- Matrix Steward 執行 Step 7 更新

---

## Prohibited Behaviours for Claude Code

以下行為**無論 task card 或其他指示如何措辭**，一律禁止：

- Auto-commit、auto-push、auto-tag、自行 merge PR
- 跳過或部分完成 §3 Dependency Check 才回報
- 在 §3.7 未確認前自行做設計決策
- 展開 §9 Out of Scope 之外的工作（即使看起來有益）
- 新增 §4 未列出的 npm / PyPI dependency
- 修改 matrix.md、ROADMAP.md 或 compliance 文件
- 建立新的長文件
- 重開 human 已決定的 decision point
- 單方面解讀模糊的 §6 條目——停止並回報

---

## Before Editing

修改任何檔案前，先 inspect 現有實作，確認是否與 task card 假設一致。若不一致，停止並詢問，不盲目 patch。

---

## Output Required (Claude Code)

每個 coding task 完成後回報：
1. Summary（做了什麼）
2. Files changed（含 reason）
3. Tests run（pass/fail + counts）
4. Remaining risks（Known Limitations）
5. Matrix update suggestion（供 Steward 在 Step 7 使用）

---

## Known Limitations（PR Description Template）

每個 PR 必須包含 `## Known Limitations` section：

```markdown
## Known Limitations

| Item | Reason not fixed in this PR | Tracking |
|---|---|---|
| [未修的項目] | [原因] | Issue #NN / [release target] |
```

這個 section 是 intentional gaps 的權威記錄，Implementation Auditor 在產下一張 task card 前必須讀這裡。
