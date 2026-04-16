#!/usr/bin/env python3
"""
Phase 2: Gemma 4 E2B Benchmark — Pi 500 評估腳本

用法:
  # 文字模式（測試結構化輸出 + 矛盾偵測，不需音檔）
  python run_benchmark.py --text-only

  # 完整模式（含 STT，需要 test_audio/ 目錄下的 .wav 檔案）
  python run_benchmark.py --audio-dir ./test_audio

  # 指定 Ollama 端點
  python run_benchmark.py --text-only --ollama-url http://localhost:11434

需求: pip install requests
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
TEST_CASES_DIR = SCRIPT_DIR / "test_cases"
PROMPT_TEMPLATE_PATH = SCRIPT_DIR / "prompt_template.json"

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e2b"  # Ollama 模型名稱，依實際安裝調整

# 通過標準
PASS_CER = 0.15            # STT 字元錯誤率 < 15%
PASS_FIELD_ACCURACY = 0.85  # 結構化欄位準確率 > 85%
PASS_CONTRADICTION = 0.60   # 矛盾偵測率 > 60%
PASS_LATENCY_SEC = 15.0     # 推論延遲 < 15 秒


# ---------------------------------------------------------------------------
# 資料結構
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    case_id: str
    test_type: str  # stt / structured / contradiction
    passed: bool
    score: float
    latency_sec: float
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Ollama API 呼叫
# ---------------------------------------------------------------------------

def call_ollama_generate(ollama_url: str, model: str, prompt: str,
                         system: str = "", tools: list = None) -> dict:
    """呼叫 Ollama /api/generate 或 /api/chat"""
    import requests

    url = f"{ollama_url}/api/chat"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    if tools:
        payload["tools"] = tools

    start = time.time()
    resp = requests.post(url, json=payload, timeout=120)
    elapsed = time.time() - start

    resp.raise_for_status()
    data = resp.json()

    # 取得回覆內容
    content = ""
    tool_calls = []
    msg = data.get("message", {})
    content = msg.get("content", "")
    tool_calls = msg.get("tool_calls", [])

    return {
        "content": content,
        "tool_calls": tool_calls,
        "latency_sec": elapsed,
        "raw": data,
    }


def extract_json_from_response(response: dict) -> dict:
    """從 Ollama 回覆中提取結構化 JSON"""
    # 優先從 tool_calls 取
    if response["tool_calls"]:
        tc = response["tool_calls"][0]
        fn = tc.get("function", {})
        return fn.get("arguments", {})

    # fallback: 從 content 中 parse JSON
    content = response["content"]
    # 嘗試找 JSON block
    import re
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


# ---------------------------------------------------------------------------
# 評分函式
# ---------------------------------------------------------------------------

def compute_cer(reference: str, hypothesis: str) -> float:
    """計算字元錯誤率 (Character Error Rate) — Levenshtein distance / ref length"""
    ref = list(reference.replace(" ", ""))
    hyp = list(hypothesis.replace(" ", ""))
    n = len(ref)
    m = len(hyp)
    if n == 0:
        return 1.0 if m > 0 else 0.0

    # DP table
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    return d[n][m] / n


def score_field(gt_val, ai_val) -> float:
    """比對單一欄位，回傳 0.0 或 1.0"""
    if gt_val is None and ai_val is None:
        return 1.0
    if gt_val is None or ai_val is None:
        return 0.0
    # 數值比對
    if isinstance(gt_val, (int, float)) and isinstance(ai_val, (int, float)):
        return 1.0 if abs(gt_val - ai_val) < 0.01 else 0.0
    # 字串比對（允許 AI 回覆包含 ground truth 的關鍵字）
    if isinstance(gt_val, str) and isinstance(ai_val, str):
        gt_lower = gt_val.lower().strip()
        ai_lower = ai_val.lower().strip()
        if gt_lower == ai_lower:
            return 1.0
        if gt_lower in ai_lower or ai_lower in gt_lower:
            return 0.8  # 部分匹配
        return 0.0
    # 列表比對（treatments_given, warnings）
    if isinstance(gt_val, list) and isinstance(ai_val, list):
        if len(gt_val) == 0 and len(ai_val) == 0:
            return 1.0
        if len(gt_val) == 0:
            return 0.5  # AI 多給了東西，不算錯但扣分
        matches = 0
        for gt_item in gt_val:
            for ai_item in ai_val:
                if isinstance(gt_item, str) and isinstance(ai_item, str):
                    if gt_item.lower() in ai_item.lower() or ai_item.lower() in gt_item.lower():
                        matches += 1
                        break
        return matches / len(gt_val)
    return 0.0


def score_structured_output(ground_truth: dict, ai_output: dict) -> tuple[float, dict]:
    """比對結構化輸出，回傳 (準確率, 詳細結果)"""
    scored_fields = [
        "gender", "age_estimate", "source_type", "triage_color",
        "trauma_type", "mechanism_of_injury", "chief_complaint",
        "treatments_given", "allergies", "medications", "past_history",
    ]
    details = {}
    total = 0
    correct = 0.0

    for f in scored_fields:
        gt_val = ground_truth.get(f)
        ai_val = ai_output.get(f)
        s = score_field(gt_val, ai_val)
        details[f] = {"gt": gt_val, "ai": ai_val, "score": s}
        total += 1
        correct += s

    # 生命徵象子欄位
    gt_vitals = ground_truth.get("vital_signs", {}) or {}
    ai_vitals = ai_output.get("vital_signs", {}) or {}
    vital_fields = [
        "heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic",
        "respiratory_rate", "spo2", "gcs",
    ]
    for vf in vital_fields:
        gt_val = gt_vitals.get(vf)
        ai_val = ai_vitals.get(vf)
        s = score_field(gt_val, ai_val)
        details[f"vital_{vf}"] = {"gt": gt_val, "ai": ai_val, "score": s}
        total += 1
        correct += s

    accuracy = correct / total if total > 0 else 0.0
    return accuracy, details


def score_contradiction_detection(expected_warnings: list, ai_warnings: list) -> tuple[float, dict]:
    """比對矛盾偵測結果"""
    if not expected_warnings:
        return 1.0, {"note": "no expected warnings"}

    detected = 0
    details = {}
    for i, ew in enumerate(expected_warnings):
        found = False
        for aw in (ai_warnings or []):
            # 寬鬆比對：有共同關鍵字就算偵測到
            ew_chars = set(ew)
            aw_chars = set(str(aw))
            overlap = len(ew_chars & aw_chars) / max(len(ew_chars), 1)
            if overlap > 0.3:
                found = True
                break
        details[f"warning_{i}"] = {"expected": ew, "detected": found}
        if found:
            detected += 1

    rate = detected / len(expected_warnings)
    return rate, details


# ---------------------------------------------------------------------------
# 測試執行器
# ---------------------------------------------------------------------------

def run_structured_tests(ollama_url: str, model: str, prompt_cfg: dict) -> list[TestResult]:
    """執行結構化輸出測試"""
    with open(TEST_CASES_DIR / "structured_cases.json") as f:
        cases = json.load(f)["cases"]

    system_prompt = prompt_cfg["system_prompt"]
    user_template = prompt_cfg["user_prompt_template"]
    tools_cfg = prompt_cfg.get("tools", [])

    # 轉換為 Ollama tools 格式
    ollama_tools = []
    for t in tools_cfg:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
        })

    results = []
    for case in cases:
        cid = case["id"]
        print(f"  [{cid}] ", end="", flush=True)

        # 跳過特殊案例（多重傷患、非醫療）
        if "ground_truth_note" in case:
            print("SKIP (special case)")
            results.append(TestResult(
                case_id=cid, test_type="structured",
                passed=True, score=0, latency_sec=0,
                details={"skipped": True, "note": case.get("ground_truth_note", "")},
            ))
            continue

        transcript = case["transcript"]
        gt = case["ground_truth"]
        prompt = user_template.replace("{transcript}", transcript)

        try:
            resp = call_ollama_generate(ollama_url, model, prompt, system_prompt, ollama_tools)
            ai_output = extract_json_from_response(resp)
            accuracy, details = score_structured_output(gt, ai_output)
            latency = resp["latency_sec"]
            passed = accuracy >= PASS_FIELD_ACCURACY and latency <= PASS_LATENCY_SEC

            print(f"{'PASS' if passed else 'FAIL'} acc={accuracy:.1%} lat={latency:.1f}s")
            results.append(TestResult(
                case_id=cid, test_type="structured",
                passed=passed, score=accuracy, latency_sec=latency,
                details={"field_details": details, "ai_raw": ai_output},
            ))
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(TestResult(
                case_id=cid, test_type="structured",
                passed=False, score=0, latency_sec=0,
                details={"error": str(e)},
            ))

    return results


def run_contradiction_tests(ollama_url: str, model: str, prompt_cfg: dict) -> list[TestResult]:
    """執行矛盾偵測測試"""
    with open(TEST_CASES_DIR / "contradiction_cases.json") as f:
        cases = json.load(f)["cases"]

    system_prompt = prompt_cfg["system_prompt"]
    user_template = prompt_cfg["user_prompt_template"]
    tools_cfg = prompt_cfg.get("tools", [])

    ollama_tools = []
    for t in tools_cfg:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
        })

    results = []
    for case in cases:
        cid = case["id"]
        print(f"  [{cid}] ", end="", flush=True)

        transcript = case["transcript"]
        expected_warnings = case["expected_warnings"]
        prompt = user_template.replace("{transcript}", transcript)

        try:
            resp = call_ollama_generate(ollama_url, model, prompt, system_prompt, ollama_tools)
            ai_output = extract_json_from_response(resp)
            ai_warnings = ai_output.get("warnings", [])
            rate, details = score_contradiction_detection(expected_warnings, ai_warnings)
            latency = resp["latency_sec"]
            passed = rate >= PASS_CONTRADICTION

            print(f"{'PASS' if passed else 'FAIL'} detect={rate:.0%} lat={latency:.1f}s")
            results.append(TestResult(
                case_id=cid, test_type="contradiction",
                passed=passed, score=rate, latency_sec=latency,
                details={"warning_details": details, "ai_warnings": ai_warnings},
            ))
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(TestResult(
                case_id=cid, test_type="contradiction",
                passed=False, score=0, latency_sec=0,
                details={"error": str(e)},
            ))

    return results


# ---------------------------------------------------------------------------
# 報告產生
# ---------------------------------------------------------------------------

def generate_report(all_results: list[TestResult], output_path: Path):
    """產生 JSON + 摘要報告"""
    summary = {
        "structured": {"total": 0, "passed": 0, "avg_accuracy": 0, "avg_latency": 0},
        "contradiction": {"total": 0, "passed": 0, "avg_detection": 0, "avg_latency": 0},
    }

    for r in all_results:
        t = r.test_type
        if t not in summary:
            continue
        if r.details.get("skipped"):
            continue
        summary[t]["total"] += 1
        if r.passed:
            summary[t]["passed"] += 1
        summary[t]["avg_accuracy"] += r.score
        summary[t]["avg_latency"] += r.latency_sec

    for t in summary:
        n = summary[t]["total"]
        if n > 0:
            summary[t]["avg_accuracy"] /= n
            summary[t]["avg_latency"] /= n

    # 整體判定
    struct_pass = (summary["structured"]["total"] > 0 and
                   summary["structured"]["avg_accuracy"] >= PASS_FIELD_ACCURACY)
    contra_pass = (summary["contradiction"]["total"] > 0 and
                   summary["contradiction"]["avg_detection"] >= PASS_CONTRADICTION)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pass_criteria": {
            "field_accuracy": PASS_FIELD_ACCURACY,
            "contradiction_detection": PASS_CONTRADICTION,
            "max_latency_sec": PASS_LATENCY_SEC,
        },
        "overall_verdict": "PASS" if (struct_pass and contra_pass) else "FAIL",
        "summary": summary,
        "results": [
            {
                "case_id": r.case_id,
                "test_type": r.test_type,
                "passed": r.passed,
                "score": r.score,
                "latency_sec": r.latency_sec,
                "details": r.details,
            }
            for r in all_results
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 印摘要
    print("\n" + "=" * 60)
    print("Phase 2 E2B Benchmark 結果")
    print("=" * 60)
    print(f"整體判定: {report['overall_verdict']}")
    print()
    s = summary["structured"]
    print(f"結構化輸出: {s['passed']}/{s['total']} 通過, "
          f"平均準確率 {s['avg_accuracy']:.1%}, 平均延遲 {s['avg_latency']:.1f}s")
    c = summary["contradiction"]
    print(f"矛盾偵測:   {c['passed']}/{c['total']} 通過, "
          f"平均偵測率 {c['avg_accuracy']:.1%}, 平均延遲 {c['avg_latency']:.1f}s")
    print(f"\n詳細報告: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Phase 2: Gemma 4 E2B Benchmark")
    parser.add_argument("--text-only", action="store_true",
                        help="只跑結構化輸出 + 矛盾偵測（不需音檔）")
    parser.add_argument("--audio-dir", type=str, default=None,
                        help="音檔目錄（含 STT-01.wav ~ STT-10.wav）")
    parser.add_argument("--ollama-url", type=str, default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama API URL (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"模型名稱 (default: {DEFAULT_MODEL})")
    parser.add_argument("--output", type=str, default=None,
                        help="報告輸出路徑 (default: benchmark_report_TIMESTAMP.json)")
    args = parser.parse_args()

    # 載入 prompt template
    with open(PROMPT_TEMPLATE_PATH) as f:
        prompt_cfg = json.load(f)

    print(f"Ollama: {args.ollama_url}")
    print(f"Model:  {args.model}")
    print()

    all_results = []

    # 結構化輸出測試
    print("=== 結構化輸出測試 ===")
    all_results.extend(run_structured_tests(args.ollama_url, args.model, prompt_cfg))

    # 矛盾偵測測試
    print("\n=== 矛盾偵測測試 ===")
    all_results.extend(run_contradiction_tests(args.ollama_url, args.model, prompt_cfg))

    # STT 測試（需要音檔）
    if not args.text_only and args.audio_dir:
        print("\n=== STT 測試 ===")
        print("  (STT 測試需要手動執行，請參考 BENCHMARK_REPORT.md)")

    # 產生報告
    if args.output:
        output_path = Path(args.output)
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = SCRIPT_DIR / f"benchmark_report_{ts}.json"

    generate_report(all_results, output_path)


if __name__ == "__main__":
    main()
