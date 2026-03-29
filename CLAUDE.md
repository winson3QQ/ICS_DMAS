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

## Memory 同步（跨機器）

Memory 檔案存放在 repo 的 `.claude/memory/` 目錄，**每次在新機器 clone 後**需執行以下指令，將 memory 複製到 Claude Code 實際讀取的位置：

```bash
# Linux / Mac
cp /path/to/ICS_DMAS/.claude/memory/* ~/.claude/projects/$(pwd | sed 's|/|-|g' | sed 's|^-||')memory/

# Windows (Git Bash)
cp "c:/Users/yello/研究計畫/ICS_DMAS/.claude/memory/"* "C:/Users/yello/.claude/projects/c--Users-yello------ICS-DMAS/memory/"
```

若在該機器新增了 memory，記得也要 commit `.claude/memory/` 回 repo，讓其他機器能同步。

## 開發環境

- 主要開發機：Mac
- 目標部署：Raspberry Pi（未到貨，到貨後驗證）
- 測試方式：Mac 本機模擬完整架構

## 專案結構

- `command-dashboard/` — 指揮部後端（FastAPI + SQLite）
- `shelter-pwa/` — 收容組 PWA + WebSocket Pi 伺服器
- `medical-pwa/` — 醫療組 PWA（開發中）
