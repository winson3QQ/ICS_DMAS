# ICS 指揮部後端

## 檔案結構

```
command-dashboard/
├── src/
│   ├── main.py           — FastAPI 主程式（API 路由）
│   ├── db.py             — SQLite schema + CRUD
│   └── calc_engine.py    — 計算引擎（趨勢、倒數、壓力指數）
├── static/
│   ├── commander_dashboard.html  — 指揮部儀表板前端（CMD_VERSION 常數控制版號）
│   ├── qr_scanner.html           — QR 掃描介面
│   ├── ICS_Campus_map.jpg        — 站內地圖底圖
│   ├── Satellite_map.png         — 站外衛星地圖底圖
│   ├── map_config.json           — 地圖據點座標設定
│   ├── lib/                      — 前端函式庫（Leaflet 等）
│   └── 指揮部儀表板設計規格_v1_1.md  — UI/UX 規格書
├── tests/
│   └── gen_test_snapshots.py     — 生成測試快照資料
├── data/
│   └── ics.db                    — SQLite 資料庫（執行後自動建立，.gitignore）
├── docs/                         — 附加文件
├── requirements.txt
└── setup.sh                      — Pi 安裝腳本
```

---

## 快速啟動

```bash
cd command-dashboard
set PYTHONPATH=src   # Windows；Mac/Linux: export PYTHONPATH=src
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

測試資料：

```bash
python tests/gen_test_snapshots.py --batch
```

> **DB schema 變更**需刪除 `data/ics.db` 讓服務重建。

---

## API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/health` | 系統狀態 |
| GET | `/api/dashboard` | 儀表板整包資料（前端 polling） |
| POST | `/api/snapshots` | 各組推送快照 / QR 掃描寫入 |
| GET | `/api/snapshots/{node_type}` | 取某節點快照列表 |
| POST | `/api/events` | 建立事件記錄 |
| GET | `/api/events` | 取事件列表（含 resolved 最近 50 筆） |
| PATCH | `/api/events/{id}/status` | 更新事件狀態 |
| POST | `/api/decisions` | 建立待裁示事項 |
| GET | `/api/decisions` | 取裁示列表 |
| POST | `/api/decisions/{id}/decide` | 裁示（核准/保留/…） |
| GET | `/api/audit_log` | 稽核日誌（不可刪除） |

---

## 各組 Pi 推送格式

POST `/api/snapshots`：

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

`snapshot_id` 為 idempotent key，網路恢復後重送不會重複寫入。

---

## 斷網期間

各組 Pi 繼續本地作業，每 N 分鐘產生 QR code。計劃情報組用 `qr_scanner.html` 掃描，解碼後 POST `/api/snapshots`（`source=qr_scan`）。

---

## 開發路線圖

Wave 1–3 已完成（cmd-v0.6.0），Wave 4–5 待做。詳見 `.claude/memory/project_status.md`。

| Wave | 項目 | 版號 | 狀態 |
|------|------|------|------|
| 4 | Operator Fatigue 操作者疲勞偵測 | cmd-v0.7.0 | 待做 |
| 5 | Pi Read-Only API + L3/L4 地圖鑽探 | cmd-v0.8.0 | 待做 |
