#!/usr/bin/env python3
"""
產生符合 PWA 資料模型的測試快照並推送到 Command Server。

Shelter: bed_used/bed_total + SRT(red/yellow/green) + pending_intake + staff_on_duty
Medical: casualties(red/yellow/green/black) + pending_evac + staff_on_duty + extra{src_a, src_b, src_c, supplies, supplies_max}

模擬 SRT→醫療橋接效應：SRT Red+ 上升 → 約 15 分鐘後醫療 Red 跟著上升
"""

import argparse
import datetime as dt
import json
import math
import random
import sys
import time
import urllib.request

API = "http://127.0.0.1:8000"
SNAP_INTERVAL_MIN = 2  # 每筆快照間隔（模擬分鐘）


def _snap_time(i: int, total: int) -> dt.datetime:
    """
    計算第 i 筆快照的時間戳。
    在 ~50% 進度處插入 15 分鐘空洞（觸發 comm_health gap 偵測）。
    """
    base = dt.datetime(2026, 4, 5, 8, 0, 0) + dt.timedelta(minutes=i * SNAP_INTERVAL_MIN)
    gap_idx = total // 2
    if i >= gap_idx:
        base += dt.timedelta(minutes=15)  # 所有 50% 之後的快照往後推 15 分鐘
    return base


def gen_shelter(i: int, total: int) -> dict:
    """產生一筆收容組快照"""
    # 基礎：50 床，逐漸收人
    bed_total = 50
    base_used = min(int(10 + i * 0.4), 48)
    # 加隨機波動
    bed_used = max(0, min(bed_total, base_used + random.randint(-2, 3)))

    # SRT 三級檢傷：紅少、黃中、綠多
    phase = i / total  # 0~1 進度
    srt_green = max(0, int(5 + 8 * phase + random.randint(-1, 2)))
    srt_yellow = max(0, int(2 + 4 * phase + random.randint(-1, 1)))
    # 紅色在 30%~60% 進度時有一波高峰
    srt_red_base = 3 * math.exp(-((phase - 0.45) ** 2) / 0.02) if phase > 0.2 else 0
    srt_red = max(0, int(srt_red_base + random.randint(0, 1)))

    pending_intake = max(0, random.randint(0, 4) + (2 if phase > 0.3 else 0))
    staff = random.choice([4, 5, 5, 6])

    ts = _snap_time(i, total)

    return {
        "v": 3,
        "type": "shelter",
        "snapshot_id": f"test-s-{i:04d}",
        "t": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "src": "test-shelter-pi",
        "source": "auto",
        "bed_used": bed_used,
        "bed_total": bed_total,
        "srt": {"red": srt_red, "yellow": srt_yellow, "green": srt_green},
        "pending_intake": pending_intake,
        "staff_on_duty": staff,
        "extra": {
            "staff_ratio": round(bed_used / max(staff, 1), 1),
            "exited_total": max(0, int(5 * phase + random.randint(-1, 1))),
            "supplies": {
                "blanket": max(10, int(200 - 80 * phase + random.randint(-5, 5))),
                "water_bottle": max(20, int(500 - 150 * phase + random.randint(-10, 10))),
            },
            "supplies_max": {"blanket": 200, "water_bottle": 500},
            "incident_pressure": {
                "high": random.choice([0, 0, 0, 1]) if phase > 0.4 else 0,
                "medium": random.randint(0, 2),
                "low": random.randint(0, 1),
                "open_total": random.randint(0, 3),
                "resolved_30min": random.randint(0, 2),
            },
        },
    }


def gen_medical(i: int, total: int, shelter_srt_history: list) -> dict:
    """產生一筆醫療組快照，SRT→醫療橋接延遲約 7~8 筆（~15 分鐘）"""
    phase = i / total
    bed_total = 30

    # 橋接效應：醫療紅傷追蹤 ~7 筆前的 SRT Red
    bridge_delay = 7
    bridge_idx = max(0, i - bridge_delay)
    bridge_srt_red = shelter_srt_history[bridge_idx] if bridge_idx < len(shelter_srt_history) else 0

    # 各級傷患
    cas_red = max(0, int(bridge_srt_red * 0.7 + random.randint(0, 1)))
    cas_yellow = max(0, int(2 + 3 * phase + random.randint(-1, 2)))
    cas_green = max(0, int(3 + 5 * phase + random.randint(-1, 2)))
    cas_black = 1 if phase > 0.6 and random.random() < 0.15 else 0
    bed_used = min(bed_total, cas_red + cas_yellow + cas_green + cas_black)

    # 來源 A/B/C 累計
    src_a = int(3 + 8 * phase + random.randint(-1, 1))   # 前進組→醫療
    src_b = int(1 + 5 * phase + random.randint(-1, 1))   # 收容轉送→醫療
    src_c = int(2 + 3 * phase + random.randint(0, 1))    # 自行抵達→醫療

    # 60~80% 進度時 pending_evac 持續上升（觸發 output_monitor backlog）
    if 0.60 <= phase <= 0.80:
        pending_evac = max(0, int(3 + 5 * (phase - 0.60) / 0.20 + random.randint(0, 2)))
    else:
        pending_evac = max(0, random.randint(0, 3) + (2 if cas_red > 1 else 0))
    staff = random.choice([3, 3, 4, 4, 5])

    # 物資消耗（百分比遞減）
    # 70~85% 進度時 IV 消耗加速 3 倍（觸發 burn_rate crit）
    if 0.70 <= phase <= 0.85:
        iv_decay = 40 + 80 * (phase - 0.70) / 0.15  # 加速消耗
    else:
        iv_decay = 40 * phase
    iv_remain = max(5, int(100 - iv_decay + random.randint(-3, 3)))
    ox_remain = max(10, int(100 - 30 * phase + random.randint(-5, 5)))
    tq_remain = max(15, int(100 - 25 * phase + random.randint(-3, 3)))

    ts = _snap_time(i, total)

    return {
        "v": 3,
        "type": "medical",
        "snapshot_id": f"test-m-{i:04d}",
        "t": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "src": "test-medical-pi",
        "source": "auto",
        "bed_used": bed_used,
        "bed_total": bed_total,
        "casualties": {"red": cas_red, "yellow": cas_yellow, "green": cas_green, "black": cas_black},
        "pending_evac": pending_evac,
        "evacuated_total": max(0, int(8 * phase + random.randint(-1, 1))),
        "staff_on_duty": staff,
        "extra": {
            "src_a": src_a,
            "src_b": src_b,
            "src_c": src_c,
            "staff_ratio": round(bed_used / max(staff, 1), 1),
            "supplies": {"iv": iv_remain, "oxygen": ox_remain, "tourniquet": tq_remain},
            "supplies_max": {"iv": 100, "oxygen": 100, "tourniquet": 100},
            "incident_pressure": {
                "high": random.choice([0, 0, 1]) if phase > 0.3 else 0,
                "medium": random.randint(0, 2),
                "low": random.randint(0, 2),
                "open_total": random.randint(0, 4),
                "resolved_30min": random.randint(0, 2),
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="產生測試快照推送到 Command Server")
    parser.add_argument("-n", type=int, default=60, help="每組快照數量（預設 60）")
    parser.add_argument("--delay", type=float, default=0.5, help="每筆推送間隔秒數（預設 0.5）")
    parser.add_argument("--api", type=str, default=API, help="Command Server URL")
    parser.add_argument("--batch", action="store_true", help="一次全推，不等待")
    args = parser.parse_args()

    n = args.n
    print(f"產生 {n} 對快照（shelter + medical），推送到 {args.api}")

    # 先產生全部 shelter 快照取得 SRT 歷史
    shelter_snaps = [gen_shelter(i, n) for i in range(n)]
    srt_red_history = [s["srt"]["red"] for s in shelter_snaps]
    medical_snaps = [gen_medical(i, n, srt_red_history) for i in range(n)]

    ok = 0
    err = 0

    for i in range(n):
        for label, snap in [("S", shelter_snaps[i]), ("M", medical_snaps[i])]:
            try:
                body = json.dumps(snap).encode("utf-8")
                req = urllib.request.Request(
                    args.api + "/api/snapshots",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        ok += 1
                    else:
                        err += 1
                        print(f"  [{label}#{i}] HTTP {resp.status}")
            except Exception as e:
                err += 1
                print(f"  [{label}#{i}] Error: {e}")

        # 進度
        pct = (i + 1) / n * 100
        ts = shelter_snaps[i]["t"][11:16]
        srt_r = shelter_snaps[i]["srt"]["red"]
        med_r = medical_snaps[i]["casualties"]["red"]
        sys.stdout.write(f"\r  [{pct:5.1f}%] t={ts} SRT.R={srt_r} Med.R={med_r} ok={ok} err={err}")
        sys.stdout.flush()

        if not args.batch and i < n - 1:
            time.sleep(args.delay)

    print(f"\n完成。成功 {ok}，失敗 {err}")


if __name__ == "__main__":
    main()
