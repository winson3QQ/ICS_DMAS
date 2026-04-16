#!/usr/bin/env python3
"""
用 edge-tts 生成 STT 測試音檔（繁體中文男聲）
產出 test_audio/STT-01.wav ~ STT-10.wav
"""
import asyncio
import json
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CASES_PATH = SCRIPT_DIR / "test_cases" / "stt_cases.json"
OUTPUT_DIR = SCRIPT_DIR / "test_audio"

# 繁體中文男聲
VOICE = "zh-TW-YunJheNeural"


async def generate_one(case_id: str, text: str):
    mp3_path = OUTPUT_DIR / f"{case_id}.mp3"
    wav_path = OUTPUT_DIR / f"{case_id}.wav"

    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate="+0%")
    await communicate.save(str(mp3_path))

    # mp3 → wav (16kHz mono, whisper 需要)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(mp3_path),
        "-ar", "16000", "-ac", "1",
        str(wav_path)
    ], capture_output=True)

    mp3_path.unlink()
    print(f"  {case_id}: {wav_path} ({wav_path.stat().st_size // 1024} KB)")


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    data = json.loads(CASES_PATH.read_text())
    cases = data["cases"]

    print(f"生成 {len(cases)} 個測試音檔（{VOICE}）...")
    for case in cases:
        await generate_one(case["id"], case["transcript"])
    print("完成")


if __name__ == "__main__":
    asyncio.run(main())
