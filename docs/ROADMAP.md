# ICS_DMAS Release Roadmap

> **受眾**：Human owner、業務、投標。
> **維護者**：Matrix Steward，每次 Issue 關閉後自動同步。
> **技術細節**（CAP、GAP、NIST、Cx）→ [matrix.md](matrix.md)
> **商業策略**→ [commercialization_plan_v1.md](commercialization_plan_v1.md)

---

## 現在位置（2026-04-27）

| 項目 | 狀態 |
|------|------|
| 目前 Edition | Exercise Pro（進行中） |
| 目前 Release | v2.1.0（building） |
| 目前進行中 Issue | #8 Fix — WS pre-auth gate 🔄 |
| 下一個 Issue | #9 Fix — Trusted Ingest HMAC 🔲 |

---

## Release / Edition 對照

| Release | Edition | Commercial gate | Target |
|---------|---------|-----------------|--------|
| ~~v0.12.x~~ | Demo | Architecture base | ~~2026-04~~ ✅ |
| v0.13.0 | Demo | Demo-ready UI | 2026-05 |
| v2.1.0 | Exercise Pro | First biddable | 2026-06 |
| v2.2.0 | GovOps | First sellable | 2026-Q3 |
| v3.0.0 | GovOps + TTX | TTX/AAR moat | 2026-Q4 |
| v3.1.0 | AI | AI differentiation | 2027-Q1 |
| v3.2.0 | Flagship | ISO certification | 2027-Q2 |

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

完成後可投標縣市政府演訓採購。

**Fix items**:

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| #6 | Fix — Pi first-run security | P0 | ✅ |
| #8 | Fix — WebSocket pre-auth gate | P0 | 🔄 |
| #9 | Fix — Trusted Ingest HMAC | P0 | 🔲 |
| TBD | Fix — session revoke on suspend | P1 | 🔲 |
| TBD | Fix — rate limit XFF fix | P1 | 🔲 |
| TBD | Fix — Pi API key hash store | P1 | 🔲 |
| TBD | Fix — prod debug/prod mode switch | P2 | 🔲 |
| TBD | Fix — frontend modularise + CSP | P1 | 🔲 |
| TBD | Fix — 4-role RBAC + endpoint gate | P0 | 🔲 |
| TBD | Fix — audit hash chain + correlation ID | P0 | 🔲 |
| TBD | Fix — WS full security | P0 | 🔲 |
| TBD | Fix — 3-layer encryption | P0 | 🔲 |
| TBD | Fix — Pi + PWA component encryption | P0 | 🔲 |
| TBD | Fix — SBOM + SLSA L2 + dep scan | P1 | 🔲 |
| TBD | Fix — prod resilience + global rate limit | P1 | 🔲 |
| TBD | Fix — step-ca Pi real test | P1 | 🔲 |
| TBD | Fix — config externalise + install script | P1 | 🔲 |
| TBD | Fix — backup DR drill execution | P0 | 🔲 |
| TBD | Fix — IR plan + PDPC 72h procedure | P1 | 🔲 |

**Feature items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | COP redesign (heatmap + cluster + search + replay) | 🔲 |

**Claims on v2.1.0 close**:
- ✅ NIST 800-53 Moderate（scoped，self-declared）
- ✅ 個資法 §27 compliant
- ✅ 附表十 12項 Moderate
- ✅ 可用於縣市政府正式演訓採購

> ⚠️ **Gate**: #8 + #9 兩者都 close → Exercise Pro edition 才開放

---

## Edition: GovOps

### v2.2.0 — First sellable version 🔲

**Fix items**:

| Issue | Title | Priority | Status |
|-------|-------|----------|--------|
| TBD | Fix — health + metrics + alerting | P1 | 🔲 |

**Feature items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | TAK / FreeTAKServer bridge | 🔲 |
| TBD | MANET Pi Zero 2W mesh | 🔲 |
| TBD | Docker + Binary IP protection | 🔲 |
| TBD | License gate (Tier 1/2/3) | 🔲 |
| TBD | Customer debug SOP + collect_debug.sh | 🔲 |

**Claims**: 第一個可銷售版本，含部署維運完整支援

---

## Edition: TTX moat

### v3.0.0 🔲

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

**Claims**: HSEEP 演習管理對齊；ICS/NIMS 作業流程支援

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

---

## Edition: Flagship + ISO

### v3.2.0 🔲

**Fix items**:

| Issue | Title | Status |
|-------|-------|--------|
| TBD | ISO 27001 / CNS 27001 audit prep | 🔲 |
| TBD | External pen test + WCAG AA report | 🔲 |
| TBD | SBOM policy + procurement dossier | 🔲 |

---

## 守線原則

1. **Claims** 在 Issue Close Verdict 發布後才可宣稱，不得預先主張
2. **Exercise Pro gate** 需要 #8 WS pre-auth + #9 Trusted Ingest 全部 close
3. **正式演訓** 在 v2.1.0 + Exercise Pro gate 驗收前為 No-Go
4. **外部宣稱邊界** 以每個 Issue 的 Close Verdict 為準

---

_Matrix Steward 在每個 Issue 關閉後同步此文件。_
_完整技術映射（CAP / GAP / NIST / maturity）在 matrix.md。_
