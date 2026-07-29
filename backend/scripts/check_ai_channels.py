# -*- coding: utf-8 -*-
"""AI 通道连通性体检脚本：逐一验证 .env 中各 API key 是否可用并测量耗时。

用法: python scripts/check_ai_channels.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / '.env')
    load_dotenv(BACKEND / '.env.spark.local')
except ImportError:
    pass

RESULTS: list[tuple[str, str, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, 'OK' if ok else 'FAIL', detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")


def chat_probe(name: str, base: str, key: str, model: str, timeout=(3, 8)) -> None:
    if not key:
        record(name, False, '未配置 key')
        return
    start = time.time()
    try:
        resp = requests.post(
            f'{base.rstrip("/")}/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': '回复"OK"两个字母即可'}],
                'max_tokens': 5,
                'stream': False,
            },
            timeout=timeout,
        )
        cost = time.time() - start
        if resp.status_code == 200:
            text = resp.json()['choices'][0]['message']['content'][:20]
            record(name, True, f'{cost:.1f}s, 回复: {text!r}')
        else:
            record(name, False, f'{cost:.1f}s, HTTP {resp.status_code}: {resp.text[:120]}')
    except Exception as exc:
        record(name, False, f'{time.time() - start:.1f}s, {type(exc).__name__}: {exc}')


def main() -> None:
    ds_base = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    ds_model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    for env_name in (
        'DEEPSEEK_API_KEY',
        'DEEPSEEK_TRIAL_GEN_API_KEY',
        'DEEPSEEK_MESSENGER_API_KEY',
        'DEEPSEEK_EMERGENCY_API_KEY',
    ):
        chat_probe(f'DeepSeek {env_name}', ds_base, os.getenv(env_name, '').strip(), ds_model, timeout=(3, 15))

    chat_probe(
        'OpenAI OPENAI_API_KEY',
        'https://api.openai.com/v1',
        os.getenv('OPENAI_API_KEY', '').strip(),
        os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        timeout=(5, 20),
    )
    chat_probe(
        'OpenAI(填在 OPENROUTER_API_KEY)',
        'https://api.openai.com/v1',
        os.getenv('OPENROUTER_API_KEY', '').strip(),
        os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        timeout=(5, 20),
    )
    chat_probe(
        '阿里百炼 ALIYUN_API_KEY',
        os.getenv('ALIYUN_BASE_URL', ''),
        os.getenv('ALIYUN_API_KEY', '').strip(),
        os.getenv('ALIYUN_MODEL', 'deepseek-v3'),
        timeout=(5, 20),
    )
    chat_probe(
        'TeamoRouter',
        os.getenv('TEAMOROUTER_BASE_URL', 'https://api.teamorouter.com/v1'),
        os.getenv('TEAMOROUTER_API_KEY', '').strip(),
        'gpt-4o-mini',
        timeout=(5, 20),
    )

    # 讯飞 Spark Lite（OpenAI 兼容 HTTP）
    spark_key = os.getenv('IFLYTEK_SPARK_API_PASSWORD', '').strip() or os.getenv('IFLYTEK_SPARK_CREDENTIALS', '').strip()
    chat_probe(
        '讯飞 Spark Lite',
        'https://spark-api-open.xf-yun.com/v1',
        spark_key,
        os.getenv('IFLYTEK_SPARK_MODEL', 'lite'),
        timeout=(3, 10),
    )

    # 讯飞星辰 Agent
    flow_id = os.getenv('XFYUN_AGENT_FLOW_ID', '').strip()
    xf_key = os.getenv('XFYUN_AGENT_API_KEY', '').strip()
    xf_secret = os.getenv('XFYUN_AGENT_API_SECRET', '').strip()
    if flow_id and xf_key and xf_secret:
        start = time.time()
        try:
            resp = requests.post(
                os.getenv('XFYUN_AGENT_URL', 'https://xingchen-api.xf-yun.com/workflow/v1/chat/completions'),
                headers={'Authorization': f'Bearer {xf_key}:{xf_secret}', 'Content-Type': 'application/json'},
                json={
                    'flow_id': flow_id,
                    'parameters': {os.getenv('XFYUN_AGENT_USER_INPUT_KEY', 'AGENT_USER_INPUT'): '你好'},
                    'stream': False,
                },
                timeout=(3, 15),
            )
            cost = time.time() - start
            record('讯飞星辰 Agent', resp.status_code == 200, f'{cost:.1f}s, HTTP {resp.status_code}: {resp.text[:150]}')
        except Exception as exc:
            record('讯飞星辰 Agent', False, f'{time.time() - start:.1f}s, {type(exc).__name__}: {exc}')
    else:
        record('讯飞星辰 Agent', False, '凭证不全')

    # Neo4j Aura
    uri = os.getenv('NEO4J_URI', '')
    password = os.getenv('NEO4J_PASSWORD', '')
    if not password:
        record('Neo4j Aura', False, 'NEO4J_PASSWORD 为空，待用户提供')
    else:
        start = time.time()
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(uri, auth=(os.getenv('NEO4J_USER', 'neo4j'), password))
            driver.verify_connectivity()
            driver.close()
            record('Neo4j Aura', True, f'{time.time() - start:.1f}s, 连接成功 {uri}')
        except Exception as exc:
            record('Neo4j Aura', False, f'{time.time() - start:.1f}s, {type(exc).__name__}: {exc}')

    print('\n===== 汇总 =====')
    for name, status, detail in RESULTS:
        print(f'{status:4} | {name} | {detail}')


if __name__ == '__main__':
    main()
