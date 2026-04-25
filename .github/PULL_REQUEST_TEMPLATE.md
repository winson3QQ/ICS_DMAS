# Pull Request

## 摘要

<!-- 簡述這個 PR 做了什麼、為什麼 -->

## 變更類型

- [ ] feat — 新功能
- [ ] fix — bug 修復
- [ ] docs — 純文件更新
- [ ] refactor — 重構（行為不變）
- [ ] test — 補測試
- [ ] chore — 工具 / 設定 / dep 升級
- [ ] security — 資安修補
- [ ] breaking — 破壞性變更（API / DB schema）

## 對應 Roadmap

<!-- 連結到 ROADMAP.md 中的 Cx 項目，或 Wave 功能。如：實作 C1-A Phase 2 RBAC -->

- 對應項目：
- 適用標準（若有）：

## Definition of Done 檢查（CLAUDE.md「功能完成定義」）

- [ ] **CI 測試補齊** — 對應 unit / integration / security 測試已加並 green
- [ ] **規格書同步** — 介面 / 資料格式 / 行為變更已更新對應 spec
- [ ] **Compliance matrix 更新**（若適用）— `docs/compliance/matrix.md` Evidence 欄位指向新 code/test
- [ ] **ROADMAP.md 狀態** — 該 Cx 完成則改 ✅

## 測試說明

<!-- 加了哪些測試？涵蓋哪些情境？ -->

- 新增測試：
- 已過 CI：
- 手動驗證：

## 版號 / Tag（若適用）

- [ ] `PWA_VERSION` 已 bump
- [ ] `CACHE_NAME`（sw.js）已 bump
- [ ] `SERVER_VERSION`（server/config.js）已 bump
- [ ] Git tag 已標（`medical-vX.Y.Z` / `shelter-vX.Y.Z` / `server-vX.Y.Z`）

## 資安考量

<!-- 若涉及 auth / RBAC / 加密 / PII / 跨組件協議，描述設計思考與威脅模型 -->

- [ ] 不涉及資安
- [ ] 已對照 OWASP Top 10
- [ ] 已更新 threat_model.md（若改變信任邊界）

## Breaking Change 說明

<!-- 若有，描述 breaking change 內容 + migration path -->

## 截圖 / 示範（若 UI 變更）

<!-- 截圖 / GIF -->

## 相依 PR / Issue

<!-- 連結 -->

---

🤖 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
