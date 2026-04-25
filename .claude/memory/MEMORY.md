# ICS_DMAS 專案記憶索引

## 行為規則（永遠適用）

1. **跨平台不要提醒**：Mac ↔ Windows 開發時，不要主動提「記得同步 memory」或「注意路徑差異」，只在使用者主動問或遇到實際錯誤時才提。

2. **不要用 worktree 分支 commit**：commit 直接在 main 分支上做，不要用 worktree 分支再 fast-forward merge。GitHub UI 要保持 `main ← main` 的乾淨歷史。

3. **HTML 不開新檔，原地改版**：HTML 不要每次開新檔案（v13→v14→v15），直接在原檔改版，用 JS 常數（如 `PWA_VERSION`、`CMD_VERSION`）和 git commit 區分版本。

4. **缺欄位要從源頭修**：server 缺欄位先判斷是源頭該送還是本來就不適用，不要只在 server 容錯。

5. **主動思考缺口**：設計討論中主動找出使用者沒想到的缺口，不只回應問題。使用者太發散時拉回。

## 架構決策

- [架構設計決策](architecture_decisions.md) — COP 聯邦架構、TAK / AI 整合、Pi server 模組、Compliance 程式 + 5 組 Decision Sets（A-E：IP / DB 並發 / Session 設計 / 實作策略 / License 解耦）
- [C1-B HTTPS 架構決策](c1b_https_decisions.md) — nginx + step-ca + 分階段 CSP；CORS env 白名單（不徹底移除）；deploy/ 目錄落地

## Compliance 程式（Phase 0 完成 2026-04-25）

主入口在 repo `docs/compliance/`：
- `matrix.md` — 主對照表（13 大標準節區 + 88 個 gap + Evidence Index + 「可主張 compliance」master 清單）
- `threat_model.md` — STRIDE 骨架
- `security_policies.md` — 6 政策骨架
- `README.md` — Session A/B/C/D 計劃 + 交接機制

repo root 補：`SECURITY.md`（漏洞通報政策）/ `.github/PULL_REQUEST_TEMPLATE.md`（DoD checklist）

## 參考文件

- [iOS WSS zombie 參考](reference_ios_wss_zombie.md) — Happy Eyeballs 根因、已排除假設、設計決策，避免重複踩坑

## 專案狀態

- [專案狀態總覽](project_status.md) — Compliance Phase 0 + cmd-v2.0.6 + 醫療 PWA 進度 + 指揮部路線圖 + 硬體資訊 + Pi 設定步驟
- [即將到來的演練](upcoming_exercises.md) — 5/31 無線電演練、6月底/7月初 中型演練，護城河資料積累關鍵時間點
