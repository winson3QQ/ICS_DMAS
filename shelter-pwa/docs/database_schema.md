# 收容組資料庫 Schema 文件

版本：v2.2.39 · 2026-04 · 對應 server v0.3.0

本文件描述收容組系統的兩層資料庫架構，供 server 設計使用。

---

## 架構概覽

```
┌─────────────────────┐     ┌──────────────────────┐
│   PWA (IndexedDB)   │     │   Pi Server (SQLite)  │
│   Dexie.js v3       │ ←→  │   better-sqlite3      │
│                     │ WSS │                        │
│  persons (加密)      │     │  accounts              │
│  beds               │     │  config                │
│  resources          │     │  audit_log             │
│  incidents          │     │  delta_log             │
│  snapshots          │     │  snapshots             │
│  shifts             │     │  login_failures        │
│  inquiries          │     │                        │
│  config             │     └───────┬────────────────┘
│  audit_log          │             │ 三 Pass
│  time_sync          │             ↓
└─────────────────────┘     ┌──────────────────────┐
                            │  指揮部 (SQLite)       │
                            │  FastAPI + SQLAlchemy  │
                            └──────────────────────┘
```

---

## A. PWA 端（IndexedDB / Dexie.js）

### A1. persons — 收容人員

**Dexie 索引**：`++_id, display_id, status, bed_id, family_unit_id, intake_at, exit_at, updated_at, srt_color`

**加密欄位**（AES-256-GCM，存在 `_enc` blob）：
`name, gender, age_group, health_flag, cmist, immediate_needs_note, notes, id_card_items, id_card_note, medication, audit_flags`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `_id` | auto | Dexie 自動遞增 |
| `display_id` | string \| null | 識別碼，格式 S001-MA |
| `name` | string | 姓名（加密） |
| `type` | string | 災民 \| 志工 \| 工作人員 |
| `gender` | string | 男 \| 女（加密） |
| `age_group` | string | 0-4 \| 5-19 \| 20-34 \| 35-49 \| 50-64 \| 65+ （加密） |
| `status` | string | 等候中 \| 登記中 \| 已安置 \| 已離站 \| 已隔離 |
| `health_flag` | string | 正常 \| 需關注 \| 已隔離（加密） |
| `san_gate_done` | boolean | 清消關卡是否通過 |
| `immediate_needs_noted` | boolean | 即時需求是否已詢問 |
| `immediate_needs_note` | string | 即時需求描述（加密） |
| `cmist` | object | CMIST 五維特殊需求（加密） |
| `cmist_assessed` | boolean | CMIST 是否已評估 |
| `family_unit_id` | string \| null | 家庭群組 ID（FAM-xxx） |
| `is_family_head` | boolean | 是否為家長 |
| `household_size` | number | 家庭人數 |
| `pets` | object | 寵物資訊 |
| `bed_id` | string \| null | 分配的床位 display_id |
| `id_card_collected` | boolean \| null | 管制物品是否收繳 |
| `id_card_items` | string[] | 收繳物品清單（加密） |
| `id_card_note` | string | 收繳備註（加密） |
| `id_badge_issued` | boolean | 識別證是否已發放 |
| `consent_ops` | boolean \| null | B軌（日常運作）同意 |
| `consent_welfare` | boolean \| null | A軌（撫恤憑證）同意 |
| `covenant_signed` | boolean | 收容公約是否已簽署 |
| `paper_form_destroyed` | boolean \| null | 紙本是否已銷毀 |
| `intake_at` | ISO datetime | 入站時間 |
| `exit_at` | ISO datetime \| null | 離站時間 |
| `exit_reason` | string \| null | 離站原因 |
| `registering_started_at` | ISO datetime \| null | 開始登記時間 |
| `srt_score` | number \| null | SRT 脆弱性評分（0-15） |
| `srt_color` | string \| null | SRT 分色 Green \| Yellow \| Red \| Purple |
| `skills` | string[] | 專業技能 |
| `notes` | string | 備註（加密），分號分隔 |
| `intake_log` | object[] | 入站流程紀錄 `[{step, by, at}]` |
| `created_by` | string | 建立者（AuditManager） |
| `operator_name` | string | 最後操作者 |
| `updated_at` | ISO datetime | 最後更新時間 |

**CMIST 結構**：
```json
{
  "communication": ["需翻譯", "手語"],
  "maintaining_health": ["每日用藥"],
  "independence": ["輪椅"],
  "services_support": [],
  "transportation": ["需醫療轉送"]
}
```

**pets 結構**：
```json
{
  "has_pets": true,
  "counts": {"dog": 1, "cat": 0, "small": 0, "bird": 0, "reptile": 0, "other": 0},
  "placement": "同區安置",
  "placement_note": ""
}
```

---

### A2. beds — 床位

**Dexie 索引**：`++_id, display_id, zone, status, assigned_to`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `_id` | auto | |
| `display_id` | string | 床位編號（M01, F02, A03, C01, P01） |
| `zone` | string | male \| female \| family \| care \| pet |
| `status` | string | empty \| occupied \| suspended |
| `assigned_to` | string \| null | 佔用者的 display_id |

**床位編號前綴**：M(男) F(女) A(家庭) C(照護) P(寵物)

**預設容量**：男8 女8 家庭8 照護4 寵物2 = 共30

---

### A3. incidents — 事件

**Dexie 索引**：`++_id, type, status, severity, opened_at`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `_id` | auto | |
| `type` | string | 事件類型 key |
| `severity` | string | 普通 \| 緊急 |
| `status` | string | 已通報 \| 待處理 \| 處理中 \| 已結案 |
| `opened_at` | ISO datetime | 通報時間 |
| `closed_at` | ISO datetime \| null | 結案時間 |
| `linked_persons` | string[] | 涉及人員 display_id 陣列 |
| `reported_by` | string | 通報者 |
| `assigned_to` | string | 負責人 |
| `notes` | object[] | 處置紀錄 `[{time, text, by}]` |
| `source` | string \| undefined | 來源（cmist_auto = CMIST 自動派遣） |

**事件類型**：

| Key | 標籤 | 預設嚴重度 |
|-----|------|-----------|
| medical_infection | 醫療/傳染病緊急事件 | 緊急 |
| capacity_overload | 收容能量超載 | 普通 |
| noise_disturbance | 災民喧嘩 | 普通 |
| power_outage | 停電 | 普通 |
| air_raid | 空襲或飛彈攻擊 | 緊急 |
| security_threat | 攻擊或治安威脅 | 緊急 |
| id_mismatch | 身分核對不符 | 普通 |
| dangerous_resident | 危險收容者 | 普通 |
| resource_shortage | 物資缺漏 | 普通 |
| suspicious_person | 發現可疑人士 | 普通 |
| facility_damage | 場地/設備損壞 | 普通 |
| volunteer_conflict | 志工衝突升級 | 普通 |
| rumor_spread | 謠言蔓延 | 普通 |
| resident_distress | 災民情緒激動 | 普通 |
| pet_placement | 寵物外送安置 | 普通 |
| immediate_needs | 即時需求 | 普通 |
| medical_transfer | 需醫療轉介/轉送 | 緊急 |
| non_medical_transport | 需非醫療接駁 | 普通 |
| language_assist | 語言協助 | 普通 |
| medication_mgmt | 藥品管理 | 普通 |
| accessible_bed | 無障礙床位分配 | 普通 |
| charging_arrange | 電動輔具充電安排 | 普通 |
| other | 其他 | 普通 |

---

### A4. resources — 物資

**Dexie 索引**：`++_id, name, category`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `_id` | auto | |
| `name` | string | 物資名稱 |
| `category` | string | 分類 |
| `qty_current` | number | 目前數量 |
| `qty_low_threshold` | number | 低量警戒線 |
| `unit` | string | 單位 |
| `transactions` | object[] | 交易紀錄 `[{time, type, qty, reason, by}]` |

---

### A5. snapshots — 快照

**Dexie 索引**：`++_id, timestamp, snapshot_uuid`

用於 QR-SHELTER 通報和三 Pass 對齊。

---

### A6. shifts — 交班紀錄

**Dexie 索引**：`++_id, started_at`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `started_at` | ISO datetime | 交班時間 |
| `ended_at` | ISO datetime \| null | |
| `role` | string | 交班人員 |
| `operator_name` | string | 操作者 |
| `handover_notes` | string | 交班備註 |
| `snapshot` | object | 交班時的狀態摘要 |

---

### A7. audit_log — 稽核日誌

**Dexie 索引**：`++_id, action, operator_name, timestamp`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `action` | string | 操作類型 |
| `operator_name` | string | 操作者 |
| `device_id` | string | 裝置 ID |
| `session_id` | string | 會話 ID |
| `timestamp` | ISO datetime | 時間戳 |
| `detail` | string (JSON) | 詳細資訊 |

---

## B. Pi Server 端（SQLite）

### B1. config

| 欄位 | 型別 | 說明 |
|------|------|------|
| `key` | TEXT PK | 設定鍵 |
| `value` | TEXT | 設定值 |

**重要 key**：
- `admin_pin_hash` / `admin_pin_salt` — 管理員 PIN
- `site_salt` — 全站加密 salt（唯一，跨裝置共用）
- `last_sync_to_command` — 上次同步至指揮部的時間戳

### B2. accounts

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT PK | UUID |
| `username` | TEXT UNIQUE | 帳號名稱 |
| `role` | TEXT | 組長 \| 一般 |
| `pin_hash` | TEXT | PBKDF2 雜湊 |
| `pin_salt` | TEXT | Salt |
| `status` | TEXT | active \| suspended |
| `created_at` | TEXT | 建立時間 |
| `created_by` | TEXT | 建立者 |
| `last_login` | TEXT | 最後登入時間 |
| `device_id` | TEXT | 最後登入裝置 |

### B3. audit_log

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT PK | UUID |
| `action` | TEXT | 操作類型 |
| `operator_name` | TEXT | 操作者 |
| `device_id` | TEXT | |
| `session_id` | TEXT | |
| `timestamp` | TEXT | ISO datetime |
| `detail` | TEXT | JSON |

### B4. delta_log

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | INTEGER PK AUTO | |
| `src` | TEXT | 來源裝置 |
| `table_name` | TEXT | 異動的表名 |
| `record_id` | TEXT | 紀錄 ID |
| `record_json` | TEXT | 完整紀錄 JSON |
| `ts` | TEXT | 異動時間 |
| `recv_at` | TEXT | 收到時間 |

### B5. snapshots

| 欄位 | 型別 | 說明 |
|------|------|------|
| `snapshot_uuid` | TEXT PK | UUID v4 |
| `unit_id` | TEXT | 來源單位（shelter） |
| `source` | TEXT | pi_push \| qr \| auto |
| `payload_json` | TEXT | 快照完整 JSON |
| `recv_at` | TEXT | 收到時間 |
| `merged` | INTEGER | 是否已合併（0/1） |

### B6. login_failures

| 欄位 | 型別 | 說明 |
|------|------|------|
| `username` | TEXT | 帳號 |
| `failed_at` | TEXT | 失敗時間 |

索引：`idx_login_failures_username ON login_failures(username)`

---

## C. 資料流關聯

### C1. 人員 ↔ 床位

```
persons.bed_id ──→ beds.display_id
beds.assigned_to ──→ persons.display_id
```

一對一關係。分配床位時雙向更新。

### C2. 人員 ↔ 事件

```
incidents.linked_persons[] ──→ persons.display_id
```

多對多關係。一個事件可涉及多人，一個人可有多個關聯事件。

### C3. 人員 ↔ 家庭

```
persons.family_unit_id ──→ 相同 family_unit_id 的所有 persons
persons.is_family_head = true（一個家庭只有一個）
```

### C4. PWA ↔ Pi Server

```
PWA (IndexedDB) ←──WSS delta──→ Pi (SQLite delta_log)
                                      │
                                      ↓ 三 Pass
                              指揮部 (SQLite)
```

- **delta_log**：PWA 每次寫入後透過 WSS 推送 delta 至 Pi
- **snapshots**：Pi 定時產生快照推至指揮部
- **三 Pass**：網路恢復後完整同步

### C5. 加密層

```
PWA 寫入 → PersonCrypto.encryptPerson() → IndexedDB（_enc blob）
PWA 讀取 → PersonCrypto.decryptPerson() → 明文物件

金鑰 = PBKDF2(PIN, site_salt, 200000 iterations) → AES-GCM-256
site_salt = Pi 啟動時產生一次，永久不變，所有裝置共用
```

---

## D. 入站流程狀態機

```
建立人員 → 等候中
    ↓ 清消確認（+ 自動產生 display_id）
登記中
    ↓ 同意簽署（B軌拒絕→已離站）
    ↓ 登記（物品+識別證+寵物）
    ↓ 需求評估（即時需求+CMIST）
    ↓ 床位分配
已安置
    ↓ 離站
已離站
```

離站時：釋放床位、自動結案關聯事件。
