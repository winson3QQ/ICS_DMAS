# 指揮部儀表板規格 v1.3

**文件版本**：v1.3
**對應程式版本**：command-v0.2.0（staff_v13.html）
**狀態**：實作中
**最後更新**：2026-04-05

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

演習時所有人員（含指揮官）在同一空間共同使用。儀表板投影於共用螢幕，作為討論的共同認知基礎。投影距離約 3 米，全域最小字體 18px。

- **指揮官**：掃 Zone A 態勢燈 + 一句話結論，0.5 秒掌握態勢
- **幕僚**：看地圖據點分佈 + 側欄 sparkline 趨勢，提供分析和建議
- **共同**：點擊地圖據點展開切面和資料，作為討論依據

### 1.3 核心設計原則

- **認知分層**：Zone A（態勢燈）→ Zone B（地圖+sparkline）→ 切面 Modal → 個別資料，對應「有事嗎→在哪裡→多嚴重→怎麼辦」
- **地理佈局優先**：以演訓場地地圖為核心，據點標記取代純數字圖表（參考韓國 ED Dashboard PMC6284143）
- **面積 = 重要性**：地圖佔 64%，是最大元素（Stephen Few 原則）
- **色彩即訊號**：紅/黃/綠直接傳達嚴重度，不需查表解讀
- **自動分析**：把圖表訊號轉為文字結論，減少解讀負擔
- **趨勢優先**：側欄 sparkline 顯示歷史趨勢，地圖據點是趨勢的最新一個點
- **行動項目放底部**：倒數和升降級在 Zone C（軍事 C2 慣例）

---

## 2. 版面架構（三區投影佈局）

參考來源：FEMA EOC Quick Reference、韓國 ED Dashboard (PMC6284143)、軍事 C2 Battle Rhythm Board、Stephen Few Dashboard Design

### 2.1 整體版面

深色主題（`#0d1117` 背景），適合投影環境。

```
┌───────────────────────────────────────────────────────────┐
│ ZONE A — 態勢速讀（高度 64px）                             │
│ ┌─────────┐                                        ┌───┐ │
│ │ 🟢 正常  │ 14:32 運作2h12m │ 收52/醫18 │ 摘要文字  │DCI│ │
│ │ 態勢燈   │                                       │ 87│ │
│ └─────────┘                                        └───┘ │
├──────────┬──────────────────────────────┬─────────────────┤
│ 左側欄    │ ZONE B 中 — 互動地圖（~64%） │ 右側欄           │
│ (~18%)   │                              │ (~18%)          │
│          │  [演訓場地圖]                 │                 │
│ ① 量能   │                              │ ④ 物資          │
│ sparkline│  📌收容所    🚑醫療站         │ sparkline       │
│          │  52人/78%    18人/R:3         │                 │
│ ② 流向   │     ╲                        │ ⑤ 人力          │
│ sparkline│      ╲──→  流向箭頭          │ sparkline       │
│          │             ⚠️事件×2         │                 │
│ ③ 事件   │                              │                 │
│ sparkline│  🚑後送點                     │                 │
│          │  待撤:3                       │                 │
├──────────┴──────────────────────────────┴─────────────────┤
│ ZONE C — 決策倒數 + 升降級（高度 52px）                     │
│ ┌────────────┐ ┌────────────┐ ┌──────────────────────────┐│
│ │ 💉 IV 見底  │ │ 🛏 容量飽和 │ │ 📋 升級觸發              ││
│ │  45 分鐘    │ │  2h+       │ │ ESC-CAP ⚠️ 已持續30m    ││
│ └────────────┘ └────────────┘ └──────────────────────────┘│
└───────────────────────────────────────────────────────────┘
```

**側欄分類（EOC situation→resources 模式）**：
- 左側欄（態勢面）：量能壓力、流向橋接、事件態勢
- 右側欄（資源面）：物資消耗、人力負荷

點擊地圖據點 → 切面 Modal（資訊層）
切面中點數字 → 展開個別資料（資料層，Wave 5）

### 2.2 Zone A（64px）— 指揮官的 0.5 秒

| 區塊 | 內容 |
|---|---|
| 左 | 態勢燈（RAG 三色圓形） + 態勢文字（警報/注意/正常） |
| 中 | 時鐘 HH:MM:SS + 運作時間 + 收容/醫療人數摘要 + 一句話分析 |
| 右 | DCI 數字 + 快照計數 + 連線狀態 |

**一句話分析**：取當前最嚴重的 2-3 個訊號，組成因果句。

範例：
- `🔴 醫療量能上升中，主因前進組持續送入。3 起安全威脅未結案，人力負擔偏高。`
- `🟡 收容佔床率超過 70%，物資消耗速率正常。`
- `🟢 各組運作正常，無異常趨勢。`

### 2.3 Zone B — 地圖 + 側欄 sparkline

#### 2.3.1 雙地圖（tab 切換）

| Tab | 地圖檔案 | 用途 |
|-----|---------|------|
| **站內** | ICS_Campus_map.jpg | 收容/醫療/後送據點 |
| **站外** | Satellite_map.png | 前進組搜索範圍 |

預設顯示「站內」，點擊 tab 切換。地圖以 `object-fit:contain` 填充。

#### 2.3.2 地圖據點標記

據點標記用 `position:absolute` overlay 在地圖上，座標以百分比定義（不受圖片縮放影響）。

**標記樣式**：
- 純 emoji icon（無外圈），`font-size:14px`，帶 `drop-shadow`
- hover → 顯示名稱 + 統計數字
- click → 固定顯示（pin toggle）
- dblclick → 打開切面 modal

**標記類型（node_type）**：

| 類型 | 說明 | 資料綁定 |
|------|------|---------|
| shelter | 收容據點 | 顯示床位使用% |
| medical | 醫療據點 | 顯示床位%+紅色傷患 |
| forward | 前進據點 | 未來綁定前進快照 |
| security | 安全據點 | 未來綁定安全快照 |
| emergency | 緊急事件 | 地圖標記用 |
| （一般） | 靜態標記 | 無資料綁定 |

**可用 icon**：📌（靜態標記）、🚑（救護）、⚠️（事件）、👤（人員/五縱）

#### 2.3.3 地圖編輯模式

點擊 ⚙ 齒輪進入編輯模式：
- 拖曳標記調整位置（顯示即時座標百分比）
- 新增標記（選擇 icon + 類型 → 放置在地圖中央）
- 刪除選中標記
- 儲存 → `POST /api/map_config` 寫回 `map_config.json`

#### 2.3.4 map_config.json 格式

```json
{
  "maps": {
    "indoor": {
      "image": "ICS_Campus_map.jpg",
      "label": "站內",
      "zones": [
        {
          "id": "custom_1234567890",
          "label": "收容所",
          "sub": "",
          "x_pct": 45.2,
          "y_pct": 55.1,
          "node_type": "shelter",
          "icon": "📌"
        }
      ],
      "flows": []
    },
    "outdoor": {
      "image": "Satellite_map.png",
      "label": "站外",
      "zones": [],
      "flows": []
    }
  }
}
```

據點由使用者在編輯模式動態設定，無預設值。換場地只需更換圖片 + 重新定位。

#### 2.3.5 側欄 sparkline

每張 sparkline 用小 Canvas（寬度 100%，高度 ~60px），標題列整合 RAG 色點。

| 位置 | 編號 | 名稱 | 資料來源 |
|------|------|------|---------|
| 左 | ① | 量能 | 收容+醫療床位% |
| 左 | ② | 流向 | A/B/C 來源 + SRT→醫療橋接 |
| 左 | ③ | 事件 | 嚴重度堆疊 + 未結事件 |
| 右 | ④ | 物資 | IV/氧氣/止血帶/毛毯/飲水 burn rate |
| 右 | ⑤ | 人力 | 收容+醫療 staff_ratio |

### 2.4 Zone C（52px）— 決策倒數 + 升降級

Wave 1 佔位，Wave 2-3 填入：
- 左半：Decision Countdown pill（物資見底、容量飽和、人力超載）
- 右半：Escalation / De-escalation 規則狀態

---

## 3. 四張趨勢圖規格

時間軸：後端提供最近 100 筆快照，前端以 viewport 12 筆顯示，可透過 ◀▶ 按鈕左右滑動瀏覽歷史。

### 3.1 圖① 量能壓力

**回答**：「還有多少空間？兩組是否同步？」

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 收容床位% | `shelter.bed_used / bed_total` | 橘 `#E67E22` | 實線+填色 |
| 醫療床位% | `medical.bed_used / bed_total` | 深紅 `#C0392B` | 實線+填色 |
| 收容等候人數 | `shelter.pending_intake` | 藍虛線 | 右Y軸 |
| 醫療待後送 | `medical.pending_evac` | 紫虛線 | 右Y軸 |
| 警戒線 70% | 固定 | 藍虛線 | — |
| 危急線 90% | 固定 | 紅虛線 | — |

**背景色觸發**：max(兩組佔床率) ≥ 90% → 淡紅；≥ 70% → 淡黃

**決策含義**：
- 兩條線同步上升 → 全線壓力，考慮啟動備援
- 只有一組上升 → 局部瓶頸，跨組調度
- 等候/待後送線上升 → 入口或出口堵塞

### 3.2 圖② 流向與橋接

**回答**：「壓力從哪來？下一波何時到？」

合併原 v1.0 的「流量來源」和「橋接訊號」，因為它們是同一條因果鏈。

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 來源 A（前進組）累計 | `medical.extra.src_a` | 深藍 `#1565C0` | 堆疊長條 |
| 來源 B（收容轉送）累計 | `medical.extra.src_b` | 深橘 `#E65100` | 堆疊長條 |
| 來源 C（自行抵達）累計 | `medical.extra.src_c` | 深綠 `#2E7D32` | 堆疊長條 |
| SRT Red+ 人數 | `shelter.srt.red` | 紅 `#E74C3C` | 折線 |
| 醫療紅色傷患 | `medical.casualties.red` | 琥珀 `#FF8F00` | 折線 |
| 收容待入站 | `shelter.pending_intake` | 灰虛線 | 疊加 |

**背景色觸發**：B 來源速率 > 0.3/筆 或 SRT Red+ 斜率 > 0 且醫療紅傷未跟進 → 淡黃

**決策含義**：
- A 持續上升 → 前進組一直拉人進來，確認前線狀況
- B 上升 → 收容端篩出問題，SRT 壓力轉移至醫療
- SRT Red+ 上升但醫療紅傷未跟進 → 約 15 分鐘後會到，這是決策窗口
- C 突然出現 → 外圍有新壓力來源

### 3.3 圖③ 事件態勢

**回答**：「現場穩嗎？往哪個方向走？」

這是 v1.1 新增的獨立維度。事件是獨立的壓力來源——不安全的環境、安全威脅、傳染疑慮等不反映在床位數字上，但直接影響運作。

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 高嚴重度事件數（兩組合計） | `incident_pressure.high` | 紅 | 堆疊面積 |
| 中嚴重度事件數（兩組合計） | `incident_pressure.medium` | 黃 | 堆疊面積 |
| 低嚴重度事件數（兩組合計） | `incident_pressure.low` | 綠 | 堆疊面積 |
| 未結事件數（累計） | `incident_backlog.open_total` | 白折線 | 疊加 |
| 結案速率（30min 滑動窗口） | `incident_backlog.resolved_rate` | 灰虛線 | 疊加 |

**背景色觸發**：max(兩組 IPI) ≥ 6 → 淡紅；≥ 3 → 淡黃

**決策含義**：
- 堆疊面積變厚 + 紅色佔比上升 → 情勢惡化
- 未結線上升 + 結案線持平 → 事件積壓，人力分配有問題
- 同類型事件密集出現 → 系統性問題，改流程而非加人
- 突然出現高嚴重度 → 情境轉變，啟動對應計畫

### 3.4 圖④ 資源

**回答**：「還能撐多久？誰需要支援？」

| 資料系列 | 來源 | 顏色 | 樣式 |
|---|---|---|---|
| 收容人均服務量 | `extra.staff_ratio`（收容） | 藍 `#1976D2` | 實線 |
| 醫療人均服務量 | `extra.staff_ratio`（醫療） | 紫 `#7B1FA2` | 實線 |
| IV 輸液存量% | `extra.supplies.iv / supplies_max.iv` | 紅 `#D32F2F` | 虛線 |
| 氧氣瓶存量% | `extra.supplies.oxygen / supplies_max.oxygen` | 琥珀 `#F57F17` | 虛線 |
| 止血帶存量% | `extra.supplies.tourniquet / supplies_max.tourniquet` | 綠 `#388E3C` | 虛線 |
| 危急線 20% | 固定 | 紅虛線 | — |

**人均服務量**：從實際操作紀錄推算活躍人員數（30 分鐘內有操作的不重複人員），而非手動輸入。
```
人均服務量 = 在場服務對象 / 活躍操作員數
```

**背景色觸發**：任一物資 < 20% 或人均服務量超紅線 → 淡紅

**決策含義**：
- 人均服務量一組高另一組低 → 從閒的調到忙的
- 物資線陡降 → 預估見底時間，提前請求補給
- 人力和物資同時緊繃 → 最危險，需要外部增援

---

## 4. 切面互動規格（資訊層）

### 4.1 觸發方式

點擊任何圖表中的時間點（資料點圓點），觸發切面 Modal。

### 4.2 切面 Modal 內容

**標題**：`切面快照 · HH:MM`

**第一區：雙組並排**

| 收容組 | 醫療組 |
|---|---|
| 床位使用（數字+進度條） | 床位使用（數字+進度條） |
| 待入站人數 | 傷患分類橫條（紅黃綠黑） |
| 值勤人員（活躍/總） | 等待進入 / 待後送 / 值勤 |
| SRT 分布橫條 | — |

**第二區：來源分析**

三個色塊並排顯示 A/B/C 累計人數，下方自動產生來源診斷文字：
- A 為主 → `▶ 主要來自前進組，確認前線傷患狀況`
- B 為主 → `▶ 主要來自收容轉送，SRT 篩選壓力轉移中`
- C 為主 → `▶ 主要自行抵達，確認外圍壓力來源`

**第三區：事件摘要**

```
事件壓力（最近 30 分）
  收容：高 1 / 中 2 / 低 0（IPI: 5）→ 安全威脅、量能超載
  醫療：高 0 / 中 1 / 低 0（IPI: 1）→ 物資短缺
未結事件：收容 4 / 醫療 2　結案速率：3 件/30min
```

**第四區：物資狀況**

IV / 氧氣瓶 / 止血帶各一條進度條，顏色依剩餘量變化（>40% 綠、20–40% 黃、<20% 紅）

**第五區：人力效率**

| 收容組 | 醫療組 |
|---|---|
| 活躍人員 N 人 | 活躍人員 N 人 |
| 人均服務量 N 人/人 | 人均服務量 N 人/人 |
| 卡關人數 N 人（N%） | — |
| CMIST 複雜度 N% | — |

**第六區：趨勢分析（自動產生）**

比較當前時間點與前 3 筆快照的差值，以條列文字呈現：

- 床位在過去 15 分鐘的變化（+N%）
- SRT 橋接狀態（已觸發 / 尚未觸發 + 預計時間）
- 物資消耗速率 + 預計見底時間
- 來源比例變化 + 對應裁示建議
- 事件嚴重度遷移方向

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
  if (n < 4) return 0;
  const recent = (arr[n-1]+arr[n-2]+arr[n-3])/3;
  const early  = (arr[0]+arr[1]+arr[2])/3;
  return recent - early;
}
```

### 5.2 物資見底預估

```javascript
function minsUntil(current, threshold, ratePerSnap, snapMins) {
  if (ratePerSnap <= 0) return null;
  return Math.round(((current - threshold) / ratePerSnap) * snapMins);
}
```

### 5.3 IPI 事件壓力指數

```
IPI = 高嚴重度事件數 × 3 + 中嚴重度事件數 × 1
```

計算範圍：最近 30 分鐘內新開的事件（`opened_at` 或 `reported_at` ≥ cutoff）。低嚴重度不計入 IPI 但仍顯示在堆疊圖中。

**門檻**：
- IPI ≥ 6：🔴 現場高壓
- IPI 3–5：🟡 壓力上升
- IPI 0–2：🟢 正常

**事件三維指標**（切面展示用）：

| 指標 | 算法 | 意義 |
|---|---|---|
| 新開密度 | 30min 內新通報事件數 | 當前壓力輸入速率 |
| 未結負荷 | status ≠ 已結案的事件總數 | 累積壓力 |
| 結案速率 | 30min 內結案事件數 | 團隊消化能力 |

**組合判讀**：
- 新開多 + 未結多 + 結案少 → 壓力累積，消化不了
- 新開多 + 未結少 + 結案多 → 有壓力但消化得了
- 新開少 + 未結多 + 結案少 → 歷史積壓

**事件叢集偵測**：
- 同類型事件 30min 內 ≥ 3 起 → 系統性問題警示
- 嚴重度從低往高遷移 → 情勢升級警示

### 5.4 人均服務量（從操作紀錄推算）

**活躍人員數**：最近 30 分鐘內有操作紀錄的不重複操作員。

資料來源（兩組共通）：
- `audit_log`（排除系統動作：login、snapshot、qr_generated、full_data_destroy）
- `incidents.reported_by`、`incidents.notes[].by`

額外資料來源（收容組）：
- `persons.intake_log[].by`

額外資料來源（醫療組）：
- `patients.operator_name`（建檔）
- `triages.triage_by`（檢傷）

**人均服務量**：
```
收容：在場人數（非已離站）/ 活躍操作員數
醫療：在場傷患（非已離區）/ 活躍操作員數
```

**門檻**：

| 等級 | 收容 | 醫療 |
|---|---|---|
| 🟢 正常 | < 8 人/人 | < 3 人/人 |
| 🟡 偏高 | 8–12 人/人 | 3–5 人/人 |
| 🔴 危險 | > 12 人/人 | > 5 人/人 |

### 5.5 物資消耗速率（burn_rate）— v1.3 新增

`calc_engine.burn_rate(snapshots, supply_key)` 從最近 N 筆快照的 `extra.supplies[key]` 計算差分消耗速率。

**輸入**：快照序列 + 物資鍵名（如 `iv`, `blanket`）
**輸出**：

| 欄位 | 說明 |
|------|------|
| `rate_per_min` | 每分鐘消耗量 |
| `current` | 當前存量 |
| `pct_remaining` | 剩餘百分比 |
| `time_to_zero_min` | 預計歸零分鐘數 |
| `level` | ok / warn / crit |

**門檻**：
- `< 2h` → crit
- `< 4h` → warn
- `≥ 4h` → ok

### 5.6 通訊健康度（comm_health）— v1.3 新增

`calc_engine.comm_health(snapshots, node_type, thresholds)` 綜合 freshness + 間隔異常 + 欄位歸零偵測。

**輸出**：

| 欄位 | 說明 |
|------|------|
| `freshness` | 最後快照到現在的秒數 |
| `gap_detected` | 是否偵測到間隔異常（> 2 倍正常間隔） |
| `zero_anomaly` | 是否偵測到關鍵欄位突然歸零 |
| `health_level` | ok / warn / crit |
| `note` | 人可讀的描述 |

### 5.7 後送監控（output_monitor）— v1.3 新增

`calc_engine.output_monitor(medical_snaps, shelter_snaps)` 追蹤後送/離站流量。

**輸出**：

| 欄位 | 說明 |
|------|------|
| `evac_backlog` | 當前待後送人數 |
| `evac_trend` | 上升/持平/下降 |
| `discharge_rate` | 後送速率 |
| `shelter_exit_rate` | 收容離站速率 |
| `level` | ok / warn / crit |
| `note` | 人可讀的描述 |

### 5.8 分析列觸發條件

| 觸發條件 | 警示文字 | 顏色 |
|---|---|---|
| 醫療床位斜率 > 15% | 醫療量能加速上升 | 紅 |
| 醫療床位斜率 > 5% | 醫療量能持續上升 | 黃 |
| 收容床位斜率 > 20% | 收容量能加速 | 黃 |
| B 來源速率 > 0.3/筆 | B 來源（收容轉送）上升 | 黃 |
| A 來源速率 > 0.3/筆 | A 來源（前進組）持續輸入 | 藍 |
| SRT Red+ 上升且醫療紅傷跟進 | SRT 橋接延遲已觸發 | 紅 |
| SRT Red+ 上升但醫療紅傷未跟進 | SRT 橋接預警：約 15 分鐘後到達 | 黃 |
| 任一組 IPI ≥ 6 | 收容/醫療 現場高壓（IPI N） | 紅 |
| 任一組 IPI 3–5 | 收容/醫療 事件密度上升 | 黃 |
| 同類型事件 30min ≥ 3 起 | [類型] 密集發生，確認系統性原因 | 黃 |
| 事件嚴重度往高遷移 | 情勢升級中 | 紅 |
| 未結事件 > 活躍人員 ×2 | 事件積壓，每人負擔 N 件 | 黃 |
| IV 剩餘 < 60 分鐘 | IV 輸液 N 分見底 | 紅 |
| 氧氣瓶剩餘 < 60 分鐘 | 氧氣瓶 N 分見底 | 黃 |
| 人均服務量超紅線 | 收容/醫療 人力負擔危險 | 紅 |
| 醫療床位 ≥ 70% 且距 90% < 30 分 | 醫療危急倒數 N 分 | 紅 |

---

## 6. 快照欄位需求

### 6.1 收容組快照

**主欄位**（已有）：

```json
{
  "bed_used": 38,
  "bed_total": 80,
  "pending_intake": 4,
  "staff_on_duty": 7,
  "srt": { "red": 3, "yellow": 12, "green": 23 },
  "cmist_pending": 2
}
```

**extra 需新增**：

```json
{
  "incident_pressure": {
    "high": 1, "medium": 2, "low": 0,
    "ipi": 5,
    "recent_types": ["security_threat", "capacity_overload"],
    "open_total": 4,
    "resolved_30min": 1
  },
  "active_staff": 7,
  "staff_ratio": 5.4,
  "stuck_count": 3,
  "stuck_rate": 0.42,
  "supplies": {
    "飲用水": 50, "毛毯": 30, "口糧": 100
  },
  "supplies_max": {
    "飲用水": 200, "毛毯": 80, "口糧": 300
  }
}
```

### 6.2 醫療組快照

**主欄位**（需補 `bed_used`、`bed_total`、`waiting_count`）：

```json
{
  "bed_used": 5,
  "bed_total": 10,
  "waiting_count": 2,
  "pending_evac": 1,
  "casualties": { "red": 2, "yellow": 4, "green": 8, "black": 1 },
  "staff_on_duty": 5
}
```

**extra 需新增/補充**：

```json
{
  "src_a": 3, "src_b": 2, "src_c": 0,
  "supplies": {
    "tourniquet": 22, "oxygen": 3, "iv": 6
  },
  "supplies_max": {
    "tourniquet": 30, "oxygen": 5, "iv": 10
  },
  "incident_pressure": {
    "high": 0, "medium": 1, "low": 0,
    "ipi": 1,
    "recent_types": ["resource_shortage"],
    "open_total": 2,
    "resolved_30min": 0
  },
  "active_staff": 4,
  "staff_ratio": 3.75
}
```

### 6.3 `/api/dashboard` 回傳結構

```python
return {
    "calc": {
        "computed_at": "...",
        "medical":  { "snapshot", "freshness", "bed_trend", "waiting_trend",
                      "countdown_to_red", "source_breakdown",
                      "incident_pressure", "ops_metrics" },
        "shelter":  { "snapshot", "freshness", "bed_trend",
                      "incident_pressure", "ops_metrics" },
        "forward":  { "snapshot", "freshness", "units" },
        "security": { "snapshot", "freshness" },
        "medical_pressure": { "index", "level", "components" },
    },
    "events": [...],
    "decisions": { "pending": [...], "decided": [...] },
    "shelter_history": [...],   # 最近 100 筆快照（前端 viewport 12 筆 + 滑動）
    "medical_history": [...],   # 最近 100 筆快照
}
```

---

## 7. 實作路線圖

| 版本 | 內容 | 狀態 |
|---|---|---|
| v1.0 | 四張趨勢圖 + 切面 Modal + 分析列（mock 資料） | ✅ staff_v10c |
| v1.1 | calc_engine 擴充 | ✅ command-v0.1.0 |
| v1.2 | 接真實資料（polling `/api/dashboard`）、移除 mock | ✅ command-v0.1.0 |
| v1.3 | Header 色塊 + 分析列 + 背景色 + 圖③事件 + badge | ✅ command-v0.1.0 |
| v1.4 | 圖表顏色對比改善 + 歷史滑動（100 筆 viewport 12） | ✅ command-v0.1.0 |
| v1.5 | PWA 端 extra 欄位實裝（incident_pressure, supplies, staff_ratio） | ✅ command-v0.1.0 |
| v1.6 | **Wave 1：三區投影佈局 + 雙地圖 + calc_engine 新智慧** | ✅ command-v0.2.0 |
| v1.7 | Wave 2：互動事件輸入 + Decision Countdown + DCI | 🔲 待實作 |
| v1.8 | Wave 3：Escalation/De-escalation + 地圖流向箭頭 | 🔲 待實作 |
| v1.9 | Wave 4：Operator Fatigue | 🔲 待實作 |
| v1.10 | Wave 5：Pi Read-Only API + L3/L4 地圖鑽探 | 🔲 待實作 |

---

## 8. 已確認事項

| 編號 | 問題 | 結論 |
|---|---|---|
| D-01 | 快照頻率 | 5 分鐘，config 可設定 |
| D-02 | 人力 max 值 | 自動推算（從操作紀錄），不寫死 |
| D-03 | 物資初始值 | 組長演習前設定，從 config/resources 表讀 |
| D-04 | 螢幕配置 | 共用螢幕投影，所有人一起看 |
| D-05 | 儀表板分版 | 不分指揮官/幕僚，統一為一個儀表板 |
| D-06 | 版號命名 | `command-vX.Y.Z`，比照 PWA 命名規則 |
| D-07 | 歷史滑動 | 後端 100 筆、前端 viewport 12 筆、◀▶ 按鈕每次移 6 筆 |

---

## 附錄 A：IPI × 量能組合解讀

| 床位% | IPI | 解讀 |
|---|---|---|
| 高 | 高 | 最危險：量能緊繃 + 現場混亂，需立即裁示 |
| 高 | 低 | 量能緊繃但穩定，可觀察 |
| 低 | 高 | 量能有餘但現場有突發狀況，需調查原因 |
| 低 | 低 | 正常，繼續監控 |

---

## 附錄 B：卡關率（收容組專有）

**定義**：收容流程中卡住超過 10 分鐘的人數比例，反映入站流程是否有瓶頸。

```javascript
stuck_count = 登記中 && minutesAgo(registering_started_at) > 10 的人數
stuck_rate  = stuck_count / 登記中總人數
```

**門檻**：

| 等級 | 卡關率 | 或絕對數 |
|---|---|---|
| 🟢 正常 | < 20% | 且 < 2 人 |
| 🟡 偏高 | 20–50% | 或 2–4 人 |
| 🔴 危險 | > 50% | 或 > 4 人 |

---

## 附錄 C：CMIST 指標（收容組專有）

**五個維度**：communication、maintaining_health、independence、services_support、transportation

```json
"extra": {
  "cmist_total": 13,
  "cmist_rate": 0.31,
  "cmist_breakdown": {
    "communication": 3,
    "maintaining_health": 5,
    "independence": 2,
    "services_support": 1,
    "transportation": 2
  }
}
```

**門檻**：

| 等級 | cmist_rate |
|---|---|
| 🟢 正常 | < 20% |
| 🟡 偏高 | 20–40% |
| 🔴 高複雜 | > 40% |

---

## 附錄 D：設計決策紀錄

| 決策 | 結論 | 理由 |
|---|---|---|
| 快照頻率 | 5 分鐘，config 可設定 | 演習最短 2 小時，5 分鐘=24 筆夠用 |
| 人力來源 | 自動推算 | 從 audit_log/intake_log 推算活躍人員 |
| 物資初始值 | 組長演習前設定 | 每場演習備料不同 |
| 螢幕配置 | 共用投影 | 幕僚盯趨勢，指揮官掃 Header |
| IPI 權重 | 高×3 + 中×1 | 高嚴重度事件的質性壓力遠大於中等 |
| 事件獨立成圖 | 圖③ | 事件是獨立壓力來源（環境、安全），不附屬於量能 |
| 流向+橋接合併 | 圖② | 同一條因果鏈：A/B/C → SRT → 醫療 |
| 圖表背景色 | 隨嚴重度變色 | 投影時整面牆色調傳達氣氛 |
| Header 色塊 | 4 個 | 指揮官 0.5 秒掃完，不需讀圖 |
| waiting_count（醫療）| 固定 0 | 醫療組到達即建檔，無等待佇列概念 |
| 不分指揮官/幕僚 | 統一儀表板 | 演習時共用投影，不需要兩種視角 |
| 圖表顏色 | 高飽和 hex 色碼 | 投影環境亮度低，淺色對比不足 |
| 歷史滑動 | viewport 12 + 100 筆 | 演習 2 小時、2 分鐘一筆 = 60 筆，100 筆留餘裕 |
| 三區佈局取代 2×2 | Zone A/B/C | 地圖中心設計，參考 FEMA EOC + 韓國 ED Dashboard |
| 側欄 18% × 2 + 地圖 64% | 投影比例 | 側欄需足夠放 sparkline，地圖仍為最大元素 |
| 深色主題 | #0d1117 | 投影環境適用，減少眩光 |
| 據點動態設定 | 無預設值 | 換場地只需換圖+重新定位，不需改程式 |
| 地圖編輯模式 | ⚙ 齒輪進入 | 指揮部可現場調整據點位置，存回 JSON |

---

*文件版本：v1.3 | 狀態：實作中 | 對應程式：command-v0.2.0（staff_v13.html）*
