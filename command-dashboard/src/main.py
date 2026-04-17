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
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from pydantic import BaseModel, Field
from typing import Optional
import json
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone

import asyncio
import db
import calc_engine

# ──────────────────────────────────────────
# App 初始化
# ──────────────────────────────────────────

app = FastAPI(
    title="ICS 指揮部 API",
    version="1.2.0",
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

# ──────────────────────────────────────────
# Session 管理（記憶體，重啟後清空）
# ──────────────────────────────────────────

SESSION_TIMEOUT = 90  # 秒（與 PWA PinLock 一致）
_sessions: dict[str, dict] = {}

# 不需要認證的路徑（精確比對 method + path）
_AUTH_EXEMPT = {
    ("POST", "/api/auth/login"),
    ("GET",  "/api/admin/status"),
    ("GET",  "/api/health"),
    ("POST", "/api/snapshots"),     # 機對機：各組 Pi 推送
    ("POST", "/api/sync/push"),     # 機對機：網路恢復同步
}

# 不需要認證的路徑前綴
_AUTH_EXEMPT_PREFIXES = (
    "/docs", "/openapi.json", "/redoc",   # Swagger UI
    "/static/",                            # 靜態檔案
)


def _validate_session(request: Request) -> dict:
    """驗證 X-Session-Token，回傳 session dict 或拋 401"""
    token = request.headers.get("X-Session-Token")
    if not token or token not in _sessions:
        raise HTTPException(401, "未登入或 session 已過期")
    sess = _sessions[token]
    now = datetime.now(timezone.utc).timestamp()
    if now - sess["last_active"] > SESSION_TIMEOUT:
        _sessions.pop(token, None)
        raise HTTPException(401, "閒置超時，請重新登入")
    sess["last_active"] = now
    return sess


def _validate_admin_pin(request: Request):
    """驗證 X-Admin-PIN header"""
    pin = request.headers.get("X-Admin-PIN")
    if not pin or not db.verify_admin_pin(pin):
        raise HTTPException(403, "管理員 PIN 驗證失敗")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """全域認證中介層"""
    path = request.url.path
    method = request.method

    # 豁免：精確比對
    if (method, path) in _AUTH_EXEMPT:
        return await call_next(request)
    # 豁免：前綴比對
    if any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
        return await call_next(request)
    # 豁免：首頁
    if path == "/":
        return await call_next(request)
    # 豁免：GET /api/snapshots/{node_type}
    if method == "GET" and path.startswith("/api/snapshots/"):
        return await call_next(request)
    # 豁免：admin 端點（用 X-Admin-PIN 驗證，不用 session）
    if path.startswith("/api/admin/"):
        return await call_next(request)
    # 豁免：Pi push（用 Bearer token 驗證，不用 session）
    if path.startswith("/api/pi-push/"):
        return await call_next(request)

    # 其他 /api/ 端點需要 session
    if path.startswith("/api/"):
        token = request.headers.get("X-Session-Token")
        if not token or token not in _sessions:
            return JSONResponse({"detail": "未登入或 session 已過期"}, status_code=401)
        sess = _sessions[token]
        now = datetime.now(timezone.utc).timestamp()
        if now - sess["last_active"] > SESSION_TIMEOUT:
            _sessions.pop(token, None)
            return JSONResponse({"detail": "閒置超時，請重新登入"}, status_code=401)
        sess["last_active"] = now

    return await call_next(request)


# 靜態檔案（前端 HTML）
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# ── Tile server（MBTiles → Leaflet XYZ）──────────────────────────────────────
_MBTILES_DIR = static_path / "tiles"

def _get_tile_db(name: str) -> Path:
    p = _MBTILES_DIR / f"{name}.mbtiles"
    if not p.exists():
        raise HTTPException(404, f"Tile source '{name}' not found")
    return p

@app.get("/tiles/{source}/{z}/{x}/{y}.png", tags=["地圖 Tiles"])
def serve_tile(source: str, z: int, x: int, y: int):
    db_path = _get_tile_db(source)
    tms_y = (2**z - 1) - y  # Leaflet XYZ → MBTiles TMS
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, tms_y)
        ).fetchone()
    if not row:
        raise HTTPException(204, "Tile not found")
    return Response(content=row[0], media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})

@app.get("/tiles/{source}/metadata", tags=["地圖 Tiles"])
def tile_metadata(source: str):
    db_path = _get_tile_db(source)
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT name, value FROM metadata").fetchall()
    return {k: v for k, v in rows}

# CA 根憑證下載（供手機/平板安裝）
cert_path = Path(__file__).parent.parent.parent / "certs" / "rootCA.pem"

@app.get("/cert")
def download_cert():
    if not cert_path.exists():
        raise HTTPException(status_code=404, detail="rootCA.pem 未找到")
    return FileResponse(str(cert_path), filename="rootCA.pem")

@app.get("/cert/install", response_class=HTMLResponse)
def cert_install_page():
    return """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>安裝 CA 憑證</title>
<style>
  body{font-family:-apple-system,sans-serif;max-width:600px;margin:40px auto;padding:0 20px;line-height:1.6}
  h1{font-size:1.4em}
  .btn{display:inline-block;padding:14px 28px;background:#c0392b;color:#fff;text-decoration:none;border-radius:8px;font-size:1.1em;margin:20px 0}
  .step{background:#f5f5f5;padding:12px 16px;margin:8px 0;border-radius:6px}
  .num{font-weight:bold;color:#c0392b}
</style></head><body>
<h1>ICS_DMAS CA 憑證安裝</h1>
<p>安裝此憑證後，裝置才能信任本系統的 HTTPS/WSS 連線。</p>
<a class="btn" href="/cert">下載 CA 憑證</a>
<h2>iOS 安裝步驟</h2>
<div class="step"><span class="num">1.</span> 點擊上方按鈕下載</div>
<div class="step"><span class="num">2.</span> 設定 → 已下載描述檔 → 安裝</div>
<div class="step"><span class="num">3.</span> 設定 → 一般 → 關於本機 → 憑證信任設定 → 開啟信任</div>
<h2>Android 安裝步驟</h2>
<div class="step"><span class="num">1.</span> 點擊上方按鈕下載</div>
<div class="step"><span class="num">2.</span> 設定 → 安全性 → 加密與憑證 → 安裝憑證 → CA 憑證</div>
<div class="step"><span class="num">3.</span> 選擇下載的 rootCA.pem</div>
</body></html>"""

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


VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_UNITS = {"shelter", "medical", "forward", "security", "command"}

class EventIn(BaseModel):
    reported_by_unit:         str
    event_type:               str
    severity:                 str = "info"
    description:              str
    operator_name:            str
    location_desc:            Optional[str] = None
    location_zone_id:         Optional[str] = None
    response_type:            Optional[str] = None
    needs_commander_decision: bool = False
    related_person_name:      Optional[str] = None
    occurred_at:              Optional[str] = None
    session_type:             str = "real"


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


class TTXSessionCreateIn(BaseModel):
    session_name: str
    facilitator: str
    scenario_id: Optional[str] = None


class TTXInjectBulkIn(BaseModel):
    injects: list  # list of dicts with seq, target_unit, type, title, payload, etc.


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
    """建立事件記錄"""
    if ev.severity not in VALID_SEVERITIES:
        raise HTTPException(422, f"severity 必須是 {VALID_SEVERITIES} 之一，收到: {ev.severity}")
    if ev.reported_by_unit not in VALID_UNITS:
        raise HTTPException(422, f"reported_by_unit 必須是 {VALID_UNITS} 之一，收到: {ev.reported_by_unit}")
    result = db.create_event(ev.model_dump(), session_type=ev.session_type)

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
        }, session_type=ev.session_type)

    return result


@app.get("/api/events", tags=["事件"])
def get_events(status: Optional[str] = None, limit: int = 50):
    return db.get_events(status, limit)


@app.patch("/api/events/{event_id}/status", tags=["事件"])
def update_event_status(event_id: str, status: str, operator: str):
    try:
        db.update_event_status(event_id, status, operator)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


class EventNoteIn(BaseModel):
    text: str
    operator: str


@app.post("/api/events/{event_id}/notes", tags=["事件"])
def add_event_note(event_id: str, body: EventNoteIn):
    """追加處置紀錄（對齊 shelter/medical PWA 的 notes 陣列）"""
    try:
        result = db.add_event_note(event_id, body.text, body.operator)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


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
# Wave 4：Pi push records → snapshot 轉換
# ──────────────────────────────────────────

def _pi_batch_to_snapshot(unit_id: str, pushed_at: str, records: list) -> dict | None:
    """從 pi_received_batches 的 records 衍生出 calc_engine 期望的 snapshot dict"""
    if not records:
        return None

    # 按 table_name 分組
    by_table = {}
    for r in records:
        tbl = r.get("table_name", "")
        rec = r.get("record", {})
        if tbl and rec:
            by_table.setdefault(tbl, []).append(rec)

    snap = {
        "snapshot_id": f"pi_derived_{unit_id}_{pushed_at}",
        "snapshot_time": pushed_at,
        "node_type": unit_id,
        "source": "pi_push",
    }

    if unit_id == "medical":
        patients = by_table.get("patients", [])
        # 在場傷患（排除已離區）
        active = [p for p in patients if p.get("current_zone") != "已離區"]
        # 按檢傷燈號計數
        colors = {"red": 0, "yellow": 0, "green": 0, "black": 0}
        for p in active:
            c = p.get("triage_color", "")
            if c in colors:
                colors[c] += 1
        snap["casualties_red"] = colors["red"]
        snap["casualties_yellow"] = colors["yellow"]
        snap["casualties_green"] = colors["green"]
        snap["casualties_black"] = colors["black"]
        snap["bed_used"] = len(active)
        snap["bed_total"] = max(len(active) + 5, 20)  # 預設容量，可從 config 調整
        snap["waiting_count"] = len([p for p in active
                                     if p.get("care_status") == "triaged"
                                     and p.get("disposition", "在場") == "在場"])
        snap["pending_evac"] = len([p for p in active
                                    if p.get("disposition") == "後送"])
        snap["staff_on_duty"] = None
        # 傷患來源分布（source_type: A=前進, B=收容, C=自行）
        all_pts = by_table.get("patients", [])
        src_a = len([p for p in all_pts if p.get("source_type") == "A"])
        src_b = len([p for p in all_pts if p.get("source_type") == "B"])
        src_c = len([p for p in all_pts if p.get("source_type") == "C"])
        snap["extra"] = {"src_a": src_a, "src_b": src_b, "src_c": src_c}

    elif unit_id == "shelter":
        persons = by_table.get("persons", [])
        beds = by_table.get("beds", [])
        # 在站人員
        placed = [p for p in persons if p.get("status") == "已安置"]
        waiting = [p for p in persons if p.get("status") == "等候中"]
        # 床位統計
        total_beds = len(beds) if beds else max(len(placed) + 5, 12)
        snap["bed_used"] = len(placed)
        snap["bed_total"] = total_beds
        snap["pending_intake"] = len(waiting)
        snap["staff_on_duty"] = None
        # SRT 統計
        srt = {"red": 0, "yellow": 0, "green": 0}
        for p in placed:
            c = p.get("srt_color", "")
            if c in srt:
                srt[c] += 1
        snap["extra"] = {"srt": srt}

    # 共用：物資統計
    resources = by_table.get("resources", [])
    if resources:
        supplies = {}
        supplies_max = {}
        for r in resources:
            if r.get("disabled"):
                continue
            name = r.get("name", "")
            # 簡化 key（取前幾個中文字或英文）
            key = name.lower().replace(" ", "_")[:20]
            supplies[key] = r.get("qty_current", 0)
            supplies_max[key] = r.get("qty_initial", 0) or r.get("qty_current", 0)
        extra = snap.get("extra", {}) if isinstance(snap.get("extra"), dict) else {}
        extra["supplies"] = supplies
        extra["supplies_max"] = supplies_max
        snap["extra"] = extra

    # 共用：事件壓力
    incidents = by_table.get("incidents", [])
    if incidents:
        open_incs = [i for i in incidents if i.get("status") not in ("已結案", "closed")]
        sev_count = {"高": 0, "中": 0, "低": 0}
        for i in open_incs:
            s = i.get("severity", "中")
            if s in sev_count:
                sev_count[s] += 1
        ip = {
            "high": sev_count["高"],
            "medium": sev_count["中"],
            "low": sev_count["低"],
            "open_total": len(open_incs),
            "resolved_30min": len([i for i in incidents if i.get("status") in ("已結案", "closed")]),
        }
        extra = snap.get("extra", {}) if isinstance(snap.get("extra"), dict) else {}
        extra["incident_pressure"] = ip
        snap["extra"] = extra

    return snap


# ──────────────────────────────────────────
# API：儀表板整包資料（前端主要 polling 端點）
# ──────────────────────────────────────────

@app.get("/api/dashboard", tags=["儀表板"])
def get_dashboard(session_type: str = "real"):
    """
    前端每 10 秒呼叫一次此端點。
    後端算好所有數字，前端只負責顯示。
    session_type: "real"（預設）或 "exercise"（TTX 演練模式）
    回傳格式：
      {
        calc: { medical, shelter, forward, security, medical_pressure, ... },
        events: [...],
        decisions: { pending: [...], decided: [...] },
        audit_summary: { total_today: int }
      }
    """
    # 取各組最近快照（40 筆供 burn_rate / comm_health 分析）
    medical_snaps  = db.get_snapshots("medical",  40, session_type=session_type)
    shelter_snaps  = db.get_snapshots("shelter",  40, session_type=session_type)
    forward_snaps  = db.get_snapshots("forward",  40, session_type=session_type)
    security_snaps = db.get_snapshots("security", 40, session_type=session_type)

    # Wave 4：從 pi_received_batches 衍生多筆 snapshot 注入（供趨勢分析）
    for _unit in ('shelter', 'medical'):
        _batches = db.get_recent_pi_batches(_unit, 40)
        _pi_snaps = []
        for _batch in _batches:
            _recs = json.loads(_batch['records_json']) if isinstance(_batch['records_json'], str) else _batch['records_json']
            _snap = _pi_batch_to_snapshot(_unit, _batch['pushed_at'], _recs)
            if _snap:
                _pi_snaps.append(_snap)
        if _pi_snaps:
            if _unit == 'shelter':
                shelter_snaps = _pi_snaps + shelter_snaps
            elif _unit == 'medical':
                medical_snaps = _pi_snaps + medical_snaps

    # 事件（先取，供升降級引擎使用）
    open_events     = db.get_events("open",        limit=20, session_type=session_type)
    progress_events = db.get_events("in_progress", limit=20, session_type=session_type)
    resolved_events = db.get_events("resolved",    limit=50, session_type=session_type)

    # 計算引擎（含升降級檢查）
    calc = calc_engine.dashboard_calc(
        medical_snaps, shelter_snaps, forward_snaps, security_snaps,
        open_event_count=len(open_events) + len(progress_events),
        event_trend_up=len(open_events) > 5,
    )
    events = sorted(
        open_events + progress_events + resolved_events,
        key=lambda e: e["occurred_at"],
        reverse=True
    )

    # 裁示
    pending_decisions = db.get_decisions("pending", session_type=session_type)
    decided_decisions = db.get_decisions("approved", session_type=session_type) + db.get_decisions("completed", session_type=session_type)

    # 歷史快照（供趨勢圖用）+ Wave 4 Pi push 衍生歷史 snapshot
    shelter_history = db.get_snapshots("shelter", 100, session_type=session_type)
    medical_history = db.get_snapshots("medical", 100, session_type=session_type)
    for _unit2 in ('shelter', 'medical'):
        _batches2 = db.get_recent_pi_batches(_unit2, 100)
        _pi_hist = []
        for _b2 in _batches2:
            _r2 = json.loads(_b2['records_json']) if isinstance(_b2['records_json'], str) else _b2['records_json']
            _s2 = _pi_batch_to_snapshot(_unit2, _b2['pushed_at'], _r2)
            if _s2:
                _pi_hist.append(_s2)
        if _pi_hist:
            if _unit2 == 'shelter':
                shelter_history = _pi_hist + shelter_history
            elif _unit2 == 'medical':
                medical_history = _pi_hist + medical_history

    # 地圖事件（有 location_zone_id 且未結案）
    open_events_on_map = [
        e for e in events if e.get("location_zone_id")
    ]

    # Decision chain grouping（按 primary_event_id 分組）
    all_decisions = db.get_decisions(session_type=session_type)  # 全部
    chains = {}
    for dec in all_decisions:
        key = dec.get("primary_event_id") or dec["id"]
        if key not in chains:
            chains[key] = []
        chains[key].append(dec)

    return {
        "calc": calc,
        "events": events,
        "open_events_on_map": open_events_on_map,
        "decisions": {
            "pending": pending_decisions,
            "decided": sorted(decided_decisions,
                              key=lambda d: d.get("decided_at",""), reverse=True)[:20],
            "chains": chains,
        },
        "shelter_history": shelter_history,
        "medical_history": medical_history,
        "pi_nodes": db.list_pi_nodes(),
    }


# ──────────────────────────────────────────
# API：人員清單（各組 Pi 推送在 snapshot extra.staff_list）
# ──────────────────────────────────────────

@app.get("/api/staff", tags=["人員"])
def get_staff():
    """
    從各組最新快照的 extra.staff_list 取得人員清單。
    各組 Pi 推送時將值勤人員列表放在 snapshot extra 內。
    回傳 { shelter: [...], medical: [...], forward: [...], security: [...] }
    """
    result = {}
    for node_type in ("shelter", "medical", "forward", "security"):
        snap = db.get_latest_snapshot(node_type)
        if snap:
            extra = snap.get("extra") or {}
            staff_list = extra.get("staff_list", [])
            result[node_type] = {
                "staff": staff_list,
                "staff_on_duty": snap.get("staff_on_duty"),
                "snapshot_time": snap.get("snapshot_time"),
            }
        else:
            result[node_type] = {"staff": [], "staff_on_duty": None, "snapshot_time": None}
    return result


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
        "version": "1.1.0",
        "db": str(db.DB_PATH),
    }


# ──────────────────────────────────────────
# API：認證
# ──────────────────────────────────────────

class LoginIn(BaseModel):
    username: str
    pin: str


@app.post("/api/auth/login", tags=["認證"])
def auth_login(body: LoginIn):
    """驗證帳密，建立 session"""
    acct = db.verify_login(body.username, body.pin)
    if not acct:
        raise HTTPException(401, "帳號或 PIN 錯誤")
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).timestamp()
    _sessions[session_id] = {
        "username": acct["username"],
        "role": acct["role"],
        "role_detail": acct.get("role_detail"),
        "display_name": acct.get("display_name") or acct["username"],
        "login_time": now,
        "last_active": now,
    }
    db._audit(acct["username"], None, "login", "accounts", acct["username"],
              {"role": acct["role"], "role_detail": acct.get("role_detail")})
    return {
        "ok": True,
        "session_id": session_id,
        "username": acct["username"],
        "role": acct["role"],
        "role_detail": acct.get("role_detail"),
        "display_name": acct.get("display_name") or acct["username"],
    }


@app.post("/api/auth/logout", tags=["認證"])
def auth_logout(request: Request):
    """銷毀 session"""
    token = request.headers.get("X-Session-Token")
    sess = _sessions.pop(token, None)
    if sess:
        db._audit(sess["username"], None, "logout", "accounts", sess["username"], {})
    return {"ok": True}


@app.get("/api/auth/heartbeat", tags=["認證"])
def auth_heartbeat(request: Request):
    """觸碰 session，回傳剩餘秒數"""
    sess = _validate_session(request)
    now = datetime.now(timezone.utc).timestamp()
    remaining = max(0, SESSION_TIMEOUT - (now - sess["last_active"]))
    return {"ok": True, "remaining": remaining, "username": sess["username"],
            "role": sess["role"], "role_detail": sess.get("role_detail")}


@app.get("/api/auth/me", tags=["認證"])
def auth_me(request: Request):
    """取得目前登入者資訊"""
    sess = _validate_session(request)
    return {
        "username": sess["username"],
        "role": sess["role"],
        "role_detail": sess.get("role_detail"),
        "display_name": sess["display_name"],
    }


# ──────────────────────────────────────────
# API：帳號管理（Admin PIN 驗證）
# ──────────────────────────────────────────

class AccountCreateIn(BaseModel):
    username: str
    pin: str
    role: str = "操作員"
    role_detail: Optional[str] = None
    display_name: Optional[str] = None


class AccountStatusIn(BaseModel):
    status: str  # active / suspended


class PinResetIn(BaseModel):
    new_pin: str


class AdminPinIn(BaseModel):
    new_pin: str


@app.get("/api/admin/status", tags=["帳號管理"])
def admin_status():
    """檢查 admin PIN 是否已設定（首次啟動引導用）"""
    raw = db.get_config("admin_pin")
    with db.get_conn() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    return {"admin_pin_setup": raw is not None, "active_accounts": cnt}


@app.get("/api/admin/accounts", tags=["帳號管理"])
def admin_list_accounts(request: Request):
    """列出所有帳號"""
    _validate_admin_pin(request)
    return db.get_all_accounts()


@app.post("/api/admin/accounts", tags=["帳號管理"])
def admin_create_account(body: AccountCreateIn, request: Request):
    """新增帳號"""
    _validate_admin_pin(request)
    if body.role not in ("指揮官", "操作員"):
        raise HTTPException(422, "role 必須是 指揮官 或 操作員")
    if len(body.pin) < 4 or len(body.pin) > 6 or not body.pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    try:
        return db.create_account(body.username, body.pin, body.role,
                                 body.display_name, body.role_detail)
    except Exception as e:
        raise HTTPException(409, f"帳號建立失敗：{e}")


@app.delete("/api/admin/accounts/{username}", tags=["帳號管理"])
def admin_delete_account(username: str, request: Request):
    """刪除帳號"""
    _validate_admin_pin(request)
    if not db.delete_account(username, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@app.put("/api/admin/accounts/{username}/status", tags=["帳號管理"])
def admin_update_status(username: str, body: AccountStatusIn, request: Request):
    """停用/啟用帳號"""
    _validate_admin_pin(request)
    if body.status not in ("active", "suspended"):
        raise HTTPException(422, "status 必須是 active 或 suspended")
    if not db.update_account_status(username, body.status, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@app.put("/api/admin/accounts/{username}/pin", tags=["帳號管理"])
def admin_reset_pin(username: str, body: PinResetIn, request: Request):
    """重設 PIN"""
    _validate_admin_pin(request)
    if len(body.new_pin) < 4 or len(body.new_pin) > 6 or not body.new_pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    if not db.update_account_pin(username, body.new_pin, "admin"):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


class RoleUpdateIn(BaseModel):
    role: str
    role_detail: Optional[str] = None


@app.put("/api/admin/accounts/{username}/role", tags=["帳號管理"])
def admin_update_role(username: str, body: RoleUpdateIn, request: Request):
    """變更角色（role + role_detail）"""
    _validate_admin_pin(request)
    if body.role not in ("指揮官", "操作員"):
        raise HTTPException(422, "role 必須是 指揮官 或 操作員")
    if not db.update_account_role(username, body.role, "admin", body.role_detail):
        raise HTTPException(404, "帳號不存在")
    return {"ok": True}


@app.post("/api/admin/reset-db", tags=["系統"])
def admin_reset_db(request: Request):
    """重設指揮部資料庫（清除快照、事件、Pi 批次等，保留帳號和 admin PIN）"""
    _validate_admin_pin(request)
    tables = ["snapshots", "events", "decisions", "predictions",
              "manual_records", "sync_log", "pi_received_batches", "audit_log"]
    with db.get_conn() as conn:
        for t in tables:
            try:
                conn.execute(f"DELETE FROM {t}")
            except Exception:
                pass
    db._audit("admin", None, "db_reset", None, None, {"tables": tables})
    return {"ok": True, "cleared_tables": tables}


@app.post("/api/admin/reset-exercise", tags=["系統"])
def admin_reset_exercise(request: Request):
    """清除所有演練資料（session_type='exercise'），保留實戰資料"""
    _validate_session(request)
    data_tables = ["snapshots", "events", "decisions", "predictions",
                   "manual_records", "audit_log"]
    cleared = {}
    with db.get_conn() as conn:
        for t in data_tables:
            try:
                cur = conn.execute(f"DELETE FROM {t} WHERE session_type = 'exercise'")
                cleared[t] = cur.rowcount
            except Exception:
                pass
        # TTX 專用表：全部清除（本身就是演練資料）
        for t in ["ttx_injects", "ttx_sessions"]:
            try:
                cur = conn.execute(f"DELETE FROM {t}")
                cleared[t] = cur.rowcount
            except Exception:
                pass
    db._audit("admin", None, "exercise_reset", None, None, {"cleared": cleared})
    return {"ok": True, "cleared": cleared}


@app.post("/api/admin/suspend-all", tags=["帳號管理"])
def admin_suspend_all(request: Request):
    """緊急停用所有帳號"""
    _validate_admin_pin(request)
    count = db.suspend_all_accounts("admin")
    return {"ok": True, "suspended_count": count}


@app.get("/api/admin/audit-log", tags=["帳號管理"])
def admin_audit_log(request: Request, limit: int = 100):
    """稽核日誌（Admin PIN 驗證）"""
    _validate_admin_pin(request)
    return db.get_audit_log(limit)


@app.put("/api/admin/pin", tags=["帳號管理"])
def admin_change_pin(body: AdminPinIn, request: Request):
    """變更 Admin PIN"""
    _validate_admin_pin(request)
    if len(body.new_pin) < 4 or len(body.new_pin) > 6 or not body.new_pin.isdigit():
        raise HTTPException(422, "PIN 必須是 4-6 位數字")
    db.set_admin_pin(body.new_pin, "admin")
    return {"ok": True}


# ──────────────────────────────────────────
# Wave 4：Pi 節點管理（Admin PIN 驗證）
# ──────────────────────────────────────────

class PiNodeCreateIn(BaseModel):
    unit_id: str
    label: str


@app.get("/api/admin/pi-nodes", tags=["Pi 節點"])
def admin_list_pi_nodes(request: Request):
    """列出所有 Pi 節點"""
    _validate_admin_pin(request)
    return db.list_pi_nodes()


@app.post("/api/admin/pi-nodes", tags=["Pi 節點"])
def admin_create_pi_node(body: PiNodeCreateIn, request: Request):
    """註冊新 Pi 節點，回傳完整 API key（僅此一次）"""
    _validate_admin_pin(request)
    allowed = ("shelter", "medical", "forward", "security")
    if body.unit_id not in allowed:
        raise HTTPException(422, f"unit_id 必須是 {allowed} 之一")
    try:
        return db.create_pi_node(body.unit_id, body.label)
    except Exception as e:
        if "UNIQUE" in str(e) or "PRIMARY" in str(e):
            raise HTTPException(409, f"unit_id '{body.unit_id}' 已存在")
        raise


@app.delete("/api/admin/pi-nodes/{unit_id}", tags=["Pi 節點"])
def admin_delete_pi_node(unit_id: str, request: Request):
    """刪除 Pi 節點"""
    _validate_admin_pin(request)
    if not db.delete_pi_node(unit_id):
        raise HTTPException(404, "Pi 節點不存在")
    return {"ok": True}


@app.post("/api/admin/pi-nodes/{unit_id}/rekey", tags=["Pi 節點"])
def admin_rekey_pi_node(unit_id: str, request: Request):
    """重新產生 API key（舊 key 立即失效）"""
    _validate_admin_pin(request)
    result = db.revoke_pi_node_key(unit_id)
    if not result:
        raise HTTPException(404, "Pi 節點不存在")
    return result


# ──────────────────────────────────────────
# Wave 4：Pi Push 接收端（Bearer token 驗證）
# ──────────────────────────────────────────

@app.post("/api/pi-push/{unit_id}", tags=["Pi 推送"])
async def receive_pi_push(unit_id: str, request: Request):
    """各組 Pi 定時推送 current_state"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "缺少 Bearer token")
    token = auth_header[7:]
    if not db.validate_pi_push(unit_id, token):
        raise HTTPException(403, "API 金鑰驗證失敗或 unit_id 不符")

    body = await request.json()
    records = body.get("records", [])
    pushed_at = body.get("pushed_at", "")
    if not pushed_at:
        from datetime import datetime, timezone
        pushed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # heartbeat（無資料）：只更新 last_seen_at，不寫 batch
    if not records or body.get("heartbeat"):
        db.touch_pi_node(unit_id)
        return {"ok": True, "heartbeat": True}

    batch_id = db.insert_pi_batch(
        unit_id=unit_id,
        pushed_at=pushed_at,
        records_json=json.dumps(records, ensure_ascii=False),
    )
    return {"ok": True, "batch_id": batch_id, "records_count": len(records)}


# ──────────────────────────────────────────
# Wave 4：Pi 資料查詢（L3，Session 驗證）
# ──────────────────────────────────────────

@app.get("/api/pi-data/{unit_id}/list", tags=["Pi 資料"])
def get_pi_data_list(unit_id: str, request: Request):
    """取得某組最新 Pi 推送的記錄列表（L3 層級）"""
    _validate_session(request)
    batch = db.get_latest_pi_batch(unit_id)
    if not batch:
        return {"records": [], "grouped": {}, "pushed_at": None, "received_at": None, "offline": True}

    records = json.loads(batch["records_json"]) if isinstance(batch["records_json"], str) else batch["records_json"]

    # 按 table_name 分組
    grouped = {}
    for r in records:
        tbl = r.get("table_name", "unknown")
        if tbl not in grouped:
            grouped[tbl] = []
        grouped[tbl].append(r)

    return {
        "records": records,
        "grouped": grouped,
        "pushed_at": batch["pushed_at"],
        "received_at": batch["received_at"],
        "offline": False,
    }


# ──────────────────────────────────────────
# API：系統設定（指揮官限定）
# ──────────────────────────────────────────

class ConfigIn(BaseModel):
    value: str


@app.get("/api/config/{key}", tags=["系統設定"])
def get_config(key: str, request: Request):
    """取得設定值"""
    sess = _validate_session(request)
    if key == "admin_pin":
        raise HTTPException(403, "不可讀取 admin_pin")
    val = db.get_config(key)
    return {"key": key, "value": val}


@app.post("/api/config/{key}", tags=["系統設定"])
def set_config(key: str, body: ConfigIn, request: Request):
    """設定值（僅指揮官）"""
    sess = _validate_session(request)
    if sess["role"] != "指揮官":
        raise HTTPException(403, "僅指揮官可修改設定")
    if key == "admin_pin":
        raise HTTPException(403, "請使用 /api/admin/pin 變更管理員 PIN")
    db.set_config(key, body.value, sess["username"])
    return {"ok": True}


# ──────────────────────────────────────────
# 首頁（開發用）
# ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html><head><meta charset="UTF-8"><title>ICS 指揮部</title></head>
    <body style="font-family:monospace;padding:20px;background:#0a0e1a;color:#9ab0c8">
    <h2 style="color:#fff">ICS 指揮部 command-v0.8.0</h2>
    <p style="margin-top:16px;font-size:12px;color:#6e7b96">儀表板</p>
    <p><a href="/static/commander_dashboard.html" style="color:#f0883e;font-weight:bold">▶ 儀表板 command-v0.8.0</a></p>
    <p style="margin-top:16px;font-size:12px;color:#6e7b96">工具</p>
    <p><a href="/static/qr_scanner.html" style="color:#90b8e8">▶ QR 快照掃描</a></p>
    <p style="margin-top:16px;font-size:12px;color:#6e7b96">API</p>
    <p><a href="/docs" style="color:#90b8e8">/docs — Swagger UI</a></p>
    <p><a href="/api/health" style="color:#90b8e8">/api/health — 系統狀態</a></p>
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


# ──────────────────────────────────────────
# API：TTX 演練
# ──────────────────────────────────────────

@app.post("/api/ttx/sessions", tags=["TTX"])
def ttx_create_session(body: TTXSessionCreateIn, request: Request):
    """建立演練場次"""
    _validate_session(request)
    return db.create_ttx_session(body.session_name, body.facilitator, body.scenario_id)


@app.get("/api/ttx/sessions", tags=["TTX"])
def ttx_list_sessions(request: Request):
    """列出所有演練場次"""
    _validate_session(request)
    return db.list_ttx_sessions()


@app.get("/api/ttx/sessions/{session_id}", tags=["TTX"])
def ttx_get_session(session_id: str, request: Request):
    """取得單一場次"""
    _validate_session(request)
    result = db.get_ttx_session(session_id)
    if not result:
        raise HTTPException(404, "TTX session 不存在")
    return result


@app.post("/api/ttx/sessions/{session_id}/start", tags=["TTX"])
def ttx_start_session(session_id: str, request: Request):
    """開始演練"""
    sess = _validate_session(request)
    if not db.update_ttx_session_status(session_id, "running", sess["username"]):
        raise HTTPException(404, "TTX session 不存在")
    return {"ok": True}


@app.post("/api/ttx/sessions/{session_id}/pause", tags=["TTX"])
def ttx_pause_session(session_id: str, request: Request):
    """暫停演練"""
    sess = _validate_session(request)
    if not db.update_ttx_session_status(session_id, "paused", sess["username"]):
        raise HTTPException(404, "TTX session 不存在")
    return {"ok": True}


@app.post("/api/ttx/sessions/{session_id}/end", tags=["TTX"])
def ttx_end_session(session_id: str, request: Request):
    """結束演練"""
    sess = _validate_session(request)
    if not db.update_ttx_session_status(session_id, "completed", sess["username"]):
        raise HTTPException(404, "TTX session 不存在")
    return {"ok": True}


@app.get("/api/ttx/sessions/{session_id}/injects", tags=["TTX"])
def ttx_list_injects(session_id: str, request: Request):
    """列出場次所有 injects"""
    _validate_session(request)
    return db.get_ttx_injects(session_id)


@app.post("/api/ttx/sessions/{session_id}/injects", tags=["TTX"])
def ttx_bulk_injects(session_id: str, body: TTXInjectBulkIn, request: Request):
    """批次匯入 injects"""
    _validate_session(request)
    ttx = db.get_ttx_session(session_id)
    if not ttx:
        raise HTTPException(404, "TTX session 不存在")
    count = db.bulk_create_ttx_injects(session_id, body.injects)
    return {"ok": True, "imported": count}


@app.post("/api/ttx/sessions/{session_id}/inject/{inject_id}/push", tags=["TTX"])
def ttx_push_inject(session_id: str, inject_id: str, request: Request,
                    live: bool = False):
    """執行單一 inject。live=true 時用當前 UTC 時間取代固定時間戳。"""
    sess = _validate_session(request)
    injects = db.get_ttx_injects(session_id)
    inject = next((i for i in injects if i["id"] == inject_id), None)
    if not inject:
        raise HTTPException(404, "Inject 不存在")
    if inject["status"] != "pending":
        raise HTTPException(409, f"Inject 已執行（status={inject['status']}）")

    payload = inject["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    inject_type = inject["inject_type"]
    results = []

    # live 模式：用當前時間取代固定時間戳
    if live:
        _live_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if "t" in payload:
            payload["t"] = _live_now
        if "snapshot_id" in payload:
            payload["snapshot_id"] = f"live-{inject_id[:8]}-{int(datetime.now(timezone.utc).timestamp())}"
        # forward units 的 last_update
        for u in payload.get("extra", {}).get("units", []):
            if "last_update" in u:
                u["last_update"] = _live_now

    # snapshot payload 的 type → node_type 映射（與 post_snapshot 一致）
    def _map_snapshot_payload(p):
        _type_map = {"snapshot_shelter":"shelter","snapshot_medical":"medical",
                     "snapshot_forward":"forward","snapshot_security":"security",
                     "shelter":"shelter","medical":"medical","forward":"forward","security":"security"}
        if "node_type" not in p and "type" in p:
            p["node_type"] = _type_map.get(p["type"], p["type"])
        return p

    if inject_type == "snapshot":
        r = db.upsert_snapshot(_map_snapshot_payload(payload), session_type="exercise")
        results.append({"type": "snapshot", "result": r})
    elif inject_type == "event":
        event_data = {
            "reported_by_unit": payload.get("reported_by_unit", inject["target_unit"]),
            "event_type": payload.get("event_type", "ttx_inject"),
            "severity": payload.get("severity", "info"),
            "description": payload.get("description", inject["title"]),
            "operator_name": payload.get("operator_name", sess["username"]),
            "location_desc": payload.get("location_desc"),
            "location_zone_id": payload.get("location_zone_id"),
            "needs_commander_decision": payload.get("needs_commander_decision", 0),
        }
        r = db.create_event(event_data, session_type="exercise")
        results.append({"type": "event", "result": r})
    elif inject_type == "decision":
        decision_data = {
            "decision_type": payload.get("decision_type", "initial"),
            "severity": payload.get("severity", "warning"),
            "decision_title": payload.get("decision_title", inject["title"]),
            "impact_description": payload.get("impact_description", ""),
            "suggested_action_a": payload.get("suggested_action_a", ""),
            "suggested_action_b": payload.get("suggested_action_b"),
            "created_by": payload.get("created_by", sess["username"]),
            "primary_event_id": payload.get("primary_event_id"),
        }
        r = db.create_decision(decision_data, session_type="exercise")
        results.append({"type": "decision", "result": r})
    elif inject_type == "compound":
        # payload 是子項目列表
        items = payload if isinstance(payload, list) else payload.get("items", [])
        for item in items:
            sub_type = item.get("type", "snapshot")
            sub_payload = item.get("payload", item)
            if sub_type == "snapshot":
                r = db.upsert_snapshot(_map_snapshot_payload(sub_payload), session_type="exercise")
                results.append({"type": "snapshot", "result": r})
            elif sub_type == "event":
                sub_event_data = {
                    "reported_by_unit": sub_payload.get("reported_by_unit", "system"),
                    "event_type": sub_payload.get("event_type", "ttx_inject"),
                    "severity": sub_payload.get("severity", "info"),
                    "description": sub_payload.get("description", ""),
                    "operator_name": sub_payload.get("operator_name", sess["username"]),
                }
                r = db.create_event(sub_event_data, session_type="exercise")
                results.append({"type": "event", "result": r})

    # 標記 inject 已執行
    db.mark_ttx_inject_done(inject_id, sess["username"])
    return {"ok": True, "inject_id": inject_id, "results": results}


# ──────────────────────────────────────────
# API：TTX 預建情境
# ──────────────────────────────────────────

@app.get("/api/ttx/scenarios", tags=["TTX"])
def ttx_list_scenarios(request: Request):
    """列出可用預建情境"""
    _validate_session(request)
    import glob
    import os
    scenario_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios")
    if not os.path.isdir(scenario_dir):
        return []
    files = sorted(glob.glob(os.path.join(scenario_dir, "*.json")))
    result = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.loads(fh.read())
            result.append({
                "id": data.get("id", os.path.basename(f).replace(".json", "")),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "duration_min": data.get("duration_min"),
                "inject_count": len(data.get("injects", [])),
            })
        except Exception:
            pass
    return result


@app.post("/api/ttx/scenarios/{scenario_id}/load", tags=["TTX"])
def ttx_load_scenario(scenario_id: str, request: Request):
    """載入預建情境到新 session"""
    sess = _validate_session(request)
    import os
    scenario_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios")
    fpath = os.path.join(scenario_dir, f"{scenario_id}.json")
    if not os.path.isfile(fpath):
        raise HTTPException(404, f"情境 {scenario_id} 不存在")
    with open(fpath, "r", encoding="utf-8") as fh:
        data = json.loads(fh.read())
    # 建立 session
    ttx = db.create_ttx_session(
        name=data.get("name", scenario_id),
        facilitator=sess["username"],
        scenario_id=scenario_id,
    )
    # 批次匯入 injects
    count = db.bulk_create_ttx_injects(ttx["id"], data.get("injects", []))
    return {"ok": True, "session": ttx, "injects_loaded": count}
