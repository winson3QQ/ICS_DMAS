# ICS_DMAS Release Roadmap

> **受眾**：Human owner、業務、投標。
> **維護者**：Matrix Steward，每次 Issue 關閉後自動同步。
> **技術細節**（CAP、GAP、NIST、Cx）→ [matrix.md](matrix.md)
> **商業策略**→ [commercialization_plan_v1.md](commercialization_plan_v1.md)

---

## 現在位置（2026-04-27）

> **注意**：#8 (WS-01) ✅ 已 closed (PR #9)。#11 (TI-01) ✅ 已 closed (PR #12)。Exercise Pro gate 開放。

| 項目 | 狀態 |
|------|------|
| 目前 Edition | Exercise Pro（進行中） |
| 目前 Release | v2.1.0（building） |
| 最新完成 Issue | #8 Fix — WS pre-auth gate ✅ (PR #9 merged) |
| 最新完成 Issue | #11 Fix — Trusted Ingest HMAC ✅ (PR #12, commits 6bda2dc + 5e855c6) |

---

## Priority → Edition 對應

> Priority 決定一個 Issue **阻擋哪個 Edition**。Edition 無法宣稱，直到對應 priority 的所有 Issues 全部 close。

| Priority | 定義 | Blocks Edition |
|----------|------|----------------|
| **P0** | 當前 stage 必修；任何對外宣稱的最低前提 | 所有 Edition |
| **P1** | Exercise Pro / GovOps 前必完成 | Exercise Pro 以上 |
| **P2** | GovOps 採購強化項 | GovOps 以上 |
| **P3** | 護城河 / 完整合規 | Flagship |
| **P4** | Tactical 高敏感場景專屬 | Tactical only |

---

## Release / Edition / Golden Path 對照

| Release | Edition | GP scope | Commercial gate | Target |
|---------|---------|----------|-----------------|--------|
| ~~v0.12.x~~ | Demo | — | Architecture base | ~~2026-04~~ ✅ |
| v0.13.0 | Demo | — | Demo-ready UI | 2026-05 |
| v2.1.0 | Exercise Pro | GP2 + GP3 | First biddable · field drill | 2026-06 |
| v2.2.0 | GovOps | GP2 + GP3 + GP4 | First sellable | 2026-Q3 |
| v3.0.0 | GovOps + TTX | GP1 + GP2 + GP3 + GP4 | TTX / AAR moat | 2026-Q4 |
| v3.1.0 | AI | GP1–GP4 + AI | AI differentiation | 2027-Q1 |
| v3.2.0 | Flagship | GP1–GP5 | ISO certification | 2027-Q2 |

> **GP 定義**：GP1=TTX→AAR · GP2=現場回報→COP→決策 · GP3=斷網→同步 · GP4=部署→驗收→證據包 · GP5=真實災害→DR→稽核

---

## Edition: Demo

### v0.12.x ✅

**Fix**: C0 backend refactor · session persistence · TOCTOU mutex bug
**Feature**: Wave 1–4（事件、決策、快照、地圖、PWA 同步）
**Claims**: 可展示 ICS 基本 COP 流程於受控環境

---

### v0.13.0 🔄

**Fix items**:

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| #6 | Fix — Pi first-run security | P0 | ✅ |

**Feature items**:

| Issue | Title | Status |
|-------|-------|--------|
| — | Burn rate prediction line | 🔲 |

**Claims**: Pi 部署需由 IT 人員透過一次性 token 完成初始設定；fresh DB 不含預設帳號或 PIN

---

## Edition: Exercise Pro

### v2.1.0 — First biddable version 🔄

> 支援 **GP2**（現場回報→COP→決策→回報）+ **GP3**（斷網→離線→恢復同步）。
> **不支援** TTX MSEL inject 與自動 AAR report（見 v3.0.0）。
> v2.1.0 = 第一個正式部署版本，依下方 A→B→C→D→E 序列執行。

---

#### 序列 A — 部署基礎設施（最優先，在所有 P0 Security 之前）

> 沒有 logging 和 /health，後面所有 Gate B 實機驗證都缺少診斷工具。

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| TBD | Fix — structured logging + audit hash chain + correlation ID + collect_debug.sh | P0 | 🔲 |
| TBD | Fix — /health liveness endpoint | P1 | 🔲 |

---

#### 序列 B — P0 Security Fix

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| #6 | Fix — Pi first-run security | P0 | ✅ |
| #8 | Fix — WebSocket pre-auth gate | P0 | ✅ |
| #11 | Fix — Trusted Ingest HMAC | P0 | ✅ |
| TBD | Fix — frontend modularise + CSP | P0 | 🔲 |
| TBD | Fix — 4-role RBAC + endpoint gate | P0 | 🔲 |
| TBD | Fix — WS full security | P0 | 🔲 |
| TBD | Fix — 3-layer encryption | P0 | 🔲 |
| TBD | Fix — Pi + PWA component encryption | P0 | 🔲 |
| TBD | Fix — backup DR drill execution | P0 | 🔲 |

---

#### 序列 C — P1 Hardening Fix（P0 全 close 後）

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| TBD | Fix — session revoke on suspend | P1 | 🔲 |
| TBD | Fix — rate limit XFF fix | P1 | 🔲 |
| TBD | Fix — Pi API key hash store | P1 | 🔲 |
| TBD | Fix — SBOM + SLSA L2 + dep scan | P1 | 🔲 |
| TBD | Fix — prod resilience + global rate limit | P1 | 🔲 |
| TBD | Fix — step-ca Pi real test | P1 | 🔲 |
| TBD | Fix — config externalise + install script | P1 | 🔲 |
| TBD | Fix — IR plan + PDPC 72h procedure | P1 | 🔲 |
| TBD | Fix — prod debug/prod mode switch | P2 | 🔲 |

---

#### 序列 D — Feature（P1 全 close 後）

| Issue | Title | Status |
|-------|-------|--------|
| TBD | COP redesign (heatmap + cluster + search + replay) | 🔲 |

---

#### 序列 E — Release Acceptance（最後，發布前 2 週完成）

> 所有 Issues close 後，整體 end-to-end 驗收。非 coding task，人工驗收流程 + Owner sign-off。

| Checkpoint | 內容 | Status |
|---|---|--------|
| Fresh install | Install script → systemd → /health 200 OK | 🔲 |
| GP2 end-to-end | Pi push → COP 更新 → 指揮決策 → 任務回報 | 🔲 |
| GP3 end-to-end | 斷網 → PWA 離線記錄 → 恢復同步 → AAR 可追溯 | 🔲 |
| Multi-Pi stress | 3 台 Pi 同時推送，無 DB lock，無 ERROR log | 🔲 |
| Logging & debug | collect_debug.sh 執行，zip 產出完整 | 🔲 |
| RBAC isolation | 各角色只看授權資料，無越界 | 🔲 |
| CSP clean | browser console 無 violation，無 JS error | 🔲 |
| Owner sign-off | Human owner 確認通過 ✍️ | 🔲 |

---

> ✅ **Exercise Pro gate OPEN**: #8 ✅ + #11 ✅ → Exercise Pro Edition 已開放
> ⚠️ 但 Release Acceptance (序列 E) 仍需完成才可正式宣稱
> ⚠️ **Release Acceptance** 必須在 6 月演練前 **2 週** 完成（留 buffer 修問題）

**Claims on v2.1.0 close**:
- ✅ 支援縣市政府**現場演練（field drill）**採購投標
- ✅ GP2 現場回報 → COP → 決策 → 回報　完整閉環
- ✅ GP3 斷網 → 離線 → 恢復同步　完整閉環
- ✅ NIST 800-53 Moderate（scoped，self-declared）
- ✅ 個資法 §27 compliant
- ✅ 附表十 12項 Moderate
- ❌ TTX MSEL inject 不支援（見 v3.0.0）
- ❌ 自動 AAR report 不支援（見 v3.0.0）

---

> **C2-B** (esbuild bundle + minify + vitest coverage) → 另開 task，待 v2.2.0 CI/CD 強化規劃

## Edition: GovOps

### v2.2.0 — First sellable version 🔲

> 新增 GP4（部署→驗收→證據包）支援。第一個可銷售版本。

**Fix items**:

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| TBD | Fix — /metrics + alerting + Prometheus | P2 | 🔲 |

**Feature items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | TAK / FreeTAKServer bridge | 🔲 |
| TBD | MANET Pi Zero 2W mesh | 🔲 |
| TBD | Docker + Binary IP protection | 🔲 |
| TBD | License gate (Tier 1/2/3) | 🔲 |
| TBD | Customer debug SOP (FAQ + troubleshooting playbook) | 🔲 |

**Claims**: 第一個可銷售版本；完整部署維運支援；GP4 部署→驗收→證據包

---

## Edition: GovOps + TTX moat

### v3.0.0 🔲

> 新增 **GP1**（TTX→MSEL inject→AAR）完整閉環。

**Feature items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | ICS 201/214 PDF export | 🔲 |
| TBD | Resource request workflow ICS 213RR | 🔲 |
| TBD | SitRep auto-generate ICS 209 | 🔲 |
| TBD | TTX scenario DB + MSEL inject | 🔲 |
| TBD | AAR report engine (PDF + JSON) | 🔲 |
| TBD | HSEEP AAR/IP export | 🔲 |
| TBD | NIMS full compliance | 🔲 |

**Claims**: GP1 TTX→MSEL→AAR 完整閉環；HSEEP 演習管理對齊；ICS/NIMS 作業流程支援

---

## Edition: AI differentiation

### v3.1.0 🔲

**Feature items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | Silent Scribe STT (N100) | 🔲 |
| TBD | LLM ICS-214 auto-fill (Breeze) | 🔲 |
| TBD | AI predict layer + audit log | 🔲 |
| TBD | Prompt injection defense | 🔲 |
| TBD | Panic Wipe (3-layer) | 🔲 |

**Claims**: AI 決策支援；Silent Scribe 語音轉錄；NIST AI RMF 對齊

---

## Edition: Flagship + ISO

### v3.2.0 🔲

> GP5（真實災害→IR/DR→稽核保存）完整支援。

**Fix items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | ISO 27001 / CNS 27001 audit prep | 🔲 |
| TBD | External pen test + WCAG AA report | 🔲 |
| TBD | SBOM policy + procurement dossier | 🔲 |

**Claims**: ISO 27001 / CNS 27001 第三方驗證；GP5 真實災害輔助完整支援

---

## 守線原則

1. **Claims** 在 Issue Close Verdict 發布後才可宣稱，不得預先主張
2. **P0 全 close** 才能宣稱 Exercise Pro；**P1 全 close** 才能宣稱 GovOps
3. **v2.1.0 = field drill 支援**；TTX（GP1 完整）在 v3.0.0
4. **Release Acceptance sign-off（序列 E）** 是 v2.1.0 發布的最後一個 gate
5. **外部宣稱邊界** 以每個 Issue 的 Close Verdict 為準

---

_Matrix Steward 在每個 Issue 關閉後同步此文件。_
_完整技術映射（CAP / GAP / NIST / maturity）在 matrix.md。_
