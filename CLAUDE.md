# ICS_DMAS 專案規則

## 安全與供應鏈規則

**禁止使用任何與中國相關的軟體、函式庫、或服務。**

包含但不限於：
- npm / PyPI 套件的維護者或主要貢獻者為中國實體
- 中國雲端服務（阿里雲、騰訊雲、百度雲等）
- 任何來源不明、無法驗證供應鏈的套件

遇到不確定的情況，**必須先詢問使用者確認**，不得擅自引入。

## Debug 規則

1. **平台與工具的設計規則優先**：不管 iOS 或 Windows 平台都有自己的設計規則，我們用的程式語言也有自己的設計規則。開始計畫前，要對運行的平台及使用的工具已有足夠的認識。
2. **一定有先例**：我們要做的事不是新的、複雜的，一定有先例。除了參考成功的 source code，網路上應該也有成功的 pcap 抓包可以參考。
3. **基礎確認後才判斷 log**：如果前面這些基礎已經確認，再來判斷我們的 log 所指出的邏輯及方向，才有意義。

## 溝通與推論規則

1. **檢查假設**：使用者的假設若有問題，必須明確指出，不得默默接受。
2. **指出邏輯漏洞**：發現設計或推論中的漏洞，要主動說出，不迴避。
3. **區分事實、假設、推論、意見**：回覆中要清楚標示依據來源。
   - 事實：有明確根據（程式碼、規格、文件）
   - 假設：未經驗證但合理的前提
   - 推論：從已知資訊推導出的結論
   - 意見：個人判斷，可能有其他立場
4. **不確定就說**：資訊不確定時直接說「不確定」或問清楚，不得填補猜測當事實。

## 語言規則

- 所有回覆、程式碼 comment 一律使用**繁體中文**
- 禁止混入日文或韓文
- 英文僅用於技術術語、變數名、API 名稱等無法翻譯的部分

## Git 操作規則

- **任何 git 操作（commit、push、tag、PR）一律等使用者明確指示才執行**
- 程式碼改完後停下來，告知改了什麼，等使用者說 ok 再動 git
- 例外：使用者明確說「commit」、「push」、「推上去」、「開 PR」才執行對應操作
- **不得自行判斷「應該順便 commit」或「順便 push」**

### Branch 工作流（Feature Branch）

- 每個功能 / Cx 項目建立獨立分支，命名規則：
  - `feat/<scope>` — 新功能（如 `feat/c2-c-ruff`、`feat/c1-e-migrations`）
  - `fix/<scope>` — bug fix（如 `fix/archive-404`）
  - `docs/<scope>` — 純文件更新
- 分支完成後透過 PR merge 回 `main`
- `main` 只接受 merge commit（不直接 push feature code）
- hotfix 或純文件更新可直接在 `main` commit

## 版號規則

### 兩軌版本命名

本專案使用兩套獨立的版本號，**不可混用**：

**軌道一：程式版本（SemVer）** — 格式 `vMAJOR.MINOR.PATCH`，以 git tag 標記。

**Git tag 命名規則**（三組各自獨立）：
- `medical-vX.Y.Z[-alpha|-beta]` — 醫療組 PWA
- `shelter-vX.Y.Z[-alpha]` — 收容組 PWA
- `server-vX.Y.Z` — 共用 Pi Server（`server/index.js`）

每次 commit 若包含版號遞增，**必須同時打對應的 git tag**。舊有 `v0.1.0`（無 prefix）為歷史遺留，不再使用。

| 位號 | 觸發條件 |
|------|---------|
| PATCH +1 | bug fix 完成，行為有改變 |
| MINOR +1 | 一個功能完整可用 |
| MAJOR +1 | 介面或資料格式有破壞性變更（Pi ↔ 指揮部 API、DB schema） |

**軌道二：規格書版本（vX.Y）** — 各文件獨立編號，不跟隨程式 SemVer。

| 位號 | 觸發條件 |
|------|---------|
| Y +1 | 規格內容新增、修正、或對應程式里程碑更新 |
| X +1 | 規格架構重大改版 |

規格書 changelog 須標注對應的程式里程碑（若有 tag）或「規格先行」。

### 每次改動的 bump checklist（缺一不可）

1. `PWA_VERSION`（HTML 檔案內的常數）
2. `CACHE_NAME`（`sw.js`，格式：`shelter-pwa-vX.X.XX` / `medical-pwa-vX.X.XX`）
3. `SERVER_VERSION`（`server/config.js`）— 若 server 有改動
4. **規格書同步** — 若有介面、資料格式、或功能行為變更，需更新對應規格文件

不需詢問，直接遞增。

### 主動提出效率建議

任何可增進開發或 debug 效率的工具、做法、架構改善，都可以主動提出，不需要等被問。

## Memory 同步（跨機器）

Memory 檔案存放在 repo 的 `.claude/memory/` 目錄。`git pull` 會自動觸發 sync（透過 `.githooks/post-merge`），**每台新機器只需執行一次 hook 啟用指令**：

```bash
# Mac / Linux / Git Bash（在 repo 根目錄執行一次）
git config core.hooksPath .githooks
```

啟用後，`git pull` 完自動將 `.claude/memory/` 同步到 Claude Code 讀取位置，無需手動操作。

### 手動 sync（備用）

hook 尚未啟用，或需要立即強制同步時：

```bash
# Mac / Linux
REPO=$(git rev-parse --show-toplevel)
PROJECT_DIR=$(echo "$REPO" | sed 's|^/||; s|[^a-zA-Z0-9]|-|g')
mkdir -p ~/.claude/projects/$PROJECT_DIR/memory
cp "$REPO/.claude/memory/"* ~/.claude/projects/$PROJECT_DIR/memory/
```

```powershell
# Windows（PowerShell）
$repo = git rev-parse --show-toplevel
$encoded = ($repo -replace '^/', '' -replace '[^a-zA-Z0-9]', '-')
$dest = "$env:USERPROFILE\.claude\projects\$encoded\memory"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item "$repo\.claude\memory\*" $dest
```

> **路徑編碼規則**：Claude Code 將絕對路徑的每個非英數字元（`/`、`\`、`:`、空格、`_` 等）全部換成 `-`，並去掉開頭的 `-`。

若在該機器新增了 memory，記得也要 commit `.claude/memory/` 回 repo，讓其他機器能同步。

## 開發環境

- 主要開發機：Mac
- 目標部署：Raspberry Pi 500（已到貨，Phase 2 E2B AI 評估已在 Pi 500 執行）
- 測試方式：Mac 本機模擬完整架構

## 專案結構

- `command-dashboard/` — 指揮部後端（FastAPI + SQLite）
- `shelter-pwa/` — 收容組 PWA + WebSocket Pi 伺服器
- `medical-pwa/` — 醫療組 PWA（開發中）
