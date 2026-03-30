# 🏠 收容組 PWA 收容管理系統

## 系統需求與規格書

**v2.3 · 2026-03**

---

## 版本與標記說明

| 項目 | 內容 |
|------|------|
| **文件版本** | v2.3（整合 v2.2 + 程式 v0.1.0 新增功能） |
| **對應程式版本** | v0.1.0 |
| **編制日期** | 2026-03 |
| **適用範圍** | 鄉鎮層防災演訓及實際災害收容作業（多裝置協作 + 安全網路版） |
| **機密層級** | C（僅供收容組內部使用） |
| **維護單位** | 收容組／人管隊 |
| **程式輸出** | shelter_pwa.html + sw.js + shelter_ws_server.js + admin.html |
| **上游文件** | shelter_pwa_spec_v2_2.md、security_network_spec_v1.2.md、民防輔助感知系統規格 v1.3 |

### 標記說明

| 標記 | 來源說明 |
|------|----------|
| **【SOP更新】** | 來源：收容組 SOP 更新 / 會議決議 |
| **【開發決策】** | 來源：開發過程決策 / 現場測試回饋 |
| **【待確認】** | 來源：會議紀錄待確認，尚未完全實作 |
| **【v2.2新增】** | 來源：security_network_spec_v1_0.md 整合 |

---

## 0　文件目的與背景

本規格書描述「收容組 PWA 收容管理系統（以下簡稱本系統）」的完整需求，供開發者據以實作，並作為換 chat room 或換手後的銜接文件。

本系統是現行 SOP 查詢程式（shelter_sop_mobile.html）的後繼演進，方向從「程序導向（步驟勾選）」轉變為「狀態導向（實體追蹤）」，使指揮者能即時掌握「誰在哪、床位還剩多少、物資狀況如何」。

### 0.1　設計哲學

- **離線優先（Offline-First）**：完全離線可用，網路恢復後自動同步，不假設網路穩定
- **實體導向（Entity-Centric）**：Person、Bed、Resource 是核心，SOP 是附掛在實體上的作業指引
- **最低操作門檻**：無培訓者在高壓情境下 10 分鐘內完成第一筆入站登記
- **降級完備（Graceful Degradation）**：停電後能印出完整紙本，電力恢復後從紙本補登
- **最小可行版本優先**：先做「能用」再做「功能完整」

### 0.2　與指揮部儀表板的關係

收容組 PWA 為資料產出方，指揮部儀表板（ICS_DMAS）為彙整方。兩者透過以下管道銜接：

| 管道 | 說明 |
|------|------|
| 有網路時（L2） | 各組 Pi → WebSocket → 指揮部 FastAPI，完整記錄自動同步 |
| 斷網時（L0） | 組長產生 QR-SHELTER（§9），截圖/印出交指揮部人員掃描，維持態勢感知 |
| 網路恢復後（§10） | Pi 自動推送斷線期間記錄，指揮部執行三 Pass 對齊 |

---

## 1　系統範圍與設計假設

### 1.1　v2.x 範圍內

- 單一收容所的人員入站流程數位化（個人入站 + 家庭入站）
- 床位分配與即時容量顯示（取代手寫白板）
- 容量燈號自動計算（綠/黃/紅）
- 物資開場盤點與取用追蹤
- 基本事件紀錄（含時間戳、負責人、處置備註）
- 所有資料可匯出為 CSV 和 JSON（離線備份、事後檢討）
- 完整離線運作（PWA，可安裝至 iOS / Android 主畫面）
- 角色視角切換（4 個功能角色）
- 家庭入站：一次建立多位成員，一鍵全家清消、套用公約與同意
- Pi WebSocket 跨裝置自動即時同步（同一 Wi-Fi 下）
- IndexedDB PBKDF2 衍生金鑰加密（persons 表 + 自動快照）
- SRT 脆弱性評分介面（手動輸入，公式待醫療組協議）
- CMIST 特殊需求自動分派
- 三層分級銷毀 UI

### 1.2　設計假設

| 假設項目 | 假設內容 | 若假設不成立的降級方案 |
|----------|----------|------------------------|
| 操作設備 | 操作者有 Android 或 iOS 手機或平板 | 改用電腦瀏覽器，功能相同 |
| 網路情境 | 依 §7 三種情境之一 | 降至情境 3（單機），QR 快照維持指揮部態勢感知 |
| 傳輸加密 | 部署 mkcert 憑證，HTTPS/WSS | 情境 3 無跨裝置通訊，單機 HTTP 可接受 |
| 電力 | 大部分時間有電，短暫停電用電池 | 印出床位表紙本，電力恢復後補登 |
| 操作者 | 志工，無 IT 背景，高壓下操作 | 所有功能 3 步以內完成 |
| 收容規模 | 單所最多 50 人，5 種寢區類別 | 可在設定中調整 |

---

## 2　核心資料模型（摘要）

詳細欄位定義延續 v2.1 規格（shelter_pwa_spec_v2_1.docx §2）。本節僅列 v2.2 新增或修改的要點。

### 2.1　snapshots 表——v2.2 DB schema version 3

> **【v2.2新增】** DB schema 升至 version 3：snapshots 表新增 snapshot_uuid（UUID v4）欄位，舊資料於升級時自動補值。指揮部規格 §13.2 要求 snapshot_id 為 UUID v4；此欄為 QR-SHELTER payload 的 snapshot_id，也是三 Pass 對齊的主鍵。

| 欄位 | 類型 | 說明 |
|------|------|------|
| **_id** | Number | IndexedDB 自增主鍵 |
| **timestamp** | DateTime | 快照產生時間（UTC） |
| **snapshot_uuid** | UUID v4 | 【v2.2新增】QR payload 及三 Pass 對齊主鍵 |
| **source** | String | auto / qr / sync_recovery |
| **summary** | Object | 狀態摘要（去識別化） |
| **_enc_blob** | String | 加密個資快照（有金鑰時） |

---

## 3　功能需求（摘要）

§3.1–§3.12 延續 v2.1 規格。以下僅列 v2.2 新增或修改的條目。

### 3.1　角色與視角（v2.2 更新）

| 角色 | 主要功能 | v2.2 高權限操作 |
|------|----------|-----------------|
| 組長 ★YubiKey | 儀表板、容量燈號、事件通覽、名冊、匯出、設定、帳號管理 | 全站快照匯出、場復銷毀、帳號建立/停用、QR 通報產生 |
| 人管 | 入站流程、床位分配、服務窗口、事件 | — |
| 物管 | 物資盤點、取用記錄、缺料通報、事件 | — |
| 環管 | 床位地圖、帶位、事件 | — |

### 3.2　QR-SHELTER 斷網快照通報（§9，v2.1 完整實作）

> **【v2.2新增】** 已在 shelter_pwa_v2.1.html 實作。

**設計原則：**

- **最小必要**：只包含指揮官計算引擎所需的欄位，不含個人姓名
- **一次一個快照**：每次產生代表當下整體狀態的 QR，不是每個事件一個
- **snapshot_uuid 必填**：產生 QR 時同步建立本機 snapshots 表一筆記錄
- **無個資**：payload 不含姓名、ID 號碼、健康細節等個人識別資料

**QR-SHELTER JSON 格式（§9.2，對接指揮部規格 §13.3）：**

```json
{
  "v": 1,
  "type": "snapshot_shelter",
  "snapshot_id": "<UUID v4>",
  "t": "2026-04-11T14:30:00Z",
  "src": "shelter_pwa_v2",
  "bed_used": 42,
  "bed_total": 80,
  "srt": { "red": 3, "yellow": 6, "green": 27 },
  "pending_intake": 3,
  "cmist_pending": 5,
  "staff_on_duty": 8
}
```

**欄位計算規則：**

| 欄位 | 收容組計算規則 | 備註 |
|------|---------------|------|
| **bed_used** | db.beds.count(status = "occupied") | — |
| **bed_total** | db.beds.count(status ≠ "suspended") | — |
| **srt.red** | srt_color = Red 或 Purple 的在場人數之和 | Purple 合入 red（高風險） |
| **srt.green** | srt_color = Green + 未評分（null）的在場人數 | 未評分保守估計為 Green |
| **pending_intake** | db.persons.count(status = "等候中") | — |
| **cmist_pending** | CMIST 自動分派事件未結案數 | — |
| **staff_on_duty** | 組長手動輸入（產生前彈出輸入框） | Phase 3 考慮班表自動計算 |

**操作流程：**

- 設定頁 → 斷網通報 → 組長輸入當前值勤人數 → 產生 QR
- 預設頻率每 20 分鐘；緊急時可縮至 5 分鐘
- 全螢幕顯示，同時顯示 snapshot_uuid 後 8 碼供口頭確認
- QR 使用 qrcode-generator（MIT），Error Correction Level M，Version ≤ 10，payload < 500 bytes
- 稽核日誌寫入（action: qr_generated）

### 3.3　網路斷線與恢復同步機制（§10，v2.1 完整實作）

> **【v2.2新增】** 已在 shelter_pwa_v2.1.html 及 shelter_ws_server_v2.1.js 實作。

| 線 | 收容組做什麼 | 指揮部收到什麼 |
|----|-------------|---------------|
| 線一：定時 QR | 每 N 分鐘組長產生 QR-SHELTER | SNAPSHOT（最小必要），source=qr |
| 線二：完整記錄 | PWA 繼續在本機 IndexedDB 完整記錄每一筆操作 | （斷線期間無）網路恢復後自動補齊 |

**網路恢復後推送程序（§10.4，收容組 Pi 視角）：**

1. 讀取 config.last_sync_to_command（記為 t_last）
2. 從各 IndexedDB 表篩選 updated_at ≥ t_last 的記錄
3. 透過 WebSocket 推送至指揮部 Pi（訊息類型：sync_push）
4. 指揮部 Pi 回傳 sync_ack（含三 Pass 執行結果）
5. 收容組 Pi 收到 sync_ack 後，更新 config.last_sync_to_command = nowISO()

> **注意**：三 Pass 對齊邏輯由指揮部 Pi 執行，收容組不需要實作三 Pass。

---

## 4　同步架構

### 4.1　四層同步全貌（含 QR 備援通道）

> **【v2.2新增】** L1/L2 通訊加密：v2.2 起，Pi WebSocket 由 ws:// 改為 wss://，Admin HTTP 由 http:// 改為 https://（mkcert 本地 CA）。

| 層級 | 通道 | 範圍 | 自動 | 說明 |
|------|------|------|------|------|
| L0 | QR code 實體傳遞 | 收容組 → 指揮部（單向） | 手動 | 態勢快照，指揮部掃描後寫入 SNAPSHOT |
| L1 | BroadcastChannel | 同裝置、同瀏覽器分頁 | ✅ | Last-Write-Wins 合併（v1.3 延續） |
| L2 | Pi WebSocket（WSS） | 同 Wi-Fi 下所有裝置 | ✅ | 有 Pi 時自動即時同步；斷線後重連補傳 |
| L3 | Peer Delta AES-256-GCM | 不同裝置（無 Wi-Fi） | 手動 | AirDrop/藍牙傳輸，降級備援 |

---

## 5　非功能需求

### 5.1　效能

- 頁面初始載入（已安裝，離線）< 2 秒
- 任何操作回應 < 300 毫秒
- 本地資料庫支援單所 500 筆 Person 記錄

### 5.2　可用性

- 首次使用者（無培訓）10 分鐘內完成第一筆入站登記
- 所有必要操作不超過 3 次點擊
- 所有破壞性操作有確認提示 + 5 秒撤銷

### 5.3　可靠性

- 每次資料變更立即寫入 IndexedDB（不依賴記憶體狀態）
- 崩潰重啟後資料完整恢復
- 每 15 分鐘自動全站快照（滾動保留最近 48 份）

### 5.4　資安與隱私（v2.2 更新）

> **【v2.2新增】** 傳輸層加密（mkcert + HTTPS/WSS）已列為 Phase 2 必須項目，詳見 §7 安全與網路架構及 §8 實作路線圖。

| 防護層 | 方案 | 適用情境 |
|--------|------|----------|
| 應用層（個資欄位） | AES-256-GCM + PBKDF2（PIN 衍生） | 所有情境，v2.0 起 |
| 傳輸層（跨裝置通訊） | HTTPS + WSS（mkcert 本地 CA） | 情境 1A/1B/2，v2.2 起（Phase 2） |
| 傳輸層（公網） | WireGuard VPN | 情境 1B，v2.2 起（Phase 2） |
| 靜態加密（Pi 磁碟） | LUKS data 分區 | Pi 正式部署（Phase 2） |
| 靜態加密（Mini PC） | LUKS 全磁碟 + YubiKey | Phase 3 |
| PIN 鎖（本機補償） | 4-6 位 PIN，閒置 90 秒警告 + 30 秒倒數後自動登出 | 所有情境，v1.3 起；v0.1.0 縮短為 2 分鐘 |

- 所有資料儲存在本地設備，不傳送到任何雲端服務
- 匯出檔案加密：含個資欄位的所有匯出強制 AES-256-GCM 加密
- 特種個資識別：health_flag、cmist 欄位屬個資法 §6，套用最高保護等級
- YubiKey 組長高權限授權（選配）：含個資全站快照匯出、場復資料銷毀

---

## 6　技術規格

### 6.1　技術選擇

| 層面 | v2.1 | v2.2 更新 | 說明 |
|------|------|-----------|------|
| 框架 | 原生 HTML/CSS/JS | 不變 | 零依賴，離線可靠 |
| 本地資料庫 | IndexedDB via Dexie.js | DB version 3 | 新增 snapshot_uuid 索引 |
| QR 生成 | — | qrcode-generator（MIT，~57KB，內嵌） | 無外部 CDN 依賴，斷網可用 |
| Pi 通訊 | ws:// / http:// | wss:// / https://（mkcert） | Phase 2 啟用 TLS |
| Pi 磁碟加密 | — | LUKS data 分區 | Phase 2，不影響程式碼 |
| 色系 | 金色 #C07800 | 不變 | 延續現行 SOP 程式設計語言 |

### 6.2　shelter_ws_server TLS 支援（v0.1.0 已完成）

> **【v2.3更新】** shelter_ws_server.js 已支援 TLS，透過環境變數載入憑證，無需修改程式碼。未設定時自動退回 HTTP/WS（開發用）。

```bash
CERT_PATH=/path/to/cert.pem \
KEY_PATH=/path/to/key.pem \
node shelter_ws_server.js
```

前端 PWA 的 Pi URL 由使用者在設定頁輸入並存入 localStorage，支援 `wss://` 與 `ws://`。

### 6.3　靜態 IP 規劃（§7.3 補充）

| 節點 | IP | 服務 |
|------|----|------|
| 指揮部 Mini PC | **192.168.100.10** | FastAPI :8000、WebSocket Console |
| 收容組 Pi | **192.168.100.20** | WebSocket :8765（WSS）、Admin :8766（HTTPS） |
| 醫療組 Pi | **192.168.100.30** | WebSocket :8775（WSS）、Admin :8776（HTTPS） |
| 前進組 Field Node | **192.168.100.40** | 心跳 + 上傳 |
| 安全組 Field Node | **192.168.100.50** | 心跳 + 上傳 |
| DHCP 範圍（手機等） | **192.168.100.100–200** | 動態分配 |

> 演訓前須在 AP 的 DHCP 設定中排除 .10–.99 段，確保靜態 IP 不被覆蓋。

---

## 7　安全與網路架構

> **【v2.2新增】** 本節整合自 security_network_spec_v1_0.md v1.0。

### 7.1　系統整體架構

```
【前進組 / 安全組】
Field Node (Pi Zero 2W)
PTT 錄音 → 本機 Whisper STT → 上傳指揮部
                    ↓
【收容組 / 醫療組】              【指揮部 Console】
手機 PWA                         Mini PC (Intel N100)
   ↕ WebSocket (WSS)              - ICS_DMAS 指揮部儀表板
各組 Pi ─────────────────→        - 民防感知系統 Console
(Raspberry Pi 4B)                 - SQLite（LUKS 加密）
                                  - 幕僚版儀表板
                                  - 指揮官版儀表板（初版完成）
```

### 7.2　資料所有權

| 資料類型 | 所有權 | 儲存位置 |
|----------|--------|----------|
| 完整人員名單 | 各組 Pi | 各組 Pi SQLite（LUKS 加密） |
| 完整人員名單（同步後） | 指揮部 | Mini PC SQLite（LUKS 加密） |
| 快照 aggregate | 指揮部 | Mini PC SQLite |
| 語音記錄 | 指揮部 | Mini PC Data Cartridge（LUKS） |
| 稽核日誌 | 各層 | 各機器，不可刪除 |

> **設計原則**：斷網期間，指揮部僅取得 QR 快照（aggregate），不含個人識別資料。有網路時，各組完整資料同步至指揮部，供計劃情報組作業。指揮部 Console 為最高價值目標，LUKS 加密為強制要求。

### 7.3　三種網路情境定義

#### 情境 1A：有公網，手機連同一 WiFi（本地 LAN）

```
手機 ─── WiFi ───> 各組 Pi (192.168.100.x)
                        ↓
              指揮部 Mini PC (192.168.100.10)
```

- 通訊加密：HTTPS + WSS（mkcert 本地 CA）
- 手機驗證：預裝 mkcert CA 憑證（iOS: AirDrop rootCA.pem → 設定 → 信任憑證）

#### 情境 1B：有公網，手機使用行動網路

```
手機 ─── 行動網路 ─── WireGuard VPN ───> 指揮部 Mini PC
                                               ↓
                                         各組 Pi（同 LAN）
```

- 通訊加密：WireGuard（端對端）+ HTTPS + WSS
- 前提：Mini PC 有穩定公網 IP 或 DDNS（DuckDNS / No-IP）
- WireGuard 生效後，手機視為在同一虛擬 LAN，後續通訊與情境 1A 相同

#### 情境 2：無公網，自建 WiFi

```
手機 ─── 自建 WiFi AP（Bridge Mode）───> 各組 Pi
                                              ↓
                                        指揮部 Mini PC
```

- 所有 AP 必須設定為 Bridge Mode（同一子網）
- 通訊加密：HTTPS + WSS（mkcert）

#### 情境 3：單機作業（最低要求）

```
各組 Pi ─── 本地 ───> 本組手機
（無跨組網路連線）
```

- 各組獨立運作，不需要跨組加密
- 資料等網路恢復後，透過三 Pass 對齊同步至指揮部
- QR code 快照為此期間指揮部獲取資訊的唯一通道

### 7.4　傳輸安全（HTTPS/WSS — mkcert 本地 CA）

**方案選擇依據：**

- 作者 Filippo Valsorda（義大利裔美國人，前 Go 安全團隊），無中國關聯
- 開源、免費，適用所有三種情境的本地網路
- 不適用 Let's Encrypt：需要公開域名 + 網路驗證，情境 2、3 無法使用

**憑證管理 SOP（演訓前，Phase 2 執行）：**

```bash
# 步驟 1：管理員 Mac 安裝 mkcert
brew install mkcert && mkcert -install

# 步驟 2：為各節點 IP 簽發憑證
mkcert 192.168.100.10  # 指揮部
mkcert 192.168.100.20  # 收容組 Pi
mkcert 192.168.100.30  # 醫療組 Pi

# 步驟 3：將 CA 根憑證安裝至所有手機/平板
# iOS：AirDrop rootCA.pem → 設定 → 信任憑證
# Android：設定 → 安全性 → 安裝憑證

# 步驟 4：將憑證部署至各 Pi
scp 192.168.100.20+1.pem pi@192.168.100.20:~/certs/
scp 192.168.100.20+1-key.pem pi@192.168.100.20:~/certs/

# 步驟 5：全裝置連線測試
# 憑證有效期預設 825 天，演訓前須檢查是否過期。
```

### 7.5　靜態加密（LUKS）

**方案選擇依據：**

- OS 層磁碟加密，覆蓋所有資料（SQLite、log、設定檔、暫存檔）
- Linux kernel 內建，無額外供應鏈風險，不需修改任何應用程式碼
- 與民防輔助感知系統規格 §4.2 一致（cryptsetup luksErase）

| 節點 | 加密對象 | 金鑰管理 |
|------|----------|----------|
| 指揮部 Mini PC | OS 碟 + Data Cartridge | YubiKey（主）+ 備援密碼（雙人原則） |
| 各組 Pi | Data 分區（/data） | 演訓前設定 passphrase，任務結束後銷毀 |
| Field Node | MicroSD | Panic 長按 5 秒快速格式化 |

**Panic Wipe：**

- Field Node：長按實體按鈕 5 秒 → MicroSD 快速格式化（需有防誤觸保護蓋）

### 7.6　情境 1B 補充：WireGuard VPN

- Jason Donenfeld（美國）開發，已併入 Linux kernel 5.6，無中國關聯
- Mini PC 開 WireGuard server，監聽 UDP 51820
- 每台手機一組金鑰對，設定以 QR code 分發
- 若無固定公網 IP，使用 DuckDNS（社群維護）或 No-IP（美國）
- 路由器需開 UDP 51820 port forwarding

---

## 8　實作路線圖

### 8.1　v2.0 / v2.1（已完成）

| 功能 | 狀態 |
|------|------|
| Pi WebSocket 伺服器 + 任務帳號系統 | ✅ 完成 |
| 登入降級機制 + 失敗鎖定（SQLite 持久化） | ✅ 完成 |
| IndexedDB persons 表加密 + 自動快照加密 | ✅ 完成 |
| 稽核日誌表（audit_log，含 file_hash） | ✅ 完成 |
| SRT 評分 UI（手動）+ CMIST 自動分派 | ✅ 完成 |
| 三層分級銷毀 UI | ✅ 完成 |
| QR-SHELTER 生成介面（§9）——DB v3、qrcode-generator | ✅ v2.1 完成 |
| last_sync_to_command + 網路恢復推送（§10） | ✅ v2.1 完成 |
| snapshots 表補 snapshot_uuid（DB version 3） | ✅ v2.1 完成 |

### 8.1b　程式 v0.1.0 新增功能（規格 v2.3 補錄）

| 功能 | 狀態 | 說明 |
|------|------|------|
| Session restore | ✅ 完成 | 刷新頁面後透明還原身份，不需重新輸入 PIN |
| 自動登出倒數 + overlay | ✅ 完成 | 閒置 90 秒顯示警告，再 30 秒自動執行 switchRole() |
| Header 登入時間顯示 | ✅ 完成 | role-chip 顯示登入時間及閒置倒數 |
| iOS WebSocket 穩定性大幅改善 | ✅ 完成 | WsManager 完整重寫：zombie socket 修正、exponential backoff、visibilitychange 重連、CONNECT_TIMEOUT 2s |
| 飛航模式恢復自動重連 | ✅ 完成 | 恢復後直接 backoff 重試，不等 online 事件 |
| 登出不 reload 頁面 | ✅ 完成 | WS 保持連線，登出後直接顯示登入頁 |
| start_mac.sh | ✅ 完成 | 一鍵啟動全服務，自動偵測 LAN IP / Tailscale IP |
| start_windows.bat | ✅ 完成 | Windows 對應啟動腳本（UTF-8 編碼問題待修）|

### 8.2　Phase 1：Mac 模擬（現階段）

> **【v2.2新增】** 開發路線圖整合 security_network_spec Phase 1-3。

- 所有服務跑在 Mac 本機
- TLS 可選：設定 `CERT_PATH`/`KEY_PATH` 啟用 HTTPS/WSS，未設定則退回 HTTP/WS
- `start_mac.sh` 支援自動偵測 LAN IP / Tailscale IP，一鍵啟動全服務
- FileVault 保護開發資料

### 8.3　Phase 2：Pi 到貨（TLS + LUKS）

- 各組 Pi 部署 shelter_ws_server.js（TLS 已內建，見 §6.2）
- 設定 LUKS data 分區（/data）
- 部署 mkcert 憑證（§7.4），改用 HTTPS / WSS
- 靜態 IP 設定（§6.3），DHCP 排除 .10–.99
- 所有手機/平板安裝 mkcert CA 根憑證

### 8.4　Phase 3：Mini PC 到貨（全整合）

- 指揮部 Console 部署至 Mini PC（Intel N100，ASUS 建議 / Beelink 待驗證；32GB RAM）
- LUKS 全磁碟加密 + YubiKey（§7.5）
- WireGuard server 設定（情境 1B）
- YubiKey 整合——組長高權限操作完整實作
- Field Node（Pi Zero 2W）與 ICS_DMAS 整合（STT 輸出寫入 EVENT 表）

### 8.5　待確認事項（v2.2 更新）

| 項目 | 狀態 | 說明 |
|------|------|------|
| 藥品管制介面（完整記錄欄位 + 提醒機制） | ⏳ 待協議 | 待人管/醫療組協議流程 |
| 識別證手環個別編碼格式 | ⏳ 待確認 | 待安全組確認格式 |
| SRT 自動計算公式 | ⏳ 待協議 | 待醫療組協議 |
| 醫療組交界緩衝區雙向交接流程 | ⏳ 待協議 | 待協議 |
| Mini PC 品牌確認 | ⏳ 待確認 | Beelink / ASUS / 其他，需符合非中國品牌要求，統一規格 32GB RAM |
| Anker 行動電源 | ⏳ 待決定 | 總部深圳，依組織安全政策個案決定 |
| 指揮官版儀表板 | ✅ 初版完成 | `commander_dashboard.html`，待端對端測試 |
| YubiKey 雙人原則實作 | Phase 3 | 依民防感知系統規格 §4.3 |
| Field Node 與 ICS_DMAS 整合 | Phase 3 | STT 輸出寫入 EVENT 表 |
| 縣市 EOC 定時推送（EMIC 介接） | 【待確認】 | 需取得縣市政府主管機關介接規格後確認 |

---

## 附錄 A　硬體安全清單（v2.2 更新）

> **【v2.2新增】** 整合自 security_network_spec_v1_0.md §2.2。新增 Mini PC、Pi Zero 2W；更新 Lexar、D-Link、Anker 評等。

### A.1　建議使用（非中國品牌）

| 產品 | 品牌/原產地 | 用途 |
|------|-------------|------|
| Intel N100 Mini PC | ASUS Mini PC（建議）/ Beelink（待驗證，見 A.3） | 指揮部 Console |
| Raspberry Pi 4B（4GB） | Raspberry Pi Foundation，英國 | 各組 Pi（WebSocket server） |
| Raspberry Pi Zero 2W | Raspberry Pi Foundation，英國 | Field Node（PTT 錄音） |
| Raspberry Pi 官方電源 | Raspberry Pi Foundation，英國 | Pi 電源 |
| Samsung PRO Endurance SD | Samsung，韓國 | Pi 系統儲存 |
| SanDisk Extreme Pro | SanDisk（WD），美國 | Pi 系統儲存（備選） |
| Ubiquiti（UniFi）路由器 | Ubiquiti，美國法人 | 本地 WiFi 基地台 |
| ASUS / Netgear / Mikrotik | 台灣/美國 | 自建 WiFi AP（情境 2） |
| YubiKey 5 NFC | Yubico，瑞典 | 組長高權限授權（選配） |
| Mophie Powerstation | Mophie，美國 | Pi 行動電源 |
| Goal Zero | Goal Zero，美國 | Pi 行動電源（備選） |
| Apple iPhone / iPad | Apple，美國 | 現場操作手機/平板 |
| Samsung Galaxy | Samsung，韓國 | 現場操作手機/平板 |
| Google Pixel | Google，美國 | 現場操作手機/平板 |

### A.2　禁止使用（中國品牌）

| 產品 | 原因 |
|------|------|
| **小米（Xiaomi）手機/路由器** | 中國法人，資料存取疑慮 |
| **TP-Link（中國版）路由器** | 中國法人（美國子公司版本個案評估） |
| **華為（Huawei）** | 中國法人，已有多國政府禁用 |
| **GL.iNet 路由器** | 母公司 GL Technologies (HK) 為香港法人，研發製造在廣州，受中國司法管轄 |
| **Lexar SD 卡** | 2017 年被中國龍存科技收購 |
| **OPPO / Vivo 手機** | 中國法人 |

### A.3　需個案評估

| 產品 | 說明 |
|------|------|
| **Anker 行動電源** | 總部深圳（中國），依組織安全政策個案決定 |
| **D-Link 路由器** | 台灣公司（台北），但在中國有大量製造，需個案評估 |
| **Beelink Mini PC** | 台灣設計，但需確認具體製造地點 |

---

## 附錄 B　SOP 事件類型對應表

| 系統 Incident type | 來源 SOP | 來源事件名稱 |
|--------------------|----------|-------------|
| medical_infection | 填表分流（等候區） | 醫療/傳染病緊急事件 |
| capacity_overload | 填表分流（等候區） | 收容能量超載 |
| noise_disturbance | 填表分流（等候區） | 災民喧嘩影響他人 |
| power_outage | 填表分流（等候區） | 停電 |
| air_raid | 填表分流（等候區） | 空襲或飛彈攻擊 |
| security_threat | 填表分流（等候區） | 攻擊或治安威脅 |
| id_mismatch | 身份標籤與物品對應 | 核對不符 → 轉維安 |
| covenant_refused | 確認收容公約 | 不同意公約 |
| dangerous_resident | 環管帶位 | 收容者造成他人危險 |
| resource_shortage | 物管開場盤點 | 缺料/缺件/損壞 |
| suspicious_person | 環管日常 | 發現可疑人士或危險物品 |
| facility_damage | 環管日常 | 場地/設備遭破壞 |
| volunteer_conflict | 服務窗口日常 | 志工衝突升級 |
| rumor_spread | 服務窗口日常 | 謠言蔓延全場 |
| resident_distress | 服務窗口日常 | 災民情緒激動 |
| language_assist | CMIST 自動分派 | 語言/翻譯協助 |
| medication_mgmt | CMIST 自動分派 | 藥品管理 |
| accessible_bed | CMIST 自動分派 | 無障礙床位分配 |
| charging_arrange | CMIST 自動分派 | 電動輔具充電安排 |
| medical_transfer | CMIST 自動分派 | 需醫療轉介/轉送 |
| non_medical_transport | CMIST 自動分派 | 需非醫療接駁 |
| pet_placement | 入站 tagging | 寵物外送安置 |
| qr_generated | 稽核日誌（v2.1新增） | QR-SHELTER 通報產生 |
| network_recovery_push | 稽核日誌（v2.1新增） | 網路恢復推送 |

---

## 附錄 C　降級模式（停電/斷網應對）

| 降級情境 | 系統行為 | 人工配合動作 |
|----------|----------|-------------|
| 區域 WiFi 中斷 | 各裝置獨立運作，Peer Delta 手動合併；L0 QR 快照定時產生 | 口頭通報重要狀態變化；每 20 分鐘產生 QR 給指揮部 |
| 設備電池耗盡 | 儲存最後快照，重開後恢復 | 改用另一台設備繼續 |
| 全站停電 | 系統無法使用 | 執行「紙本降級包」（預先印好） |
| 全部設備故障 | 使用預先印好的紙本床位表 | 電力恢復後從紙本手動補登 |
| Pi 故障（WSS） | PWA 自動降級為 BroadcastChannel + Peer Delta（v1.3 模式） | 確認 Pi 重啟後 PWA 自動重連 |

---

## 附錄 D　法律合規對照表

| 法律義務 | 法源 | v2.x 系統對應 |
|----------|------|--------------|
| 個資蒐集分別同意（雙軌） | 個資法第7條 | consent_ops / consent_welfare 兩個獨立欄位 |
| 收容四件套（民事責任保護） | 民法侵權責任 | 列印功能 + covenant_signed 欄位 |
| 個資最小化（假名化） | 個資法比例原則 | 列表/統計顯示 display_id |
| 紙本補登後銷毀 | ARC SCIA 規範 | paper_form_destroyed 欄位 |
| 主動詢問政府並留存紀錄 | 災害防救法第64條 | 主動詢問紀錄表單（設定畫面） |
| 稽核不可刪除 | 稽核原則 | audit_log 表，只增不減 |
| 特種個資保護 | 個資法 §6 | health_flag、cmist 強制假名化＋強制加密匯出 |
| Write-Freeze | 稽核完整性 | 已離站人員核心欄位自動鎖定，不可回改 |

---

## 附錄 E　變更摘要

### v2.2 變更

> 整合 security_network_spec_v1.0，補強傳輸層與靜態加密，確立開發三 Phase 路線圖。

| # | 變更項目 | 說明 | 影響範圍 |
|---|----------|------|----------|
| 1 | **新增 §7 安全與網路架構** | 整合 security_network_spec，涵蓋三種網路情境、靜態 IP 規劃、mkcert、LUKS、WireGuard | §7（全新） |
| 2 | **HTTPS/WSS 傳輸加密** | shelter_ws_server 改用 https/wss 模組（Phase 2），前端 URL 改 wss:// | §6.2、§4.1 |
| 3 | **靜態 IP 規劃** | 收容組 Pi 固定 192.168.100.20，完整節點 IP 表 | §6.3 |
| 4 | **實作路線圖 Phase 1/2/3** | 明確區分 Mac 開發 / Pi 部署 / Mini PC 全整合三個階段 | §8.2–8.4 |
| 5 | **硬體安全清單更新** | 新增 N100 Mini PC、Pi Zero 2W；Lexar 列禁用；D-Link、Anker 列個案評估 | 附錄 A |
| 6 | **資料所有權說明** | 明確各層資料所在，LUKS 為強制要求 | §7.2 |
| 7 | **待確認事項更新** | 補充 Mini PC 品牌、Anker、指揮官版儀表板等待決定項目 | §8.5 |

### v2.3 變更（對應程式 v0.1.0）

| # | 變更項目 | 說明 | 影響範圍 |
|---|----------|------|----------|
| 1 | **程式輸出檔名更新** | 移除版號後綴，統一為 `shelter_pwa.html`、`shelter_ws_server.js`、`admin.html` | Header |
| 2 | **閒置鎖定時間修正** | 10 分鐘 → 90 秒警告 + 30 秒自動登出（共 2 分鐘） | §5.4 |
| 3 | **§6.2 WSS 升級完成** | TLS 已透過 env var 實作，不再是 Phase 2 待辦 | §6.2 |
| 4 | **指揮官版儀表板狀態更新** | 初版已完成（`commander_dashboard.html`） | §7.1、§8.5 |
| 5 | **Phase 1 更新** | TLS 可選；補充 `start_mac.sh` 一鍵啟動 | §8.2 |
| 6 | **v0.1.0 新增功能補錄** | Session restore、自動登出、iOS WS 穩定性、啟動腳本等 | §8.1b（新增） |
| 7 | **上游文件版號更新** | security_network_spec v1.0 → v1.2 | Header |

---

*收容組 PWA 規格書 v2.3 · 2026-03 · 對應程式版本 v0.1.0 · 整合 security_network_spec_v1.2 · 機密層級 C*
