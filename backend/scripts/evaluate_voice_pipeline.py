"""Prepare a 30-round voice-pipeline measurement without fabricating audio evidence."""
from __future__ import annotations

import json
import argparse
import statistics
import time
from pathlib import Path

from app.services.llm_stream import stream_provider_chain
from app.services.tts_service import IflytekTtsService, TtsService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-rounds', action='store_true', help='run 30 local TTS rounds; may be slow')
    args = parser.parse_args()
    report = {
        'benchmark': 'plex-voice-pipeline', 'requested_rounds': 30,
        'status': 'not_configured',
        'asr_configured': False,
        'spark_stream_provider_available': bool(stream_provider_chain('messenger')),
        'iflytek_tts_configured': IflytekTtsService.configured(),
        'tts_fallback_available': TtsService.configured(),
        'rounds_completed': 0, 'latency_ms': [],
        'stages': ['asr', 'intent', 'llm_first_token', 'tts_first_packet', 'playback_start'],
        'note': 'ASR 与播放启动没有本地供应商适配器；未用规则或静态音频冒充真实语音链路。',
    }
    # If TTS is available locally, measure only the real local synthesis path;
    # ASR and playback remain explicitly unmeasured.
    if TtsService.configured() and args.run_rounds:
        for index in range(30):
            started = time.monotonic()
            result = TtsService.synthesize_to_media_with_metrics(
                f'语音测评第 {index + 1} 轮，请复习 Python 列表索引。', prefix='voice-benchmark'
            )
            if not result.get('url'):
                break
            report['rounds_completed'] += 1
            report['latency_ms'].append(result.get('first_packet_ms'))
        report['status'] = 'partial' if report['rounds_completed'] < 30 else 'partial_no_asr'
        values = [value for value in report['latency_ms'] if isinstance(value, (int, float))]
        report['tts_latency'] = {
            'p50_ms': round(statistics.median(values), 1) if values else None,
            'p95_ms': round(sorted(values)[max(0, int(len(values) * .95) - 1)], 1) if values else None,
        }
    if not args.run_rounds:
        report['note'] += ' 使用 --run-rounds 才会执行本地 TTS 30 轮。'
    output = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-voice-20260828.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
