"""
main.py — ICS 指揮部後端 API
FastAPI + SQLite，跑在指揮部 Pi

啟動方式：
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

各組 Pi 推送端點：
  POST http://<指揮部IP>:8000/api/snapshots

前端 polling 端點：
  GET  http://<指揮部IP>:8000/api/dashboard
"""

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
from pathlib import Path

import asyncio
import db
import calc_engine

# ──────────────────────────────────────────
# App 初始化
# ──────────────────────────────────────────

app = FastAPI(
    title="ICS 指揮部 API",
    version="1.0.0",
    docs_url="/docs",   # 開發時可用 Swagger UI 測試
)


# 預留：定時快照 loop（各組快照由 /api/snapshots 推送，此 loop 供未來擴充）
@app.on_event("startup")
async def start_snapshot_scheduler():
    asyncio.create_task(_snapshot_loop())


async def _snapshot_loop():
    """預留結構：未來可在此自動產生 sentinel 快照"""
    await asyncio.sleep(30)  # 啟動後 30 秒才開始，等各組連線
    while True:
        try:
            # 目前只是預留，實際快照來自各組 PWA 推送
            pass
        except Exception:
            pass
        await asyncio.sleep(300)  # 每 5 分鐘


# CORS：允許同區網所有裝置（各組 Pi、iPad）存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # 區網內不需要限制 origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態檔案（前端 HTML）
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# 啟動時建立 DB
@app.on_event("startup")
def startup():
    db.init_db()
    print("[OK] ICS 後端啟動，資料庫已初始化")


# ──────────────────────────────────────────
# Pydantic models（請求驗證）
# ──────────────────────────────────────────

class SnapshotIn(BaseModel):
    """
    通用快照格式。相容 QR-SHELTER / QR-MEDICAL / QR-FORWARD / QR-SECURITY。
    必填欄位對應規格 13.2 通用技術規格。
    """
    v:           int
    type:        str              # snapshot_shelter / snapshot_medical / ...
    snapshot_id: str
    t:           str              # ISO 8601 UTC
    src:         str              # 來源系統代號

    # 以下欄位各格式選填
    source: Optional[str] = "auto"   # auto / qr_scan / auto_sync / manual

    # SHELTER
    bed_used:      Optional[int]  = None
    bed_total:     Optional[int]  = None
    srt:           Optional[dict] = None
    pending_intake:Optional[int]  = None
    cmist_pending: Optional[int]  = None
    staff_on_duty: Optional[int]  = None

    # MEDICAL
    casualties:      Optional[dict] = None
    waiting_count:   Optional[int]  = None
    pending_evac:    Optional[int]  = None
    evacuated_total: Optional[int]  = None
    supplies:        Optional[dict] = None

    # FORWARD
    units: Optional[list] = None   # [{unit, casualties, ccp_status, ...}]

    # SECURITY
    post_total:      Optional[int]  = None
    post_anomaly:    Optional[str]  = None
    qrf_available:   Optional[int]  = None
    isolation_count: Optional[int]  = None

    # 通用選填
    vehicle_available: Optional[int]  = None
    extra:             Optional[dict] = None

    class Config:
        extra = "allow"   # 允許額外欄位，向下相容


class EventIn(BaseModel):
    reported_by_unit:         str
    event_type:               str
    severity:                 str = "info"
    description:              str
    operator_name:            str
    location_desc:            Optional[str] = None
    response_type:            Optional[str] = None
    needs_commander_decision: bool = False
    related_person_name:      Optional[str] = None
    occurred_at:              Optional[str] = None


class DecisionIn(BaseModel):
    decision_type:      str   # initial / revision / escalation / closure
    severity:           str   # critical / warning
    decision_title:     str
    impact_description: str
    suggested_action_a: str
    created_by:         str
    suggested_action_b: Optional[str] = None
    primary_event_id:   Optional[str] = None
    parent_decision_id: Optional[str] = None


class DecideIn(BaseModel):
    action:         str   # approved / hold / redirect / completed
    decided_by:     str
    execution_note: str = ""


class SyncPushIn(BaseModel):
    """網路恢復後，各組 Pi 推送斷線期間完整資料"""
    source_unit:   str           # shelter / medical / forward / security
    sync_start_ts: str           # 斷線起始時間（ISO UTC）
    device_id:     Optional[str] = None
    snapshots:     list = []     # 含 snapshot_id 的快照列表
    events:        list = []     # 斷線期間事件
    manual_records: list = []    # 斷線期間手動輸入記錄

    class Config:
        extra = "allow"


class ConflictResolveIn(BaseModel):
    conflict_idx: int    # 衝突在列表中的索引
    action:       str    # keep_incoming / keep_existing / merge
    operator:     str


# ──────────────────────────────────────────
# API：快照
# ──────────────────────────────────────────

@app.post("/api/snapshots", tags=["快照"])
def post_snapshot(snap: SnapshotIn):
    """
    各組 PWA 推送快照，或計劃情報組掃 QR code 後呼叫此端點。
    idempotent：同一個 snapshot_id 重複推送只寫入一次。
    """
    # 從 type 欄位推算 node_type
    type_map = {
        "snapshot_shelter":  "shelter",
        "snapshot_medical":  "medical",
        "snapshot_forward":  "forward",
        "snapshot_security": "security",
        "snapshot_ccp":      "ccp",
        "snapshot_evac":     "evac",
        # 相容 Pi Server 推送的短名格式
        "shelter":  "shelter",
        "medical":  "medical",
        "forward":  "forward",
        "security": "security",
        "ccp":      "ccp",
        "evac":     "evac",
    }
    node_type = type_map.get(snap.type)
    if not node_type:
        raise HTTPException(400, f"未知的 type: {snap.type}")

    data = snap.model_dump()
    data["node_type"] = node_type
    result = db.upsert_snapshot(data)
    return result


@app.get("/api/snapshots/{node_type}", tags=["快照"])
def get_snapshots(node_type: str, limit: int = 20):
    """取某節點最近 N 筆快照"""
    return db.get_snapshots(node_type, limit)


# ──────────────────────────────────────────
# API：事件
# ──────────────────────────────────────────

@app.post("/api/events", tags=["事件"])
def post_event(ev: EventIn):
    """建立事件記錄（manual_input.html 呼叫此端點）"""
    result = db.create_event(ev.model_dump())

    # 若需要指揮官裁示，自動建立待裁示事項（decision_type=initial）
    if ev.needs_commander_decision:
        db.create_decision({
            "primary_event_id":  result["id"],
            "decision_type":     "initial",
            "severity":          ev.severity if ev.severity != "info" else "warning",
            "decision_title":    ev.description[:60],
            "impact_description": f"來源：{ev.reported_by_unit}　{ev.event_type}",
            "suggested_action_a": "（計劃情報組補充建議動作）",
            "created_by":        ev.operator_name,
        })

    return result


@app.get("/api/events", tags=["事件"])
def get_events(status: Optional[str] = None, limit: int = 50):
    return db.get_events(status, limit)


@app.patch("/api/events/{event_id}/status", tags=["事件"])
def update_event_status(event_id: str, status: str, operator: str):
    db.update_event_status(event_id, status, operator)
    return {"ok": True}


# ──────────────────────────────────────────
# API：裁示
# ──────────────────────────────────────────

@app.post("/api/decisions", tags=["裁示"])
def post_decision(dec: DecisionIn):
    """計劃情報組建立待裁示事項"""
    result = db.create_decision(dec.model_dump())
    return result


@app.get("/api/decisions", tags=["裁示"])
def get_decisions(status: Optional[str] = None):
    return db.get_decisions(status)


@app.post("/api/decisions/{decision_id}/decide", tags=["裁示"])
def decide(decision_id: str, body: DecideIn):
    """
    指揮官（或計劃情報組代操）裁示。
    寫入後進入 Write-Freeze，不可再修改。
    """
    try:
        result = db.decide(decision_id, body.action, body.decided_by, body.execution_note)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


# ──────────────────────────────────────────
# API：稽核日誌
# ──────────────────────────────────────────

@app.get("/api/audit_log", tags=["系統"])
def get_audit_log(limit: int = 100):
    """不可刪除的完整操作紀錄"""
    return db.get_audit_log(limit)


# ──────────────────────────────────────────
# API：儀表板整包資料（前端主要 polling 端點）
# ──────────────────────────────────────────

@app.get("/api/dashboard", tags=["儀表板"])
def get_dashboard():
    """
    前端每 10 秒呼叫一次此端點。
    後端算好所有數字，前端只負責顯示。
    回傳格式：
      {
        calc: { medical, shelter, forward, security, medical_pressure, ... },
        events: [...],
        decisions: { pending: [...], decided: [...] },
        audit_summary: { total_today: int }
      }
    """
    # 取各組最近快照（40 筆供 burn_rate / comm_health 分析）
    medical_snaps  = db.get_snapshots("medical",  40)
    shelter_snaps  = db.get_snapshots("shelter",  40)
    forward_snaps  = db.get_snapshots("forward",  40)
    security_snaps = db.get_snapshots("security", 40)

    # 計算引擎
    calc = calc_engine.dashboard_calc(
        medical_snaps, shelter_snaps, forward_snaps, security_snaps
    )

    # 事件
    open_events     = db.get_events("open",        limit=20)
    progress_events = db.get_events("in_progress", limit=20)
    events = sorted(
        open_events + progress_events,
        key=lambda e: e["occurred_at"],
        reverse=True
    )

    # 裁示
    pending_decisions = db.get_decisions("pending")
    decided_decisions = db.get_decisions("approved") + db.get_decisions("completed")

    # 歷史快照（供趨勢圖用）
    shelter_history = db.get_snapshots("shelter", 100)
    medical_history = db.get_snapshots("medical", 100)

    return {
        "calc": calc,
        "events": events,
        "decisions": {
            "pending": pending_decisions,
            "decided": sorted(decided_decisions,
                              key=lambda d: d.get("decided_at",""), reverse=True)[:20],
        },
        "shelter_history": shelter_history,
        "medical_history": medical_history,
    }


# ──────────────────────────────────────────
# API：系統狀態
# ──────────────────────────────────────────

# ──────────────────────────────────────────
# API：地圖設定
# ──────────────────────────────────────────

@app.post("/api/map_config", tags=["系統"])
async def save_map_config(request: Request):
    """儲存地圖據點配置（由前端編輯模式呼叫）"""
    body = await request.json()
    config_path = static_path / "map_config.json"
    config_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(config_path)}


@app.get("/api/health", tags=["系統"])
def health():
    """各組 Pi 可 ping 此端點確認指揮部後端存活"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "db": str(db.DB_PATH),
    }


# ──────────────────────────────────────────
# 首頁（開發用）
# ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html><head><meta charset="UTF-8"><title>ICS 指揮部</title></head>
    <body style="font-family:monospace;padding:20px;background:#0a0e1a;color:#9ab0c8">
    <h2 style="color:#fff">ICS 指揮部 command-v0.2.0</h2>
    <p style="margin-top:16px;font-size:12px;color:#6e7b96">儀表板</p>
    <p><a href="/static/staff_v13.html" style="color:#f0883e;font-weight:bold">▶ 儀表板 command-v0.2.0（地圖投影）</a></p>
    <p><a href="/static/staff_v12.html" style="color:#6e7b96">▶ 舊版儀表板 v0.1.0</a></p>
    <p style="margin-top:16px;font-size:12px;color:#6e7b96">工具</p>
    <p><a href="/static/qr_scanner.html" style="color:#90b8e8">▶ QR 快照掃描</a></p>
    <p><a href="/static/manual_input.html" style="color:#90b8e8">▶ 手動輸入</a></p>
    <p style="margin-top:16px;font-size:12px;color:#6e7b96">API</p>
    <p><a href="/docs" style="color:#90b8e8">/docs — Swagger UI</a></p>
    <p><a href="/api/dashboard" style="color:#90b8e8">/api/dashboard — 儀表板資料</a></p>
    <p><a href="/api/health" style="color:#90b8e8">/api/health — 系統狀態</a></p>
    <p><a href="/api/sync/log" style="color:#90b8e8">/api/sync/log — 三 Pass 同步記錄</a></p>
    </body></html>
    """


# ──────────────────────────────────────────
# API：手動輸入記錄（person / patient / vehicle / situation）
# ──────────────────────────────────────────

# 表單 → 目標資料表的對應
FORM_TARGET_MAP = {
    "shelter-intake":  ("S1_入站登記",    "PERSON+SHELTER_PROFILE"),
    "shelter-srt":     ("S2_SRT評估",     "SHELTER_PROFILE"),
    "shelter-cmist":   ("S3_CMIST評估",   "CMIST"),
    "shelter-exit":    ("S4_離站記錄",    "SHELTER_PROFILE"),
    "med-patient":     ("M2_傷患接收",    "MEDICAL_PROFILE"),
    "intel-vehicle":   ("V1_車輛狀態",    "VEHICLE"),
    "intel-situation": ("C1_局勢摘要",    "COMMAND_SUMMARY"),
}


class ManualRecordIn(BaseModel):
    form_id:  str        # e.g. "shelter-intake"
    operator: str
    summary:  str
    payload:  dict       # 完整表單資料
    device_id: Optional[str] = None

    class Config:
        extra = "allow"


@app.post("/api/manual_records", tags=["手動輸入"])
def post_manual_record(body: ManualRecordIn):
    """
    接收 manual_input.html 所有人員/傷患/車輛類表單。
    儲存後等待人工確認同步至最終資料表，或在 PWA 上線後自動補入。
    """
    meta = FORM_TARGET_MAP.get(body.form_id, ("手動輸入", "未知"))
    result = db.create_manual_record({
        "form_id":     body.form_id,
        "form_type":   meta[0],
        "target_table": meta[1],
        "operator":    body.operator,
        "summary":     body.summary,
        "payload":     body.payload,
        "device_id":   body.device_id,
    })
    return result


@app.get("/api/manual_records", tags=["手動輸入"])
def get_manual_records(sync_status: Optional[str] = None, limit: int = 100):
    """取手動輸入記錄列表（供後台審核補同步用）"""
    return db.get_manual_records(sync_status, limit)


@app.patch("/api/manual_records/{record_id}/synced", tags=["手動輸入"])
def mark_synced(record_id: str, operator: str):
    """人工確認同步完成後標記"""
    db.mark_manual_record_synced(record_id, operator)
    return {"ok": True}


# ──────────────────────────────────────────
# API：三 Pass 同步（網路恢復後）
# ──────────────────────────────────────────

@app.post("/api/sync/push", tags=["三 Pass 同步"])
def sync_push(body: SyncPushIn, request: Request):
    """
    各組 Pi 網路恢復後推送斷線期間資料。
    指揮部執行三 Pass 對齊邏輯。

    Pass 1（自動）：SNAPSHOT 去重與補齊
    Pass 2（人工）：手動記錄模糊比對，衝突標記待審核
    Pass 3（自動）：無衝突記錄直接補傳

    回傳：sync_id + 各 Pass 統計 + 待審衝突列表
    """
    operator = request.headers.get("X-Operator", "auto")
    result = db.execute_three_pass(
        source_unit=body.source_unit,
        sync_data=body.model_dump(),
        operator=operator,
    )
    return result


@app.get("/api/sync/log", tags=["三 Pass 同步"])
def get_sync_log(source_unit: Optional[str] = None, limit: int = 20):
    """取同步執行記錄列表"""
    return db.get_sync_log(source_unit, limit)


@app.get("/api/sync/{sync_id}", tags=["三 Pass 同步"])
def get_sync_entry(sync_id: str):
    """取特定同步記錄（含 Pass 2 衝突詳情）"""
    entry = db.get_sync_conflicts(sync_id)
    if not entry:
        raise HTTPException(status_code=404, detail="sync_id not found")
    return entry


@app.post("/api/sync/{sync_id}/resolve", tags=["三 Pass 同步"])
def resolve_conflict(sync_id: str, body: ConflictResolveIn):
    """
    解決 Pass 2 衝突。
    action: keep_incoming / keep_existing / merge
    """
    try:
        return db.resolve_conflict(
            sync_id=sync_id,
            conflict_idx=body.conflict_idx,
            action=body.action,
            operator=body.operator,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
