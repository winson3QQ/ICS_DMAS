---
name: Medical PWA 對齊 shelter 待辦（2026-04-03）
description: Medical PWA 網路架構/登入/同步需完全複製 shelter 的實作，不可自己寫
type: project
---

## 狀態

Medical Pi Server（medical_ws_server.js）已完成，port 8775/8776，完全複製自 shelter。
Medical PWA client 端的 WsManager/登入流程需要**重做**，目前是簡化版，跟 shelter 差異巨大。

## 必須從 shelter 完整複製的模組（不可自己寫）

以下模組必須從 `shelter-pwa/public/shelter_pwa.html` 原封不動複製到 `medical-pwa/public/medical_pwa.html`，只改 key 名稱（shelter_ → med_）和 element ID：

1. **SyncManager IIFE**（shelter :2408-2444）— 裝置 ID、BroadcastChannel、Delta 同步
2. **syncAfterWrite 函式**（shelter :2446-2448）
3. **_wsLog IIFE**（shelter :2453-2463）— WS 日誌系統
4. **WsManager IIFE**（shelter :2464-2650）— 完整的連線管理、驗證、session 還原、time sync、catchup、recovery push、visibilitychange、online/offline
5. **handleLogin 函式**（shelter :2701-2739）— server 驗證 + 降級模式 + PinLock + site_salt
6. **登入頁 HTML 結構**（shelter :335-382）— 燈號、按鈕、伺服器設定
7. **updateLoginStatus 函式**（shelter :2674-2694）— 4 狀態（ok/pending/offline/degraded）+ 按鈕文字切換

## 只改不複製的（medical 專屬）

- `showApp()` — medical 有自己的 tab 結構和角色系統
- 入站/檢傷/治療/後送流程 — medical 專屬
- 事件系統 — medical 有自己的事件類型

## 必改的 key 名稱對照

| Shelter | Medical |
|---------|---------|
| `shelter_pi_url` | `med_pi_url` |
| `shelter_session_id` | `med_session_id` |
| `shelter_session_username` | `med_session_username` |
| `shelter_login_time` | `med_login_time` |
| `shelter_site_salt` | `med_site_salt` |
| `shelter_role` | `med_role` |
| `shelter_last_sync_ts` | `med_last_sync_ts` |
| `shelter_device_id` | `med_device_id` |
| `shelter-sync-v1` | `medical-sync-v1` |
| `pi-url-input` | `med-pi-url-input` |
| `pi-url-status` | `med-pi-url-status` |
| Port 8765 (WSS) | Port 8775 (WSS) |
| Port 8766 (Admin) | Port 8776 (Admin) |

## 未 commit 的改動

以下改動在 working tree 中，需要一起 commit：
- medical_pwa.html: openAdminPanel 改為指向 Pi server admin URL
- medical_pwa.html: authenticate 欄位名 pin_hash → pin 修正
- medical_pwa.html: PWA_VERSION v0.4.6-alpha
- sw.js: CACHE_NAME v0.4.6-alpha
- admin.html: PIN 輸入改 type=password、tab 記憶、版號 v0.1.1-alpha
- shelter admin.html: 同步修改（PIN type、tab 記憶）

## 規則提醒

- **不可自己寫，必須從 shelter 複製再改 key 名稱**
- **改完先讀 shelter 比對確認，再動手**
- **每次改動遞增版號（PWA_VERSION + CACHE_NAME）**
- **commit 前問使用者確認**
