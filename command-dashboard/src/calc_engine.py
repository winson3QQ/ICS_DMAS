"""
calc_engine.py — ICS 計算引擎
實作規格第六部分（6.2～6.5）

所有函式都是純函式（pure function），輸入快照列表，輸出計算結果。
不直接讀資料庫，由 main.py 傳入資料。
"""

from datetime import datetime, timezone
from typing import Optional


# ──────────────────────────────────────────
# 門檻預設值（規格 6.5）
# 可由外部 threshold_settings 覆蓋
# ──────────────────────────────────────────

DEFAULT_THRESHOLDS = {
    "medical": {
        "bed_usage_yellow": 0.70,   # 70%
        "bed_usage_red":    0.90,   # 90%
        "red_casualties_yellow": 1,
        "red_casualties_red":    2,
        "waiting_yellow": 3,
        "waiting_red":    6,
        "supply_yellow":  0.30,     # 剩餘 30%
        "supply_red":     0.10,     # 剩餘 10%
        "freshness_warn_min":  3,   # 分鐘
        "freshness_crit_min":  5,
        "lkp_min":            10,
    },
    "shelter": {
        "bed_usage_yellow": 0.70,
        "bed_usage_red":    0.90,
        "pending_intake_yellow": 5,
        "pending_intake_red":   10,
        "srt_red_yellow": 3,
        "srt_red_red":    6,
        "freshness_warn_min": 3,
        "freshness_crit_min": 5,
        "lkp_min":           10,
    },
    "forward": {
        "red_per_team_yellow": 1,
        "red_per_team_red":    2,
        "freshness_warn_min":  5,
        "freshness_crit_min": 10,   # 10分→LKP
        "lkp_min":            10,
    },
    "security": {
        "freshness_warn_min": 3,
        "freshness_crit_min": 5,
        "lkp_min":           10,
    },
}

# 最小快照跨度（分鐘），才能計算趨勢
MIN_SPAN_FOR_TREND = 10


# ──────────────────────────────────────────
# 時間工具
# ──────────────────────────────────────────

def _parse_dt(s: str) -> datetime:
    """解析 ISO 8601 UTC 字串"""
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def minutes_ago(dt_str: str) -> float:
    """距離現在幾分鐘（正數 = 過去）"""
    try:
        dt = _parse_dt(dt_str)
        delta = _now_utc() - dt
        return delta.total_seconds() / 60
    except Exception:
        return 999.0


# ──────────────────────────────────────────
# 6.5 新鮮度（Freshness）
# ──────────────────────────────────────────

def freshness(snapshot_time: str, node_type: str = "medical",
              thresholds: dict = None) -> dict:
    """
    回傳 {level: 'ok'|'warn'|'crit'|'lkp', minutes: float, label: str}
    """
    th = (thresholds or DEFAULT_THRESHOLDS).get(node_type,
          DEFAULT_THRESHOLDS["medical"])
    mins = minutes_ago(snapshot_time)

    lkp_min  = th.get("lkp_min", 10)
    crit_min = th.get("freshness_crit_min", 5)
    warn_min = th.get("freshness_warn_min", 3)

    if mins >= lkp_min:
        level = "lkp"
        label = f"LKP {int(mins)}分"
    elif mins >= crit_min:
        level = "crit"
        label = f"逾時 {int(mins)}分"
    elif mins >= warn_min:
        level = "warn"
        label = f"{int(mins)}分前"
    else:
        level = "ok"
        label = "即時"

    return {"level": level, "minutes": round(mins, 1), "label": label}


# ──────────────────────────────────────────
# 6.2 趨勢計算
# ──────────────────────────────────────────

def trend(snapshots: list[dict], field: str,
          thresholds: dict = None) -> dict:
    """
    趨勢速率 = (現值 - N分前值) ÷ N
    輸入：依時間倒序的快照列表（最新在前）
    回傳：
      {
        rate: float | None,        # 每分鐘變化量
        direction: 'up'|'down'|'flat'|None,
        current: float | None,
        confidence: 'high'|'medium'|'low'|'insufficient',
        span_min: float,           # 使用的快照跨度
        note: str
      }
    """
    if not snapshots:
        return _no_trend("無快照資料")

    # 篩掉 field 為 None 的快照
    valid = [s for s in snapshots if s.get(field) is not None]
    if len(valid) < 2:
        return _no_trend("快照數量不足（需 ≥ 2 筆有效值）")

    newest = valid[0]
    oldest = valid[-1]

    span_min = _span_minutes(oldest["snapshot_time"], newest["snapshot_time"])
    if span_min < MIN_SPAN_FOR_TREND:
        # 資料存在但跨度不足，顯示但標低信心度
        rate = (newest[field] - oldest[field]) / max(span_min, 0.1)
        return {
            "rate": round(rate, 2),
            "direction": _direction(rate),
            "current": newest[field],
            "confidence": "low",
            "span_min": round(span_min, 1),
            "note": f"快照跨度 {round(span_min,1)} 分鐘（< {MIN_SPAN_FOR_TREND} 分），信心度低"
        }

    rate = (newest[field] - oldest[field]) / span_min
    conf = "high" if span_min >= 30 else "medium"
    return {
        "rate": round(rate, 2),
        "direction": _direction(rate),
        "current": newest[field],
        "confidence": conf,
        "span_min": round(span_min, 1),
        "note": f"依據 {len(valid)} 筆快照，跨度 {round(span_min,1)} 分鐘"
    }


def _direction(rate: float) -> str:
    if rate > 0.05:
        return "up"
    elif rate < -0.05:
        return "down"
    return "flat"


def _no_trend(note: str) -> dict:
    return {
        "rate": None, "direction": None, "current": None,
        "confidence": "insufficient", "span_min": 0, "note": note
    }


def _span_minutes(older_dt_str: str, newer_dt_str: str) -> float:
    try:
        older = _parse_dt(older_dt_str)
        newer = _parse_dt(newer_dt_str)
        return (newer - older).total_seconds() / 60
    except Exception:
        return 0.0


# ──────────────────────────────────────────
# 6.4 警戒倒數計算
# ──────────────────────────────────────────

def countdown(snapshots: list[dict], field: str,
              threshold_value: float,
              node_type: str = "medical") -> dict:
    """
    預計到達門檻時間 = (門檻值 - 現值) ÷ 趨勢速率
    回傳：
      {
        minutes_to_threshold: float | None,
        label: str,
        confidence: str,
        already_breached: bool
      }
    """
    t = trend(snapshots, field)

    if t["current"] is None:
        return {"minutes_to_threshold": None, "label": "資料不足",
                "confidence": "insufficient", "already_breached": False}

    current = t["current"]
    if current >= threshold_value:
        return {"minutes_to_threshold": 0, "label": "已超門檻",
                "confidence": t["confidence"], "already_breached": True}

    if t["rate"] is None or t["rate"] <= 0:
        return {"minutes_to_threshold": None, "label": "趨勢穩定或下降，無倒數",
                "confidence": t["confidence"], "already_breached": False}

    mins = (threshold_value - current) / t["rate"]
    mins = round(mins, 1)

    if t["confidence"] == "insufficient":
        label = "資料不足"
    elif t["confidence"] == "low":
        label = f"≈{int(mins)}分（信心度低）"
    else:
        label = f"{int(mins)}分鐘後達門檻"

    return {
        "minutes_to_threshold": mins,
        "label": label,
        "confidence": t["confidence"],
        "already_breached": False
    }


# ──────────────────────────────────────────
# 6.3 醫療壓力指數
# ──────────────────────────────────────────

def medical_pressure_index(
    medical_snap:  dict | None,
    shelter_snap:  dict | None,
    forward_snap:  dict | None,
    security_snap: dict | None,
    coefficients:  dict = None,
) -> dict:
    """
    MPI = (等待÷床位剩餘) + (前進傷患×0.8) + (收容升級×0.3) + (安全事件×0.1)
    規格 6.3
    """
    coef = coefficients or {
        "forward":  0.8,
        "shelter":  0.3,
        "security": 0.1,
    }

    components = {}

    # ① 等待壓力：等待÷床位剩餘
    if medical_snap:
        waiting   = medical_snap.get("waiting_count") or 0
        bed_used  = medical_snap.get("bed_used")  or 0
        bed_total = medical_snap.get("bed_total") or 10
        remaining = max(bed_total - bed_used, 1)  # 避免除以零
        wait_pressure = waiting / remaining
        components["waiting"] = round(wait_pressure, 2)
    else:
        components["waiting"] = 0

    # ② 前進組傷患壓力
    if forward_snap:
        extra = forward_snap.get("extra") or {}
        units = extra.get("units", [])
        if units:
            # 多小隊：加總
            fwd_red = sum(u.get("casualties", {}).get("red", 0) for u in units)
        else:
            fwd_red = forward_snap.get("casualties_red") or 0
        components["forward"] = round(fwd_red * coef["forward"], 2)
    else:
        components["forward"] = 0

    # ③ 收容組 SRT 升級壓力
    if shelter_snap:
        extra = shelter_snap.get("extra") or {}
        srt   = extra.get("srt", {})
        srt_red = srt.get("red", 0) if srt else 0
        components["shelter"] = round(srt_red * coef["shelter"], 2)
    else:
        components["shelter"] = 0

    # ④ 安全事件密度（以隔離人數近似）
    if security_snap:
        extra = security_snap.get("extra") or {}
        iso   = extra.get("isolation_count", 0) or 0
        components["security"] = round(iso * coef["security"], 2)
    else:
        components["security"] = 0

    total = sum(components.values())

    # 判斷等級
    if total >= 3.0:
        level = "critical"
    elif total >= 1.5:
        level = "warning"
    else:
        level = "normal"

    return {
        "index": round(total, 2),
        "level": level,
        "components": components,
        "note": (
            f"等待壓力 {components['waiting']} + "
            f"前進 {components['forward']} + "
            f"收容 {components['shelter']} + "
            f"安全 {components['security']}"
        )
    }


# ──────────────────────────────────────────
# 整合：產生儀表板所需的所有計算結果
# ──────────────────────────────────────────

def dashboard_calc(
    medical_snaps:  list[dict],
    shelter_snaps:  list[dict],
    forward_snaps:  list[dict],
    security_snaps: list[dict],
    thresholds: dict = None,
) -> dict:
    """
    一次計算所有儀表板需要的數字。
    main.py 呼叫這個函式，回傳給前端。
    """
    th = thresholds or DEFAULT_THRESHOLDS

    med  = medical_snaps[0]  if medical_snaps  else None
    shel = shelter_snaps[0]  if shelter_snaps  else None
    fwd  = forward_snaps[0]  if forward_snaps  else None
    sec  = security_snaps[0] if security_snaps else None

    # 新鮮度
    freshness_medical  = freshness(med["snapshot_time"],  "medical",  th) if med  else _stale()
    freshness_shelter  = freshness(shel["snapshot_time"], "shelter",  th) if shel else _stale()
    freshness_forward  = freshness(fwd["snapshot_time"],  "forward",  th) if fwd  else _stale()
    freshness_security = freshness(sec["snapshot_time"],  "security", th) if sec  else _stale()

    # 醫療趨勢
    med_bed_trend     = trend(medical_snaps, "bed_used")
    med_waiting_trend = trend(medical_snaps, "waiting_count")

    # 醫療警戒倒數（床位達 90%）
    med_bed_total = med["bed_total"] if med and med.get("bed_total") else 10
    med_red_threshold = int(med_bed_total * th["medical"]["bed_usage_red"])
    med_countdown = countdown(medical_snaps, "bed_used", med_red_threshold, "medical")

    # 收容趨勢
    shel_bed_trend = trend(shelter_snaps, "bed_used")

    # 醫療壓力指數
    mpi = medical_pressure_index(med, shel, fwd, sec)

    # 前進組資訊
    forward_units = _parse_forward_units(fwd)

    # 信心度低的預測數量
    low_conf_count = sum(1 for t in [
        med_bed_trend, med_waiting_trend, shel_bed_trend
    ] if t["confidence"] in ("low", "insufficient"))

    return {
        "computed_at": _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),

        "medical": {
            "snapshot":  med,
            "freshness": freshness_medical,
            "bed_trend": med_bed_trend,
            "waiting_trend": med_waiting_trend,
            "countdown_to_red": med_countdown,
            "source_breakdown": _extract_source_breakdown(med),
            "incident_pressure": _extract_ipi(med),
            "supplies": _extract_supplies(med),
            "ops_metrics": _extract_ops_metrics(med),
        },
        "shelter": {
            "snapshot":  shel,
            "freshness": freshness_shelter,
            "bed_trend": shel_bed_trend,
            "incident_pressure": _extract_ipi(shel),
            "supplies": _extract_supplies(shel),
            "ops_metrics": _extract_ops_metrics(shel),
        },
        "forward": {
            "snapshot":  fwd,
            "freshness": freshness_forward,
            "units":     forward_units,
        },
        "security": {
            "snapshot":  sec,
            "freshness": freshness_security,
        },
        "medical_pressure": mpi,
        "low_confidence_count": low_conf_count,
    }


def _extract_source_breakdown(snap: dict | None) -> dict:
    """從快照 extra 欄位取得醫療入站來源分布"""
    if not snap:
        return {"a": 0, "b": 0, "c": 0}
    extra = snap.get("extra") or {}
    return {
        "a": extra.get("src_a", 0),
        "b": extra.get("src_b", 0),
        "c": extra.get("src_c", 0),
    }


def _extract_ipi(snap: dict | None) -> dict:
    """從快照 extra.incident_pressure 取事件壓力三維指標"""
    default = {
        "high": 0, "medium": 0, "low": 0,
        "ipi": 0, "recent_types": [],
        "open_total": 0, "resolved_30min": 0,
    }
    if not snap:
        return default
    extra = snap.get("extra") or {}
    ip = extra.get("incident_pressure")
    if not ip:
        return default
    return {
        "high":           ip.get("high", 0),
        "medium":         ip.get("medium", 0),
        "low":            ip.get("low", 0),
        "ipi":            ip.get("ipi", 0),
        "recent_types":   ip.get("recent_types", []),
        "open_total":     ip.get("open_total", 0),
        "resolved_30min": ip.get("resolved_30min", 0),
    }


def _extract_supplies(snap: dict | None) -> dict:
    """從快照 extra 取物資當前值與最大值"""
    default = {"current": {}, "max": {}}
    if not snap:
        return default
    extra = snap.get("extra") or {}
    return {
        "current": extra.get("supplies", {}),
        "max":     extra.get("supplies_max", {}),
    }


def _extract_ops_metrics(snap: dict | None) -> dict:
    """從快照 extra 取人力與營運指標"""
    default = {
        "active_staff": None,
        "staff_ratio": None,
        "stuck_count": 0,
        "stuck_rate": 0,
    }
    if not snap:
        return default
    extra = snap.get("extra") or {}
    return {
        "active_staff": extra.get("active_staff"),
        "staff_ratio":  extra.get("staff_ratio"),
        "stuck_count":  extra.get("stuck_count", 0),
        "stuck_rate":   extra.get("stuck_rate", 0),
    }


def _stale() -> dict:
    return {"level": "lkp", "minutes": 999, "label": "無資料"}


def _parse_forward_units(fwd_snap: dict | None) -> list[dict]:
    """從快照解析前進小隊列表（支援多小隊 QR-FORWARD 格式）"""
    if not fwd_snap:
        return []
    extra = fwd_snap.get("extra") or {}
    units = extra.get("units")
    if units:
        # QR-FORWARD 多小隊格式
        result = []
        now_str = _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
        for u in units:
            last_update = u.get("last_update", fwd_snap.get("snapshot_time", now_str))
            f = freshness(last_update, "forward")
            result.append({
                "unit":        u.get("unit"),
                "casualties":  u.get("casualties", {}),
                "ccp_status":  u.get("ccp_status"),
                "vehicle_needed": u.get("vehicle_needed", 0),
                "hazard":      u.get("hazard", "none"),
                "freshness":   f,
            })
        return result
    else:
        # 單小隊格式（舊式）
        f = freshness(fwd_snap.get("snapshot_time", ""), "forward")
        return [{
            "unit": "A",
            "casualties": {
                "red":    fwd_snap.get("casualties_red",    0),
                "yellow": fwd_snap.get("casualties_yellow", 0),
                "green":  fwd_snap.get("casualties_green",  0),
                "black":  fwd_snap.get("casualties_black",  0),
            },
            "ccp_status": None,
            "vehicle_needed": 0,
            "hazard": "none",
            "freshness": f,
        }]
