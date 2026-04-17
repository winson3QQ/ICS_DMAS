# ICS_DMAS

**Incident Command System — Disaster Management & Assistance System**

鄉鎮層災害應變指揮系統。設計給民防 / 災防演訓使用，可不依賴外網、不依賴雲端，所有運算在本地局域網完成。

---

## 系統概覽

### 一句話

前線靠 PTT + 自動 STT 零操作回報；
各組靠 PWA 本地優先同步狀態；
指揮部整合所有資訊供決策；所有節點可獨立作業、可降級為 QR code 人工傳遞、全程硬體加密且具備秒級銷毀能力。

---

## 物理節點架構

```
前進組 / 安全組          收容組              醫療組
Pi Zero 2W x N        Pi 500             Pi 500
PTT 錄音 → STT        WebSocket          WebSocket
心跳上傳              :8765/8766         :8775/8776
.40 / .50             .20                .30
     ↓                   ↓                  ↓
          ┌─────────────────────────────────────┐
          │         指揮部 Pi 500                  │
          │  ICS_DMAS :8000 │ 民防感知 :8001    │
          │  FastAPI + SQLite                   │
          └─────────────────────────────────────┘
                         .10
```

同一台 Pi 500 跑兩套系統，端口分開：

| 端口 | 系統 | 用途 |
|------|------|------|
| :8000 | ICS_DMAS | 收容、醫療、整合儀表板 |
| :8001 | 民防感知 Console | 前進/安全組語音轉文字鏈 |

靜態 IP 段：`192.168.100.0/24`，.10–.50 保留給固定節點，.100–.200 動態分配。

---

## 資料流

### 鏈一：語音紀錄鏈（前進 / 安全組）

```
操作員按 PTT → Field Node 錄音
→ Whisper Tiny 本機草稿（< 5 秒）
→ 上傳 Console :8001
→ Whisper Large-v3 重推論（正式版）
→ Llama 3 8B 摘要
→ 指揮官審核 + YubiKey 簽署
→ ICS-214 PDF 存入資料彈匣
```

### 鏈二：狀態同步鏈（收容 / 醫療組）

```
各組 PWA 實時輸入
→ WebSocket 中繼（Pi）
→ API 同步至指揮部 :8000
→ 三 Pass 對齊合併（去重）
→ 指揮部儀表板顯示
```

---

## 降級設計（四種網路情境）

| 情境 | 條件 | 通訊方式 |
|------|------|---------|
| 1A | 同一 WiFi LAN | WebSocket 全自動同步 |
| 1B | 手機用行動網路 | WireGuard VPN 穿透後同 1A |
| 2 | 自建 AP，無公網 | 同 1A（封閉 LAN） |
| **3** | **完全離線** | **QR code 快照，每 20 分鐘人工掃描** |

情境 3 是真正的底線。每組 PWA 產生 `snapshot_uuid`（UUID v4）QR 碼，幕僚掃描後三 Pass 對齊合併進指揮部。

---

## 人員介面

| 角色 | 工具 | 核心任務 |
|------|------|---------|
| ICS 指揮官 | 指揮部儀表板（指揮官版） | 態勢判讀、裁示決策 |
| 計劃情報幕僚 | 指揮部儀表板（幕僚版） | 資料輸入、各組狀態監控 |
| 收容組 | 收容組 PWA | 床位、入站人員、物資 |
| 醫療組 | 醫療組 PWA | 檢傷、治療位、後送、物資 |
| 前進 / 安全組 | 只需按 PTT | 語音自動轉文字，零操作 |

---

## 安全架構

| 層級 | 機制 |
|------|------|
| 傳輸層（ICS_DMAS） | mkcert 本地 CA；Phase 1 HTTP/WS，Phase 2+ HTTPS/WSS；情境 1B WireGuard UDP 51820 |
| 傳輸層（民防感知） | Nginx mTLS 雙向憑證（更嚴格，獨立 CA） |
| 靜態加密 | 各 Pi /data 分區 LUKS2；指揮部 Pi 500 全磁碟 LUKS2；Field Node MicroSD 加密 |
| 實體安全 | USB 點火鑰匙（開機解密）；YubiKey FIDO2 雙人原則（關鍵操作授權） |
| 緊急銷毀 | `cryptsetup luksErase`，0.5 秒抹除 SSD Header；Field Node 長按 5 秒快速格式化 MicroSD |
| 供應鏈 | 禁用中國品牌（GL.iNet ❌、Huawei ❌、小米 ❌）；Beelink ⚠ 待驗證；見各規格書附錄 |

---

## 開發階段

| Phase | 說明 |
|-------|------|
| Phase 1 | HTTP/WS，Mac 本機模擬完整架構 |
| Phase 2 | HTTPS/WSS（mkcert），LUKS 部署至各 Pi，WireGuard |
| Phase 3 | 演訓正式環境，YubiKey + 全加密 + WireGuard 全部到位 |

目前開發階段：**Phase 1**（醫療 PWA medical-v0.6.3-alpha、指揮部 cmd-v0.6.0、收容組 PWA shelter-v2.3）

---

## 目錄結構

```
ICS_DMAS/
├── command-dashboard/       # 指揮部後端（FastAPI + SQLite）+ 前端儀表板
│   ├── src/                 # main.py / db.py / calc_engine.py
│   ├── static/              # commander_dashboard.html、qr_scanner.html、地圖底圖
│   ├── docs/                # 指揮部儀表板設計規格 v1.1
│   └── tests/               # gen_test_snapshots.py
├── shelter-pwa/             # 收容組 PWA + WebSocket Pi 伺服器
│   └── docs/                # 收容組規格 v2.3、SOP、DB schema
├── medical-pwa/             # 醫療組 PWA + WebSocket Pi 伺服器
│   └── docs/                # 醫療組規格 v0.6、SOP
├── security & forward/      # 民防輔助感知系統（前進/安全組，規格先行）
│   └── docs/                # 規格書、開發計畫、測試計畫 v1.4
└── docs/                    # 跨組共用規格
    └── ui_ux_design_guide.md
```

---

## 規格書索引

| 文件 | 版本 | 對應程式 |
|------|------|---------|
| [指揮部儀表板設計規格](command-dashboard/docs/指揮部儀表板設計規格.md) | v1.6 | cmd-v0.9.2 |
| [PWA UI/UX 設計規範](docs/ui_ux_design_guide.md) | — | 醫療 + 收容共用 |
| [醫療組 PWA 規格](medical-pwa/docs/medical_pwa_spec.md) | v0.6 | medical-v0.6.7-alpha |
| [醫療組 SOP](medical-pwa/docs/醫療組SOP_20260323.md) | 2026-03-23 | — |
| [收容組 PWA 規格](shelter-pwa/docs/shelter_pwa_spec.md) | v2.7 | shelter-v2.3 |
| [收容組 SOP](shelter-pwa/docs/收容組_SOP_彙整_20260330.md) | 2026-03-30 | — |
| [民防感知系統規格書](security%20&%20forward/docs/民防輔助感知系統_規格書_v1_4.md) | v1.4 | 規格先行 |
| [民防感知開發計畫](security%20&%20forward/docs/民防輔助感知系統_開發計畫_v1_4.md) | v1.4 | 規格先行 |
| [民防感知測試計畫](security%20&%20forward/docs/民防輔助感知系統_測試計畫_v1_4.md) | v1.4 | 規格先行 |
