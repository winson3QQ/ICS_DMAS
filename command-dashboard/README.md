# ICS 指揮部後端 v1.0

## 檔案結構

```
ics_backend/
├── main.py           — FastAPI 主程式（API 路由）
├── db.py             — SQLite schema + CRUD
├── calc_engine.py    — 計算引擎（趨勢、倒數、壓力指數）
├── requirements.txt  — Python 套件
├── setup.sh          — Pi 安裝腳本
├── ics.db            — SQLite 資料庫（執行後自動建立）
└── static/           — 前端 HTML 放這裡
    ├── staff_dashboard.html
    ├── qr_scanner.html
    └── manual_input.html
```

---

## 快速啟動（指揮部 Pi）

```bash
bash setup.sh
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## API 端點

| 方法   | 端點                                   | 說明                        |
|--------|----------------------------------------|-----------------------------|
| GET    | `/api/health`                          | 系統狀態（各組 Pi 可 ping）  |
| POST   | `/api/snapshots`                       | 各組推送快照 / QR 掃描寫入  |
| GET    | `/api/snapshots/{node_type}`           | 取某節點快照列表             |
| POST   | `/api/events`                          | 建立事件記錄                 |
| GET    | `/api/events`                          | 取事件列表                   |
| PATCH  | `/api/events/{id}/status`              | 更新事件狀態                 |
| POST   | `/api/decisions`                       | 建立待裁示事項               |
| GET    | `/api/decisions`                       | 取裁示列表                   |
| POST   | `/api/decisions/{id}/decide`           | 裁示（approved/hold/...）   |
| GET    | `/api/dashboard`                       | 儀表板整包資料（前端 polling）|
| GET    | `/api/audit_log`                       | 稽核日誌（不可刪除）         |

---

## 各組 Pi 推送格式

與規格第十三部分 QR code 格式完全一致，直接 POST `/api/snapshots`：

```json
{
  "v": 1,
  "type": "snapshot_medical",
  "snapshot_id": "<UUID>",
  "t": "2026-04-11T14:30:00Z",
  "src": "medical_pwa_v1",
  "source": "auto",
  "casualties": {"red": 2, "yellow": 4, "green": 0, "black": 0},
  "bed_used": 6,
  "bed_total": 10,
  "waiting_count": 7,
  "pending_evac": 2,
  "staff_on_duty": 12,
  "supplies": {"tourniquet": 24, "iv": 7, "saline": 6}
}
```

---

## GET /api/dashboard 回傳格式

```json
{
  "calc": {
    "computed_at": "...",
    "medical": {
      "snapshot": {...},
      "freshness": {"level": "ok"|"warn"|"crit"|"lkp", "minutes": 2.1, "label": "即時"},
      "bed_trend": {"rate": 0.07, "direction": "up", "confidence": "medium", "note": "..."},
      "waiting_trend": {...},
      "countdown_to_red": {"minutes_to_threshold": 42.9, "label": "42分鐘後達門檻", ...}
    },
    "shelter": { "snapshot": {...}, "freshness": {...}, "bed_trend": {...} },
    "forward": { "snapshot": {...}, "freshness": {...}, "units": [{...}, {...}] },
    "security": { "snapshot": {...}, "freshness": {...} },
    "medical_pressure": {
      "index": 4.85,
      "level": "critical",
      "components": {"waiting": 1.75, "forward": 2.4, "shelter": 0.6, "security": 0.1}
    },
    "low_confidence_count": 1
  },
  "events": [...],
  "decisions": {
    "pending": [...],
    "decided": [...]
  }
}
```

---

## 斷網期間

斷網時各組 Pi 繼續本地作業，每 N 分鐘產生 QR code。
計劃情報組用 `qr_scanner.html` 掃描，解碼後 POST `/api/snapshots`（source=qr_scan）。
快照會帶 `snapshot_id`，網路恢復後各組推送時，後端自動 IGNORE 重複的 snapshot_id（idempotent）。

---

## 第二階段（演訓後）

- [ ] 斷網同步機制（SYNC_LOG 三 Pass 對齊）
- [ ] PREDICTION 實體化（非同步計算存表）
- [ ] 收容組 PWA 介接對齊（已有 `snapshot_id` 機制）
- [ ] 指揮官版儀表板（v8）
- [ ] threshold_settings.html（門檻可調介面）
