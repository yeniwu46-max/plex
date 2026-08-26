"""增强 #1：为每道题生成"小E"讲述的题目背景小故事，写入 `problems.background`。

设计要点（详见 REPORT.md 增强篇）：
  - 人设与语气复用 `app/services/messenger_chat.py` 里已经定义好的"小E"驿站
    助手人设，不另起炉灶；只是把对话场景换成"讲故事引出编程题"。
  - 同一个 concept_group（题号字母分组，如 D=循环）下的题目背景是同一个
    "故事世界"的连续章节，按 problem_no 顺序推进情节，后一章会引用前一章
    的摘要以保持连贯，而不是互不相关的独立小段子。
  - AI 调用链复用仓库已有的 provider 链约定："讯飞星火 → 讯飞星辰 Agent →
    DeepSeek → 规则模板兜底"，与 `messenger_chat.py`/`pedagogical_resource.py`
    的降级顺序一致。任一步抛异常或返回空都会静默降级到下一步，最终必定有
    可用文本（模板兜底是纯规则、确定性的，不依赖网络）。
  - 每条结果都记录 `background_source`（'ai:spark' | 'ai:xfyun_agent' |
    'ai:deepseek' | 'template'），写进 DB 供审计，不面向学生展示。

用法（在 backend/ 目录下执行，需要先 `python manage.py upgrade` 到最新）：
    python scripts/problem_bank_import/generate_backgrounds.py               # 仅补全缺失的
    python scripts/problem_bank_import/generate_backgrounds.py --force       # 全部重新生成
    python scripts/problem_bank_import/generate_backgrounds.py --dry-run     # 只打印不写文件

本脚本只读写 `output/problems.json`（同时可选地同步进本地 SQLite via
--sync-db），不会重新跑一遍原始 dump 清洗（那是 clean_and_transform.py 的
职责）；也会把"AI 全程失败、需要人工复核故事质量"的题目记录进
`output/manual_review_items_backgrounds.json`，供 finalize_manual_review.py
合并进最终版 manual_review.md。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / '.env')
except ImportError:
    pass

OUT_DIR = Path(__file__).resolve().parent / 'output'
PROBLEMS_JSON = OUT_DIR / 'problems.json'
REVIEW_ITEMS_PATH = OUT_DIR / 'manual_review_items_backgrounds.json'

ASSISTANT_PERSONA = (
    '你叫小E，是 PLEX / A3 学习系统里的驿站助手。你现在要为一套 Python 编程练习题库'
    '撰写"题目背景"小故事，用你自己的口吻（第一人称"我"或直接讲述，不要写"小E："这样'
    '的自称开头）讲给学生听。'
)

STORY_BRIEF = (
    '故事主题不限于编程本身，可以是天文地理、人文历史、日常生活、神话传说等，只要能'
    '自然引出这道题要完成的编程任务即可。同一知识点分组下的题目背景必须是同一个连续'
    '小故事的不同章节，情节要向前推进、承接上一章内容，不要重复或另起无关的新故事。'
    '每段控制在 100-160 字中文，不使用星号加粗、不提及AI/模型/接口/供应商来源，结尾'
    '自然过渡到"接下来要做的编程任务是什么"，但不要写具体代码、不要剧透解法或输出格式。'
)

# 世界观设定沿用旧题库自身的 quest 章节命名（受伤的兔子/可怕的老虎/新大陆等，见
# problem_legacy_quest_map / REPORT.md），让新故事和题库原有的"关卡"氛围一致，
# 而不是凭空编造一套无关的世界观。
WORLD_BY_GROUP = {
    'A': {
        'name': '新大陆·启程',
        'setting': (
            '小E带着一位刚抵达"新大陆"的新手同伴（就叫他"小步"）落地在驿站门口，'
            '一切都要从最基础的自我介绍、说话方式学起。'
        ),
        'companion': '小步',
        'scenes': ['驿站门口', '新大陆的第一条街', '写着欢迎语的告示牌前', '驿站的储物角落'],
    },
    'B': {
        'name': '运算集市',
        'setting': (
            '小E领着小步走进新大陆最热闹的"运算集市"——这里商贩们用加减乘除、'
            '取余取整来讨价还价，谁算得又快又准，谁就能换到最好的货。'
        ),
        'companion': '小步',
        'scenes': ['集市入口的称重摊', '换算货币的钱庄', '拼图摊位', '卖水果论堆计价的小摊'],
    },
    'C': {
        'name': '十字路口森林',
        'setting': (
            '出了集市，小E和小步一头扎进"十字路口森林"——林子里布满岔路，每一步'
            '都得先判断条件，才能决定往哪走。'
        ),
        'companion': '小步',
        'scenes': ['第一处岔路口', '写着谜语的路牌前', '需要通行证的关卡', '雾气弥漫的分叉小径'],
    },
    'D': {
        'name': '循环回廊',
        'setting': (
            '森林尽头是一座绕不出去的"循环回廊"，传说里那只可怕的老虎就守在回廊深处，'
            '巡逻的脚步日复一日、一圈又一圈——小E说，看懂了"重复"的规律，就能看穿回廊的秘密。'
        ),
        'companion': '小步',
        'scenes': [
            '回廊入口的石阶', '第一圈巡逻路线', '老虎脚印排成的规律', '回廊中段的休息平台',
            '刻满数字的石柱', '越走越深的第二段回廊', '回音特别响的转角', '布满藤蔓的岔口',
            '老虎巡逻的瞭望台', '回廊尽头透出的光',
        ],
    },
    'E': {
        'name': '魔法工坊',
        'setting': (
            '走出回廊，小E带小步找到了魔王松鼠贪吃时落下的"魔法工坊"——工坊里的老师傅'
            '教他们把常用的小魔法打包成"可以反复召唤的咒语"，这就是函数。'
        ),
        'companion': '小步',
        'scenes': ['工坊的第一张工作台', '挂满零件的墙面', '试炼咒语的小房间', '师傅的配方笔记本'],
    },
    'F': {
        'name': '百宝箱阁楼',
        'setting': (
            '熊猫想拍一张彩色照片，翻箱倒柜找道具，把小E和小步也拉去帮忙整理阁楼里的'
            '"百宝箱"——箱子里什么形状、什么类型的东西都有，得先分门别类才找得到。'
        ),
        'companion': '小步',
        'scenes': ['阁楼入口的旧木箱', '贴着标签的架子', '熊猫的道具清单', '摆满杂物的角落'],
    },
    'G': {
        'name': '山顶天文台',
        'setting': (
            '整理完百宝箱，小E带小步登上山顶的天文台，眺望新大陆的全貌——这里的观测'
            '记录本用更复杂的结构记下满天星辰，是新大陆里"进阶收纳术"的终点。'
        ),
        'companion': '小步',
        'scenes': ['天文台顶层的望远镜前'],
    },
}

CONNECTORS = ['紧接着上一次的脚步，', '故事继续往前走，', '还没来得及喘口气，', '眼前的场景一换，', '照旧，']


def _load_problems() -> list[dict]:
    with open(PROBLEMS_JSON, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def _save_problems(problems: list[dict]) -> None:
    with open(PROBLEMS_JSON, 'w', encoding='utf-8') as fh:
        json.dump(problems, fh, ensure_ascii=False, indent=2, default=str)


def _short_desc(problem: dict) -> str:
    text = (problem.get('description_cn') or problem.get('description_en') or problem.get('title_cn') or '').strip()
    text = text.replace('\n', ' ')
    return text[:120]


def _ai_chain(system: str, user: str) -> tuple[str | None, str | None]:
    """DeepSeek → 讯飞星火 → 讯飞星辰 Agent，依次尝试，返回 (文本, 来源标签)。"""
    try:
        from agents.llm_client import chat_text, llm_provider

        provider = llm_provider()
        if provider:
            text = chat_text(system=system, user=user, timeout=15, max_tokens=420, provider=provider)
            if text and text.strip():
                return text.strip(), 'ai:deepseek'
    except Exception:
        pass

    try:
        from app.services.iflytek_spark import IflytekSparkService

        if IflytekSparkService.configured():
            text = IflytekSparkService.chat_text(system, user, timeout=12)
            if text and text.strip():
                return text.strip(), 'ai:spark'
    except Exception:
        pass

    try:
        from app.services.xfyun_agent import XfyunAgentService

        if XfyunAgentService.configured():
            text = XfyunAgentService.chat_text(user_id=0, message=user, context=system, timeout=12)
            if text and text.strip():
                return text.strip(), 'ai:xfyun_agent'
    except Exception:
        pass

    return None, None


def _template_chapter(group: str, index: int, total: int, problem: dict, prev_summary: str) -> str:
    world = WORLD_BY_GROUP.get(group, WORLD_BY_GROUP['A'])
    scene = world['scenes'][(index - 1) % len(world['scenes'])]
    connector = CONNECTORS[(index - 1) % len(CONNECTORS)]
    opening = world['setting'] if index == 1 else connector
    recap = f'（接上回：{prev_summary[:40]}……）' if index > 1 and prev_summary else ''
    title = problem.get('title_cn') or problem.get('title_en') or '这道题'
    return (
        f'{opening}{recap}这是「{world["name"]}」第 {index}/{total} 篇。'
        f'小E和{world["companion"]}来到了{scene}，眼前摆着一个绕不开的小麻烦——'
        f'要解决它，正好用得上「{title}」这道题里练的本领。写完这段程序，'
        f'{world["companion"]}才能带着答案继续往前走。'
    )


def generate(*, missing_only: bool, dry_run: bool) -> dict:
    problems = _load_problems()
    by_group: dict[str, list[dict]] = {}
    for p in problems:
        by_group.setdefault(p['concept_group'], []).append(p)
    for rows in by_group.values():
        rows.sort(key=lambda r: r['problem_no'])

    stats = {'ai:spark': 0, 'ai:xfyun_agent': 0, 'ai:deepseek': 0, 'template': 0, 'skipped_existing': 0}
    review_items: list[dict] = []

    for group, rows in sorted(by_group.items()):
        total = len(rows)
        prev_summary = ''
        for index, problem in enumerate(rows, start=1):
            already = bool(problem.get('background'))
            if already:
                # 幂等：即使跳过重新生成，也要用已有背景续上下文，保证后面
                # 新生成的章节仍然承接得上（见 clean_and_transform.py 对
                # background 字段的"跨脚本保留"说明）。
                prev_summary = problem['background'][:80]
            if already and missing_only:
                stats['skipped_existing'] += 1
                continue

            world = WORLD_BY_GROUP.get(group, WORLD_BY_GROUP['A'])
            system = f'{ASSISTANT_PERSONA}{STORY_BRIEF}'
            user = (
                f'故事世界设定：{world["setting"]}\n'
                f'这是「{world["name"]}」第 {index}/{total} 篇章节。\n'
                f'上一章节摘要：{prev_summary or "（这是第一章，无需承接）"}\n'
                f'本题信息：\n'
                f'- 题号/标题：{problem["problem_no"]} 《{problem.get("title_cn") or problem.get("title_en")}》\n'
                f'- 知识点：{problem.get("concept") or group}\n'
                f'- 题目大意（仅供你理解任务，不要在背景里剧透具体解法/输出格式）：{_short_desc(problem)}\n'
                f'请撰写这一章节的题目背景小故事（100-160字，中文，直接开始讲述）。'
            )

            text, source = _ai_chain(system, user)
            if not text:
                text = _template_chapter(group, index, total, problem, prev_summary)
                source = 'template'
                review_items.append({
                    'table': 'problem',
                    'id': problem['id'],
                    'issue': 'AI 全链路（讯飞星火/星辰Agent/DeepSeek）均不可用或返回空，题目背景已使用规则模板兜底生成',
                    'suggestion': '功能不受影响（模板故事仍保持知识点内连续性），如需更丰富的文风可在网络/凭证恢复后重跑 --force 重新生成',
                })

            problem['background'] = text
            problem['background_source'] = source
            prev_summary = text[:80]
            stats[source] = stats.get(source, 0) + 1
            print(f'[{problem["problem_no"]}] source={source} len={len(text)}')
            if source != 'template':
                time.sleep(0.2)  # 轻微限速，避免连续请求触发限流

    if not dry_run:
        _save_problems(problems)
        with open(REVIEW_ITEMS_PATH, 'w', encoding='utf-8') as fh:
            json.dump(review_items, fh, ensure_ascii=False, indent=2)

    stats['manual_review_count'] = len(review_items)
    return stats


def main():
    parser = argparse.ArgumentParser(description='为题库生成"小E"题目背景小故事')
    parser.add_argument('--force', action='store_true', help='强制重新生成全部题目的背景（默认只补全缺失的）')
    parser.add_argument('--dry-run', action='store_true', help='只打印结果，不写回 output/problems.json')
    args = parser.parse_args()

    stats = generate(missing_only=not args.force, dry_run=args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
