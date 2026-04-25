# ICS_DMAS Compliance Matrix

> **主 deliverable**：控制項 × 組件 × 狀態對照表。投標 / 稽核 / 行銷主要依據。
> **最後更新**：2026-04-25（骨架建立，Session A/B/C/D 填入內容）
> **審查原則**：架構層級對照，非 line-by-line code review。
>
> 狀態代號：✅ 符合 / ⚠️ 部分符合 / ❌ 未實作 / N/A 不適用（附理由）

---

## Session Log（給下一個 session 的 context）

> **重要**：每個 session 結束前必須更新此區。切換 session 讀此區就能延續工作。

### 整體進度

| Session | 範圍 | 狀態 | 完成日期 | Context 要點 |
|:---:|---|:---:|---|---|
| A | C0 + C1-A + C1-B + C1-E（Auth/Transport/Schema） | ⏸ 未開始 | — | — |
| B | C1-C + C1-D + C1-F + W-C1-* + P-C1-*（PII/Audit/Frontend） | ⏸ 未開始 | — | — |
| C | C2 + C3 + P-C2-* + W-C2-*（Quality/Deploy/Ops） | ⏸ 未開始 | — | — |
| D | Wave 功能 + NIMS + ICS 508 + 整合 | ⏸ 未開始 | — | — |

### 讀過的檔案清單（避免 session 間重複讀）

_（Session 執行時追加，每個 session 末記錄本次讀過的檔案）_

### 未決定 / 待追問（cross-session issue）

_（跨 session 的未解議題記錄這裡；session 結束時掃過一遍）_

### 重大架構發現（觸發 ROADMAP 或 architecture_decisions 更新的）

_（只記影響跨 session 的決策或新增 Cx / 修訂既有 Cx scope 的發現）_

---

## Meta：Scope 與基線確認

### 標的系統
- `command-dashboard/`（FastAPI + SQLite，Python 3.11+）
- `server/`（Node.js Pi server，原 `ics_ws_server.js`）
- `shelter-pwa/`（Progressive Web App，Dexie + WebSocket）
- `medical-pwa/`（Progressive Web App，Dexie + WebSocket）
- 部署基礎：`deploy/nginx/` + `deploy/step-ca/`

### 標準基線鎖定
詳見 [README.md § 涵蓋標準](README.md#涵蓋標準已鎖定)。關鍵選擇：
- **NIST 800-53 Moderate**（非 Low，因系統儲存個資 / 醫療資料）
- **SBOM 格式：CycloneDX**
- **Policy 語言**：繁中為主 + 術語英文（NIST 原文 reference）

### 評估方法
- 架構層級對照（design / data flow / 責任歸屬），**不做** line-by-line code review
- 證據（evidence）欄位標示「file:line」或「doc:section」指向確實存在的實作
- 無實作但規劃中 → 狀態 ⚠️ + gap 欄位描述 + target Cx
- 完全不做 → N/A + 說明理由（例：HIPAA 不適用台灣）

---

## 對照表使用說明

每個標準自成一節。節內格式：

```
| Control ID | 要求摘要 | Command | Pi | PWA | Cx owner | Priority | Evidence | Gap |
```

- **Command / Pi / PWA**：三組件獨立狀態
- **Cx owner**：負責此項的 Cx 編號（含 P-Cx、W-Cx）
- **Priority**：🔴 critical / 🟡 high / 🟠 medium / ⚪ low
- **Evidence**：file:line / PR#/ doc:section
- **Gap**：⚠️ 或 ❌ 時說明缺口

Gap 過長時移到最下方「Gap Register」section，matrix 只留編號。

---

## 1. NIST SP 800-53 Rev. 5（Moderate Baseline）

> 標準原文：https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
> Moderate baseline 涉及約 260 個 control，本節按 family 分列本系統相關項。

### 1.1 AC — Access Control

_Session A 填入：AC-1 ~ AC-25，focus AC-2/3/6/7/11/12/14/17_

### 1.2 AU — Audit and Accountability

_Session A 填入 AU-2/3/4/6/8/9/11/12，Session B 延伸 hash chain_

### 1.3 IA — Identification and Authentication

_Session A 填入：IA-2/3/5/6/7/8/11/12_

### 1.4 SC — System and Communications Protection

_Session A 填入 SC-7/8/12/13/17/23/28，Session B 補前端 SC_

### 1.5 SI — System and Information Integrity

_Session C 填入：SI-2/3/4/7/10/11/16_

### 1.6 CM — Configuration Management

_Session C 填入：CM-2/3/6/7/8_

### 1.7 CP — Contingency Planning

_Session C 填入：CP-2/4/9/10_

### 1.8 IR — Incident Response

_Session C 填入：IR-4/5/6/8_

### 1.9 PL — Planning

_Session D 填入：PL-2/8_

### 1.10 RA — Risk Assessment

_Session D 填入：RA-3/5（含 threat_model）_

### 1.11 SA — System and Services Acquisition

_Session C 填入：SA-8/11/15（SSDF 相關）_

### 1.12 SR — Supply Chain Risk Management

_Session C 填入：SR-3/5/11（SBOM / SLSA 相關）_

### 1.13 MP / PE / PS / AT

_Session D 評估：本系統多為組織流程層（訓練、實體安全、人員管理），部分 N/A_

---

## 2. NIST SP 800-63-3（Digital Identity）

> 原文：https://pages.nist.gov/800-63-3/

### 2.1 AAL（Authenticator Assurance Level）

_Session A 填入：當前 AAL1 / 目標 AAL2（MFA 後）_

### 2.2 IAL（Identity Assurance Level）

_Session A 填入：本系統 IAL1（自我聲明即可）_

### 2.3 FAL（Federation Assurance Level）

_N/A（目前無聯邦身份識別）_

---

## 3. NIST CSF 2.0

> 原文：https://www.nist.gov/cyberframework

### 3.1 GOVERN

_Session D 填入：治理、風險策略、角色責任_

### 3.2 IDENTIFY

_Session C 填入：資產清單、風險評估、供應鏈_

### 3.3 PROTECT

_Session A + B 填入：AC / AT / DS（Data Security）/ IP（Information Protection）/ MA_

### 3.4 DETECT

_Session C 填入：異常事件、持續監控_

### 3.5 RESPOND

_Session C 填入：事件應變、分析、溝通_

### 3.6 RECOVER

_Session C 填入：恢復計畫、改善_

---

## 4. NIST SP 800-218 SSDF（Secure Software Development Framework）

> 原文：https://csrc.nist.gov/Projects/ssdf

### 4.1 PO — Prepare the Organization

_Session C 填入：PO.1/2/3/4/5_

### 4.2 PS — Protect the Software

_Session C 填入：PS.1/2/3_

### 4.3 PW — Produce Well-Secured Software

_Session C 填入：PW.1-9_

### 4.4 RV — Respond to Vulnerabilities

_Session C 填入：RV.1/2/3_

---

## 5. ISO/IEC 25010:2023（軟體品質 8 特性）

> 原文：ISO/IEC 25010:2023 Systems and software engineering - Systems and software quality models

### 5.1 Functional Suitability（功能性）

_Session C 填入_

### 5.2 Performance Efficiency（效能效率）

_Session C 填入_

### 5.3 Compatibility（相容性）

_Session C 填入_

### 5.4 Interaction Capability（使用性）

_Session C 填入_

### 5.5 Reliability（可靠性）

_Session C 填入_

### 5.6 Security（資訊安全）

_交互 reference NIST + OWASP ASVS；Session A/B/C 貢獻_

### 5.7 Maintainability（可維護性）

_Session C 填入，與 C0 分層架構對照_

### 5.8 Portability（可攜性）

_Session C 填入_

### 5.9 Flexibility（彈性，2023 新增）

_Session C 填入_

### 5.10 Safety（安全，2023 新增）

_Session D 填入（涉及事件操作的生命安全）_

---

## 6. ISO/IEC 5055:2021（CWE-based 軟體量測）

> 原文：ISO/IEC 5055:2021 Information technology - Software measurement - Software quality measurement

### 6.1 Reliability

_Session C 填入：CWE 依 ASVS / CIS 輔以測試_

### 6.2 Security

_Session C 填入_

### 6.3 Performance Efficiency

_Session C 填入_

### 6.4 Maintainability

_Session C 填入_

---

## 7. OWASP ASVS 4.0（Level 2）

> 原文：https://owasp.org/www-project-application-security-verification-standard/

### V1-V14 Level 2 requirements

_Session A / B / C 分工填入（V2 Auth, V3 Session, V4 Access Control, V7 Crypto, V8 Data Protection, V9 Comm, V10 Malicious Code, V14 Config）_

---

## 8. CIS Controls v8

> 原文：https://www.cisecurity.org/controls/

### 18 CIS controls

_Session A/B/C 分工填入（Control 1-18），每個 control 的 Safeguard level IG1/IG2_

---

## 9. OWASP SAMM 2.0

> 原文：https://owaspsamm.org/

### 5 Business Functions × 3 Practices × 3 Maturity Levels

_Session C 填入：目標 Level 2（Governance / Design / Implementation / Verification / Operations）_

---

## 10. SLSA v1.0（Supply Chain Integrity）

> 原文：https://slsa.dev/spec/v1.0/

### Build Levels 1-4

_Session C 填入：目標 L2（short-term），L3（long-term, C2-E）_

---

## 11. FEMA NIMS / ICS Doctrine

> 原文：FEMA IS-700, IS-800, NIMS Implementation Plan

### 11.1 Incident Command System 結構

_Session D 填入：與本系統 role / operational period 對應_

### 11.2 Unity of Command

_Session D 填入：對照 C1-A Phase 2 commander of record 機制_

### 11.3 Operational Period / Planning P

_Session D 填入：對照 operational_periods 表設計_

### 11.4 Multi-Agency Coordination（MACS）

_Session D 填入：TAK 整合（Wave 7）_

### 11.5 Resource Management

_Session D 填入：對照 resource_requests + ICS 213RR_

### 11.6 Information Management / Public Information

_Session D 填入_

---

## 12. FEMA ICS 508 表單對應

> 原文：https://training.fema.gov/icsresource/icsforms.aspx

| 表單 | 用途 | 本系統欄位來源 | Status | Cx owner |
|---|---|---|:---:|---|
| ICS 201 | Incident Briefing | events / operational_periods / decisions | _Session D_ | Wave 8 |
| ICS 202 | Incident Objectives | iap_notes（operational_periods） | _Session D_ | Wave 8 |
| ICS 203 | Organization Assignment | accounts + duty_log | _Session D_ | Wave 8 |
| ICS 205 | Communications Plan | pi_nodes + network config | _Session D_ | Wave 8 |
| ICS 206 | Medical Plan | medical-pwa 的 ISBAR 資料 | _Session D_ | Wave 8 |
| ICS 209 | Status Summary | resource_snapshots + events 統計 | _Session D_ | Wave 8 |
| ICS 213RR | Resource Request | resource_requests（新表，Wave 8）| _Session D_ | Wave 8 |
| ICS 214 | Unit Log / Activity Log | duty_log + audit_log | _Session D_ | Wave 8 |
| ICS 215 | Operational Planning Worksheet | resource allocation records | _Session D_ | Wave 8 |
| ICS 215A | IAP Safety Analysis | safety officer notes（operational_periods）| _Session D_ | Wave 8 |

---

## 13. Taiwan 法規對應

### 13.1 資通安全管理法 + 附表十防護基準

_Session D 填入：12 項防護基準對應 NIST 800-53 控制項_

### 13.2 個資法 PDPA

_Session B 填入：個資欄位清單 / 蒐集目的 / 存取稽核 / 72h 通報_

### 13.3 災害防救法

_Session D 填入：演練資料保存 / 應變中心運作 / 跨機關協調_

### 13.4 政府資通安全整體防護計畫（12 項）

_Session D 填入_

---

## Gap Register（統整所有 ⚠️/❌ 項目）

> 格式：`[Control-ID] Priority | Component | Gap | Target Cx | ETA`
> Session A/B/C 發現後彙整，Session D 排序 + 指派 Cx

_（Session 執行時追加）_

---

## Evidence Index（關鍵 control 的實作位置）

> 用途：稽核時快速對應「我們符合 AC-2 帳號管理，請看這些檔案」

_（Session 執行時追加）_

---

## 主張 compliance 的清單（供投標 / 行銷引用）

> 完成 session A/B/C/D 後，此區列出「可對外主張已 comply」的標準 / 控制項清單，搭配實作證據。
>
> **原則**：寧可少說，不誇大。未完成的標記「規劃中（target Cx-X）」，不隱瞞。

_（Session D 結束時填入）_
