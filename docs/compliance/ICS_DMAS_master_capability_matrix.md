# ICS_DMAS Master Capability Matrix

> 本文件是 ICS_DMAS「功能能力總矩陣」的說明版。  
> 詳細可篩選矩陣請見同名 XLSX：`ICS_DMAS_master_capability_matrix.xlsx`。

---

## 1. 目的

本矩陣把前面討論過的功能、商業化、資安、合規、資料治理、驗收與文件治理結論收斂在一個總控架構中。

它不是單純功能清單，而是用來回答：

```text
- 這個 capability 支撐哪條 Golden Path？
- 目前成熟度是 L0/L1/L2/L3/L4 哪一級？
- 做到什麼才算完成？
- 屬於 Demo、Exercise Pro、GovOps 還是 Tactical？
- 是否有 current-stage P0/P1 安全 gate？
- 是否涉及 FEMA/NIMS/HSEEP/NIST/個資等合規要求？
- 對客戶可以怎麼宣稱？
- 要交什麼驗收證據？
```

---

## 2. Golden Paths

| ID | Golden Path | 說明 |
|---|---|---|
| GP1 | TTX → 決策 → AAR | 演訓建立、狀況注入、受訓單位回應、指揮決策、事件時間線、AAR 與改善事項。 |
| GP2 | 現場回報 → COP → 任務/決策 → 回報 | 收容、醫療、前進組或 Field Node 回報進入 COP，指揮部決策並追蹤任務回報。 |
| GP3 | 斷網 → 離線資料 → 恢復同步 → AAR 可追溯 | PWA / Pi / QR 在斷網下暫存與恢復同步，衝突處理後保留來源、時間差與採納狀態。 |
| GP4 | 部署 → 驗收 → 證據包 | 客戶部署、健康檢查、備份還原、測試報告、SBOM、弱掃與驗收文件交付。 |
| GP5 | 真實災害輔助 → IR/DR → 稽核保存 | 支援高敏感資料、事件應變、復原演練、不可竄改紀錄與長期稽核保存。 |

---

## 3. Maturity Levels

| Level | 名稱 | 定義 |
|---|---|---|
| L0 | Not Implemented | 尚未實作，僅存在於 roadmap / backlog。 |
| L1 | Demo | 可演示或 PoC，但不能依賴於正式演訓或真實場景。 |
| L2 | Operational | 可在受控正式演訓中穩定使用，有基本錯誤處理與操作流程。 |
| L3 | Auditable | 具備權限、稽核、證據、測試與可追溯性，可支援採購驗收。 |
| L4 | Mission-ready | 可支援真實災害輔助或高敏感場景，含 IR/DR、加密、外部稽核與操作訓練。 |

---

## 4. Edition Gates

| Edition | 適用定位 |
|---|---|
| Demo / Community | 受控展示、假資料、低敏感資料。 |
| Exercise Pro | 正式演訓、TTX、AAR、基本資安。 |
| GovOps | 政府採購、個資、audit、DR、正式驗收。 |
| Tactical | Field Node、戰術敏感、高安全部署。 |

---

## 5. Capability Matrix 摘要

XLSX 中主表目前納入 34 項 capability，分成以下群組：

```text
- TTX / Exercise
- Command / COP
- Command / Workflow
- Field / PWA
- Field / Sync
- Field / Offline
- Security / Data Integrity
- Security / Sync
- Security / Auth
- Security / Audit
- AAR
- Resource
- ICS / Workflow
- ICS / Reporting
- Ops / Reliability
- Ops / Deployment
- Product / Commercial
- Data Governance
- AI
- Tactical / AI
- Quality / Accessibility
- UX / Field
- Release / Procurement
```

---

## 6. Priority 解讀

| Priority | 意義 |
|---|---|
| P0 | current-stage 必修或會阻斷可信演示 / 正式演訓的安全或產品 gate。 |
| P1 | 進入 Exercise Pro / GovOps 前應完成。 |
| P2 | 正式演訓與採購交付強化項。 |
| P3 | 護城河、完整合規或進階產品能力。 |
| P4 | Tactical / 高敏感場景專屬能力。 |

---

## 7. 如何使用 XLSX

建議用 XLSX 篩選：

```text
- 只看 P0：找 current-stage 阻斷項
- 只看 GP1：確認 TTX → AAR 功能閉環
- 只看 Exercise Pro：確認正式演訓可交付範圍
- 只看 L0/L1：找 demo-only 或尚未成熟的功能
- 只看 Internal Only：避免對外揭露內部弱點細節
- 只看 GovOps：整理政府採購驗收範圍
```

---

## 8. 目前優先結論

第一批應優先處理的 capability：

```text
CAP-012 Snapshot / Sync Trusted Ingest
CAP-013 WebSocket Pre-auth Gate
CAP-010 Pi / Field Node Sync
CAP-011 QR Offline Snapshot
CAP-002 TTX Inject
CAP-025 Product Edition Gate
CAP-026 Claim Language Guardrail
```

這些能力會直接影響：

```text
- COP 資料完整性
- TTX / real session 隔離
- 正式演訓可信度
- 對外宣稱邊界
- GovOps 採購驗收基礎
```

---

## 9. 建議維護方式

```text
- 每個 sprint 更新 Status / Current Maturity / Next Action
- 每個 release 更新 Evidence Required 是否已具備
- 每個商業版本更新 Edition Gate
- 每次重大安全修補更新 Security Gate / Dependency
- 對外文件只引用 Customer Deliverable / Public / Sales Safe 欄位
```

---

## 10. 檔案

```text
docs/product/master_capability_matrix.md
docs/product/master_capability_matrix.xlsx
```
