#!/usr/bin/env python3
"""
Phase 2: 資源監測腳本 — 在 Pi 500 上跑 benchmark 時同步監測 RAM/CPU

用法:
  # 背景執行，每 2 秒記錄一次，持續到手動停止
  python monitor_resources.py --interval 2 --output resource_log.csv

  # 搭配 benchmark 一起跑
  python monitor_resources.py --interval 2 --output resource_log.csv &
  python run_benchmark.py --text-only
  kill %1

通過標準: 推論期間 RSS < 6GB，無 OOM
"""

import argparse
import csv
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

running = True


def signal_handler(sig, frame):
    global running
    running = False
    print("\n停止監測...")


def get_system_memory():
    """讀取 /proc/meminfo（Linux only）"""
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    val_kb = int(parts[1])
                    info[key] = val_kb
    except FileNotFoundError:
        return None
    return info


def get_process_rss(process_names):
    """取得特定 process 的 RSS（MB）"""
    results = {}
    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            try:
                with open(f"/proc/{entry.name}/comm") as f:
                    comm = f.read().strip()
                if any(pn in comm for pn in process_names):
                    with open(f"/proc/{entry.name}/status") as f:
                        for line in f:
                            if line.startswith("VmRSS:"):
                                rss_kb = int(line.split()[1])
                                key = comm
                                results[key] = results.get(key, 0) + rss_kb / 1024
                                break
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
    except Exception:
        pass
    return results


def get_cpu_temp():
    """讀取 CPU 溫度（Pi 專用）"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except (FileNotFoundError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Phase 2: 資源監測")
    parser.add_argument("--interval", type=float, default=2.0, help="取樣間隔（秒）")
    parser.add_argument("--output", type=str, default="resource_log.csv", help="輸出 CSV 路徑")
    parser.add_argument("--watch", type=str, default="ollama,llama-server,node,python",
                        help="監測的 process 名稱（逗號分隔）")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    watch_list = [p.strip() for p in args.watch.split(",")]
    output_path = Path(args.output)

    print(f"監測 process: {watch_list}")
    print(f"取樣間隔: {args.interval}s")
    print(f"輸出: {output_path}")
    print("按 Ctrl+C 停止\n")

    # CSV header
    fieldnames = [
        "timestamp", "elapsed_sec",
        "mem_total_mb", "mem_used_mb", "mem_available_mb", "mem_used_pct",
        "cpu_temp_c",
    ]
    # 動態加 process RSS 欄位
    proc_fields = [f"rss_{p}_mb" for p in watch_list]
    fieldnames.extend(proc_fields)
    fieldnames.append("rss_total_watched_mb")

    with open(output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        start_time = time.time()
        peak_rss = 0
        sample_count = 0

        while running:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elapsed = time.time() - start_time

            row = {"timestamp": now, "elapsed_sec": f"{elapsed:.1f}"}

            # 系統記憶體
            mem = get_system_memory()
            if mem:
                total_mb = mem.get("MemTotal", 0) / 1024
                available_mb = mem.get("MemAvailable", 0) / 1024
                used_mb = total_mb - available_mb
                used_pct = (used_mb / total_mb * 100) if total_mb > 0 else 0
                row["mem_total_mb"] = f"{total_mb:.0f}"
                row["mem_used_mb"] = f"{used_mb:.0f}"
                row["mem_available_mb"] = f"{available_mb:.0f}"
                row["mem_used_pct"] = f"{used_pct:.1f}"

            # CPU 溫度
            temp = get_cpu_temp()
            row["cpu_temp_c"] = f"{temp:.1f}" if temp else ""

            # Process RSS
            proc_rss = get_process_rss(watch_list)
            total_watched_rss = 0
            for p in watch_list:
                rss = proc_rss.get(p, 0)
                # 也嘗試部分匹配
                for pk, pv in proc_rss.items():
                    if p in pk and pk != p:
                        rss = max(rss, pv)
                row[f"rss_{p}_mb"] = f"{rss:.1f}" if rss > 0 else "0"
                total_watched_rss += rss

            row["rss_total_watched_mb"] = f"{total_watched_rss:.1f}"
            peak_rss = max(peak_rss, total_watched_rss)

            writer.writerow(row)
            csvfile.flush()

            sample_count += 1
            if sample_count % 10 == 0:
                print(f"  [{now}] RAM used: {row.get('mem_used_mb', '?')}MB / "
                      f"{row.get('mem_total_mb', '?')}MB ({row.get('mem_used_pct', '?')}%) | "
                      f"Watched RSS: {total_watched_rss:.0f}MB (peak: {peak_rss:.0f}MB) | "
                      f"Temp: {row.get('cpu_temp_c', '?')}°C")

            time.sleep(args.interval)

    print(f"\n監測結束。共 {sample_count} 筆記錄。")
    print(f"Peak watched RSS: {peak_rss:.0f} MB")
    print(f"通過標準: < 6144 MB → {'PASS' if peak_rss < 6144 else 'FAIL'}")
    print(f"結果: {output_path}")


if __name__ == "__main__":
    main()
