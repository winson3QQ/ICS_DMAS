---
name: 即將到來的演練
description: 5/31 無線電演練 / 6 月底-7 月初中型演練 / 8/30 無線電演練 — 護城河資料積累關鍵時間點
type: project
---

## 為何重要

每場真實演練 = 一筆 AAR + TTX 場景 JSON 進「演練資料護城河」（commercialization plan v1.x § 護城河閉環）。
3 場 + 既有 10 個情境 = 13 個場景樣本，TTX 場景庫接近商業化最低門檻。

## 排程

| 日期 | 類型 | 規模 | 預期產出 |
|---|---|---|---|
| **2026-05-31** | 無線電演練 | 小型 | 第 11 個場景 JSON + 第 1 筆真實 AAR 原始資料 |
| **2026-06 底 / 07 初** | 中型演練 | medium | 第 12 個場景 + 第 2 筆 AAR；同時是 v2.1.0 投標前壓力測試 |
| **2026-08-30** | 無線電演練 | 小型 | 第 13 個場景 + 第 3 筆 AAR session log |

## 對 Cx / Wave 排程的影響

### v2.1.0 必補（5/31 演練前）— 壓力時點 #1
- **C3-D 自動備份**：演練資料是護城河，演練中故障要能還原
- **C1-A Phase 2 RBAC**：multi-role 演練要對應 ICS 結構
- **C1-D audit log + correlation ID**：真實 AAR 必須有完整 audit trail 才能事後分析

### v2.1.0 完整（6 月演練前）— 壓力時點 #2
- 全部 6 波 Critical Path 完成
- 演練同時驗證 v2.1.0 投標版

### Wave 5 收尾（任何演練前）
- **物資 burn rate 預測線**（剩餘 Wave 5 唯一項目）

## 演練後追蹤

每場演練結束 1 週內：
1. 把演練 session log → TTX 場景 JSON（手工填 disaster_type / scale / key_decision_points）
2. 寫第 N 筆 AAR entry（well / improve / recommend 各 3-5 條）
3. 跨場次 KPI 比較表更新（exercise_kpis 表）
4. compliance matrix evidence 欄位更新（演練實證能補強哪些 control 主張）

## 注意事項

- 5/31 演練可能是公開活動 → 對外口徑須遵守 SECURITY.md「coordinated disclosure」原則
- 中型演練若涉及多個指揮部 / 跨機關 → 是測試 NIMS Multi-Agency Coordination 的好機會
- AAR 資料含 **PII**（病患 / 收容人員）→ 演練後資料存放需符合個資法 §27 安全維護義務（C1-C 三層加密如未完成，需手動隔離保存）

## 風險

| 風險 | 緩解 |
|---|---|
| C3-D 備份未及時做 → 演練中故障無還原 | C3-D 列 v2.1.0 第 1 波優先做 |
| RBAC 未完成 → 演練 role 混用、操作員可改指揮官帳號 | C1-A Phase 2 列第 2 波 |
| 病患 PII 明文 → 演練資料外洩風險 | 演練前完成 C1-C 至少 Fernet 應用層加密 |
