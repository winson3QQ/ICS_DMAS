# 醫療組 PWA

## 現場醫療管理系統

**系統需求與規格書**

**v0.6 · 2026-04**

以醫療組 SOP 為主體，沿用收容組 PWA 架構思路，整合安全與網路架構規格 v1.2

---

| 項目 | 內容 |
|------|------|
| **文件版本** | v0.6 |
| **對應程式版本** | v0.6.7-alpha |
| **文件定位** | 醫療組工具第一版系統規格；供開發、討論與換手使用 |
| **適用範圍** | 鄉鎮層防災演訓及實際災害應變之據點醫療站 |
| **機密層級** | C（依上游文件沿用內部使用層級） |
| **預計輸出** | medical_pwa.html + sw.js + ics_ws_server.js（共用） |
| **上游文件** | 醫療組SOP_20260323.md、security_network_spec_v1.2.md、shelter_pwa_spec.md |

---

> **【v0.6 本版重點】（對應 medical-v0.5.5-alpha ～ v0.6.3-alpha）**
>
> 1. **年齡輸入改數字**（v0.5.5）：intake 年齡欄從 C/J/A/E 下拉改為數字輸入，`_ageToCode()` 自動換算識別碼後綴，`source_age` 儲存原始數字。
>
> 2. **傷患姓名欄**（v0.5.6/v0.5.8）：檢傷加姓名選填欄，卡片標題 ID 後顯示姓名，詳情頁新增「姓名」與「性別／年齡」欄位。
>
> 3. **重評預填前次數值**（v0.5.7）：`openTreatmentAssessment()` 開啟時，生命徵象與主訴自動帶入 `patient.vitals_structured` / `chief_issue`。
>
> 4. **後送流程拆分（P0-10）**：治療區一鍵後送（無需填目的地），目的地與方向移至後送區 ISBAR modal 填寫，`_confirmInModal` 一鍵確認。
>
> 5. **ISBAR B 欄預填（P0-12）**：`_buildTreatmentSummary()` 查詢 triages 表，自動摘要歷次評估、照護紀錄、轉色事件填入 B 欄。
>
> 6. **創傷評估加 MOI + 用藥/過敏（P2-8）**（v0.6.0）：XABCDE 區段前加「受傷機轉」下拉 + 補充欄、「M 用藥史」、「A 過敏史」，儲存至 `moi`、`sample_m`、`allergy_flags`。
>
> 7. **非創 SAMPLE 順序（P2-9）**（v0.6.0）：SAMPLE 欄位順序改為 A（過敏）→ M（用藥）→ S → P → L → E，讓高優先資訊先填。
>
> 8. **後送醫院近到遠排序（P2-11）**（v0.6.1）：ISBAR 醫院選單依 `min`（車程）升序排列，`priority:true` 院所（南投基督教、亞洲大學附屬）置頂加 ★。
>
> 9. **物資自訂：編輯/停用/匯入（P3-14）**（v0.6.1～v0.6.3）：詳情頁加「編輯」（名稱/類別/警戒線）、「停用」（軟刪除，灰顯保留可恢復）按鈕；物資頁加「📥 匯入清單」支援 JSON 貼入，重複名稱自動略過。

> **【v0.5 本版重點】**
>
> 1. **結構化就醫紀錄表**（v0.8.0-alpha）：治療評估改為結構化欄位 — 生命徵象格線（HR/BP/RR/Temp/SpO₂/GCS/瞳孔/血糖）、非創傷狀態 16 項 checkbox、創傷機轉 9 項 checkbox + 止血帶位置與時間、過去病史 12 項多選、過敏分類 checkbox、呼吸道/O₂/IV 管路欄位、處置紀錄。自動產生生命徵象文字摘要。
>
> 2. **延長照護紀錄表**（v0.8.2-alpha）：新增 `care_status: 'monitoring'` 留觀狀態。留觀中病患卡片顯示「+ 照護紀錄」「↻ 重評」「後送」按鈕。照護紀錄為簡易表單（生命徵象 + 意識 + 處置 + 備註），寫入 triages 表作為時間序列。
>
> 3. **後送流程強化**（v0.7.0-alpha）：27 間醫院清單（含距離、等級、車程分鐘）、後送方向（119/車/自容/容帶回/自行離開）、緊急順序自動排序、通話狀態追蹤、ISBAR 自動帶入醫院與方向。
>
> 4. **物資管理對齊 shelter**（v0.8.3-alpha）：取用/補充改為 modal + stepper、交易紀錄 transactions[] 審計追蹤、新增物資 modal、物資詳情頁含異動紀錄、缺料通報按鈕。
>
> 5. **Bug fix 8 項**（v0.7.0-alpha）：步驟順序驗證、清消單向、CSS 溢出、已結案事件保護、PersonCrypto 跨帳號共享金鑰（deriveKey(salt,salt)）、後送頁 escHtml 未定義修正。
>
> 6. **病患詳情歷程**：統一時間軸（最新→最舊），顯示所有事件（檢傷、評估、照護紀錄、轉色、後送、交接）。

> **【v0.2 歷史重點】**
>
> 1. 整合安全與網路架構規格 v1.2，醫療組 Pi 作為系統節點的網路配置、加密與非中國品牌硬體要求全部納入本文件。
>
> 2. 醫療組工具不再只是 SOP 查詢頁，而是以傷患、檢傷、治療位、後送與物資為核心的狀態管理系統。
>
> 3. 直接沿用收容組已驗證的 Offline-First、IndexedDB、PWA、同步、交班快照與資安骨架，以縮短開發路徑。
>
> 4. 醫療版新增高優先模組：再評估倒數、後送佇列、ISBAR 交接、治療區容量、醫療物資低量警示與撤退模式。

**依據文件：**

- \[密級C\] 醫療組SOP_20260323.md
- shelter_pwa_spec.md
- shelter_pwa.html / shelter_ws_server.js / sw.js
- security_network_spec_v1.2.md（★ v0.2 新增整合）

---

## 0　文件目的與背景

本規格書描述「醫療組 PWA 現場醫療管理系統」（以下簡稱本系統）的第一版需求，供開發者據以實作，並作為日後換手、擴充與跨組協作的基準文件。

系統定位不是電子病歷系統，也不是完整院前 EMS 系統；它是一套面向民防據點醫療站的現場作戰工具，目標是在高壓、低網路、多人輪替的情境下，讓醫療組能即時掌握：誰在哪一區、檢傷等級是否變化、哪些傷患待再評估、誰需要後送、還剩多少治療位與關鍵物資。

### 0.1　設計哲學

- **離線優先（Offline-First）**：完全離線可用；網路恢復後再同步，不假設網路穩定。
- **實體導向（Entity-Centric）**：Patient、Treatment Slot、Transfer、Resource 是核心；SOP 為附掛在實體上的作業規則。
- **時間敏感（Time-Critical）**：系統必須支援 5 分鐘 / 15 分鐘再評估倒數與逾時警示。
- **最低操作門檻**：新手在高壓下 3 分鐘內可完成一筆檢傷分流，不依賴大量打字。
- **可降級（Graceful Degradation）**：停電或設備不足時可輸出紙本清單與交班摘要，復電後再補登。
- **最小可行版本優先**：先做可作戰的 v0.1 / v1.0，再擴充到跨組介接、醫囑與統計分析。
- **安全隔離**：資料不上傳雲端，傳輸加密，靜態加密，硬體非中國品牌（見 §7、§8）。

### 0.2　與上游文件的關係

**醫療組 SOP** 提供本系統的業務邊界與作業規則，例如單一入口/出口、安檢不可省略、START 檢傷、創傷走 XABCDE、非創走 ABC、30 分鐘量能回報、每 2 小時輪替、超過 4 小時交班、ISBAR 後送與撤退優先順序。

**收容組 PWA** 則提供可沿用的系統骨架：PWA 離線安裝、IndexedDB 本機資料庫、角色視角、儀表板、物資追蹤、交班快照、匯出加密、PIN 鎖、假名化與 WebSocket 區網同步。

**安全與網路架構規格 v1.2**（★ v0.2 新增）定義醫療組 Pi（Pi 500）作為 ICS_DMAS 系統節點的：三情境網路架構、靜態 IP（192.168.100.30）、LUKS 加密、mkcert TLS 憑證、WireGuard VPN、非中國品牌硬體清單，以及與指揮部 Pi 500 的整合關係。

### 0.3　從 SOP 到系統物件的轉換

| SOP 重點 | 系統化後的核心物件 | 系統功能 |
|----------|-------------------|----------|
| 檢傷與分流 | Patient + Triage | 接收/檢傷頁、分流與顏色標記 |
| 紅黃綠黑區與後送區 | Treatment Slot | 區域地圖、床位/治療位占用 |
| 再評估與升降級 | Patient Status | 5/15 分鐘倒數、逾時與升級警示 |
| 後送與交班 | Transfer + Shift | 待後送佇列、ISBAR 交接單、交班快照 |
| 物資領用與補給 | Resource | 盤點、取用、低量警示、補給申請 |
| 安全威脅與撤退 | Incident | 警示橫幅、撤退模式、事件紀錄 |

---

## 1　系統範圍與設計假設

### 1.1　v0.1 / v1.0 範圍內

- 單一醫療站的接收、檢傷、分流、治療位管理與後送佇列。
- 紅區、黃區、綠區、黑區、後送區與入口安檢/檢傷區的即時狀態呈現。
- Patient 假名化名冊與關鍵病況摘要，不做完整病歷長文輸入。
- 危急每 5 分鐘、非危急每 15 分鐘的再評估提醒與逾時警示。
- 30 分鐘量能回報與 30 分鐘物資盤點支援。
- 後送 ISBAR 交接內容產生與後送狀態追蹤。
- 醫療物資開場盤點、取用扣減、低量警示與補給紀錄。
- 安全事件、暴力/傳染病疑慮、撤退模式與交班快照。
- CSV / JSON 匯出、列印交班摘要、離線 PWA 安裝。

### 1.2　暫不納入（後續版本考慮）

- 完整電子病歷、醫囑、用藥醫令、簽章與法律效力病歷保存。
- 跨據點整合後端、跨站傷患查詢、醫院端 API 介接。
- 影像上傳、照片蒐證、生命徵象裝置自動串接。
- 精細藥品批號/效期追蹤與受管制藥品核銷。
- 智慧分派演算法、統計分析報表、機器學習預測。

### 1.3　設計假設

| 假設項目 | 假設內容 | 不成立時的降級方案 |
|----------|----------|-------------------|
| 操作設備 | Android / iPhone / iPad / 筆電瀏覽器均可操作 | 改用單機 + 紙本補登 |
| 網路 | 多數時間無穩定外網，但可有本地 Wi-Fi | 以單機模式或手動 Peer Delta 匯入 |
| 醫療站規模 | 同時處置 10–30 名傷患，紅區床位有限 | 由設定調整各區容量與治療位 |
| 操作者背景 | 含非 IT 志工與輪替人員 | 所有核心任務 3 步內可完成 |
| 法規定位 | 內部訓練與作戰紀錄輔助工具 | 正式醫療文書仍以紙本/既有制度為主 |

---

## 2　核心資料模型

本系統延續收容組的「實體導向」思路，但將核心實體由 Person / Bed / Resource 改為 Patient / Triage / Treatment Slot / Transfer / Resource / Incident / Shift。

### 2.1　核心實體總覽

| 實體 | 用途 | 關鍵欄位（摘要） |
|------|------|-----------------|
| Patient | 傷患主檔 | display_id、來源、是否安檢、是否已登記、檢傷顏色、創傷/非創、目前區域、再評估時間、結果 |
| Triage | 檢傷紀錄 | START 結果、可行走、呼吸、循環、意識、操作者、時間戳 |
| Treatment Slot | 治療位/床位 | zone、slot_id、status、assigned_patient、priority |
| Transfer | 後送案件 | requested_at、reason、destination、vehicle_status、ISBAR、departed_at、handoff_done_at |
| Resource | 醫療物資 | name、category、qty_initial、qty_current、qty_low_threshold、transactions |
| Incident | 安全/營運事件 | type、severity、status、linked_patients、notes、assigned_to |
| Shift/Snapshot | 交班與狀態快照 | timestamp、summary、open_incidents、low_resources、handover_notes |
| Config | 站點設定 | station_name、zones、capacity、radio、alert_thresholds |

### 2.2　Patient（傷患主檔）

Patient 為所有作業中心。系統列表與大多數畫面以 display_id 呈現，不主動顯示真實姓名。

| 欄位 | 型別 | 說明 | v0.1 |
|------|------|------|------|
| id | UUID | 系統主鍵 | 系統 |
| display_id | String | 可讀編號，例如 M-001 | 系統 |
| name | String | 真實姓名；可留空或填匿名 | 選填 |
| source_type | Enum | 前進組 / 收容組 / 自行抵達 / 其他 | 必填 |

> **【指揮部儀表板依賴】** `source_type`（A/B/C）是指揮部儀表板「② 流量來源圖」的關鍵資料來源。
> 快照推送時必須包含每個時間點的 A/B/C 累計人數（`src_a`、`src_b`、`src_c` 欄位），
> 否則指揮部無法診斷醫療壓力的根源。
>
> **【v0.5 新增 extra 欄位】** 快照 `extra` 現包含：
> - `src_a`, `src_b`, `src_c`：來源累計人數
> - `staff_ratio`：人均服務量（在場傷患 / 活躍操作員）
> - `supplies`：物資現況 `{ iv, oxygen, tourniquet }`（從 resources 表讀取 qty_current）
> - `supplies_max`：物資初始值 `{ iv, oxygen, tourniquet }`（從 config 表讀取）
> - `incident_pressure`：事件壓力 `{ high, medium, low, open_total, resolved_30min }`（最近 30 分鐘）

| security_cleared | Bool | 是否完成安檢；危急時可標記同步處理中 | 必填 |
| registered_with_shelter | Enum | 已登記 / 未登記 / 已通知補登 | 必填 |
| triage_color | Enum | 紅 / 黃 / 綠 / 黑 | 必填 |
| injury_type | Enum | 創傷 / 非創 | 必填 |
| current_zone | Enum | 檢傷 / 紅區 / 黃區 / 綠區 / 黑區 / 後送區 / 已離區 | 必填 |
| slot_id | String | 當前治療位/床位 | 選填 |
| chief_issue | String | 主要傷情摘要 | 必填 |
| vitals_summary | String | HR、BP、RR、SpO2、GCS 等文字摘要（自動產生） | 系統 |
| vitals_structured | Object | 結構化生命徵象（hr, sbp, dbp, rr, temp, spo2, glucose, gcs_e/v/m, pupil_r/l） | 系統 |
| condition_types | Array[String] | 傷情類型 checkbox 結果（創傷機轉或非創狀態） | 系統 |
| past_medical_history | Array[String] | 過去病史多選結果 | 系統 |
| allergy_flags | Array[String] | 過敏分類（無/藥物/食物/其他） | 系統 |
| allergy_detail | String | 過敏詳細說明 | 選填 |
| routes | Object | 管路：airway[], o2[], iv, 各項 detail | 系統 |
| treatment | String | 處置紀錄 | 選填 |
| care_status | Enum | triaged / assessed / monitoring / pending_transfer | 系統 |
| reassess_due_at | Datetime | 下次再評估時間 | 系統 |
| disposition | Enum | 在場 / 留觀 / 後送 / 死亡 / 撤退中 / 離開 | 系統 |
| transfer_direction | String | 後送方向（119/車/自容/容帶回/自行離開） | 系統 |
| transfer_hospital | String | 後送目的地醫院名稱 | 系統 |
| transfer_order | Int | 後送緊急順序（系統依檢傷分類自動排序） | 系統 |
| transfer_called | Bool | 是否已聯繫目的地 | 系統 |
| operator_name / updated_at | System | 稽核欄位 | 系統 |

### 2.3　Triage（檢傷與評估紀錄）

Triage 表為多用途紀錄表，用於存放檢傷、治療評估、轉色、處置變更與照護紀錄。不覆蓋舊紀錄，每次新增一筆。

**紀錄類型（★ v0.5 新增 record_type 欄位）：**

| record_type | 說明 |
|-------------|------|
| （未設定） | 初始檢傷、轉色、處置變更等既有紀錄 |
| （含 trauma_or_medical） | 治療評估紀錄（就醫紀錄表） |
| `care` | 延長照護紀錄（留觀巡視） |

**共用欄位（所有傷患）：**

| 欄位 | 說明 |
|------|------|
| patient_id | 所屬傷患 ID |
| record_type | 紀錄類型（null / 'care'） |
| start_walk | 是否可自行行走 |
| start_breathing | 呼吸狀態；含開放呼吸道後才呼吸 |
| start_circulation | 橈動脈 / CRT 判斷 |
| start_mental | 是否可配合簡單指令 |
| trauma_or_medical | 創傷 / 非創判斷 |
| override_reason | 人工覆核或例外處理原因 |
| triage_by / triage_at | 操作者與時間 |

**創傷欄位（trauma_or_medical = 創傷，對應 SOP §6.3 XABCDE）：**

| 欄位 | 說明 | XABCDE 對應 |
|------|------|------------|
| x_hemorrhage_controlled | 大出血控制狀態（Enum：已止血 / 止血帶中 / 未控制） | X — 止血優先 |
| a_airway_patent | 呼吸道是否通暢（Bool；開放後通暢請記錄手法） | A — 呼吸道 |
| a_airway_notes | 呼吸道處置備注（String；如：頭頸后仰、口腔異物清除） | A |
| b_breathing_status | 呼吸品質（Enum：正常 / 費力 / 缺氧 / 無自主呼吸） | B — 呼吸 |
| b_interventions | 呼吸處置（Enum 多選：給氧 / BVM 輔助 / 密封胸腔傷口） | B |
| c_pulse_quality | 脈搏品質（Enum：正常 / 細速 / 無） | C — 循環 |
| c_interventions | 循環處置（Enum 多選：IV 建立 / 加壓包紮 / 輸液中） | C |
| d_gcs | GCS 總分（Int 3–15）；或 AVPU（Enum：A/V/P/U） | D — 神經 |
| d_pupils | 瞳孔反應（Enum：正常 / 不等大 / 無反應） | D |
| e_exposed | 全身暴露檢查是否完成（Bool） | E — 暴露 |
| e_findings | 暴露檢查發現摘要（String；如：背部穿刺傷） | E |

**非創欄位（trauma_or_medical = 非創，對應 SOP §6.4 ABC + SAMPLE/OPQRST）：**

| 欄位 | 說明 |
|------|------|
| abc_airway | 呼吸道（Enum：通暢 / 需處置） |
| abc_breathing | 呼吸（Enum：正常 / 異常）|
| abc_circulation | 循環（Enum：正常 / 異常） |
| sample_s | S — 主訴 / 症狀（String） |
| sample_a | A — 過敏史（String） |
| sample_m | M — 用藥史（String） |
| sample_p | P — 過去病史（String） |
| sample_l | L — 最後進食時間（String） |
| sample_e | E — 事件經過（String） |
| opqrst_onset | O — 何時開始（String） |
| opqrst_provoke | P — 加重 / 緩解因素（String） |
| opqrst_quality | Q — 疼痛性質（String；如：刺痛、悶痛） |
| opqrst_radiation | R — 是否放射（String） |
| opqrst_severity | S — 疼痛分級 0–10（Int） |
| opqrst_time | T — 持續時間與變化趨勢（String） |
| blood_glucose | 血糖值（Float，mg/dL；選填） |

> *※ 創傷欄位與非創欄位依 trauma_or_medical 值切換顯示，不互相干擾。UI 以分頁或折疊區塊呈現，避免畫面過長。選填欄位留空代表「未評估」，不視為錯誤。*

**結構化生命徵象（★ v0.5 新增，共用於治療評估與照護紀錄）：**

| 欄位 | 說明 |
|------|------|
| vitals_structured.hr | 心跳 HR（次/分） |
| vitals_structured.sbp / dbp | 收縮壓 / 舒張壓（mmHg） |
| vitals_structured.rr | 呼吸 RR（次/分） |
| vitals_structured.temp | 體溫（°C） |
| vitals_structured.spo2 | 血氧 SpO₂（%） |
| vitals_structured.glucose | 血糖（mg/dL） |
| vitals_structured.gcs_e / gcs_v / gcs_m | GCS 睜眼/語言/運動（臨床值 select） |
| vitals_structured.pupil_r / pupil_l | 瞳孔 R/L（mm） |
| vitals_summary | 自動產生文字摘要，如「HR 100  BP 120/80  RR 25  T 38°C  SpO₂ 95%  GCS E4V5M6=15  瞳孔 R3/L3  血糖 120」 |

**結構化傷情分類 checkbox（★ v0.5 新增）：**

非創傷狀態 16 項：呼吸問題、異物哽塞、疑似中毒、癲癇/抽搐、昏迷、行為異常、胸痛/悶、孕婦急症、腹痛、溺水、一般疾病、OHCA、頭痛/頭暈、發燒、噁心/嘔吐、肢體無力

創傷機轉 9 項：一般外傷、墜落傷、穿刺傷、燒燙傷、電擊傷、生物咬噬傷、OHCA、輾/壓傷、其他

止血帶 4 位置：上肢左/右、下肢左/右，各含施加時間欄位

**過去病史多選（★ v0.5 新增）：** 心臟疾病、肝臟疾病、腎臟疾病、精神疾病、高血壓、糖尿病、COPD、中風、癲癇、癌症、無、不詳

**過敏分類 checkbox（★ v0.5 新增）：** 無已知過敏 / 藥物 / 食物 / 其他（互斥邏輯：選「無」自動取消其他）

**管路欄位（★ v0.5 新增）：**

| 欄位 | 說明 |
|------|------|
| routes.airway | 呼吸道器材（NPA / OPA / I-GEL / ETT / 氣切） |
| routes.o2 | 給氧方式（鼻管 / 面罩 / NRB / BVM）+ 流速 |
| routes.iv | 靜脈通路已建立（Bool）+ 詳情 |

**照護紀錄專用欄位（★ v0.5 新增，record_type = 'care'）：**

| 欄位 | 說明 |
|------|------|
| consciousness | 意識狀態（清醒 / 嗜睡 / 混亂 / 昏迷 / 躁動） |
| care_notes | 備註（特殊觀察、家屬交代） |
| treatment | 處置紀錄（給藥、換藥、管路處理） |

### 2.4　Treatment Slot（治療位/床位）

醫療版不沿用收容組「住宿床位」語意，而是改成各區治療位。紅區、黃區、綠區、黑區與後送區皆可配置若干 slot。

| 欄位 | 說明 |
|------|------|
| slot_id | 例如 R-01、Y-03、G-05、T-02 |
| zone | red / yellow / green / black / transfer |
| status | empty / occupied / suspended / reserved_transfer |
| assigned_patient_id | 目前占用之 Patient |
| last_cleaned_at | 供撤床與重置紀錄 |
| updated_at | 最後更新時間 |

### 2.5　Transfer、Resource、Incident、Shift

| 實體 | 最小必要欄位 | 說明 |
|------|-------------|------|
| Transfer | patient_id、reason、requested_at、destination、vehicle_status、isbar_text、departed_at、handoff_done_at | 後送案件必須保存「已完成必要救命處置」的交接摘要。 |
| Resource | name、category、unit、qty_initial、qty_current、qty_low_threshold、transactions | 關鍵物資低量時自動產生 Incident。 |
| Incident | type、severity、status、linked_patients、reported_by、assigned_to、notes | 涵蓋安全威脅、傳染疑慮、量能滿載、設備故障等事件。 |
| Shift | started_at、role、operator_name、handover_notes、snapshot | 任何交班皆留存快照，不可刪除。 |

### 2.6　特種敏感資料標注

- 以下欄位應比照收容組 v1.3 的高保護等級：name、傷情摘要、生命徵象、GCS、病史/用藥摘要、血糖、傳染病疑慮、暴力/精神狀態。
- 所有列表、儀表板、快照與無線電通報預設只顯示 display_id，不顯示姓名。
- 含敏感資料的匯出必須強制加密；純統計匯出可不加密。
- 已完成後送或離區後，核心醫療紀錄不得任意回改；僅能追加備註。

---

## 3　角色、畫面與權限

### 3.1　建議角色

| 角色 | 主要工作 | 預設首頁 | 可見重點 |
|------|----------|----------|----------|
| 組長 | 全局控盤、量能回報、調度與撤退決策 | 儀表板 | 全站資料、交班、匯出、設定 |
| 副組長 | 支援控盤、追蹤逾時與待後送 | 儀表板 | 大部分頁面，不含高權限設定 |
| 檢傷官 | 接收、檢傷、分流 | 接收/檢傷 | 新建 Patient、檢傷紀錄、分流 |
| 紅/黃/綠區治療官 | 區內處置與再評估 | 治療區看板 | 區內名單、再評估、升降級 |
| 後送官 | 待後送清單、ISBAR 交接 | 後送 | Transfer 佇列、交接單 |
| 後勤官 | 物資盤點與補給 | 物資 | Resource、低量警示 |
| 通訊官 | 對外聯絡、通報 | 儀表板或後送 | 通報文案、目的地與運輸狀態 |
| 機動人員 | 支援各區、填補缺口 | 治療區看板 | 與副組長相同，不含設定；無固定區域，可跨區操作 |

### 3.2　主要頁面

| 頁面 | 核心任務 | 必要元件 |
|------|----------|----------|
| 儀表板 | 全站控盤 | 各色傷患數、可用紅區治療位、待後送、逾時再評估、低量物資、開放事件、通報文字 |
| 接收/檢傷 | 新建與分流 | 來源管道、安檢確認、START、創傷/非創、治療位指派 |
| 治療區看板 | 區內管理 | 按紅/黃/綠/黑/後送區顯示卡片、再評估倒數、升降級、轉後送 |
| 後送 | 轉送作業 | 待後送佇列、ISBAR 範本、車輛/醫院狀態、交接完成 |
| 物資 | 盤點與領用 | 開場盤點、取用、低量警示、補給需求 |
| 事件 | 安全與異常 | 事件建立、指派、追加紀錄、結案 |
| 交班/快照 | 輪替與留痕 | 狀態摘要、交班備註、歷史記錄 |
| 設定 | 站點參數 | 治療位數、警示門檻、無線電、同步設定 |

### 3.3　畫面原則

- 少打字、多單選與快捷按鈕；常用術語用標籤呈現。
- 名單卡片至少顯示：display_id、顏色、目前區域、主要傷情摘要、下次再評估倒數、是否待後送。
- 紅色與逾時警示一律放畫面上方；任何角色都看得到開放事件橫幅。
- 同一患者的「目前狀態」與「歷史紀錄」分層呈現，避免畫面過度擁擠。

---

## 4　業務流程與狀態機

### 4.1　Patient 生命週期狀態機

| 狀態 | 進入條件 | 可轉移至 | 系統要求 |
|------|----------|----------|----------|
| new_intake | 建立新患者 | security_pending / triaged | 若危急可標記為同步安檢 |
| security_pending | 尚未完成安檢 | triaged / blocked | 不可直接關閉案件 |
| triaged | 完成 START | in_red / in_yellow / in_green / in_black | 必須有 triage_color |
| in_red / in_yellow / in_green / in_black | 分流至各區 | monitoring / transfer_pending / discharged / 關區移轉 | 系統自動計時再評估 |
| monitoring | 處置狀態選「留觀」（★ v0.5 新增） | transfer_pending / in_red~black（重評後可變色） | care_status 設為 monitoring；病患卡片顯示「+ 照護紀錄」「↻ 重評」「後送」 |
| transfer_pending | 決定後送 | in_transfer_area / transferred_out | 需建立 Transfer 記錄 |
| discharged | 處置後離開 | closed | 保留離區時間與結果 |
| transferred_out | 已後送離站 | closed | 凍結核心欄位 |
| evacuating | 啟動撤退模式 | closed / transferred_out | 顯示撤退優先順序 |
| closed | 案件結束 | 僅可追加備註 | 不可刪除 |

### 4.2　接收流程

**三種來源（UI 快捷入口各一）：**

- **來源 A：前進組轉入。** 前進組以 MIST 口頭交接（見下方格式），系統記錄 MIST 摘要。**即使有 MIST 交接，檢傷官仍必須重新執行 START，不可直接沿用前進組判斷。**
- **來源 B：收容組轉送。** 即使已在收容組登記，仍需再次安檢。確認身份後補齊醫療紀錄。
- **來源 C：自行抵達。** 安檢後檢傷，並通知收容組補登（registered_with_shelter = 已通知補登）。

**危急例外：** 可先直送醫療區評估，但安檢、手環與收容登記必須同步執行，系統以 security_cleared = 同步處理中 標記，不得省略此欄位。

**MIST 接收格式（前進組→醫療組，來源 A 專用）：**

| 欄位 | 代表 | 範例 |
|------|------|------|
| M（Mechanism） | 受傷機轉 | 建物倒塌壓傷、爆炸波及 |
| I（Injuries） | 已發現傷害 | 左下肢開放性骨折、頭部擦傷 |
| S（Signs） | 目前生命徵象 | HR 120、BP 90/60、RR 24、GCS 13 |
| T（Treatment） | 已做處置 | 已上止血帶、已給氧 |

UI 規格：來源 A 接收頁呈現四個文字欄位（M/I/S/T），可快速輸入或選擇常用片語；完成後系統帶入 Patient.chief_issue（由 I 欄位）與 Patient.vitals_summary（由 S 欄位）作為初始值，操作者可覆寫。MIST 原始記錄保存於 Triage 紀錄，不可刪除。

### 4.3　再評估規格

| 對象 | 標準間隔 | 逾時後行為 | 備註 |
|------|----------|-----------|------|
| 紅區 / 危急 | 5 分鐘 | 卡片轉紅框、排序置頂、儀表板警示 | 重新評估後重設倒數 |
| 黃區 / 非危急但需觀察 | 15 分鐘 | 卡片轉橘框、排序提前 | 若惡化可一鍵升紅 |
| 綠區 | 依操作者手動設定或處置完成 | 無預設強警示 | 以離區或轉黃為主 |
| 黑區 | 僅於資源允許時手動再評估 | 不自動倒數 | 避免無效警示 |

### 4.4　後送流程

- 治療官判斷需後送後，一鍵建立 Transfer 案件，帶入目前區域、主要傷情與必要救命處置摘要。
- 後送官收到案件後，更新目的地、運輸狀態與等待時間；通訊官可直接複製通報文字。
- ISBAR 交接單必須可編修，但需保留系統自動帶出的生命徵象 / GCS / 已完成處置。
- 後送完成時，Patient 狀態改為 transferred_out，系統同步釋放原治療位並更新量能。

### 4.5　撤退模式

**觸發：** 組長在儀表板按「啟動撤退」（需二次確認），或接收指揮部下令事件。

**切換後系統行為：**
1. 接收頁快捷入口凍結，停止新收案。
2. 主視角切換為「撤退清單」，依下方優先順序排列所有現存患者。
3. 每位患者可標記為「已撤離」、「後送中」、「原地留置（記錄位置）」。
4. 關鍵物資清單（AED、藥品、氧氣）單獨列出，供後勤官確認是否攜出。

**撤退優先順序與系統支援：**

| 撤退優先順序 | 系統支援 |
|-------------|----------|
| ① 紅區傷患 | 置頂、紅色標示、快速轉後送或移動狀態 |
| ② 黃區傷患 | 第二序列 |
| ③ 綠區傷患（可自行移動者先行） | 標示可自行離開，引導至出口 |
| ④ 黑區患者 | 依資源判斷；若無法攜帶，必須記錄位置（position_note 欄位），並向指揮部回報 |
| ⑤ 醫療物資 | 只列關鍵物資：AED、藥品、氧氣；後勤官逐項確認 |
| ⑥ 醫療人員 | 確認所有患者已標記後才可離開 |
| ⑦ 組長（最後） | 系統提供「組長確認撤退完成」按鈕，觸發後產生撤退快照並自動產生回報文字 |

**撤退完成回報文字（自動產生）：**
```
醫療區已完成撤退。
已撤離傷患：紅 X 名、黃 X 名、綠 X 名。
後送中：X 名。
黑區原地留置：X 名（位置已記錄）。
醫療人員全數安全。
```

### 4.6　留觀與延長照護流程（★ v0.5 新增）

**觸發：** 治療評估完成後，操作者在處置狀態選擇「留觀」。

**系統行為：**
1. `care_status` 設為 `monitoring`，`disposition` 設為 `留觀`。
2. 病患卡片顯示「👁 留觀中」標示，按鈕組改為：移區 / + 照護紀錄 / ↻ 重評 / 後送。
3. 病患詳情 progress bar 新增「留觀」步驟。
4. 儀表板顯示「留觀中」人數統計。

**照護紀錄（簡易巡視表單）：**
- 生命徵象格線（與就醫紀錄表相同欄位）
- 意識狀態（清醒 / 嗜睡 / 混亂 / 昏迷 / 躁動）
- 處置紀錄（給藥、換藥、管路處理）
- 備註

每筆照護紀錄寫入 `triages` 表（`record_type: 'care'`），同時更新 `patients` 表的 `vitals_summary` 與 `vitals_structured`。

**狀態流轉：**
```
triaged → assessed → monitoring（留觀中）→ 可重評（重新完整就醫紀錄表）
                                           → 可後送
                   → pending_transfer（後送中）
```

留觀中仍可執行完整重評（↻ 重評），不鎖死流程。所有紀錄在病患詳情歷程時間軸中統一顯示。

---

## 5　功能規格

### 5.1　儀表板

- 傷患統計：紅、黃、綠、黑、已後送、已離區。
- 容量摘要：可用紅區治療位、各區占用、後送區等待數。
- 警示摘要：再評估逾時、待後送超時、低量物資、開放事件。
- 量能燈號（綠/黃/紅，見 §6.1）。
- 交班入口：一鍵生成快照與交班備註。
- **30 分鐘量能回報提醒**：距上次通報超過 30 分鐘時，儀表板顯示提醒橫幅。
- **一鍵複製量能回報文字**：依 SOP 附錄一格式自動產生，操作者可補充「預計達上限時間」。

**量能回報文字格式（SOP 附錄一，系統自動填入）：**

```
指揮部，醫療組回報：
目前紅傷 {N} 名、黃傷 {N} 名、綠傷 {N} 名、黑 {N} 名。已後送 {N} 名。
可用紅區床位剩 {N} 床、止血帶剩 {N} 條、氧氣瓶剩 {N} 支。
{若量能燈號紅：預計 {N} 分鐘內將達醫療量能上限。}
```

欄位說明：
- 紅/黃/綠/黑：系統自動從 Patient 狀態統計
- 已後送：transferred_out 計數
- 可用紅區床位：slot 表中 zone=red 且 status=empty 的數量
- 止血帶、氧氣瓶：從 Resource 表自動帶入（需後勤官設定 qty_current）
- 「預計達上限」：操作者手動填入（自由文字欄位）

### 5.2　接收/檢傷頁

- 可用三個快捷入口：前進組轉入、收容組轉送、自行抵達。
- 安檢完成與收容補登狀態用兩個獨立欄位，不互相取代。
- START 判斷改用單題式流程，避免一次顯示過多欄位。
- 完成檢傷後系統立即提示推薦區域與可用治療位。

### 5.3　治療區看板

- 依紅 / 黃 / 綠 / 黑分頁顯示，含待評估佇列。
- 卡片可快速執行：重設再評估、移轉區域、評估/重評、後送。
- 紅區卡片需顯示生命徵象摘要、GCS 與已完成救命處置。
- 若無可用紅區位，系統顯示「紅區滿載」並提示組長啟動備援。
- **結構化就醫紀錄表**（★ v0.5 已實作）：點擊「▶ 評估」或「↻ 重評」開啟完整結構化表單，含傷情分類、生命徵象格線、GCS、瞳孔、condition checkbox、止血帶、PMH 多選、過敏分類、管路（呼吸道/O₂/IV）、處置紀錄。儲存後自動更新 care_status 為 assessed，重設再評估倒數。
- **留觀中病患**（★ v0.5）：care_status = monitoring 時，卡片顯示「👁 留觀中」，按鈕為「+ 照護紀錄」「↻ 重評」「後送」。

### 5.4　後送頁

- Transfer 佇列依臨床優先（紅>黃>綠）與等待時間排序，等待超過 30 分鐘顯示逾時警示。
- **後送 modal**（★ v0.5 已實作）：選擇後送方向（119/車/自容/容帶回/自行離開）、目的地醫院（27 間，依車程分鐘降序排列，含等級與縣市）、車牌欄位。系統自動計算緊急順序。
- **醫院清單**：27 間醫院，欄位含 id、name、level（重度級/中度級/一般級）、county、km、min、priority。
- **通話狀態**：每張後送卡片有「☎ call / ✅ 已call」toggle 按鈕，追蹤是否已聯繫目的地。
- ISBAR 自動帶入 Identify / Situation / Assessment 草稿，R 欄位自動填入選定醫院與方向；操作者補充 Background / Recommendation。
- 交接完成後保留不可刪除的交接摘要。

### 5.5　物資頁（★ v0.5 大幅更新，對齊 shelter）

- **開場盤點**：預設物資清單（12 項），後勤官逐項調整實際數量後確認。
- **物資卡片**：顯示名稱、當前/初始數量、進度條（百分比）、低量警示。點擊卡片開啟物資詳情頁（含異動紀錄）。
- **取用 modal**：stepper 數量選擇 + 取用原因欄位。低量時自動建立 Incident。
- **補充 modal**：stepper 數量選擇 + 補充說明欄位。
- **交易紀錄 transactions[]**（★ v0.5 新增）：每筆取用/補充記錄操作者、時間、數量、原因。物資詳情頁可查閱完整異動歷史。
- **新增物資**（★ v0.5 新增）：手動新增非預設項目（名稱、類別、數量、警戒線）。
- **缺料通報**（★ v0.5 新增）：低量項目顯示獨立「缺料通報」按鈕，一鍵建立 Incident。
- **低量警示**：qty_current ≤ threshold 時卡片左側橘色邊框，全頁提示低量項目列表。
- **盤點提醒**：距上次盤點超過 30 分鐘顯示提醒；可標記盤點完成。
- 管制物資優先列示：止血類、呼吸道類、循環類、藥品、固定類、保暖類、監測器材。

### 5.6　事件頁

- 事件類型至少含：security_threat、violent_patient、infectious_risk、resource_shortage、capacity_overload、equipment_failure、evacuation。
- 任何角色可通報新事件；組長可指派負責人與結案。
- 未結案事件在所有頁面頂端顯示警示橫幅。

### 5.7　交班/快照

- 任何角色可發起交班；系統自動抓取當前傷患統計、各區占用、待後送、低量物資與開放事件。
- 紅區患者需逐一交接，因此交班頁需有「紅區明細」區塊，不可只列統計。
- 交班記錄不可刪除，僅可追加備註。

### 5.8　匯出與列印

| 類型 | 格式 | 用途 | 敏感等級 |
|------|------|------|----------|
| 全站快照 | JSON | 狀態恢復、事後檢討 | 高，須加密 |
| 傷患名冊（假名化） | CSV | 檢討與統計 | 中，建議加密 |
| 待後送清單 | 列印 / PDF | 交接與手持備援 | 高，須受控 |
| 交班摘要 | 列印 / PDF | 輪替使用 | 中，視內容加密 |
| 物資盤點 | CSV | 補給與場復 | 低 |

---

## 6　警示與通報規格

### 6.1　醫療量能燈號【開發決策】

SOP 明確要求每 30 分鐘回報醫療量能，但未規定系統燈號門檻。為了讓畫面更直觀，本版提出以下建議規格，後續可依演訓調整。

| 燈號 | 觸發條件（建議） | 通報建議文字 |
|------|-----------------|-------------|
| 綠 | 紅區可用位 > 2，且無關鍵物資低量 | 醫療組回報：量能穩定，現可持續收治。 |
| 黃 | 紅區可用位 ≤ 2，或有一項關鍵物資低量，或待後送 ≥ 2 | 醫療組回報：量能趨緊，請預作補給/後送準備。 |
| 紅 | 紅區無空位，或氧氣/止血帶/AED 等關鍵物資不足，或待後送壅塞 | 醫療組回報：量能已逼近上限，請啟動備援或加速後送。 |

### 6.2　自動警示清單

| 警示名稱 | 條件 | 出現位置 |
|----------|------|----------|
| 再評估逾時 | reassess_due_at 已過 | 治療區卡片 / 儀表板 |
| 待後送過久 | Transfer 建立後超過設定時間仍未出發 | 後送頁 / 儀表板 |
| 低量物資 | qty_current ≤ threshold | 物資頁 / 儀表板 / 事件頁 |
| 安全威脅 | 開放事件屬安全類 | 全頁頂端橫幅 |
| 量能滿載 | 紅區零空位或燈號紅 | 全頁頂端橫幅 |
| 物資盤點提醒 | 距上次盤點超過 30 分鐘 | 儀表板 / 物資頁（後勤官視角） |
| 待補登 | registered_with_shelter ≠ 已登記 且已入區 | 接收頁 / 名單卡 |
| 輪替提醒 | 距最後一次 Shift 記錄超過 2 小時（對應 SOP §附錄三） | 儀表板頂端（組長視角）；建議性警示，不強制 |
| 強制交班提醒 | 距最後一次 Shift 記錄超過 4 小時（對應 SOP §4.2） | 儀表板頂端全角色可見；橘色橫幅，需組長確認後關閉 |

---

## 7　資安與隱私（整合安全架構規格 v1.2）

本節依據 security_network_spec_v1.2.md 整合，涵蓋應用層資安、傳輸安全、靜態加密三個層次。醫療組 Pi（192.168.100.30）為受保護節點，所有措施與全系統規格一致。

### 7.1　應用層資安（原有規格）

- 所有資料預設只存本地設備，不上傳任何雲端服務。
- APP 啟動需輸入操作者姓名（或工號）與 PIN；PIN 不落地，閒置 90 秒顯示警告 + 30 秒後自動登出（共 2 分鐘，與收容組一致）。
- 所有主要實體自動寫入 operator_name 與 updated_at，不可手動刪除。
- 含敏感資料的匯出強制 AES-256-GCM 加密；密碼以第二管道傳遞。
- 歷史檢傷、後送與交班紀錄不可刪除，只能追加備註，維持稽核可追性。
- 對外通報文案預設僅含統計與 display_id，不含姓名與不必要病史。

### 7.2　傳輸安全（mkcert TLS）

依 security_network_spec_v1_2 §4，本系統採用 mkcert 本地 CA 方案，不使用 Let's Encrypt（後者需公開域名驗證，情境 2、3 無法使用）。

作者 Filippo Valsorda（義大利裔美國人，前 Go 安全團隊），無中國關聯，開源免費。

- 醫療組 Pi 服務端點：WSS 192.168.100.30:8775、Admin HTTPS 192.168.100.30:8776
- 所有前端 URL 須由 ws:// → wss://，http:// → https://
- 憑證有效期預設 825 天，演訓前須檢查是否過期。
- 手機/平板須預裝 mkcert CA 根憑證（iOS：AirDrop → 設定 → 信任；Android：設定 → 安全性）。

**情境 1B 補充：WireGuard VPN**（Jason Donenfeld 開發，美國，已併入 Linux kernel 5.6，無中國關聯）

- 指揮部 Pi 500 開 WireGuard server，監聽 UDP 51820。
- 手機連入後視為同一虛擬 LAN，後續通訊與情境 1A / 2 相同。
- 每台手機一組金鑰對，設定以 QR code 分發。

### 7.3　靜態加密（LUKS）

依 security_network_spec_v1_2 §5，所有節點使用 LUKS（Linux Unified Key Setup）OS 層磁碟加密，覆蓋 SQLite、log、設定檔、暫存檔，無需修改應用程式碼。

| 節點 | 加密對象 | 金鑰管理 |
|------|----------|----------|
| 指揮部 Pi 500 | OS 碟 + Data Cartridge | YubiKey（主）+ 備援密碼（雙人原則） |
| 醫療組 Pi（本節點） | Data 分區（/data） | 演訓前設定 passphrase，任務結束後銷毀 |
| Field Node | MicroSD | Panic 長按 5 秒快速格式化 |

**Panic Wipe**：Pi 500 執行 `cryptsetup luksErase`，0.5 秒內 Header 抹除，資料永久遺失。Panic 按鈕需有防誤觸保護蓋。

開發階段（Mac）：使用 FileVault 全磁碟加密。LUKS 僅在 Pi 正式部署時設定。

### 7.4　API 驗證

依 security_network_spec_v1_2 §7，情境 1A / 2 / 3 由 WireGuard 或封閉 LAN 保護，不需額外 API 驗證。

| 等級 | 方案 | 說明 |
|------|------|------|
| 基本（現階段） | API Key per device | Header 帶 X-Device-Key，演訓前統一配發 |
| 進階（Phase 3） | YubiKey OTP | 與民防感知系統 §4.3 YubiKey 方案整合 |

### 7.5　硬體安全（非中國品牌）

依 security_network_spec_v1_2 §2.2，所有節點硬體必須符合非中國品牌要求。與醫療組直接相關的項目如下（完整清單見附錄 D）。

- 醫療組 Pi：Raspberry Pi 500（英國 Raspberry Pi Foundation）✅
- 醫療組手機/平板：Apple iPhone / iPad、Samsung Galaxy、Google Pixel ✅
- 禁止：Huawei、Xiaomi、OPPO、Vivo ❌
- WiFi（自建網路情境）：ASUS、Netgear、Mikrotik ✅；禁止 TP-Link、GL.iNet ❌
- SD 卡：Samsung PRO Endurance（韓）、SanDisk（美）✅；禁止 Lexar（2017 年被中國龍存科技收購）❌

---

## 8　技術架構（整合安全架構規格 v1.2）

### 8.1　系統整體架構與節點定位

依 security_network_spec_v1_2 §1，ICS_DMAS 系統架構如下（醫療組 Pi 以 ★ 標示）：

```
【前進組 / 安全組】
Field Node (Pi Zero 2W)
PTT 錄音 → 本機 Whisper STT → 上傳指揮部

【收容組】                          【指揮部 Console】
收容組 Pi (Pi 500) ─────────→        Pi 500
手機 PWA ↕ WebSocket                 - ICS_DMAS 指揮部儀表板

【醫療組】★ 本文件節點               - 民防感知系統 Console
醫療組 Pi (Pi 500) ─────────→        - SQLite（LUKS 加密）
手機 PWA ↕ WebSocket                 - 幕僚版儀表板
IP: 192.168.100.30
```

### 8.2　資料所有權

| 資料類型 | 所有權 | 儲存位置 |
|----------|--------|----------|
| 完整醫療人員名單 | 醫療組 Pi | 醫療組 Pi SQLite（LUKS 加密） |
| 完整人員名單（同步後） | 指揮部 | 指揮部 Pi SQLite（LUKS 加密） |
| QR 快照 aggregate | 指揮部 | 指揮部 Pi SQLite |
| 稽核日誌 | 各層 | 各機器，不可刪除 |

斷網期間：指揮部僅取得 QR 快照（aggregate），不含個人識別資料。有網路時：完整資料同步至指揮部，供計劃情報組作業。

### 8.3　網路情境

| 情境 | 說明 | 通訊加密 | 醫療組 Pi 備注 |
|------|------|----------|---------------|
| 1A：有公網，手機連同一 WiFi | 手機與 Pi 在同一 LAN | HTTPS + WSS（mkcert） | 標準情境，WSS :8775 |
| 1B：有公網，手機用行動網路 | WireGuard VPN 穿透 | WireGuard + HTTPS + WSS | 手機視為同一虛擬 LAN |
| 2：無公網，自建 WiFi | AP Bridge Mode 組網 | HTTPS + WSS（mkcert） | 距離遠時可退化至情境 3 |
| 3：單機作業（離線） | 各組獨立，無跨組連線 | 不需跨組加密 | QR code 快照為指揮部唯一資訊通道 |

> *※ 情境 3 離線作業時，醫療組應每 20 分鐘產生 QR-MEDICAL 快照供指揮部幕僚掃描（預設間隔；不得超過指揮部設定值）。*

### 8.4　靜態 IP 規劃（醫療組相關）

| 節點 | IP | 服務 |
|------|----|------|
| 指揮部 Pi 500 | 192.168.100.10 | FastAPI :8000（ICS_DMAS；民防感知 Console 走 :8001）、WebSocket Console |
| 收容組 Pi | 192.168.100.20 | WebSocket :8765、Admin :8766 |
| 醫療組 Pi ★ | 192.168.100.30 | WebSocket :8775、Admin :8776 |
| 前進組 Field Node | 192.168.100.40 | 心跳 + 上傳 |
| 安全組 Field Node | 192.168.100.50 | 心跳 + 上傳 |
| DHCP 範圍（手機等） | 192.168.100.100–200 | 動態分配 |

> 演訓前須在 AP 的 DHCP 設定中排除 .10–.99 段。

### 8.5　前端技術選型

| 層面 | 技術選擇 | 理由 |
|------|----------|------|
| 前端 | 單檔 HTML + CSS + JS（PWA） | 延續收容組單檔部署優勢，現地發放容易 |
| 資料庫 | IndexedDB（Dexie） | 本地持久化、可離線、可查詢 |
| 同步 | BroadcastChannel + Peer Delta；有本地 Wi-Fi 時可加 WebSocket 中繼 | 與收容組架構相容，支援單機與多機 |
| 快取 | Service Worker | 離線優先與版本控制 |
| 匯出 | CSV / JSON + 強制加密 | 方便檢討與備援 |
| 部署 | 手機/平板瀏覽器加入主畫面 | 不需 App Store / Play Store 上架 |

### 8.6　初版資料表建議

建議資料表：patients、triages、slots、transfers、resources、incidents、shifts、snapshots、config。命名與同步格式應盡量比照收容組，方便共用工具函式與 WS 中繼。

**snapshots 表必要欄位（與收容組 v2.3 對齊）：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID v4 | 本地自動生成，本地主鍵 |
| snapshot_uuid | UUID v4 | PWA 端生成的快照 UUID；作為 QR-MEDICAL payload 的 `snapshot_id` 及三 Pass 對齊主鍵；與指揮部 SNAPSHOT.id 不同，此欄由來源節點產生 |
| snapshot_time | DateTime (UTC) | 快照時間戳 |
| type | Enum | `auto` / `qr` / `manual` / `sync_recovery` / `merged` |

> *※ snapshot_uuid 必須在 QR 產生時寫入；指揮部以此欄位進行三 Pass 去重合併。*

---

## 9　部署設定（★ v0.2 新增）

本節依 security_network_spec_v1_2 §6 整合，說明醫療組 Pi 服務啟動時的 TLS 設定方式。

### 9.1　憑證管理 SOP（演訓前執行）

**步驟 1：管理員 Mac 安裝 mkcert**

```bash
brew install mkcert
mkcert -install
```

**步驟 2：為醫療組 Pi IP 簽發憑證**

```bash
mkcert 192.168.100.30  # 醫療組 Pi
```

**步驟 3：將 CA 根憑證安裝至所有醫療組手機/平板**

```
iOS：AirDrop rootCA.pem → 設定 → 信任憑證
Android：設定 → 安全性 → 安裝憑證
```

**步驟 4：將憑證部署至醫療組 Pi**

```bash
scp 192.168.100.30+1.pem pi@192.168.100.30:~/certs/
scp 192.168.100.30+1-key.pem pi@192.168.100.30:~/certs/
```

**步驟 5：** 啟動服務時載入憑證（見 §9.2）

**步驟 6：** 全裝置連線測試

> 注意：憑證有效期預設 825 天，演訓前檢查是否過期。

### 9.2　醫療組 Pi 服務啟動設定（Node.js WebSocket）

medical_ws_server.js 沿用 shelter_ws_server.js 架構，TLS 透過環境變數載入，無需修改程式碼：

```bash
CERT_PATH=/path/to/192.168.100.30+1.pem \
KEY_PATH=/path/to/192.168.100.30+1-key.pem \
WS_PORT=8775 \
ADMIN_PORT=8776 \
node medical_ws_server.js
```

未設定 `CERT_PATH`/`KEY_PATH` 時自動退回 HTTP/WS（開發用）。

服務端點：
```
WSS：   wss://192.168.100.30:8775
Admin： https://192.168.100.30:8776
```

前端 Pi URL 由使用者在設定頁輸入並存入 localStorage，支援 `wss://` 與 `ws://`。

### 9.3　LUKS Data 分區設定（Pi 正式部署）

開發階段（Mac）使用 FileVault 全磁碟加密即可，LUKS 設定僅在 Pi 正式部署時執行。

- 設定 /data 分區 LUKS 加密，passphrase 演訓前設定。
- 任務結束後執行 `cryptsetup luksErase` 銷毀資料。
- Panic 按鈕需有防誤觸保護蓋。

---

## 10　實作路線圖

| 規格版本 | 範圍 | 成果 | 對應程式里程碑 |
|----------|------|------|----------------|
| v0.1 | 規格定稿 | 確認資料模型、角色、頁面、警示門檻與欄位命名 | 規格先行 |
| v0.2 ★ | 安全架構整合 | 整合安全網路規格 v1.2：LUKS、mkcert、WireGuard、硬體清單、網路情境、服務部署設定 | 規格先行 |
| v0.3 | 前端骨架 | PWA、IndexedDB、角色頁、接收/檢傷、治療區看板 | ✅ 已完成 |
| v0.4 ★ | SOP 對齊補強 | §2.3 補入 XABCDE/SAMPLE/OPQRST 欄位；§3.1 補入機動人員角色；§6.2 補入輪替提醒 | ✅ 已完成 |
| v0.5 ★ | 作戰核心 + 結構化 | 結構化就醫紀錄表、延長照護紀錄、後送流程強化（27 醫院清單）、物資管理對齊 shelter、Bug fix 8 項、PersonCrypto 跨帳號 | ✅ medical-v0.8.3-alpha |
| v0.5 | 同步與資安 | PIN 鎖、匯出加密、Peer Delta / WebSocket、PersonCrypto deriveKey(salt,salt) | ✅ 已完成 |
| v1.0 | 演訓可用版 | 離線穩定、列印交班摘要、資料凍結、缺陷修正、Pi 部署驗證 | 待定 |

---

## 11　待確認議題

| 項目 | 狀態 | 說明 |
|------|------|------|
| N100 Mini PC 角色 | 待定 | 已改用 Pi 500 為主要硬體；N100 保留，AI 推論硬體評估中 |
| Anker 行動電源 | 待決定 | 總部深圳，依組織安全政策決定 |
| 指揮官版儀表板 | ✅ 初版完成 | `commander_dashboard.html`，待端對端測試 |
| YubiKey 雙人原則實作 | Phase 3 | 依民防感知系統規格 §4.3 |
| Field Node 與 ICS_DMAS 整合 | Phase 3 | STT 輸出寫入 EVENT 表 |
| 是否與收容組共用 display_id | 待確認 | 或透過手環編碼串接？ |
| 非創患者欄位 | ✅ 已實作 | SAMPLE/OPQRST + 16 項非創狀態 checkbox（v0.8.0-alpha） |
| 黑區患者撤退記錄格式 | 待確認 | 是否需額外定位欄位？ |
| 藥品管理範圍 | 待確認 | 只做數量追蹤，或納入發放對象與時間？ |
| 前進組 MIST 接收 | ✅ 已決定 | 整合於接收/檢傷頁（來源 A 快捷入口），顯示 M/I/S/T 四欄位；不設獨立頁面 |
| D-Link AP 個案評估 | 待確認 | 台灣公司但在中國有大量製造，需逐項核查 |

---

## 附錄 A　SOP 對應矩陣（摘要）

| SOP 條目 | 系統需求 |
|----------|----------|
| 單一入口 / 單向動線 | 接收頁固定入口流程，不允許跳過安檢狀態 |
| START 檢傷 + 創傷/非創分流 | Triage 模組 + injury_type 欄位 |
| 紅/黃/綠/黑區與後送區 | Treatment Slot / Zone Map |
| 危急可先送醫療區但安檢不得省略 | security_cleared 支援「同步處理中」狀態 |
| 每 30 分鐘量能回報 | 儀表板 + 通報文字產生器 |
| 每 30 分鐘物資盤點 | Resource 盤點提醒 |
| 每 2 小時輪替、超過 4 小時交班 | Shift / Snapshot + 交班頁 |
| 危急每 5 分鐘、非危急每 15 分鐘再評估 | 自動倒數與逾時警示 |
| ISBAR 後送交接 | Transfer 模組 + 交接摘要 |
| 安全威脅與撤退流程 | Incident + Evacuation Mode |

---

## 附錄 B　初版物資模板（建議）

| 類別 | 建議物資 | 低量門檻示例 |
|------|----------|-------------|
| 止血類 | 止血帶、止血敷料、壓力繃帶、紗布 | 依演訓數量設定；至少保留紅區 1 輪使用量 |
| 呼吸道類 | OPA/NPA、BVM、氧氣瓶、面罩 | 氧氣瓶 ≤ 1 時警示 |
| 循環類 | IV/IO、輸液、加壓袋 | 低於 20% 警示 |
| 監測/診斷 | AED、血壓計、血氧機、血糖機 | 設備故障即建 Incident |
| 固定/保暖 | 頸圈、三角巾、護木、保暖毯 | 低於 20% 警示 |
| PPE | 手套、口罩、護目鏡、隔離衣 | 任一關鍵品項不足 1 班量即警示 |
| 紀錄 | 檢傷卡、救護紀錄表、筆 | 低於 10 份警示 |

---

## 附錄 C　建議下一步

本文件完成後，建議直接進入兩個產出：

- 醫療組 PWA 的 ERD / 資料表草圖。
- 醫療組 PWA 的畫面線框（儀表板、檢傷頁、治療區看板、後送頁）。
- （★ v0.2 新增）演訓前 mkcert 憑證部署 SOP 演練（見 §9.1）。
- （★ v0.2 新增）確認 N100 Mini PC 角色（已改用 Pi 500 為主要硬體）及 Anker 行動電源安全政策（見 §11）。

---

## 附錄 D　安全硬體清單（★ v0.2 新增，源自安全架構規格 v1.2 §2.2）

### 主機與運算

| 硬體 | 建議品牌/型號 | 狀態 |
|------|-------------|------|
| Raspberry Pi 500（指揮部、各組 Pi） | 英國 Raspberry Pi Foundation | ✅ |
| N100 Mini PC | 保留，角色待定（AI 推論硬體評估中） | — |
| Raspberry Pi Zero 2W（Field Node） | 英國 Raspberry Pi Foundation | ✅ |
| 官方 Raspberry Pi 電源供應器 | 原廠配件 | ✅ |

### 儲存

| 硬體 | 品牌 | 狀態 |
|------|------|------|
| SD 卡 | Samsung PRO Endurance（韓國）、SanDisk（美國） | ✅ |
| SD 卡 | Lexar | ❌ 2017 年被中國龍存科技收購 |

### WiFi AP（情境 2 自建網路）

| 品牌 | 狀態 | 備注 |
|------|------|------|
| ASUS、Netgear、Mikrotik | ✅ | |
| TP-Link | ❌ | 禁止 |
| GL.iNet | ❌ | 禁止 |
| D-Link | ⚠️ | 台灣公司，但在中國有大量製造，需個案評估 |

### 手機 / 平板

| 品牌 | 狀態 |
|------|------|
| Apple iPhone / iPad、Samsung Galaxy、Google Pixel | ✅ |
| Huawei、Xiaomi、OPPO、Vivo | ❌ 禁止 |

### 電源

| 品牌 | 狀態 | 備注 |
|------|------|------|
| Mophie Powerstation、Goal Zero | ✅ | |
| Anker | ⚠️ | 總部深圳，依組織安全政策個案決定（見 §11） |

### 安全金鑰

| 硬體 | 品牌 | 狀態 |
|------|------|------|
| 安全金鑰 | YubiKey（Yubico，瑞典） | ✅ |

---

*文件版本：v0.5 | 對應程式版本：v0.8.3-alpha | 整合來源：醫療組SOP_20260323.md、shelter_pwa_spec.md、security_network_spec_v1.2.md*

## 附錄 D：待辦項目（截至 v0.6.3-alpha）

醫療組傷患來源分三種：

| 來源代碼 | 說明 | 資料狀況 |
|----------|------|----------|
| A | 前進組送入 | 有 MIST（QR 掃描或手動輸入） |
| B | 收容組轉介 | 已有登記資料 |
| C | 非前進組送入 | 可能有（自行走入）或完全沒有（他人抬入）資料 |

| 優先 | 項目 | 說明 |
|------|------|------|
| ⏸ | P0-3 簡化登入 | 帳號快選晶片，保留完整 PIN 驗證不動，方案確認中 |
| 🔴 | P3 紅區容量 | `getRedSlotsFree()` 永遠回傳 999；從 config 讀 `red_capacity`，預設 5，管理員可調整 |
| 🟡 | P4 生命徵象分開 | 現場 MIST-S vs 到院 START 數值混用；DB 加 `arrival_vitals` 欄位分開顯示 |
| 🟡 | Badge 定義 | 分區 tab badge 建議改為「待評估 + 逾時合計」，待決定 |
| 🟢 | P5 Pi URL config | IP hardcode `192.168.100.30`，改為 admin 介面設定，換場地不需改程式碼 |
| 🟢 | P6 WS 多裝置同步 | `handleWsMsg()` 目前空函式，最小實作：收 `patient_updated` 後 `loadPatients()` 再重繪 |
| 🟢 | P7 腕帶 QR | 演習不需要（display_id 手寫），熱感應印表機到位後再做 |
| 🟢 | P8 全域掃碼 | 同 P7，演習後 |
| 🟢 | P9 語音建檔 | Pi 5 離線辨識（faster-whisper），P3–P6 完成後再做 |
