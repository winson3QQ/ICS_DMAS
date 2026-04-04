# 指揮部儀表板規格 v1.0

**文件版本**：v1.0  
**對應程式版本**：staff_v10b（幕僚版）、commander_dashboard.html（指揮官版）  
**狀態**：草稿  
**最後更新**：2026-04

---

## 1. 目的與背景

### 1.1 定位

指揮部儀表板是 ICS_DMAS 系統的決策支援層，負責將各組 PWA 收集的原始資料整合為可供決策的趨勢資訊。

資訊流：

```
收容組 PWA ─┐
醫療組 PWA ─┼──→ 指揮部 Pi (calc_engine) ──→ 指揮部儀表板
前進組 PWA ─┘
```

### 1.2 使用情境

演習時所有人員（含指揮官）在同一空間共同使用，扁平化決策。儀表板顯示於共用螢幕，作為討論的共同認知基礎。

### 1.3 核心設計原則

- **趨勢優先**：主視角是歷史趨勢，當下截面是趨勢的最新一個點
- **按問題組織**：四張圖按「要回答的問題」分，不按組別分
- **層層展開**：趨勢 → 切面 → 個別資料，按需深入
- **自動分析**：把圖表訊號轉為文字結論，減少解讀負擔

---

## 2. 版面架構

### 2.1 整體版面

```
┌─────────────────────────────────────────────┐
│ HEADER（48px）：logo + 時鐘 + 摘要 + 指標   │
├─────────────────────────────────────────────┤
│ 分析列（28px）：自動產生的趨勢警示文字      │
├──────────────────┬──────────────────────────┤
│  ① 量能壓力      │  ② 流量來源              │
│  收容+醫療床位%  │  A/B/C來源堆疊+待入站    │
├──────────────────┼──────────────────────────┤
│  ③ 橋接訊號      │  ④ 資源                  │
│  SRT Red+→醫療紅 │  人力+物資消耗           │
└──────────────────┴──────────────────────────┘
```

點任何圖的時間點 → 切面 Modal（v9 邏輯）  
切面 Modal 包含趨勢分析文字

### 2.2 Header（48px）

| 區塊 | 內容 |
|---|---|
| 左 | ICS logo、版本、時鐘 |
| 中 | 自動摘要：量能%、主要來源、橋接狀態、資源警示 |
| 右 | 醫療警戒倒數、主要來源標示、最後更新時間 |
| 最右 | 連線狀態指示燈 |

### 2.3 分析列（28px）

常駐於 Header 下方，自動產生最多 5 條異常警示，格式：

```
🔴 醫療量能加速上升 · ⚠️ B來源上升（收容轉送壓力轉移）· 🔴 IV輸液35分見底 · 🔗 SRT橋接延遲觸發
```

無異常時顯示：`✅ 目前無異常趨勢`

---

## 3. 四張趨勢圖規格

時間軸：過去 N 筆快照，預設 12 筆（由後端 `shelter_history` / `medical_history` 提供）。

### 3.1 圖① 量能壓力

**目的**：回答「現在多嚴重、兩組是否同步」

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 收容床位% | `shelter_history[].bed_used/bed_total` | 黃 | 實線+填色 |
| 醫療床位% | `medical_history[].bed_used/bed_total` | 紅 | 實線+填色 |
| 警戒線 70% | 固定 | 藍虛線 | — |
| 危急線 90% | 固定 | 紅虛線 | — |

Y軸：0–100%，X軸：時間標籤

### 3.2 圖② 流量來源

**目的**：回答「壓力從哪來、為什麼」

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 來源A（前進組）累計 | `medical_history[].src_a` | 藍 | 堆疊長條 |
| 來源B（收容轉送）累計 | `medical_history[].src_b` | 黃 | 堆疊長條 |
| 來源C（自行抵達）累計 | `medical_history[].src_c` | 綠 | 堆疊長條 |
| 收容待入站人數 | `shelter_history[].pending_intake` | 藍虛線 | 折線疊加 |

Y軸：人數，X軸：時間標籤

**決策含義**：
- B 佔比上升 → 根源在收容端，確認 SRT 篩選
- A 持續輸入 → 確認前進組狀況，評估是否需準備下一階段
- C 突然出現 → 確認外圍是否有新的壓力來源

### 3.3 圖③ 橋接訊號

**目的**：回答「下一波壓力何時從收容轉移至醫療」

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| SRT Red+ 人數 | `shelter_history[].srt_red` | 紅 | 實線+填色 |
| 醫療紅色傷患數 | `medical_history[].casualties_red` | 黃 | 實線+填色 |

Y軸：人數，X軸：時間標籤

**解讀邏輯**：SRT Red+ 上升後約 15 分鐘，醫療紅色傷患跟進。此延遲是決策窗口。

### 3.4 圖④ 資源

**目的**：回答「還能撐多久」

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 收容值勤人力% | `shelter_history[].staff_on_duty/max` | 藍 | 虛線 |
| 醫療值勤人力% | `medical_history[].staff_on_duty/max` | 紫 | 虛線 |
| IV 輸液存量% | `medical_history[].supplies.iv/iv_max` | 紅 | 實線 |
| 氧氣瓶存量% | `medical_history[].supplies.oxygen/oxy_max` | 黃 | 實線 |
| 止血帶存量% | `medical_history[].supplies.tourniquet/tour_max` | 綠 | 實線 |
| 危急線 20% | 固定 | 紅虛線 | — |

**解讀邏輯**：人力（虛線）和物資（實線）對照，找出最早見底的限制條件。

---

## 4. 切面互動規格

### 4.1 觸發方式

點擊任何圖表中的時間點（資料點圓點），觸發切面 Modal。

> **【單螢幕設計】** 儀表板顯示於共用螢幕，所有人員共同觀看。
> 點擊時間點展開切面 Modal，展示給全員看，不需多裝置同步。
> 未來若改為多裝置，切面展開邏輯不需改動，只需加入 URL 路由即可。

### 4.2 切面 Modal 內容

**標題**：`切面快照 · HH:MM`

**第一區：雙組並排**

| 收容組 | 醫療組 |
|---|---|
| 床位使用（數字+進度條） | 床位使用（數字+進度條） |
| 待入站人數 | 傷患分類橫條（紅黃綠黑） |
| 值勤人員 | 等待進入 / 待後送 / 值勤 |
| SRT 分布橫條 | — |

**第二區：來源分析**

三個色塊並排顯示 A/B/C 累計人數，下方自動產生來源診斷文字：
- A 為主 → `▶ 主要來自前進組，確認前線傷患狀況`
- B 為主 → `▶ 主要來自收容轉送，SRT 篩選壓力轉移中`
- C 為主 → `▶ 主要自行抵達，確認外圍壓力來源`

**第三區：物資狀況**

IV / 氧氣瓶 / 止血帶各一條進度條，顏色依剩餘量變化（>40% 綠、20–40% 黃、<20% 紅）

**第四區：趨勢分析（自動產生）**

比較當前時間點與前 3 筆快照的差值，以條列文字呈現：

- 床位在過去 15 分鐘的變化（+N%）
- SRT 橋接狀態（已觸發 / 尚未觸發 + 預計時間）
- 物資消耗速率 + 預計見底時間
- 來源比例變化 + 對應裁示建議

### 4.3 第三層（Phase 2）

點切面中的傷患或收容者數字，展開個別人員列表。

**需要後端支援**：
```
GET /api/patients?before={timestamp}        # 醫療組 Pi
GET /api/residents?before={timestamp}       # 收容組 Pi
```

單 Pi 模式：直接查本地 SQLite  
多 Pi 模式：透過環境變數設定各組 Pi IP

---

## 5. 自動分析算法

### 5.1 斜率計算

```javascript
// 比較最近3筆平均 vs 最初3筆平均
function slope(arr) {
  const n = arr.length;
  const recent = (arr[n-1]+arr[n-2]+arr[n-3])/3;
  const early  = (arr[0]+arr[1]+arr[2])/3;
  return recent - early;
}
```

### 5.2 物資見底預估

```javascript
// 按目前消耗速率，N 分鐘後達到門檻
function minsUntil(current, threshold, ratePerSnap, snapMins) {
  if (ratePerSnap <= 0) return null;
  return Math.round(((current - threshold) / ratePerSnap) * snapMins);
}
```

### 5.3 分析列觸發條件

| 觸發條件 | 警示文字 | 顏色 |
|---|---|---|
| 醫療床位斜率 > 15% | 醫療量能加速上升 | 紅 |
| 醫療床位斜率 > 5% | 醫療量能持續上升 | 黃 |
| 收容床位斜率 > 20% | 收容量能加速 | 黃 |
| B 來源速率 > 0.3/筆 | B來源（收容轉送）上升 | 黃 |
| A 來源速率 > 0.3/筆 | A來源（前進組）持續輸入 | 藍 |
| SRT Red+ 上升且醫療紅傷跟進 | SRT橋接延遲已觸發 | 紅 |
| IV 剩餘 < 60 分鐘 | IV輸液 N 分見底 | 紅 |
| 氧氣瓶剩餘 < 60 分鐘 | 氧氣瓶 N 分見底 | 黃 |
| 醫療人力斜率 < -10% | 醫療人力下降 | 黃 |
| 醫療床位 ≥ 70% 且距 90% < 30 分 | 醫療危急倒數 N 分 | 紅 |

---

## 6. 後端 API 變更需求

### 6.1 `/api/dashboard` 新增欄位

```python
# main.py - get_dashboard()
shelter_history = db.get_snapshots("shelter", limit=12)
medical_history = db.get_snapshots("medical", limit=12)

return {
  "calc": { ... },           # 現有欄位不變
  "events": [ ... ],
  "decisions": { ... },
  "shelter_history": shelter_history,   # 新增
  "medical_history": medical_history,   # 新增
}
```

### 6.2 快照欄位需求

每筆快照需包含：

**收容組快照（shelter_history）**

```json
{
  "timestamp": "2026-04-15T10:30:00",
  "bed_used": 38,
  "bed_total": 80,
  "pending_intake": 4,
  "staff_on_duty": 7,
  "srt_red": 3,
  "srt_yellow": 12,
  "srt_green": 23
}
```

**醫療組快照（medical_history）**

```json
{
  "timestamp": "2026-04-15T10:30:00",
  "bed_used": 5,
  "bed_total": 10,
  "waiting_count": 2,
  "pending_evac": 1,
  "casualties_red": 2,
  "casualties_yellow": 4,
  "casualties_green": 8,
  "casualties_black": 1,
  "staff_on_duty": 5,
  "src_a": 3,
  "src_b": 2,
  "src_c": 0,
  "supplies": {
    "iv": 6,
    "oxygen": 3,
    "tourniquet": 22
  },
  "supplies_max": {
    "iv": 10,
    "oxygen": 5,
    "tourniquet": 30
  }
}
```

> **【自動推算】** `staff_on_duty` 由 PWA 自動計算，無需手動填入。
>
> 計算邏輯（最近30分鐘內有操作記錄的不重複人員數）：
> - **收容組**：`persons[].intake_log[].by` + `incidents.reported_by` + `audit_log.operator_name`（排除系統動作）
> - **醫療組**：`triages.triage_by` + `patients.operator_name`
>
> 推算值顯示於 QR 通報 modal 供組長確認，若推算為 0 則 fallback 至手動輸入值。

> **物資初始值（`supplies_max`）**：由醫療組組長在演習前設定，存於醫療 PWA config 表，
> 推送快照時帶入 `extra.supplies_max`。儀表板用 `supplies_max` 計算消耗百分比和見底時間，不使用寫死常數。

### 6.3 第三層 API（Phase 2）

```python
# 醫療組 Pi
GET /api/patients?before={iso_timestamp}

# 收容組 Pi
GET /api/residents?before={iso_timestamp}
```

環境變數設定（`config.yaml`）：

```yaml
SHELTER_PI_URL: "http://localhost:8001"   # 單Pi
MEDICAL_PI_URL: "http://localhost:8002"   # 單Pi

# 多Pi時改為各組靜態IP
# SHELTER_PI_URL: "http://192.168.1.10:8001"
# MEDICAL_PI_URL: "http://192.168.1.11:8002"
```

---

## 7. 實作路線圖

| 版本 | 內容 | 狀態 |
|---|---|---|
| v1.0 | 四張趨勢圖 + 切面 Modal + 分析列（mock 資料） | ✅ staff_v10b 完成 |
| v1.1 | 接後端真實資料（`shelter_history` + `medical_history`） | 🔲 待實作 |
| v1.2 | 第三層個別人員展開（單 Pi 模式） | 🔲 待實作（Phase 2）|
| v1.3 | 多 Pi 網路模式切換 | 🔲 待實作（Phase 3）|

---

## 8. 待確認事項

| 編號 | 問題 | 影響 |
|---|---|---|
| D-01 | 快照頻率：收容/醫療多久推一筆快照？ | 影響圖表時間軸密度 |
| D-02 | 人力 max 值：收容最大值勤人數為幾人？醫療？ | 影響圖④人力% 計算 |
| D-03 | 物資初始值是否固定？ | 影響消耗速率計算基準 |
| D-04 | ✅ 已確認：單一共用螢幕 | 互動設計以觸控/點擊展開為主，不需多裝置同步 |

---

*文件版本：v1.0 | 狀態：草稿 | 對應程式：staff_v10b.html*
