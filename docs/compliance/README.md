# ICS_DMAS Compliance Program

> **用途**：對外可用於投標 / 行銷 / 稽核；對內作為工作根據。
> **原則**：盡量蒐集公開資訊並符合；無法主張的項目明確標示、不誇大。
> **建立日期**：2026-04-25
> **最後 review**：2026-04-25

---

## 文件結構（僅 3 份新增，其餘擴充既有）

| 檔案 | 用途 | 對外用途 |
|---|---|---|
| [matrix.md](matrix.md) | 控制項 × 組件 × 狀態對照表（主 deliverable）| 投標附件、稽核 evidence、行銷 claim 依據 |
| [threat_model.md](threat_model.md) | STRIDE 威脅模型 + 信任邊界圖 | 資安架構說明（800-53 RA-3 要求）|
| [security_policies.md](security_policies.md) | 6 份政策一檔：InfoSec / AC / AU / IR / CP / Privacy | 800-53 xx-1 family 要求，稽核必備 |

### 既有文件的對應角色（不重複建新檔）

| 既有文件 | 在 compliance 的角色 |
|---|---|
| [docs/ROADMAP.md](../ROADMAP.md) | 每個 Cx 項目標註「適用標準」— matrix row 的反向索引 |
| [docs/commercialization_plan_v1.md](../commercialization_plan_v1.md) | 「標準 compliance」章節作為行銷 / 競標對外表述（Session D 補） |
| [.claude/memory/architecture_decisions.md](../../.claude/memory/architecture_decisions.md) | Compliance 架構決策條目（指向本資料夾） |
| [CLAUDE.md](../../CLAUDE.md) | 入口指引 |

---

## 涵蓋標準（已鎖定）

### 資安（必須 comply）
- **NIST SP 800-53 Rev. 5** — Moderate baseline
- **NIST SP 800-63-3** — Digital Identity
- **NIST CSF 2.0** — 組織框架
- **NIST SP 800-218 SSDF** — Secure Software Development Framework
- **FEMA NIMS doctrine** + **ICS 508 表單系列**（201 / 202 / 209 / 213RR / 214 / 215 / 215A）

### 軟體品質（競標 / 行銷用）
- **ISO/IEC 25010:2023**（品質 8 特性）
- **ISO/IEC 5055:2021**（CWE-based 軟體量測）
- **CNS 25010**（Taiwan 對應）
- **OWASP ASVS 4.0 Level 2**
- **CIS Controls v8**

### 開發流程成熟度（競標差異化）
- **OWASP SAMM 2.0**
- **SLSA v1.0**（供應鏈）
- **DORA metrics**（現代 SaaS 標配）

### Taiwan 政府標案
- **資通安全管理法** + **附表十防護基準**
- **個資法 PDPA** + **災害防救法**
- **行政院政府資通安全整體防護計畫** 12 項防護基準

### 明確不納入（以免誇大）
- ISO 27001 外部驗證（C6 才做，需第三方 auditor）
- FedRAMP / HIPAA（非 Taiwan 市場）
- CMMI（對小團隊過重）

---

## Audit Session 計劃（4 段式，依現有 Cx 家族切）

### Session 狀態

| Session | 範圍 | 對應 Cx | 狀態 | 產出 |
|:---:|---|---|:---:|---|
| **A** | Auth / Transport / Schema | C0 + C1-A + C1-B + C1-E | ⏸ 未開始 | matrix §NIST AC / IA / SC / AU 對應列 |
| **B** | PII / Audit / Frontend | C1-C + C1-D + C1-F + W-C1-* + P-C1-* | ⏸ 未開始 | matrix §MP / SC / PII + 個資法列 |
| **C** | Quality / Deploy / Ops | C2 + C3 + P-C2-* / W-C2-* | ⏸ 未開始 | matrix §SSDF / ISO 25010 / SAMM / SLSA / DORA 列 |
| **D** | NIMS + ICS 508 + 整合 | Wave 功能 + 整合所有 session | ⏸ 未開始 | master matrix + threat_model + policies 完稿 + commercialization_plan 擴充 |

### Session 順序：A → B → C → D
Session D 的 threat model + policies 需要 A/B/C 的發現當素材，最後寫最有效率。

### 每個 Session 的工作流

1. **開始**：讀本 README + 讀 matrix.md 的「session log」區塊 → 知道前面做到哪
2. **執行**：深度讀程式碼（架構層，非 line-by-line）→ 對照標準 → 填 matrix
3. **結束**：更新 matrix「session log」區塊（下次 session 要的 context）→ 提交摘要給使用者
4. **不 commit，等使用者審閱後再處理 git**

---

## Session 交接機制（避免換 session 失憶）

### matrix.md 內建「Session Log」區塊

每個 session 結束前**必須**在 matrix.md 頂部的 session log 更新：
- 這 session 完成了哪些 control family
- 發現的重大 gap（需要新 Cx 或重新排序 roadmap 的）
- 下個 session 需要特別注意的 context
- 讀過哪些檔案（避免重讀，浪費 context window）

### 每個 session 結束時的 checklist

- [ ] matrix.md 對應 section 填完
- [ ] matrix.md session log 更新
- [ ] 重大 gap 是否影響 ROADMAP.md → 如有，同步更新
- [ ] 有新架構決策 → 同步 architecture_decisions.md
- [ ] 產出摘要給使用者（哪些已 comply、哪些需補 / 用哪個 Cx 補 / 優先級）

---

## 閱讀順序建議

- **第一次閱讀**：README.md（本檔）→ matrix.md meta + session log → 了解進度與整體架構
- **投標 / 行銷用**：matrix.md 摘要表 + commercialization_plan_v1.md § compliance 章節
- **稽核用**：matrix.md 完整表 + policies + threat_model + evidence（code 連結）
- **開發 / 修補用**：ROADMAP.md 看 Cx 對應標準 → matrix.md 看具體 gap → 程式碼修補
