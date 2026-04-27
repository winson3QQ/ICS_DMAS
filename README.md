# ICS_DMAS

**Incident Command System — Disaster Management & Assistance System**

鄉鎮層災害應變指揮系統。設計給民防 / 災防演訓使用，可不依賴外網、不依賴雲端，所有運算在本地局域網完成。

---

## 系統概覽

前線靠 PTT + 自動 STT 零操作回報；各組靠 PWA 本地優先同步狀態；指揮部整合所有資訊供決策。所有節點可獨立作業、可降級為 QR code 人工傳遞、全程硬體加密且具備秒級銷毀能力。

```
前進組 / 安全組          收容組              醫療組
Pi Zero 2W x N        Pi 500             Pi 500
PTT 錄音 → STT        WebSocket          WebSocket
.40 / .50             .20                .30
     ↓                   ↓                  ↓
          ┌─────────────────────────────────────┐
          │         指揮部 Pi 500                  │
          │  ICS_DMAS :8000 │ 民防感知 :8001    │
          │  FastAPI + SQLite                   │
          └─────────────────────────────────────┘
                         .10
```

| 角色 | 工具 | 核心任務 |
|------|------|---------|
| ICS 指揮官 | 指揮部儀表板（指揮官版） | 態勢判讀、裁示決策 |
| 計劃情報幕僚 | 指揮部儀表板（幕僚版） | 資料輸入、各組狀態監控 |
| 收容組 | 收容組 PWA | 床位、入站人員、物資 |
| 醫療組 | 醫療組 PWA | 檢傷、治療位、後送、物資 |
| 前進 / 安全組 | 只需按 PTT | 語音自動轉文字，零操作 |

降級底線：完全離線時每組 PWA 產生 QR code 快照，每 20 分鐘人工掃描合併進指揮部。

---

## 依需求導航

### 想了解這個計劃

→ [docs/commercialization_plan_v1.md](docs/commercialization_plan_v1.md)
商業目標、目標市場、C0–C6 工程軌道、護城河策略、IP 策略

### 規劃 / 里程碑 / 目前在哪

→ [docs/ROADMAP.md](docs/ROADMAP.md)
Edition → Release → Items 人類視角。技術細節在 matrix.md

### 指揮部儀表板開發

→ [command-dashboard/docs/指揮部儀表板設計規格.md](command-dashboard/docs/指揮部儀表板設計規格.md)（UI/UX 規格 v2.2）

### 收容組 PWA 開發

→ [shelter-pwa/docs/shelter_pwa_spec.md](shelter-pwa/docs/shelter_pwa_spec.md)（功能規格 v2.7）

### 醫療組 PWA 開發

→ [medical-pwa/docs/medical_pwa_spec.md](medical-pwa/docs/medical_pwa_spec.md)（功能規格 v0.6）

### AI / 語音輸入開發

→ [docs/AI_integration_roadmap.md](docs/AI_integration_roadmap.md)
Phase 0–7 技術路線、E2B 評估結果、STT 路線決策

### 前進 / 安全組（民防感知系統）

→ [security & forward/docs/](security%20&%20forward/docs/)
規格書、開發計畫、測試計畫 v1.4（CONFIDENTIAL）

### 演訓現場志工

→ [shelter-pwa/docs/收容組_SOP_彙整_20260330.md](shelter-pwa/docs/收容組_SOP_彙整_20260330.md)
→ [medical-pwa/docs/醫療組SOP_20260323.md](medical-pwa/docs/醫療組SOP_20260323.md)

### 共用 UI/UX 設計規範

→ [docs/ui_ux_design_guide.md](docs/ui_ux_design_guide.md)

---

## 指揮部後端快速啟動

```bash
cd command-dashboard
export PYTHONPATH=src          # Windows: set PYTHONPATH=src
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

測試資料注入：

```bash
python tests/gen_test_snapshots.py --batch
```

> **DB schema 變更**需刪除 `data/ics.db` 讓服務重建。

---

## 開發狀態

| 元件 | 目前版號 | 開發階段 |
|------|---------|---------|
| 指揮部（FastAPI + 儀表板） | cmd-v2.0.5 | Phase 1 ✅ / Security hardening in progress |
| 收容組 PWA | shelter-v2.2.53 | Phase 1 |
| 醫療組 PWA | medical-v0.6.7-alpha | Phase 1 |
| Pi Server（共用） | server-v1.2.0 | Phase 1 |

Phase 1 = Mac 本機模擬，HTTP/WS。Phase 2 = HTTPS/WSS + LUKS 部署至各 Pi。Phase 3 = 演訓正式環境，YubiKey + 全加密。
