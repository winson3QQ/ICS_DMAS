#!/usr/bin/env python3
"""
TTX 情境測試 Runner — 載入預建情境並透過 API 注入系統。

用法：
  python tests/ttx_runner.py --list                         # 列出可用情境
  python tests/ttx_runner.py --scenario 01_baseline         # 跑單一情境
  python tests/ttx_runner.py --scenario 01_baseline --batch # 無延遲全灌
  python tests/ttx_runner.py --all                          # 逐一跑全部情境
  python tests/ttx_runner.py --scenario 02 --api http://192.168.100.10:8000

每個情境會：
1. 自動設定 admin PIN + 建立測試帳號（如果不存在）
2. 建立 TTX session（session_type='exercise'）
3. 載入情境 injects
4. 依序 push 每個 inject
5. 結束 session
"""

import argparse
import glob
import json
import os
import sys
import time
import urllib.request
import urllib.error

API = "http://127.0.0.1:8000"
ADMIN_PIN = "1234"
TEST_USER = "ttx_runner"
TEST_PIN = "1234"


def _req(method, path, body=None, token=None, admin_pin=None, api=API):
    """送 HTTP request，回傳 (status_code, response_dict)"""
    url = api + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Session-Token"] = token
    if admin_pin:
        headers["X-Admin-PIN"] = admin_pin
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = {"detail": str(e)}
        return e.code, detail
    except Exception as e:
        return 0, {"detail": str(e)}


def setup_auth(api=API):
    """確保 admin PIN 已設定 + 測試帳號存在 → 回傳 session token"""
    # 檢查 admin 狀態
    code, d = _req("GET", "/api/admin/status", api=api)
    if code != 200:
        print(f"  ✗ 無法連線 {api}：{d}")
        return None

    # 設定 admin PIN（如果尚未設定）
    if not d.get("admin_pin_setup"):
        code2, d2 = _req("POST", "/api/config/admin_pin",
                         {"value": ADMIN_PIN}, api=api)
        if code2 not in (200, 405):
            # 嘗試直接寫 config
            pass

    # 嘗試建立測試帳號（已存在會 409，正常）
    _req("POST", "/api/admin/accounts", {
        "username": TEST_USER,
        "pin": TEST_PIN,
        "role": "指揮官",
        "role_detail": "測試主持人",
        "display_name": "TTX Runner",
    }, admin_pin=ADMIN_PIN, api=api)

    # 登入
    code, d = _req("POST", "/api/auth/login", {
        "username": TEST_USER,
        "pin": TEST_PIN,
    }, api=api)
    if code != 200 or not d.get("ok"):
        print(f"  ✗ 登入失敗：{d}")
        return None
    return d["session_id"]


def list_scenarios(scenario_dir):
    """列出可用情境"""
    files = sorted(glob.glob(os.path.join(scenario_dir, "*.json")))
    if not files:
        print("  （無情境檔案）")
        return []
    print(f"\n可用情境（{len(files)} 個）：\n")
    scenarios = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        sid = data.get("id", os.path.basename(f).replace(".json", ""))
        name = data.get("name", "")
        desc = data.get("description", "")[:60]
        n = len(data.get("injects", []))
        dur = data.get("duration_min", "?")
        print(f"  {sid:30s}  {n:2d} injects  {str(dur):>3s}min  {name}")
        scenarios.append(sid)
    print()
    return scenarios


def run_scenario(scenario_id, scenario_dir, token, api=API, batch=False):
    """執行單一情境"""
    # 找到情境檔
    fpath = None
    for f in glob.glob(os.path.join(scenario_dir, "*.json")):
        basename = os.path.basename(f).replace(".json", "")
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("id") == scenario_id or basename == scenario_id or basename.startswith(scenario_id):
            fpath = f
            break
    if not fpath:
        print(f"  ✗ 情境 '{scenario_id}' 不存在")
        return False

    with open(fpath, "r", encoding="utf-8") as fh:
        scenario = json.load(fh)

    name = scenario.get("name", scenario_id)
    injects = scenario.get("injects", [])
    expected = scenario.get("expected_dashboard", {})
    print(f"\n{'='*60}")
    print(f"情境：{name}")
    print(f"說明：{scenario.get('description', '')}")
    print(f"Injects：{len(injects)} 筆，預估 {scenario.get('duration_min', '?')} 分鐘")
    print(f"{'='*60}\n")

    # 建立 TTX session
    code, sess = _req("POST", "/api/ttx/sessions", {
        "session_name": name,
        "facilitator": TEST_USER,
        "scenario_id": scenario.get("id"),
    }, token=token, api=api)
    if code != 200:
        print(f"  ✗ 建立 session 失敗：{sess}")
        return False
    session_id = sess["id"]
    print(f"  Session: {session_id[:8]}...")

    # 開始演練
    _req("POST", f"/api/ttx/sessions/{session_id}/start", token=token, api=api)

    # 批次匯入 injects
    code, result = _req("POST", f"/api/ttx/sessions/{session_id}/injects", {
        "injects": injects,
    }, token=token, api=api)
    if code != 200:
        print(f"  ✗ 匯入 injects 失敗：{result}")
        return False
    print(f"  匯入 {result.get('imported', 0)} 筆 injects")

    # 取得所有 inject ID
    code, inject_list = _req("GET", f"/api/ttx/sessions/{session_id}/injects",
                             token=token, api=api)
    if code != 200:
        print(f"  ✗ 讀取 injects 失敗：{inject_list}")
        return False

    # 依序 push
    ok = 0
    err = 0
    prev_offset = 0
    for i, inj in enumerate(inject_list):
        inject_id = inj["id"]
        title = inj.get("title", "")
        offset = inj.get("scheduled_offset_min") or 0

        # 非 batch 模式：按 offset 差異 delay
        if not batch and offset > prev_offset:
            delay = min((offset - prev_offset) * 0.5, 3)  # 縮時：1 分鐘 → 0.5 秒，上限 3 秒
            time.sleep(delay)
        prev_offset = offset

        code, result = _req("POST",
                            f"/api/ttx/sessions/{session_id}/inject/{inject_id}/push",
                            token=token, api=api)
        if code == 200 and result.get("ok"):
            ok += 1
            status = "✓"
        else:
            err += 1
            status = f"✗ {code}"

        pct = (i + 1) / len(inject_list) * 100
        sys.stdout.write(f"\r  [{pct:5.1f}%] {status} T+{offset:>3d}min  {title[:40]}")
        sys.stdout.flush()

    print(f"\n\n  完成：{ok} 成功 / {err} 失敗")

    # 結束演練
    _req("POST", f"/api/ttx/sessions/{session_id}/end", token=token, api=api)

    # Dashboard 驗證提示
    if expected:
        print(f"\n  ▶ Dashboard 驗證（切到演練模式）：")
        for k, v in expected.items():
            print(f"    • {k}: {v}")

    print()
    return err == 0


def main():
    parser = argparse.ArgumentParser(description="TTX 情境測試 Runner")
    parser.add_argument("--list", action="store_true", help="列出可用情境")
    parser.add_argument("--scenario", type=str, help="執行指定情境（ID 或前綴）")
    parser.add_argument("--all", action="store_true", help="逐一執行所有情境")
    parser.add_argument("--batch", action="store_true", help="無延遲全灌（預設有縮時延遲）")
    parser.add_argument("--api", type=str, default=API, help=f"Command Server URL（預設 {API}）")
    args = parser.parse_args()

    # 情境目錄
    scenario_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios")
    if not os.path.isdir(scenario_dir):
        print(f"情境目錄不存在：{scenario_dir}")
        sys.exit(1)

    if args.list:
        list_scenarios(scenario_dir)
        return

    if not args.scenario and not args.all:
        parser.print_help()
        return

    # 認證
    print("認證中...")
    token = setup_auth(args.api)
    if not token:
        print("認證失敗，請確認 server 已啟動")
        sys.exit(1)
    print(f"  ✓ 已登入（{TEST_USER}）\n")

    if args.scenario:
        success = run_scenario(args.scenario, scenario_dir, token, args.api, args.batch)
        sys.exit(0 if success else 1)

    if args.all:
        scenarios = list_scenarios(scenario_dir)
        total = len(scenarios)
        passed = 0
        for i, sid in enumerate(scenarios):
            print(f"\n[{i+1}/{total}]", end="")
            if run_scenario(sid, scenario_dir, token, args.api, args.batch):
                passed += 1
        print(f"\n{'='*60}")
        print(f"結果：{passed}/{total} 通過")
        print(f"{'='*60}")
        sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
