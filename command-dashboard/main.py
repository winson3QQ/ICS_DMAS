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

# CORS：允許同區網所有裝置（各組 Pi、iPad）存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # 區網內不需要限制 origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態檔案（前端 HTML）
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# 啟動時建立 DB
@app.on_event("startup")
def startup():
    db.init_db()
    print("✓ ICS 後端啟動，資料庫已初始化")


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
    # 取各組最近快照
    medical_snaps  = db.get_snapshots("medical",  20)
    shelter_snaps  = db.get_snapshots("shelter",  20)
    forward_snaps  = db.get_snapshots("forward",  20)
    security_snaps = db.get_snapshots("security", 20)

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

    return {
        "calc": calc,
        "events": events,
        "decisions": {
            "pending": pending_decisions,
            "decided": sorted(decided_decisions,
                              key=lambda d: d.get("decided_at",""), reverse=True)[:20],
        },
    }


# ──────────────────────────────────────────
# API：系統狀態
# ──────────────────────────────────────────

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
    <body style="font-family:monospace;padding:20px;background:#1a2535;color:#9ab0c8">
    <h2 style="color:#fff">ICS 指揮部後端 v1.0</h2>
    <p>API 文件：<a href="/docs" style="color:#90b8e8">/docs</a></p>
    <p>儀表板資料：<a href="/api/dashboard" style="color:#90b8e8">/api/dashboard</a></p>
    <p>系統狀態：<a href="/api/health" style="color:#90b8e8">/api/health</a></p>
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
