#!/usr/bin/env python3
"""
Phase 2: Whisper Tiny STT Benchmark — Pi 500
測試 faster-whisper tiny 模型在 Pi 500 上的中文語音辨識準確率和延遲
"""
import json
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CASES_PATH = SCRIPT_DIR / "test_cases" / "stt_cases.json"
AUDIO_DIR = SCRIPT_DIR / "test_audio"
PASS_CER = 0.15  # CER < 15%


def compute_cer(reference: str, hypothesis: str) -> float:
    """字元錯誤率 (Character Error Rate)"""
    ref = list(reference.replace(" ", "").replace("，", "").replace("。", ""))
    hyp = list(hypothesis.replace(" ", "").replace("，", "").replace("。", ""))
    n, m = len(ref), len(hyp)
    if n == 0:
        return 1.0 if m > 0 else 0.0

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


def check_key_terms(hypothesis: str, key_terms: list) -> dict:
    """檢查關鍵術語是否出現在辨識結果中"""
    results = {}
    for term in key_terms:
        results[term] = term in hypothesis
    return results


def main():
    from faster_whisper import WhisperModel

    data = json.loads(CASES_PATH.read_text())
    cases = data["cases"]

    # 載入模型
    print("載入 Whisper Tiny 模型...")
    t0 = time.time()
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print(f"模型載入：{time.time() - t0:.1f}s\n")

    results = []
    total_cer = 0
    total_key_found = 0
    total_key_count = 0

    print(f"{'Case':<8} {'CER':>6} {'延遲':>7} {'關鍵詞':>8}  {'結果'}")
    print("-" * 70)

    for case in cases:
        wav_path = AUDIO_DIR / f"{case['id']}.wav"
        if not wav_path.exists():
            print(f"{case['id']:<8} SKIP — 音檔不存在")
            continue

        # 辨識
        start = time.time()
        segments, info = model.transcribe(
            str(wav_path),
            language="zh",
            beam_size=5,
            vad_filter=True,
        )
        text = "".join(seg.text for seg in segments)
        latency = time.time() - start

        # CER
        cer = compute_cer(case["transcript"], text)
        total_cer += cer

        # 關鍵詞
        key_check = check_key_terms(text, case["key_terms"])
        found = sum(key_check.values())
        total_key_found += found
        total_key_count += len(case["key_terms"])

        passed = "✅" if cer < PASS_CER else "❌"
        key_str = f"{found}/{len(case['key_terms'])}"

        print(f"{case['id']:<8} {cer:>5.1%} {latency:>6.1f}s {key_str:>8}  {passed}")

        result = {
            "case_id": case["id"],
            "cer": round(cer, 4),
            "latency_sec": round(latency, 2),
            "key_terms_found": found,
            "key_terms_total": len(case["key_terms"]),
            "reference": case["transcript"],
            "hypothesis": text,
            "key_term_details": key_check,
            "passed": cer < PASS_CER,
        }
        results.append(result)

    n = len(results)
    avg_cer = total_cer / n if n else 0
    avg_latency = sum(r["latency_sec"] for r in results) / n if n else 0
    passed_count = sum(1 for r in results if r["passed"])

    print("-" * 70)
    print(f"{'平均':<8} {avg_cer:>5.1%} {avg_latency:>6.1f}s {total_key_found}/{total_key_count:>5}")
    print(f"\n通過率：{passed_count}/{n}（門檻 CER < {PASS_CER:.0%}）")
    print(f"整體判定：{'✅ PASS' if avg_cer < PASS_CER else '❌ FAIL'}")

    # 存報告
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": "whisper-tiny",
        "device": "cpu",
        "compute_type": "int8",
        "pass_criteria_cer": PASS_CER,
        "summary": {
            "avg_cer": round(avg_cer, 4),
            "avg_latency_sec": round(avg_latency, 2),
            "passed": passed_count,
            "total": n,
            "key_terms_accuracy": round(total_key_found / total_key_count, 4) if total_key_count else 0,
            "overall_pass": avg_cer < PASS_CER,
        },
        "results": results,
    }

    out_path = SCRIPT_DIR / f"stt_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n報告已存：{out_path.name}")

    # 顯示錯誤最多的案例
    print("\n--- 辨識差異最大的案例 ---")
    worst = sorted(results, key=lambda r: r["cer"], reverse=True)[:3]
    for r in worst:
        print(f"\n{r['case_id']} (CER {r['cer']:.1%}):")
        print(f"  原文：{r['reference'][:80]}...")
        print(f"  辨識：{r['hypothesis'][:80]}...")


if __name__ == "__main__":
    main()
