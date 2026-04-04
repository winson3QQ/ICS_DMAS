# ICS_DMAS 安全與網路架構規格
# Security & Network Architecture Specification v1.2

整合對象：指揮部儀表板設計規格 v1.1、收容組規格 v2.2、民防輔助感知系統規格 v1.3

---

## 1. 系統整體架構

### 1.1 兩套系統的整合關係

```
【前進組 / 安全組】
  Field Node (Pi Zero 2W)
  PTT 錄音 → 本機 Whisper STT → 上傳指揮部
                                        ↓
【收容組 / 醫療組】            【指揮部 Console】
  手機 PWA                     Mini PC (Intel N100)
  ↕ WebSocket                  - ICS_DMAS 指揮部儀表板
  各組 Pi ─────────────────→  - 民防感知系統 Console
  (Raspberry Pi 4B)            - SQLite（LUKS 加密）
                                - 幕僚版儀表板
                                - 指揮官版儀表板（待建）
```

### 1.2 資料所有權

| 資料類型 | 所有權 | 儲存位置 |
|---------|--------|---------|
| 完整人員名單 | 各組 Pi | 各組 Pi SQLite（LUKS 加密）|
| 完整人員名單（同步後）| 指揮部 | Mini PC SQLite（LUKS 加密）|
| 快照 aggregate | 指揮部 | Mini PC SQLite |
| 語音記錄 | 指揮部 | Mini PC Data Cartridge（LUKS）|
| 稽核日誌 | 各層 | 各機器，不可刪除 |

**設計原則（§10.2 補充）**：
- 斷網期間：指揮部僅取得 QR 快照（aggregate），不含個人識別資料
- 有網路時：各組完整資料同步至指揮部（Architecture A），供計劃情報組作業
- 指揮部 Console 為最高價值目標，LUKS 加密為強制要求

---

## 2. 硬體規格

### 2.1 各節點硬體

| 節點 | 硬體 | 用途 |
|------|------|------|
| 指揮部 Console | Intel N100 Mini PC | ICS_DMAS 後端、民防感知 Console |
| 收容組 Pi | Raspberry Pi 4B（4GB）| WebSocket 伺服器、本地資料庫 |
| 醫療組 Pi | Raspberry Pi 4B（4GB）| WebSocket 伺服器、本地資料庫 |
| Field Node | Raspberry Pi Zero 2W | PTT 錄音、本機 Whisper STT |
| 測試機（現階段）| Mac | 模擬所有節點 |

### 2.2 非中國品牌硬體清單

詳見民防輔助感知系統規格 §12.2。以下為補充項目：

**主機與運算**
- Intel N100 Mini PC：建議品牌 Beelink（台灣設計）、ASUS Mini PC
- Raspberry Pi 4B / Zero 2W：英國 Raspberry Pi Foundation ✅
- 官方 Raspberry Pi 電源供應器 ✅

**儲存**
- SD 卡：Samsung PRO Endurance（韓國）✅、SanDisk（美國）✅
- 禁止：Lexar（2017 年被中國龍存科技收購）❌

**WiFi AP（情境 2 自建網路）**
- ASUS ✅、Netgear ✅、Mikrotik ✅
- 禁止：TP-Link ❌、GL.iNet ❌
- 注意：D-Link 為台灣公司但在中國有大量製造，需個案評估

**手機 / 平板**
- Apple iPhone / iPad ✅、Samsung Galaxy ✅、Google Pixel ✅
- 禁止：Huawei ❌、Xiaomi ❌、OPPO ❌、Vivo ❌

**電源**
- Mophie Powerstation ✅、Goal Zero ✅
- Anker：總部深圳，依組織安全政策個案決定

**安全金鑰**
- YubiKey（Yubico，瑞典）✅

---

## 3. 網路情境

### 3.1 三種情境定義

**情境 1A：有公網，手機連同一 WiFi**
```
手機 ─── WiFi ───> 各組 Pi (192.168.100.x)
                         ↓
                   指揮部 Mini PC (192.168.100.10)
                         ↓（可選）
                   公網（備援上傳）
```
- 通訊加密：HTTPS + WSS（mkcert）
- 手機驗證：預裝 mkcert CA 憑證

**情境 1B：有公網，手機使用行動網路**
```
手機 ─── 行動網路 ─── WireGuard VPN ───> 指揮部 Mini PC
                                                ↓
                                         各組 Pi（同 LAN）
```
- 通訊加密：WireGuard（端對端）+ HTTPS + WSS
- 手機驗證：預裝 WireGuard profile + mkcert CA 憑證
- 前提：Mini PC 有穩定公網 IP 或 DDNS

**情境 2：無公網，自建 WiFi**
```
手機 ─── 自建 WiFi AP（Bridge Mode）───> 各組 Pi
                                                ↓
                                         指揮部 Mini PC
```
- 所有 AP 必須設定為 **Bridge Mode**（同一子網）
- 通訊加密：HTTPS + WSS（mkcert）
- 若各組距離遠無法組網 → 退回情境 3

**情境 3：單機作業**
```
各組 Pi ─── 本地 ───> 本組手機
（無跨組網路連線）
```
- 各組獨立運作，不需要跨組加密
- 資料等網路恢復後，透過三 Pass 對齊同步至指揮部
- QR code 快照為此期間指揮部獲取資訊的唯一通道

### 3.2 靜態 IP 規劃

| 節點 | IP | 服務 |
|------|-----|------|
| 指揮部 Mini PC | 192.168.100.10 | FastAPI :8000、WebSocket Console |
| 收容組 Pi | 192.168.100.20 | WebSocket :8765、Admin :8766 |
| 醫療組 Pi | 192.168.100.30 | WebSocket :8775、Admin :8776 |
| 前進組 Field Node | 192.168.100.40 | 心跳 + 上傳 |
| 安全組 Field Node | 192.168.100.50 | 心跳 + 上傳 |
| DHCP 範圍（手機等）| 192.168.100.100–200 | 動態分配 |

演訓前須在 AP 的 DHCP 設定中排除 .10–.99 段。

### 3.3 指揮部 Mini PC 端口分配

同一台 Mini PC 同時運行兩套系統：

| 服務 | 系統 | 端口 | 協定 |
|------|------|------|------|
| ICS_DMAS 後端 API | ICS_DMAS | :8000 | HTTPS (FastAPI + uvicorn) |
| 民防感知 Console API | 民防輔助感知系統 | :8001 | HTTPS (FastAPI + uvicorn) |
| 收容組 WebSocket | 各組 Pi | :8765 | WSS |
| 收容組 Admin | 各組 Pi | :8766 | HTTPS |
| 醫療組 WebSocket | 各組 Pi | :8775 | WSS |
| 醫療組 Admin | 各組 Pi | :8776 | HTTPS |

### 3.4 系統整合機制（民防感知 → ICS_DMAS）

民防感知系統（前進組/安全組 Field Node）透過 HTTP POST 將事件寫入 ICS_DMAS：

```
民防感知 Console (:8001)
  └─ POST http://localhost:8000/api/events
       Content-Type: application/json
       {
         "unit": "前進組",
         "type": "感知警報",
         "description": "...",
         "source": "sensor"
       }
```

**設計原則**：
- 整合僅限本機 localhost 呼叫（不跨網路）
- ICS_DMAS `/api/events` 端點需驗證 source 白名單
- 民防感知系統不直接寫入 ICS_DMAS SQLite（避免跨系統耦合）

---

## 4. 傳輸安全（HTTPS / WSS）

### 4.1 方案：mkcert 本地 CA

**選擇依據**：
- 作者 Filippo Valsorda（義大利裔美國人，前 Go 安全團隊）
- 無中國關聯，開源，免費
- 適用於所有三種情境的本地網路

**不適用 Let's Encrypt 的原因**：Let's Encrypt 需要公開域名 + 網路驗證，情境 2、3 無法使用。

### 4.2 憑證管理 SOP（演訓前）

```
步驟 1：管理員 Mac 安裝 mkcert
  brew install mkcert
  mkcert -install

步驟 2：為各節點 IP 簽發憑證
  mkcert 192.168.100.10  # 指揮部
  mkcert 192.168.100.20  # 收容組 Pi
  mkcert 192.168.100.30  # 醫療組 Pi

步驟 3：將 CA 根憑證安裝至所有手機/平板
  iOS：AirDrop rootCA.pem → 設定 → 信任憑證
  Android：設定 → 安全性 → 安裝憑證

步驟 4：將憑證部署至各 Pi / Mini PC
  scp 192.168.100.10+1.pem pi@192.168.100.10:~/certs/
  scp 192.168.100.10+1-key.pem pi@192.168.100.10:~/certs/

步驟 5：啟動各服務時載入憑證（見第 6 節）

步驟 6：全裝置連線測試
```

**注意**：憑證有效期預設 825 天，演訓前檢查是否過期。

### 4.3 情境 1B 補充：WireGuard

**選擇依據**：
- Jason Donenfeld（美國）開發
- 已併入 Linux kernel 5.6
- 無中國關聯

**設定要點**：
- Mini PC 開 WireGuard server，監聽 UDP 51820
- 每台手機一組金鑰對，設定以 QR code 分發
- 若無固定公網 IP，使用 DuckDNS（社群維護，免費）或 No-IP（美國）
- 路由器需開 UDP 51820 port forwarding

**WireGuard 生效後**：手機視為在同一虛擬 LAN，後續通訊與情境 1A / 2 相同，不需額外處理。

---

## 5. 靜態加密（LUKS）

### 5.1 方案選擇

**選用 LUKS（Linux Unified Key Setup）**，不使用 SQLCipher 或應用層加密。

**原因**：
- OS 層磁碟加密，覆蓋所有資料（SQLite、log、設定檔、暫存檔）
- 已是 Linux kernel 內建，無額外供應鏈風險
- 不需修改任何應用程式碼
- 與民防輔助感知系統規格 §4.2 一致（`cryptsetup luksErase`）

### 5.2 各節點 LUKS 設定

| 節點 | 加密對象 | 金鑰管理 |
|------|---------|---------|
| 指揮部 Mini PC | OS 碟 + Data Cartridge | YubiKey（主）+ 備援密碼（雙人原則）|
| 各組 Pi | Data 分區（/data）| 演訓前設定 passphrase，任務結束後銷毀 |
| Field Node | MicroSD | Panic 長按 5 秒快速格式化 |

### 5.3 開發階段（Mac）

Mac 使用 FileVault 全磁碟加密（系統偏好設定 → 隱私與安全性）。
LUKS 僅在 Pi / Mini PC 正式部署時設定，不影響 Mac 開發流程。

### 5.4 Panic Wipe

依民防輔助感知系統規格 §4.2：
- Mini PC / Pi：`cryptsetup luksErase` → 0.5 秒內 Header 抹除，資料永久遺失
- Field Node：長按實體按鈕 5 秒 → MicroSD 快速格式化
- Panic 按鈕需有防誤觸保護蓋

### 5.5 Client-Side IndexedDB 加密（TODO）

**現況**：PWA 端使用 PersonCrypto（AES-256-GCM）加密 IndexedDB 中的個資欄位。金鑰透過 `PBKDF2(passphrase, site_salt)` 派生。

**已知問題**：目前 passphrase 與 salt 皆為 `site_salt`（`PBKDF2(site_salt, site_salt)`），所有帳號共享同一金鑰以支援跨帳號換手。但 `site_salt` 存於 localStorage，等同裝置上明文可取得，因此靜態資料保護效果有限。

**長期方案（擇一）**：
1. **Server 端解密再下發**：Pi 持有 master key，sync 時以明文下發至 client，client 用 per-PIN key 加密本地副本。保留靜態保護，但需改 sync 協議。
2. **Server 下發 group key**：Pi 在登入成功後下發加密用的 group key（不存 localStorage，僅存 sessionStorage），session 結束即消失。靜態保護中等。
3. **放棄 client-side 加密，依賴 LUKS**：Pi 部署後有全碟加密，client 端 IndexedDB 加密移除。最簡單但手機端無保護。

**決策時機**：Pi 到貨、LUKS 部署完成後再決定。

---

## 6. 服務啟動設定（加入 TLS）

### 6.1 指揮部後端（FastAPI + uvicorn）

```bash
cd command-dashboard/src
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-certfile ~/certs/192.168.100.10+1.pem \
  --ssl-keyfile  ~/certs/192.168.100.10+1-key.pem
```

前端存取改為 `https://192.168.100.10:8000`

### 6.2 收容組 Pi（Node.js WebSocket）

shelter_ws_server.js 已支援 TLS，透過環境變數載入憑證：

```bash
CERT_PATH=/path/to/cert.pem \
KEY_PATH=/path/to/key.pem \
node shelter_ws_server.js
```

未設定 `CERT_PATH`/`KEY_PATH` 時自動退回 HTTP/WS（開發用）。

```
WSS：  wss://192.168.100.20:8765
Admin：https://192.168.100.20:8766
```

### 6.3 前端 URL 更新

已完成。shelter_pwa.html 的 Pi URL 由使用者在設定頁輸入並存入 localStorage，支援 wss:// 與 ws://。

---

## 7. API 驗證（情境 1B 公網場景）

情境 1A / 2 / 3 的 API 由 WireGuard 或封閉 LAN 保護，不需額外 API 驗證。

情境 1B（WireGuard 層已保護），視威脅等級選擇：

| 等級 | 方案 | 說明 |
|------|------|------|
| 基本 | API Key per device | Header 帶 `X-Device-Key`，演訓前統一配發 |
| 進階 | YubiKey OTP | 與民防感知系統 §4.3 YubiKey 方案整合 |

**現階段實作**：基本 API Key，待 YubiKey 整合完成後升級。

---

## 8. 開發階段規劃

### Phase 1：Mac 模擬（現階段）
- 所有服務跑在 Mac 本機
- TLS 可選：設定 `CERT_PATH`/`KEY_PATH` 啟用 HTTPS/WSS，未設定則退回 HTTP/WS
- `start_mac.sh` 支援自動偵測 LAN IP / Tailscale IP，一鍵啟動
- FileVault 保護開發資料
- **目標**：端對端功能驗證（shelter PWA → 指揮部儀表板）

### Phase 2：Pi 到貨
- 各組 Pi 部署 shelter / medical server
- 設定 LUKS data 分區
- 部署 mkcert 憑證，改用 HTTPS / WSS
- **目標**：多裝置真實網路測試

### Phase 3：Mini PC 到貨
- 指揮部 Console 部署至 Mini PC
- LUKS 全碟加密
- WireGuard server 設定（情境 1B）
- YubiKey 整合
- **目標**：完整演訓環境驗證

---

## 9. 跨系統資料標準

### 9.1 SNAPSHOT.source 統一詞彙

所有系統（收容組 Pi SQLite、指揮部 SQLite、PWA IndexedDB）使用相同的 source 值：

| 值 | 含義 | 產生時機 |
|----|------|---------|
| `auto` | 各組 Pi 自動定時推送 | 收容組 Pi 每 N 秒自動執行 sync_push |
| `qr` | QR code 快照掃描匯入 | 指揮部人員用 qr_scanner.html 掃各組快照 |
| `sync_recovery` | 斷網恢復後三 Pass 對齊同步 | 網路恢復後手動/自動觸發三 Pass 流程 |
| `manual` | 人工輸入或手動覆寫 | 操作員直接在介面輸入或修改 |
| `merged` | 衝突合併後的記錄 | 三 Pass 對齊遇衝突，人工或規則決議後產生 |

**禁用值**（已廢棄，不得出現在任何系統）：
- `pi_push`（改用 `auto`）
- `merged_from_qr`（改用 `merged`）
- `shelter_push`（改用 `auto`）

> ⚠️ **已知問題**：`shelter_ws_server.js` 第 506、534、541 行仍使用上述廢棄值，需在下次 PATCH 版本修正。

---

## 10. 待確認事項

| 項目 | 狀態 | 說明 |
|------|------|------|
| Mini PC 品牌確認 | 待確認 | Beelink / ASUS / 其他 |
| Anker 行動電源 | 待決定 | 總部深圳，依安全政策決定 |
| 指揮官版儀表板 | 已完成初版 | `commander_dashboard.html`，待端對端測試 |
| YubiKey 雙人原則實作 | Phase 3 | 依民防感知系統規格 §4.3 |
| Field Node 與 ICS_DMAS 整合 | Phase 3 | STT 輸出寫入 EVENT 表 |

---

*文件版本：v1.2 | 對應程式版本：v0.1.0 | 整合來源：指揮部儀表板規格 v1.1、收容組規格 v2.2、民防感知系統規格 v1.3*
