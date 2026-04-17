# ICS_DMAS AI 參考文件

> **本文件為參考資料。** 實際開發計畫與進度追蹤請見 [`docs/AI_integration_roadmap.md`](AI_integration_roadmap.md)。
> 原始文件：AI_TTX_藍圖 v1.0（2026-04-11）+ AI整合技術報告 v1.0（2026-04-11）

---

## 第一部分：AI 整合發展藍圖

## AI 整合 × 實戰工具 × TTX 訓練平台

**版本：** v1.0
**日期：** 2026-04-11
**性質：** 基於系統現況分析與 AI 整合探索討論的開發備忘錄
**來源：** 系統架構分析（README、CLAUDE.md、規格書 v1.4）+ AI 整合探索討論

---

## 壹、核心定位

### 民防的真正敵人是混亂本身

資訊太多、太少、太亂、太慢。需要做決定的人沒有足夠依據，需要執行的人不知道該做什麼，整個系統在最需要運作的時候承受最大壓力。

> **AI 的真正價值不在於自動化某個操作，而在於對抗混亂的能力。**

### 雙模式共用同一套系統

```
同一套 ICS_DMAS
├── 實戰模式：真實事件下的指揮協調工具
└── TTX 模式：桌上兵推訓練平台，磨練決策、累積經驗
```

TTX 用真實系統練 → 操作習慣直接遷移到實戰
實戰累積的資料 → 回頭餵 TTX，讓情境更真實
每次演練 → 系統壓力測試，暴露需要改進的地方

### 從記錄系統到認知夥伴

| 層次 | 現在 | AI 整合後 |
|------|------|-----------|
| 感知 | 人看螢幕上的數字 | AI 主動指出異常信號 |
| 理解 | 人自己在腦中整合 | AI 把分散資訊拼成連貫態勢 |
| 預測 | 人靠經驗猜 | AI 基於資料給出有依據的推論 |
| 決策 | 人獨自決定 | AI 提供選項分析，決定永遠是人 |
| 學習 | 事後檢討（如果有開的話） | AI 自動產生分析，每次演練都有可查記錄 |

> **AI 是指揮官的參謀，不是替代品。它提出觀察、指出矛盾、建議選項。按下「執行」的永遠是人。**

---

## 貳、現況盤點

### 已實作（可用）

| 元件 | 版本 | 狀態 |
|------|------|------|
| 收容組 PWA | shelter-v2.3 | 最完整；CMIST、雙軌同意書、四件套均已實作 |
| 醫療組 PWA | medical-v0.6.3-alpha | 實際完成度高於版號顯示 |
| 指揮部儀表板 | cmd-v0.6.0 | 基礎四條趨勢圖，staff_on_duty 自動計算 |
| WebSocket 伺服器 | — | 跨組狀態同步基礎架構 |
| 啟動腳本 | — | Mac / Pi / Windows 三平台，本機模擬可運行 |

### 規格完整但未實作

| 元件 | 備註 |
|------|------|
| 前進/安全組 Field Node | 規格書 v1.4 完整，程式碼不存在 |
| Whisper + Llama 3 8B pipeline | 架構圖存在，效能未實測驗證 |
| QR code 離線快照（情境 3） | 設計完整，未實作 |
| Phase 2/3 安全架構 | HTTPS/WSS、LUKS2、WireGuard、YubiKey 均未開始 |

### 完全不存在

- 跨組情境感知整合（AI 橫向關聯多組資訊）
- 沉默警報（`last_seen` 有欄位，無監看邏輯）
- TTX 模組（情境注入、後果引擎、主持人控制台）
- AAR 報告生成
- 角色權限細分（主持人 / 受訓者 / 觀察員）

---

## 參、模型選型：Gemma 4

### 為什麼從 Whisper + Llama 3 8B 換成 Gemma 4

現有雙模型串接有延遲、介面複雜度高、資源競爭。Gemma 4 原生支援音訊輸入，一步完成 STT + 結構化輸出，同時 agentic tool use 能力大幅提升（τ2-bench：6.6% → 86.4%）。

授權：Apache 2.0，無使用限制，完全離線，通過供應鏈安全篩選（Google DeepMind，美國）。

### 各節點部署

| 節點 | 硬體 | 模型 | 用途 |
|------|------|------|------|
| 醫療組 / 收容組 | Pi 500 | Gemma 4 E4B | 語音輸入 → 結構化欄位，錯誤偵測 |
| 指揮部 | N100 Mini PC | Gemma 4 26B A4B MoE | 情境感知整合、TTX 後果引擎、AAR 報告 |
| 前進 / 安全組 | Pi Zero 2W | Whisper Tiny（維持現有） | 資源限制，只需 STT |

### Gemma 4 E4B 在醫療 / 收容組的具體作用

```
志工說話：「男性約45歲，頭部外傷，意識清楚，血壓偏低，需要 IV」

Gemma 4 E4B 同時做：
1. 轉文字
2. 填入結構化欄位（性別、年齡、傷況、分級、處置需求）
3. 偵測矛盾 → 主動提示：「血壓偏低但分在黃區，確認嗎？」
```

不需要打字，不需要人工審閱每個欄位，錯誤被即時捕捉。

### Gemma 4 26B 的環境感知能力

透過 function calling 主動拉取多組資料，進行跨組推論：

```
Gemma 4 26B
→ GET /shelter/current_status
→ GET /medical/triage_queue
→ GET /field_nodes/last_seen
→ 推論 → 情勢摘要推送指揮部儀表板
```

**跨組關聯推論範例：**
> 收容站 80% 容量 + 醫療後送隊列積壓 + 前進組回報某里持續有人湧出
> → AI 綜合判斷：容量壓力預計 35 分鐘後達臨界，建議啟動備用收容點

**沉默警報範例：**
> `last_seen` 超過閾值 → 查詢節點最後位置與最後回報內容
> → 推論：C棟地下室為已知通訊死角，但心跳也停了，非單純訊號問題
> → 建議：派聯絡員確認

**注意事項：** Gemma 4 的 agentic benchmark 為英文環境。繁體中文加上民防術語的表現尚無已知數字，需要實測驗證後才能確認可靠性。

---

## 肆、各組 AI 整合：減少摩擦點

### 醫療組
- 語音輸入取代手打，檢傷欄位自動填寫
- 矛盾偵測（分級與生命跡象不一致時主動提示）
- 後送建議（根據醫院距離 + 當前容量）
- 每個分級決定有時間戳記和依據，AAR 可追溯

### 收容組
- 語音登記，CMIST 評估變成對話而不是填表
- 即時統計特殊需求人口分布（幾個需要藥物、幾個行動不便）
- 容量壓力預警（AI 預測何時達臨界）

### 安全組
- 語音描述威脅 → AI 給出威脅等級評估和建議處置選項
- 自動通報指揮部，附上結構化威脅摘要
- 指揮官收到的不是「門口有可疑人員」，而是有依據的評估

### 前進組
- 前端不變（PTT + Whisper Tiny）
- AI 價值在指揮部端：多個前進組回報橫向整合，找出關聯性和矛盾
- 例：A棟結構損傷 + B棟地層下陷 + 三樓求救 → AI 拼出「結構崩塌風險 + 搶救 vs 安全兩難」

### 指揮官 / 幕僚
- 每五分鐘自動情勢摘要（定時推送 + 主動查詢並行）
- 主動標記異常：哪個組超時未回報、哪兩組資訊有衝突
- 資源衝突建議：多地點同時請求同一資源時，AI 給出優先順序分析供指揮官裁示

---

## 伍、TTX 模組設計

### 設計原則

傳統 inject 卡的痛點：紙本傳遞慢、難追蹤、主持人負擔重、事後靠回憶。

TTX 模組補的不是 inject 卡本身（你的照片 + 地圖設計哲學保留），而是：
- inject 數位化注入真實系統
- 決定有後果，後果有記錄
- 事後有資料可分析，不靠回憶

### inject 卡數位化

你現有的 inject 卡（真實照片 + 位置地圖）直接數位化。Gemma 4 原生支援圖片輸入，主持人上傳照片，AI 理解情境，推送給對應組的 PWA。

受訓者在真實系統上做決定，決定有了重量。

### TTX 流程

```
主持人上傳 inject 卡（圖片 + 文字說明）
    ↓
Gemma 4 26B 理解情境
    ↓
注入對應組別的 PWA（以系統事件形式出現）
    ↓
組長 / 指揮官用真實系統做決定
    ↓
Gemma 4 根據決定 + 當前系統狀態產生後果
    ↓
主持人審核後果（人工確認，不自動注入）
    ↓
後果成為下一個 inject，演練繼續
    ↓
演練結束 → AAR 報告自動生成
```

**主持人審核是必要設計**：AI 產生的後果不能直接進系統，需要人把關，避免不合理情境破壞演練張力。

### AI 動態後果引擎

靜態劇本的問題：大家知道答案，照著走。

AI 後果引擎根據受訓者的實際決定即時產生邏輯後果，每次演練都不同，無法背答案：

```
指揮官決定：「先疏散A區」
    ↓
AI 判斷：A區疏散路線經過河岸
    ↓
注入新情境：「接獲通報，上游水庫放水，A區路線40分鐘後被淹」
    ↓
指揮官必須即時改變決策
```

### 角色分離

| 角色 | 看到的內容 | 權限 |
|------|-----------|------|
| 受訓者（組長 / 指揮官） | 自己組的介面，不知道其他組全局 | 操作自己組的 PWA |
| 主持人 | 全局狀態 + 控制台 + AI 後果預覽 | 注入情境、審核後果、暫停演練 |
| 觀察員 | 全局狀態（唯讀） | 加標記和筆記，供 AAR 參考 |

### 演練模式開關

Schema 加入 `session_type` 欄位（`real` / `exercise`）。啟動時選擇模式，所有資料帶這個標籤。演練資料和真實資料完全隔離，但共用同一套介面和操作邏輯。

---

## 陸、AAR 與累積學習

### 三層分析

**第一層：發生了什麼（描述）**
把所有組的行動按時間序整合，每個人看到自己的決定在全局裡的位置。

**第二層：關鍵時間點在哪（診斷）**
AI 標記轉折點：

```
10:03 情境注入：三名特殊需求收容者抵達
10:03–10:11 收容組長無動作（8分鐘）
10:11 決定：全部送一般區（未執行 CMIST 篩查）
10:34 後果觸發：隔離需求出現
→ 分析：初始評估缺失，8分鐘的沉默是關鍵盲點
```

**第三層：跨次模式分析（學習）**
累積三次以上演練資料後，AI 跨 session 分析：

- 這位指揮官在資源衝突情境下決策速度比平均慢 40%
- 這位收容組長三次演練都跳過 CMIST 評估
- 這位安全組長面對模糊威脅傾向過度升級

這些模式，當事人自己感覺不到，但資料說得清楚。

### 資料飛輪

```
TTX 演練 → 產生決策資料
    ↓
AAR 分析 → 找出個人盲點和系統缺口
    ↓
改進 SOP 和訓練重點
    ↓
下一次 TTX → 情境更精準，更針對已知弱點
    ↓
（循環）
```

---

## 柒、缺口清單

### 技術缺口（可開發補齊）

| 缺口 | 說明 | 優先度 |
|------|------|--------|
| Gemma 4 語音輸入整合 | 取代 Whisper + Llama，Pi 500 節點 | 高 |
| 情境感知整合層 | N100 background job，跨組推論 | 高 |
| Field Node 實作 | 按規格書 v1.4 實作，前進/安全組進入系統的入口 | 高 |
| 演練模式開關 | `session_type` 欄位，schema 層隔離 | 中 |
| 主持人控制台 | inject 注入介面，角色分離 | 中 |
| AI 後果引擎 | 接主持人控制台，需 Ground Truth 知識庫配合 | 中 |
| AAR pipeline | Log → 結構化決策分析報告 | 中 |
| 跨次模式分析 | 累積資料後才有意義 | 低（後期） |
| Phase 2/3 安全架構 | HTTPS/WSS、LUKS2、WireGuard、YubiKey | 部署前必須 |

### 非技術缺口（需要人來補）

**Ground Truth 知識庫**
AI 後果引擎需要「什麼決定導致什麼後果」的因果知識庫。需要有實戰經驗的指揮官坐下來整理，程式碼解決不了這個問題。沒有這個，AI 產生的後果只是看起來合理，不是真正正確的。

**決策弱點的初始詮釋**
AI 能找出跨次的決策模式，但「這個模式是弱點還是風格」需要人來判斷。第一次看到某個指揮官的模式，需要有人說「對，這是他的盲點」。

**Gemma 4 繁體中文 + 民防術語的實測驗證**
Gemma 4 的 benchmark 是英文環境。繁體中文加民防術語的結構化輸出準確率，是真實未知數，需要用實際演練錄音測試後才能確認。

---

## 捌、建議開發順序

按價值釋放速度排序，不按功能複雜度：

### Phase A：補齊實戰基礎
1. **Gemma 4 E4B 語音輸入**（醫療組 + 收容組）
   — 摩擦點最大的地方先解決，可直接整合現有 PWA

2. **情境感知整合層**
   — N100 background job，實戰和 TTX 都需要，先建先用

3. **Field Node 實作**
   — 前進/安全組進入系統的入口，TTX 情境完整性的前提

### Phase B：建立 TTX 模組
4. **演練模式開關 + 主持人控制台**
   — 兩個要一起設計，主持人控制台的存在意義就是演練模式

5. **AI 後果引擎**
   — 接主持人控制台；需先完成 Ground Truth 知識庫

### Phase C：累積學習系統
6. **AAR pipeline**
   — 演練跑幾次後自然有資料，但 log 格式要從 Phase A 就設計完整

7. **跨次模式分析**
   — 需要時間累積資料，放在最後

### Phase D：安全硬化（部署前）
8. **Phase 2/3 安全架構**
   — HTTPS/WSS、LUKS2、WireGuard、YubiKey
   — 必須在真實部署前完成，不影響開發順序但不能省略

---

## 玖、風險與邊界

### 技術風險

**Gemma 4 繁中民防術語表現未驗證**
benchmark 是英文環境，繁體中文 + 民防術語是少數訓練資料。這是已知未知數。

**N100 同時跑 Gemma 4 26B + 其他服務的效能**
26B MoE 推論時激活 3.8B 參數，理論上 N100 跑得動，但同時跑 FastAPI + SQLite + WebSocket + Gemma 4 的實際效能需要實測。

### 設計風險

**信任校準問題**
信任 AI 太少：指揮官忽略建議，AI 等於沒有。
信任 AI 太多：自動化偏誤，停止獨立判斷。
最危險的情況：AI 在演練中總是對，指揮官建立高度信任，真實情境中 AI 遇到訓練資料之外的狀況出錯，指揮官沒有足夠的懷疑本能。

**對策：** UI 上強制顯示 AI 的信心依據，強制要求指揮官主動確認而不是被動接受。定期在 TTX 中注入「AI 判斷錯誤」的情境，訓練指揮官對 AI 保持適當的懷疑本能。

**決策責任界面**
當 AI 給出建議，指揮官照著做但結果出錯，責任在哪？UI 上必須明確顯示「AI 建議，最終決定是你的」，且確認動作記錄進 log，事後 AAR 才能區分「人的判斷」和「跟著 AI 走的判斷」。

**過度依賴風險**
如果 AI 輔助讓志工習慣「系統會告訴我該怎麼做」，系統失效的那一刻，他們比沒有 AI 的志工更脆弱。降級設計不只是硬體降級（QR code、情境 3），也要包含「志工在沒有 AI 的情況下仍能獨立判斷」的訓練設計。

---

## 拾、長期願景

### 超越單一鄉鎮

當三層架構（收容站 → 鄉鎮 → 縣市）成熟後，縣市層的 AI 同時看到所有鄉鎮的即時數據——這是任何人類都做不到的。跨鄉鎮的資源調配、預測哪個鄉鎮會最先達到容量臨界，這個層次的 AI 才是真正的差異化。

### 民防數據的政策價值

連續幾年的演訓資料會累積出：哪些里的特殊需求人口最多、哪個收容站永遠在 20 分鐘內滿載、哪些資源永遠在第一個小時就耗盡。這些不是給指揮官看的資訊，是給縣市政府做民防預算和基礎建設決策的依據。

### 訓練頻率的突破

TTX 成熟後，指揮官在家用筆電就能練，不需要所有志工到場。訓練頻率從「一年一次大演練」變成「隨時可練」。這才是真正改變民防能力天花板的地方。

---

*本文件基於 ICS_DMAS repo 現況分析（2026-04-11）及 AI 整合探索討論整理。*
*規格先行部分（前進/安全組）尚未實作，以規格書 v1.4 為依據。*
*Gemma 4 相關資料來源：Google DeepMind 官方發布（2026-04-02），Apache 2.0 授權。*

---

## 第二部分：AI 完整整合技術報告

## 基於實際程式碼分析

**版本：** v1.0
**日期：** 2026-04-11
**分析範圍：** 實際讀取的程式碼檔案清單

| 檔案 | 大小 | 說明 |
|------|------|------|
| `medical-pwa/public/medical_pwa.html` | 4485 行 / 266KB | 醫療組 PWA 主體 |
| `medical-pwa/public/admin.html` | 415 行 / 20KB | 醫療組管理介面 |
| `medical-pwa/public/sw.js` | 88 行 | 醫療組 Service Worker |
| `shelter-pwa/public/shelter_pwa.html` | 3197 行 / 278KB | 收容組 PWA 主體 |
| `shelter-pwa/public/sw.js` | 92 行 | 收容組 Service Worker |
| `command-dashboard/src/db.py` | 1188 行 / 46KB | 資料庫 Schema + CRUD |
| `command-dashboard/src/calc_engine.py` | 1160 行 / 39KB | 計算引擎（純函式） |
| `security & forward/docs/規格書_v1.4.md` | 356 行 | 前進/安全組規格 |
| `medical-pwa/docs/醫療組SOP_20260323.md` | 681 行 | 醫療組 SOP |
| `shelter-pwa/docs/收容組_SOP_20260330.md` | 1296 行 | 收容組 SOP |

> **標注說明：** 本報告明確區分「事實」（來自程式碼）、「推論」（從程式碼推導）、「意見」（判斷）。

---

## 壹、現況盤點（事實）

### 1.1 現有 Schema（db.py）

九張資料表，功能已相當完整：

| 表名 | 用途 | 關鍵欄位 |
|------|------|---------|
| `snapshots` | 各節點快照 | node_type, casualties_*, bed_used/total, extra(JSON) |
| `events` | 事件記錄 | severity, response_deadline, needs_commander_decision |
| `decisions` | 待裁示事項 | **suggested_action_a, suggested_action_b**, status 狀態機 |
| `audit_log` | 不可篡改稽核軌跡 | operator, action_type, detail(JSON) |
| `manual_records` | 表單暫存 | form_id, sync_status(pending/synced/skipped), payload(JSON) |
| `predictions` | 計算引擎輸出 | metric, eta_threshold, confidence, trend_rate |
| `sync_log` | 三 Pass 對齊記錄 | pass1/2/3 計數, conflicts_manual |
| `accounts` | 帳號管理 | role(指揮官/操作員), pin_hash+salt |
| `config` | 系統設定 | key-value |

### 1.2 計算引擎現況（calc_engine.py）

已實作的門檻與預測邏輯：

```python
DEFAULT_THRESHOLDS = {
    "medical": {
        "bed_usage_yellow": 0.70,   # 70% 警告
        "bed_usage_red": 0.90,      # 90% 臨界
        "red_casualties_yellow": 1,
        "red_casualties_red": 2,
        "waiting_yellow": 3,
        "waiting_red": 6,
    },
    "shelter": {
        "bed_usage_yellow": 0.70,
        "bed_usage_red": 0.90,
        "pending_intake_yellow": 5,
        "pending_intake_red": 10,
    },
    "forward": {
        "freshness_warn_min": 5,
        "freshness_crit_min": 10,  # 10分鐘 → LKP 觸發
        "lkp_min": 10,
    },
}
MIN_SPAN_FOR_TREND = 10  # 最少需要 10 分鐘資料才能計算趨勢
```

calc_engine 已產生：趨勢速率（每分鐘變化量）、ETA 預測、信心等級（high/medium/low/insufficient）。

**現有資料流：**
```
PWA → manual_records → snapshots → calc_engine → predictions → 儀表板（數字）
```

### 1.3 PWA 共同架構（事實）

兩個 PWA 共用相同的技術棧：

| Library | 用途 | 來源 |
|---------|------|------|
| `dexie.min.js` | IndexedDB wrapper，本地結構化儲存 | 本地 lib |
| `papaparse.min.js` | CSV 解析/匯出 | 本地 lib |
| `qrcode.js` | QR code 生成（離線快照用） | 本地 lib |

**零 AI 整合**：兩個 PWA 均無任何 AI library 或對 AI endpoint 的 fetch 呼叫。

### 1.4 已發現的現有 Bug（事實）

**Bug 1：Service Worker 版本號不一致（兩個 PWA 都有）**

| | HTML PWA_VERSION | sw.js CACHE_NAME | 差距 |
|---|---|---|---|
| 醫療 | v0.8.3-alpha | v0.6.7-alpha | 2 個 minor |
| 收容 | v2.2.47 | v2.2.44 | 3 個 patch |

違反 CLAUDE.md 的 bump checklist，導致 Service Worker 無法正確清除舊快取。

**Bug 2：收容組 sw.js CACHE_UPDATE 指向錯誤檔名**

```javascript
// sw.js 實際寫的（錯誤）：
cache.add('./shelter_pwa_v2.1.html')

// 實際檔名：
shelter_pwa.html
```

CACHE_UPDATE 訊息永遠靜默失敗。

**Bug 3：accounts 表 role 與前端不一致**

```
後端 accounts.role：'指揮官' / '操作員'（2 種）
admin.html 前端：檢傷官/治療官/後送官/後勤官/組長（5 種）
```

角色差異化邏輯完全在前端，後端無法做角色層級的存取控制。

---

## 貳、AI 整合的關鍵發現

### 2.1 decisions 表已為 AI 準備好

```sql
suggested_action_a TEXT NOT NULL,
suggested_action_b TEXT,
```

`decisions` 表已內建兩個選項欄位——現在靠幕僚人工填。這個結構本身就是「AI 提出選項 A 和 B，指揮官選一個」的設計。**不需要改 schema，直接寫入現有欄位即可。**

狀態機完整：`pending → approved/hold/redirect/completed/superseded`，支援 revision、escalation、parent_decision_id 串鏈。

### 2.2 AI 整合的最佳時機點：manual_records

```sql
sync_status TEXT NOT NULL DEFAULT 'pending'  -- pending/synced/skipped
payload TEXT NOT NULL,  -- JSON 完整表單資料
```

PWA 表單資料先進 `manual_records`（pending），等待後端處理。**在資料到達但尚未提交的這個視窗，AI 可以介入做驗證和補全，成本最低、侵入性最小。**

`skipped` 狀態需要特別關注：被人工略過的記錄是潛在資料缺口，應定期掃描。

### 2.3 audit_log 是 AAR 的黃金資料來源

設計原則寫在 db.py 頂部：「AUDIT_LOG 只能 INSERT，禁止 UPDATE / DELETE」。

每筆記錄有：`operator`、`device_id`、`action_type`、`target_table`、`target_id`、完整 JSON `detail`、`created_at`。

**AAR pipeline 不需要另建資料結構，直接讀 audit_log 就夠。**

### 2.4 predictions 已存在，AI 是在它之後加一層

```
現在：snapshots → calc_engine → predictions（數字）→ 儀表板
加AI：predictions（數字）→ Gemma 4 → 自然語言摘要 + 跨節點關聯推論
```

AI 不替換 calc_engine，是在其後加解讀層。calc_engine 的統計輸出是 AI 的輸入，兩者互補。

### 2.5 extra 欄位是結構化挑戰

```sql
extra TEXT  -- JSON，各組特有欄位（物資量、CMIST pending、SRT 等）
```

醫療物資、收容 CMIST、SRT 狀態全部存在 `extra` 這個 JSON blob。AI 讀取時需先 `json.loads(extra)`，無 schema 約束，資料品質無法保證。這是長期需要解決的技術債。

---

## 參、需要的架構修改

### 3.1 現有表的修改

**所有主要表加 `session_type` 欄位（最優先）：**

```sql
ALTER TABLE snapshots    ADD COLUMN session_type TEXT DEFAULT 'real';
ALTER TABLE events       ADD COLUMN session_type TEXT DEFAULT 'real';
ALTER TABLE decisions    ADD COLUMN session_type TEXT DEFAULT 'real';
ALTER TABLE audit_log    ADD COLUMN session_type TEXT DEFAULT 'real';
ALTER TABLE manual_records ADD COLUMN session_type TEXT DEFAULT 'real';
```

這是隔離演練資料和實戰資料的關鍵。所有查詢都要帶這個過濾條件。**比新增任何功能都更優先。**

**decisions 表加 AI 標記：**

```sql
ALTER TABLE decisions ADD COLUMN ai_generated  INTEGER DEFAULT 0;
ALTER TABLE decisions ADD COLUMN ai_confidence TEXT;
ALTER TABLE decisions ADD COLUMN ai_basis      TEXT; -- JSON，引用哪些 insight
```

**accounts 表角色細分：**

```sql
ALTER TABLE accounts ADD COLUMN role_detail TEXT;
-- 值：指揮官/幕僚/檢傷官/治療官/後送官/後勤官/組長
```

---

### 3.2 新增資料表（5 張）

#### `ai_insights`（AI 分析輸出）

```sql
CREATE TABLE ai_insights (
    id                  TEXT PRIMARY KEY,
    generated_at        TEXT NOT NULL,
    basis_snap_ids      TEXT,   -- JSON array，引用 snapshots
    basis_pred_ids      TEXT,   -- JSON array，引用 predictions
    node_types          TEXT NOT NULL,  -- JSON array，跨哪些節點
    insight_type        TEXT NOT NULL,
    -- situation_summary / cross_node_alert / silence_alarm
    -- resource_conflict / trend_warning / ttx_consequence
    content             TEXT NOT NULL,  -- 自然語言輸出
    structured          TEXT,   -- JSON，結構化摘要（給儀表板用）
    confidence          TEXT NOT NULL,  -- high/medium/low
    human_reviewed      INTEGER DEFAULT 0,  -- 0/1
    reviewed_by         TEXT,
    reviewed_at         TEXT,
    session_type        TEXT DEFAULT 'real'
);
```

與 `predictions` 分開的原因：predictions 是純函式計算輸出（固定格式），ai_insights 是非結構化 AI 輸出。混在一起會污染 calc_engine 的設計。

#### `ttx_sessions`（演練場次）

```sql
CREATE TABLE ttx_sessions (
    id              TEXT PRIMARY KEY,
    session_name    TEXT NOT NULL,
    scenario_desc   TEXT,
    facilitator     TEXT NOT NULL,
    status          TEXT DEFAULT 'setup',
    -- setup/running/paused/completed
    started_at      TEXT,
    ended_at        TEXT,
    created_at      TEXT NOT NULL
);
```

#### `ttx_injects`（情境注入卡）

```sql
CREATE TABLE ttx_injects (
    id                    TEXT PRIMARY KEY,
    session_id            TEXT REFERENCES ttx_sessions(id),
    inject_seq            INTEGER NOT NULL,
    target_unit           TEXT NOT NULL,   -- medical/shelter/forward/security
    inject_type           TEXT NOT NULL,   -- event/status_change/resource_change
    title                 TEXT NOT NULL,
    description           TEXT NOT NULL,
    image_path            TEXT,            -- 照片 inject 卡路徑
    location_zone_id      TEXT,            -- 對應地圖 zone
    payload               TEXT NOT NULL,   -- JSON，注入的假資料
    inject_at             TEXT,            -- 計劃注入時間
    actually_injected_at  TEXT,
    injected_by           TEXT,            -- facilitator/ai_engine
    status                TEXT DEFAULT 'pending'
    -- pending/injected/skipped
);
```

#### `ttx_consequences`（AI 後果）

```sql
CREATE TABLE ttx_consequences (
    id                    TEXT PRIMARY KEY,
    session_id            TEXT REFERENCES ttx_sessions(id),
    trigger_inject_id     TEXT REFERENCES ttx_injects(id),
    trigger_decision_id   TEXT REFERENCES decisions(id),
    generated_by          TEXT DEFAULT 'ai',  -- ai/facilitator
    consequence_desc      TEXT NOT NULL,      -- 後果描述
    next_inject_id        TEXT REFERENCES ttx_injects(id),
    facilitator_approved  INTEGER DEFAULT 0,  -- 人工核准才注入
    approved_at           TEXT,
    created_at            TEXT NOT NULL
);
```

**為什麼需要 `facilitator_approved`：** AI 產生的後果不能直接注入系統，必須人工確認。這是防止 AI 製造不合理情境破壞演練張力的關鍵設計。

#### `aar_reports`（事後分析報告）

```sql
CREATE TABLE aar_reports (
    id                TEXT PRIMARY KEY,
    session_id        TEXT REFERENCES ttx_sessions(id),
    report_type       TEXT NOT NULL,   -- auto_generated/human_edited
    generated_at      TEXT NOT NULL,
    basis_audit_ids   TEXT,            -- JSON array，引用 audit_log
    timeline          TEXT NOT NULL,   -- JSON，完整決策時間軸
    decision_analysis TEXT,            -- JSON，各決策分析
    pattern_summary   TEXT,            -- 自然語言，跨次模式
    gaps_identified   TEXT,            -- JSON array，發現的缺口
    content           TEXT NOT NULL,   -- 完整報告內文（Markdown）
    reviewed_by       TEXT,
    finalized_at      TEXT
);
```

---

### 3.3 新增 Python 模組（3 個）

#### `ai_engine.py`（新建）

與 calc_engine 相同設計哲學：純函式，不直接讀資料庫，由 main.py 傳入資料、寫回結果。

```python
"""
ai_engine.py — ICS AI 分析引擎
三個核心函式，其他都是輔助。
設計原則：純函式，不直接讀 DB，由 main.py 負責資料傳入與寫回。
"""

def synthesize_situation(
    predictions: list[dict],
    recent_events: list[dict],
    recent_insights: list[dict]
) -> dict:
    """
    跨節點情勢整合
    輸入：predictions + events → Gemma 4 → insight
    輸出：{content, structured, confidence, basis_ids}
    由 main.py 寫入 ai_insights 表
    """

def generate_decision_options(
    event: dict,
    system_state: dict
) -> tuple[str, str]:
    """
    為單一事件生成 AI 決策選項
    輸出：(action_a, action_b)
    由 main.py 寫入 decisions.suggested_action_a/b
    """

def generate_ttx_consequence(
    inject: dict,
    decision: dict,
    current_state: dict,
    ground_truth: dict  # 知識庫
) -> dict:
    """
    根據指揮官決定生成邏輯後果
    輸出：{consequence_desc, suggested_next_inject}
    由 ttx_engine.py 寫入 ttx_consequences，等 facilitator 核准
    """
```

#### `ttx_engine.py`（新建）

TTX 邏輯從 main.py 獨立出來：

```python
"""
ttx_engine.py — TTX 演練引擎
管理演練場次、情境注入、後果生成的完整生命週期。
"""

def start_session(session_name, facilitator, scenario_desc) -> str:
    """建立 ttx_sessions，回傳 session_id"""

def inject_event(session_id, inject_id) -> dict:
    """
    把 ttx_injects.payload 轉化為真實的 snapshots/events
    帶 session_type='exercise' 標記
    同時寫入 audit_log（action_type='ttx_inject'）
    """

def process_consequence(session_id, decision_id) -> dict:
    """
    讀取指揮官決定 → 呼叫 ai_engine.generate_ttx_consequence
    寫入 ttx_consequences（facilitator_approved=0）
    等待主持人核准後才推送下一個 inject
    """

def generate_aar(session_id) -> dict:
    """
    讀 audit_log（session_type='exercise'）
    呼叫 aar_engine 分析
    寫入 aar_reports
    """
```

#### `aar_engine.py`（新建）

```python
"""
aar_engine.py — 事後分析引擎
從 audit_log 重建決策時間軸，分析決策模式。
"""

def build_timeline(session_id: str) -> list:
    """
    從 audit_log 重建完整決策時間軸
    計算每個 inject → 決策的延遲時間
    標記關鍵轉折點
    """

def analyze_decision_patterns(operator: str, sessions: list) -> dict:
    """
    跨 session 分析同一個人的決策模式
    找出系統性盲點（例：三次都忽略安全組人力不足信號）
    """

def compare_to_ground_truth(session_id, ground_truth: dict) -> dict:
    """
    實際決策路徑 vs 預設正確路徑比較
    需要 Ground Truth 知識庫（人工建立）
    """

def generate_report(session_id: str) -> str:
    """
    整合以上分析，呼叫 Gemma 4 生成 Markdown 格式 AAR 報告
    """
```

---

### 3.4 main.py 新增的 API Endpoint

不改現有 endpoint，只加新的：

```
# AI 分析
GET  /ai/insights/latest           最新情勢摘要
POST /ai/decisions/{event_id}      為某事件生成 AI 決策選項
POST /ai/synthesize                手動觸發跨節點分析

# TTX 演練
POST /ttx/sessions                 建立演練場次
POST /ttx/sessions/{id}/start      開始演練
POST /ttx/sessions/{id}/inject     注入情境
POST /ttx/sessions/{id}/consequence 觸發後果生成（AI → facilitator 審核）
POST /ttx/sessions/{id}/aar        生成 AAR 報告

# AAR 查閱
GET  /aar/reports/{id}             讀取 AAR 報告
GET  /aar/patterns/{operator}      跨次決策模式分析
```

**AI 呼叫架構（不阻塞主流程）：**

```python
from fastapi import BackgroundTasks

@app.post("/snapshots")
async def receive_snapshot(data: SnapshotIn, bg: BackgroundTasks):
    # 主線程：同步寫入 snapshots（< 10ms）
    result = upsert_snapshot(data.dict())

    # 背景：非同步觸發 AI 分析（2-5 秒，不等待）
    bg.add_task(ai_engine.synthesize_situation, data.node_type)

    return result  # 立刻回應 PWA，不等 AI
```

---

### 3.5 前端修改

#### 新增：`facilitator.html`（主持人控制台）

獨立頁面，不混入現有 PWA：

```
功能清單：
├── 建立/管理 TTX session
├── 上傳 inject 卡（照片 + 說明 + 目標組別）
├── 全局態勢監看（唯讀，所有組即時狀態）
├── AI 後果審核介面
│   └── 顯示 AI 建議 → 主持人核准 / 修改 / 拒絕
├── 推送下一個 inject
└── 即時決策時間軸（每個 inject 到決策的延遲）
```

#### 修改：現有 PWA 加 TTX 模式切換

最小侵入——只加 banner 和模式標記：

```javascript
const IS_TTX = sessionStorage.getItem('ttx_session_id') !== null;

if (IS_TTX) {
    // 1. 頂部橙色 banner「演練模式 ⚠️」
    // 2. 所有 POST 請求帶 session_type: 'exercise'
    // 3. 收到 inject 時顯示情境卡（圖片 + 說明）
    // 4. 提交表單時多一層確認
}
```

#### 修改：指揮部儀表板加 AI 面板

在現有四條趨勢圖旁加第五區塊：

```
AI 情勢摘要（定時推送 + 手動查詢）
┌─────────────────────────────────────┐
│ ⚡ 10:23 AI 分析  信心：中          │
│                                     │
│ 收容站容量壓力持續上升，預計 35 分  │
│ 鐘後達臨界。醫療後送隊列積壓，前   │
│ 進 B 組已 25 分鐘未回報。           │
│                                     │
│ [查看依據]  [已審閱 ✓]              │
└─────────────────────────────────────┘
```

`[已審閱]` 點擊寫入 `ai_insights.human_reviewed = 1`，同時記錄 audit_log。AAR 時可查指揮官是否有在看 AI 建議，以及看了多久後才決策。

---

## 肆、模型部署（Gemma 4）

### 4.1 各節點分工

| 節點 | 硬體 | 模型 | 主要用途 |
|------|------|------|---------|
| 醫療組 / 收容組 Pi | Pi 500 | Gemma 4 E4B | 語音輸入 → 結構化欄位，即時矛盾偵測 |
| 指揮部 | N100 Mini PC | Gemma 4 26B A4B MoE | 情勢整合、決策選項生成、TTX 後果引擎、AAR |
| 前進/安全組 | Pi Zero 2W | Whisper Tiny（維持） | 資源限制，只需 STT |

N100 跑 Gemma 4 26B A4B MoE：推論時僅激活 3.8B 參數，記憶體需求接近 4B 模型，但能力遠超 Llama 3 8B。τ2-bench（agentic tool use）: 86.4%（Gemma 3 同尺寸 6.6%）。

### 4.2 AI 寫入路徑的可追溯性設計

所有 AI 寫入都必須帶標記，讓 AAR 能區分「人的決策」和「跟著 AI 走的決策」：

```python
# decisions 表寫入
{
    "ai_generated": 1,
    "created_by": "ai_engine",
    "ai_confidence": "medium",
    "ai_basis": ["snap_id_1", "snap_id_2", "insight_id_3"]
}

# audit_log 同步寫入
{
    "action_type": "ai_suggestion_created",
    "detail": {
        "model": "gemma4-26b-a4b",
        "basis_snap_count": 3,
        "confidence": "medium",
        "node_types": ["medical", "shelter"]
    }
}
```

---

## 伍、TTX 完整流程

### 5.1 主持人視角

```
1. 建立 session（session_name, scenario_desc）
2. 上傳 inject 卡（照片 + 說明 + target_unit + payload）
3. 按「開始演練」→ status = 'running'
4. 監看全局態勢
5. 選擇並推送 inject → 出現在對應組的 PWA
6. 受訓者決策後：AI 生成後果 → 主持人審核 → 核准推送下一個 inject
7. 按「結束演練」→ 觸發 AAR 生成
```

### 5.2 受訓者視角

```
1. 登入 PWA（正常流程）
2. 看到橙色 banner「演練模式 ⚠️」
3. 收到 inject（情境卡：圖片 + 說明 + 位置地圖）
4. 用真實系統做決定（登記、分級、回報——和實戰一樣）
5. 決定被記錄，AI 在後台生成後果
6. 主持人核准後，後果以新的 inject 形式出現
```

### 5.3 AI 動態後果邏輯

```
指揮官決定「先疏散A區」
    ↓
ai_engine.generate_ttx_consequence(inject, decision, state)
    ↓
Gemma 4 推論：A區疏散路線經過河岸
    ↓
生成後果：「接獲通報，上游水庫放水，A區路線40分鐘後被淹」
    ↓
寫入 ttx_consequences（facilitator_approved=0）
    ↓
主持人審核（確認合理性）→ 核准
    ↓
成為下一個 ttx_inject，推送給指揮官
```

---

## 陸、AAR 分析架構

### 6.1 三層分析

**第一層：發生了什麼（描述）**
從 audit_log 重建時間軸，每個人看到自己決定在全局裡的位置。

**第二層：關鍵時間點（診斷）**
```
範例輸出：

10:03  inject 注入：三名特殊需求收容者抵達
10:03–10:11  收容組長無動作（8 分鐘沉默）
10:11  決定：全部送一般區（未執行 CMIST 篩查）
        → ai_generated: 0（這是人的決策）
10:34  後果觸發：隔離需求出現

分析：初始評估缺失，8 分鐘沉默是關鍵盲點。
```

**第三層：跨次模式（學習）**
累積三次以上 session 後，aar_engine 跨 session 分析：
- 這位指揮官在資源衝突情境下決策延遲比平均多 40%
- 這位收容組長三次都跳過 CMIST 評估
- 這位安全組長面對模糊威脅傾向過度升級

### 6.2 指揮官是否在看 AI 建議

audit_log 記錄 `ai_insights.human_reviewed` 的點擊時間。AAR 可以查：

```
inject 10:03 → AI 建議 10:04（延遲 1 分鐘）→ 指揮官審閱 10:09（延遲 5 分鐘）→ 決策 10:11
AI 建議內容：「建議先進行 CMIST 評估」
實際決策：直送一般區（未採納 AI 建議）
後果：10:34 隔離壓力出現
```

這讓 AAR 能明確區分「不知道該怎麼做」和「知道但選擇不做」，是兩種不同的訓練問題。

---

## 柒、開發順序

按依賴關係而非功能複雜度：

### Phase 0：基礎（必須先做）

1. **所有主要表加 `session_type` 欄位**
   這是隔離演練和實戰資料的前提，其他所有功能都依賴它。

2. **修正現有兩個 Bug**
   - 對齊 sw.js CACHE_NAME 和 HTML PWA_VERSION
   - 修正收容組 sw.js CACHE_UPDATE 的錯誤檔名

3. **accounts 加 role_detail**
   前後端 role 對齊。

### Phase A：AI 基礎層

4. 建 `ai_insights` 表
5. 建 `ai_engine.py` 骨架（先用 mock 輸出，不接 Gemma 4）
6. main.py 加 `/ai/insights/latest` endpoint
7. 指揮部儀表板加 AI 面板（先顯示 mock 資料）

### Phase B：TTX 骨架

8. 建 `ttx_sessions` + `ttx_injects` 表
9. 建 `ttx_engine.py`
10. 建 `facilitator.html`（主持人控制台）
11. PWA 加 TTX 模式 banner 和 `session_type` 標頭

> **此時 TTX 可以跑了，但後果靠主持人手動輸入，不靠 AI。**
> 這讓你在沒有 Gemma 4 之前就能開始演練測試。

### Phase C：AI 接入

12. `ai_engine.py` 接上真實 Gemma 4 26B endpoint
13. 建 `ttx_consequences` 表
14. `ttx_engine.process_consequence()` 接 ai_engine
15. Facilitator 後果審核介面

### Phase D：AAR

16. 建 `aar_reports` 表
17. 建 `aar_engine.py`
18. `ttx_engine.generate_aar()` 接 aar_engine
19. 跨次模式分析（需要 3+ sessions 才有意義）

### Phase E：安全硬化（部署前）

20. HTTPS/WSS、LUKS2、WireGuard、YubiKey
21. accounts.role_detail 正式啟用後端存取控制

---

## 捌、非技術缺口（程式碼解決不了）

### Ground Truth 知識庫

`ai_engine.generate_ttx_consequence()` 和 `aar_engine.compare_to_ground_truth()` 都需要「什麼決定導致什麼後果」的因果知識庫。

**需要有實戰經驗的指揮官坐下來建立這個知識庫。** 沒有這個，AI 產生的後果只是看起來合理，不是真正正確的。

建議格式：
```json
{
  "scenario": "收容站容量 80% + 持續湧入",
  "decision": "不啟動備用收容點",
  "consequence": "20分鐘後達臨界，入站隊列開始失控",
  "alternative": "啟動備用點，分流 30% 人流，壓力下降",
  "lesson": "容量 75% 是啟動備用點的決策點，不是 90%"
}
```

### Gemma 4 繁體中文 + 民防術語驗證

Gemma 4 的 benchmark 是英文環境。繁體中文加民防術語（ICS 術語、CMIST、ISBAR、START 檢傷）的結構化輸出準確率尚無已知數字。需要用實際演練錄音和表單資料測試後才能確認可靠性。

---

## 玖、風險

### 信任校準

- 信任太少：指揮官忽略 AI 建議，AI 等於沒有
- 信任太多：自動化偏誤，停止獨立判斷
- 最危險：AI 在演練中總是對，指揮官建立高信任，真實情境 AI 遇到邊緣案例出錯，指揮官沒有懷疑本能

**對策：** 定期在 TTX 中注入「AI 刻意給出錯誤建議」的情境，訓練指揮官保持適當懷疑。

### 降級設計的盲點

目前降級設計（QR code、情境 3）是針對硬體的降級。但如果 AI 輔助讓志工習慣「系統會告訴我該怎麼做」，AI 失效時他們比沒有 AI 的志工更脆弱。

**對策：** TTX 中加入「AI 系統全停」情境，測試志工在無 AI 輔助下的決策能力。

---

## 拾、完整資料流（目標狀態）

```
                    ┌─────────────────────────────────────┐
                    │           Gemma 4 26B (N100)        │
                    │   情勢整合 / 決策選項 / TTX後果 / AAR │
                    └──────────────┬──────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ↓                         ↓                         ↓
  ┌─────────────┐          ┌──────────────┐          ┌──────────────┐
  │ ai_insights │          │  decisions   │          │ aar_reports  │
  │（情勢摘要）  │          │（AI 選項A/B） │          │（AAR 報告）  │
  └──────┬──────┘          └──────┬───────┘          └──────────────┘
         ↓                         ↓
  ┌─────────────────────────────────────────────────────────────────┐
  │                       指揮部儀表板                               │
  │   四條趨勢圖  +  AI 情勢面板  +  待裁示決策  +  TTX 控制台      │
  └─────────────────────────────────────────────────────────────────┘
         ↑                         ↑                         ↑
  ┌─────────────┐          ┌──────────────┐          ┌──────────────┐
  │  calc_engine│          │  ttx_engine  │          │  aar_engine  │
  │（統計預測）  │          │（演練管理）   │          │（決策分析）  │
  └──────┬──────┘          └──────┬───────┘          └──────┬───────┘
         ↑                         ↑                         ↑
  ┌─────────────────────────────────────────────────────────────────┐
  │                    SQLite（ics.db）                              │
  │  snapshots / events / decisions / audit_log / manual_records    │
  │  predictions / ai_insights / ttx_* / aar_reports                │
  │  全部帶 session_type: real / exercise                           │
  └─────────────────────────────────────────────────────────────────┘
         ↑                         ↑
  ┌─────────────┐          ┌──────────────┐
  │  醫療組 PWA  │          │  收容組 PWA  │
  │ Gemma 4 E4B │          │ Gemma 4 E4B  │
  │（語音輸入）  │          │（語音輸入）   │
  └─────────────┘          └──────────────┘
         ↑
  ┌─────────────┐
  │ 前進/安全組  │
  │ Whisper Tiny│
  │（PTT → STT）│
  └─────────────┘
```

---

*本報告基於 2026-04-11 的 repo 實際程式碼分析。*
*所有技術建議均基於讀取的程式碼，非假設性分析。*
*Gemma 4 相關資料來源：Google DeepMind 官方發布（2026-04-02），Apache 2.0 授權。*
