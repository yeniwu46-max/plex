"""合并三个阶段各自产出的人工核对清单 JSON，生成最终版 `manual_review.md`。

管线里每个脚本只关心自己阶段发现的问题，各自写一份 `output/manual_review_items_*.json`：
    clean_and_transform.py   -> output/manual_review_items_clean.json      （任务1原有问题）
    generate_backgrounds.py  -> output/manual_review_items_backgrounds.json（增强#1：AI全链路失败兜底提示）

这样各脚本可以独立、幂等地重跑，不会互相覆盖对方发现的问题；最后统一跑本
脚本把它们合并成一份完整的 manual_review.md。

用法（按顺序跑完整条流水线后，最后跑本脚本）：
    python clean_and_transform.py
    python generate_backgrounds.py
    python generate_tags.py
    python finalize_manual_review.py   # <- 最后一步，生成最终 manual_review.md
"""
from __future__ import annotations

import json
from pathlib import Path

from clean_and_transform import write_manual_review

OUT_DIR = Path(__file__).resolve().parent / 'output'

ITEM_SOURCES = [
    'manual_review_items_clean.json',
    'manual_review_items_backgrounds.json',
    'manual_review_items_tags.json',
]


def main():
    all_items: list[dict] = []
    found_sources = []
    for name in ITEM_SOURCES:
        path = OUT_DIR / name
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as fh:
            items = json.load(fh)
        all_items.extend(items)
        found_sources.append(name)

    # 去重：同一 (table, id, issue) 组合只保留一条，避免多次重跑管线后清单重复膨胀。
    seen = set()
    deduped = []
    for item in all_items:
        key = (item['table'], item['id'], item['issue'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    deduped.sort(key=lambda i: (i['table'], i['id']))

    write_manual_review(
        deduped,
        source_note=f'已合并以下阶段的核对清单：{", ".join(found_sources) or "(未找到任何阶段产出，请先跑清洗流水线)"}',
    )
    print(f'merged {len(all_items)} raw items -> {len(deduped)} deduped items into manual_review.md')


if __name__ == '__main__':
    main()
