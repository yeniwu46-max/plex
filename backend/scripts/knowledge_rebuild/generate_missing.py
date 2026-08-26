# -*- coding: utf-8 -*-
"""给题目不足 4 道的知识点节点用 DeepSeek 补题。

## 为什么不直接采信 AI 给的样例输出

大模型很擅长写出"看起来对"的样例输出，但它不会真的算一遍。所以本脚本**丢弃 AI
给出的任何期望输出**，只保留它写的参考答案与测试输入，然后把
`setup + reference_answer` 丢进 sandbox_exec 真实执行，用实际 stdout 作为
`expected`。执行失败、超时、输出为空、或被安全检查拒绝的，整道题作废并重新生成。
换句话说：库里每一个样例输出都来自一次真实运行，没有一个是编造的。

## 题目形态

统一采用"变量注入"式（与 coding_question_bank.py / pythonTrialQuestions.ts 一致）：
测试数据通过 `setup` 预先定义变量，学生代码直接使用，判题比对 stdout。
这样生成的 test_cases 可以被现有判题器直接使用，不需要额外的 stdin 管道。

所有生成题均标 `source_kind='ai_generated'` + `needs_review=1`，进人工修改清单。

用法：
    python scripts/knowledge_rebuild/generate_missing.py
    python scripts/knowledge_rebuild/generate_missing.py --target 5   # 每节点补到 5 题
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / 'scripts' / 'problem_bank_import'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ai_client  # noqa: E402
from sandbox_exec import PY_TIMEOUT_SECONDS, is_safe_python  # noqa: E402

from app.data.knowledge_node_registry import (  # noqa: E402
    KNOWLEDGE_DOMAINS,
    get_domain,
    get_entry,
    nodes_for_domain,
)

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
INPUT_PATH = OUTPUT_DIR / 'assigned_questions.json'
OUTPUT_PATH = OUTPUT_DIR / 'unified_questions.json'
GENERATED_PATH = OUTPUT_DIR / 'ai_generated_questions.json'

TARGET_PER_NODE = 4
MAX_ROUNDS_PER_NODE = 4

SYSTEM_PROMPT = (
    '你是中文 Python 入门课程的命题老师，为初学者设计练习题。'
    '题目必须能用一段不超过 15 行的 Python 代码解决，不使用任何第三方库，'
    '不读取文件、不联网、不调用 input()。'
    '测试数据通过 setup 代码预先定义好变量，学生程序直接使用这些变量并用 print 输出结果。'
    '严格输出 JSON，不要任何解释文字。'
)


def build_prompt(node_id: str, count: int, existing_stems: list[str]) -> str:
    entry = get_entry(node_id)
    domain = get_domain(entry.domain_key)
    avoid = ''
    if existing_stems:
        listed = '\n'.join(f'- {s[:70]}' for s in existing_stems[:8])
        avoid = f'\n\n已有题目（请勿重复出题，换不同的情境与考法）：\n{listed}'

    return f'''请为知识点「{domain.title} / {entry.label}」出 {count} 道练习题。

该知识点的教学要点：{entry.summary}
难度基准：{entry.default_difficulty}（1 最简单，5 最难）{avoid}

每道题必须严格考察「{entry.label}」这个知识点本身，不要跑题到其他知识点。

输出 JSON 数组，每个元素包含：
- "title": 简短中文标题（不超过 12 字）
- "stem": 题目描述（中文，说明已给定哪些变量、要输出什么，100 字以内）
- "input_format": 说明测试数据以哪些变量给出
- "output_format": 说明输出内容与格式
- "starter_code": 给学生的起始代码（只含注释提示，不含答案）
- "reference_answer": 完整可运行的参考答案（直接使用 setup 里定义的变量，用 print 输出；不要包含 setup 本身）
- "hint": 一句话提示
- "notes": 字符串数组，0-2 条补充说明
- "test_cases": 数组，2-3 个元素，每个是 {{"label": "样例说明", "setup": "变量赋值语句，如 nums = [1, 2, 3]"}}

注意：不要提供 expected 字段，期望输出会由系统真实运行参考答案得到。'''


def run_snippet(code: str) -> str | None:
    """真实执行代码，返回 stdout（去尾换行）；任何异常/超时/非零退出返回 None。"""
    if not is_safe_python(code):
        return None
    with tempfile.TemporaryDirectory(prefix='kg_gen_') as tmp:
        script = Path(tmp) / 'solution.py'
        script.write_text(code, encoding='utf-8')
        try:
            proc = subprocess.run(
                [sys.executable, '-I', str(script)],
                capture_output=True, text=True,
                timeout=PY_TIMEOUT_SECONDS, cwd=tmp,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip('\n')


def verify_and_build(raw: dict, node_id: str) -> tuple[dict | None, str]:
    """校验 AI 产出并用真实执行补全期望输出。返回 (题目, 失败原因)。"""
    stem = (raw.get('stem') or '').strip()
    answer = (raw.get('reference_answer') or '').strip()
    cases = raw.get('test_cases')
    if not stem or not answer:
        return None, '缺少题干或参考答案'
    if not isinstance(cases, list) or not cases:
        return None, '缺少 test_cases'
    if 'input(' in answer:
        return None, '参考答案调用了 input()，不符合变量注入式约定'
    if not is_safe_python(answer):
        return None, '参考答案未通过沙箱安全检查'

    built_cases: list[dict] = []
    samples: list[dict] = []
    for index, case in enumerate(cases[:3], start=1):
        if not isinstance(case, dict):
            continue
        setup = (case.get('setup') or '').strip()
        program = f'{setup}\n{answer}' if setup else answer
        output = run_snippet(program)
        if output is None:
            return None, f'第 {index} 个测试点执行失败（超时/报错/不安全）'
        if not output:
            return None, f'第 {index} 个测试点输出为空'
        built_cases.append({
            'id': f't{index}',
            'label': str(case.get('label') or f'样例 {index}'),
            'setup': setup,
            'expected': output,
        })
        samples.append({'input': setup or '（无输入）', 'output': output})

    if len(built_cases) < 2:
        return None, '可用测试点少于 2 个'

    entry = get_entry(node_id)
    return {
        'source_kind': 'ai_generated',
        'source_ref': None,  # 落库时按 problem_no 生成
        'question_type': 'coding',
        'title_cn': (raw.get('title') or entry.label)[:40],
        'title_en': None,
        'stem': stem,
        'background': None,
        'input_format': raw.get('input_format'),
        'output_format': raw.get('output_format'),
        'samples': samples,
        'samples_source': 'executed_reference_answer:ai_generated',
        'notes': [str(n) for n in (raw.get('notes') or []) if str(n).strip()][:2],
        'options': [],
        'correct_index': None,
        'test_cases': built_cases,
        'starter_code': raw.get('starter_code') or '# 在这里写你的代码\n',
        'run_mode': 'stdout',
        'hint': raw.get('hint'),
        'reference_answer': answer,
        'template': None,
        'difficulty': entry.default_difficulty,
        'star_difficulty': entry.default_difficulty,
        'legacy_knowledge_key': node_id,
        'legacy_concept': entry.label,
        'legacy_concept_group': None,
        'legacy_problem_id': None,
        'legacy_problem_no': None,
        'has_english': False,
        'kg_node_id': node_id,
        'domain_key': entry.domain_key,
        'assign_method': 'ai_generated',
        'needs_review': True,
        'review_note': 'AI 新生成题目：样例输出已由沙箱真实执行产出，但题意、难度与措辞需人工核对',
        'merged_from': [],
    }, ''


def generate_for_node(node_id: str, missing: int, existing_stems: list[str]) -> list[dict]:
    entry = get_entry(node_id)
    accepted: list[dict] = []
    seen_stems = {s.strip() for s in existing_stems}

    for round_index in range(MAX_ROUNDS_PER_NODE):
        need = missing - len(accepted)
        if need <= 0:
            break
        # 多要几道，因为会有一部分执行不通过被丢弃
        ask = min(need + 2, 6)
        print(f'  [{node_id}] 第 {round_index + 1} 轮：请求 {ask} 道（还差 {need}）')
        raws = ai_client.chat_json(
            SYSTEM_PROMPT,
            build_prompt(node_id, ask, list(seen_stems)),
            max_tokens=4000,
            temperature=0.7 if round_index else 0.4,
        )
        if not isinstance(raws, list):
            print('    未拿到有效 JSON 数组，重试')
            continue
        for raw in raws:
            if len(accepted) >= missing:
                break
            if not isinstance(raw, dict):
                continue
            built, reason = verify_and_build(raw, node_id)
            if not built:
                print(f'    丢弃「{str(raw.get("title"))[:16]}」：{reason}')
                continue
            if built['stem'].strip() in seen_stems:
                print(f'    丢弃「{built["title_cn"]}」：与已有题目重复')
                continue
            seen_stems.add(built['stem'].strip())
            accepted.append(built)
            print(f'    通过「{built["title_cn"]}」（{len(built["test_cases"])} 个测试点已真实执行）')

    if len(accepted) < missing:
        print(f'  [{node_id}] 警告：{MAX_ROUNDS_PER_NODE} 轮后仍只补到 {len(accepted)}/{missing} 道')
    return accepted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=TARGET_PER_NODE, help='每节点目标题量')
    parser.add_argument('--only', help='只补指定节点（逗号分隔）')
    args = parser.parse_args()

    records = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    by_node = Counter(r['kg_node_id'] for r in records)
    stems_by_node: dict[str, list[str]] = {}
    for record in records:
        stems_by_node.setdefault(record['kg_node_id'], []).append((record.get('stem') or '').strip())

    only = {s.strip() for s in args.only.split(',')} if args.only else None
    shortfalls = []
    for domain in KNOWLEDGE_DOMAINS:
        for entry in nodes_for_domain(domain.key):
            if only and entry.kg_id not in only:
                continue
            gap = args.target - by_node.get(entry.kg_id, 0)
            if gap > 0:
                shortfalls.append((entry.kg_id, gap))

    if not shortfalls:
        print('所有节点都已达到目标题量，无需补题')
        OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
        return

    print(f'需补题的节点 {len(shortfalls)} 个，合计 {sum(g for _, g in shortfalls)} 道\n')
    if not ai_client.is_available():
        raise SystemExit('DeepSeek 不可用（缺少 API key），无法补题')

    generated: list[dict] = []
    for node_id, gap in shortfalls:
        generated.extend(generate_for_node(node_id, gap, stems_by_node.get(node_id, [])))

    GENERATED_PATH.write_text(json.dumps(generated, ensure_ascii=False, indent=2), encoding='utf-8')
    unified = records + generated
    OUTPUT_PATH.write_text(json.dumps(unified, ensure_ascii=False, indent=2), encoding='utf-8')

    final = Counter(r['kg_node_id'] for r in unified)
    print(f'\n新生成 {len(generated)} 道（全部标记 needs_review=1）')
    print('\n最终各节点题目数：')
    still_short = []
    for domain in KNOWLEDGE_DOMAINS:
        print(f'  [{domain.title}]')
        for entry in nodes_for_domain(domain.key):
            count = final.get(entry.kg_id, 0)
            flag = '' if count >= args.target else f'  <-- 仍缺 {args.target - count} 题'
            print(f'    {entry.kg_id:16s} {entry.label:12s} {count:3d}{flag}')
            if count < args.target:
                still_short.append(entry.kg_id)
    print(f'\n合计 {len(unified)} 道题；仍不足的节点：{still_short or "无"}')
    print(f'-> {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
