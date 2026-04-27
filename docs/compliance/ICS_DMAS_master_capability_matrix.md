# ICS_DMAS Master Capability Matrix

> 本文件說明 Master Capability Matrix 的結構與使用方式。
> 主表以 XLSX 維護。matrix.md 是 XLSX 的 markdown 版本。

---

## 結構：兩個視角

### Tab 1 — Release Dashboard（Human view）
受眾：Human owner、業務、投標。
問題：這個 release 有哪些 Fix / Feature？完成後可 claim 什麼？
欄位：Release · Edition · Issue# · Status · Claims

### Tab 2 — Capability Matrix（Agent view）
受眾：AI agents（Matrix Steward、Security Review、Auditor）。
問題：這個 CAP 的 maturity 是什麼？哪些 GAP 阻擋升級？NIST control 是什麼？
欄位：Issue# · CAP · GAP · NIST · maturity · Evidence · Blocks edition

---

## 命名慣例

| 層 | 格式 | 範例 |
|----|------|------|
| Edition | 英文名稱 | Exercise Pro |
| Release | SemVer | v2.1.0 |
| Item | GitHub Issue# | #8 |
| Capability | CAP-NNN (mnemonic) | CAP-013 (WSAuth) |
| Gap | GAP-DOM-NN (old G-XNN) | GAP-AUTH-02 (was G-A02) |

---

## Maturity Levels

| Level | 名稱 | 定義 |
|-------|------|------|
| L0 | Not Implemented | 僅在 roadmap/backlog |
| L1 | Demo | 可演示，不可依賴於正式演訓 |
| L2 | Operational | 可在正式演訓中使用，有基本錯誤處理 |
| L3 | Auditable | 具備 RBAC、稽核、證據、可追溯，可支援採購驗收 |
| L4 | Mission-ready | 可支援真實災害輔助，含 IR/DR、加密、外部稽核 |

---

## Edition Gates

| Edition | 適用定位 |
|---------|---------|
| Demo | 受控展示、假資料 |
| Exercise Pro | 正式演訓、TTX、AAR、基本資安 |
| GovOps | 政府採購、個資、audit、DR、正式驗收 |
| Tactical | Field Node、戰術敏感、高安全部署 |

---

## Priority（GitHub Issue Labels）

| Label | 意義 |
|-------|------|
| priority:P0 | 阻擋 Edition gate，當前 sprint 必須先做 |
| priority:P1 | Edition 強烈建議 |
| priority:P2 | Quality hardening |

---

## 使用方式

**Human owner**：看 Tab 1（ROADMAP.md 或 XLSX Tab 1）
**Agents**：看 Tab 2（matrix.md 或 XLSX Tab 2）

**Tab 2 篩選建議**：
- 只看 P0：找 current-stage 阻斷項
- 只看 Exercise Pro edition：確認正式演訓可交付範圍
- 只看 L0/L1：找 demo-only 或尚未成熟的功能
- 只看 Issue# 有值：確認哪些 capability 已有對應 GitHub Issue

---

## 維護責任

| 動作 | 執行者 | 時間點 |
|------|--------|--------|
| Tab 2 技術欄位更新（CAP maturity、GAP、Evidence）| Matrix Steward | 每次 Issue close 後 Step 7 |
| Tab 1 Item 狀態同步 | Matrix Steward | 每次 Issue close 後 Step 7 |
| External Claim 欄位 | Human owner | 獨立決定，可晚於 Step 7 |
| 新 Issue 建立 | Matrix Steward（gh CLI）| Step 1 |
