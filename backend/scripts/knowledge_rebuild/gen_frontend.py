# -*- coding: utf-8 -*-
"""从后端知识点注册表生成前端数据文件。

前端原来自己手写了一份 7 星域 / 16 节点的目录，和后端各改各的，改一处就漂移。
现在这几个文件由本脚本从 `knowledge_node_registry` + `kg_topology` 生成：

- frontend/src/data/knowledgeNodeRegistry.ts
- frontend/src/data/starPathDomains.ts
- frontend/src/data/knowledgeGraphData.ts
- frontend/src/data/teacherKnowledgeCatalog.ts

星轨的叙事文案（小E 的探索故事）无法从注册表推导，集中放在下面的 NODE_NARRATIVE
与 DOMAIN_NARRATIVE 里，改文案只改这一处。

用法：
    python scripts/knowledge_rebuild/gen_frontend.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data.kg_topology import KG_EDGES, KG_NODES  # noqa: E402
from app.data.knowledge_node_registry import (  # noqa: E402
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    get_domain,
    nodes_for_domain,
)

FRONTEND_DATA = BACKEND_ROOT.parent / 'frontend' / 'src' / 'data'

BANNER = '/** 本文件由 backend/scripts/knowledge_rebuild/gen_frontend.py 生成，请勿手改。 */'

LEVEL_LABEL = {'basic': '入门', 'intermediate': '进阶', 'advanced': '挑战'}

# 每个大类在星图叙事里的星球设定
DOMAIN_NARRATIVE = {
    'lang-basics': {
        'planet': '启航星',
        'description': '你与小E 降落「启航星」，写下第一行 print，给变量命名，再让程序听懂人的输入。',
    },
    'sequence': {
        'planet': '运算星云',
        'description': '「运算星云」里所有指令按书写顺序逐条执行，小E 教你校准算术、表达式与类型转换。',
    },
    'branch': {
        'planet': '分支峡谷',
        'description': '「分支峡谷」的岔路要靠条件判断来选，if / elif / else 决定飞船走哪一条。',
    },
    'loop': {
        'planet': '循环环带',
        'description': '「循环环带」上重复的事交给循环去做，for、while、嵌套与跳出各有各的用法。',
    },
    'array': {
        'planet': '货舱区',
        'description': '「货舱区」用列表把一批数据装在一起，遍历、统计，再堆成二维的货架。',
    },
    'string': {
        'planet': '语符卫星',
        'description': '「语符卫星」上的信息都是文本，逐字取用、切片截取、方法加工。',
    },
    'function': {
        'planet': '封装空间站',
        'description': '在「封装空间站」把一段逻辑打包成函数反复调用，再让它调用自己完成递归。',
    },
    'search': {
        'planet': '算法深空',
        'description': '「算法深空」里数据浩瀚，顺序查找、二分查找、排序与统计帮你精准定位。',
    },
}

# 每个知识点的星轨文案。summary 面向学生讲故事，detail 讲清覆盖范围。
# question_id 关联 pythonTrialQuestions.ts 里的静态题，缺省则完全走接口取真题。
NODE_NARRATIVE: dict[str, dict] = {
    'lang-print': {
        'summary': '小E 的探测器需要发出第一束信号——用 print 向宇宙问好。',
        'detail': 'print 输出、字符串字面量、换行与逗号分隔，以及用 # 写注释。',
        'question_id': 'hello-print',
        'intro_steps': [
            '在编辑器里写 print("Hello")，点击运行测试确认输出。',
            '尝试用逗号连接多个内容：print("XP", 100)。',
            '在代码上方用 # 写一行注释，说明这段程序做什么。',
            '完成左侧示例后，点击「开始编程试炼」进入第一题。',
        ],
    },
    'lang-var': {
        'summary': '把探测器读数存进变量舱，认识 int / float / str / bool。',
        'detail': '赋值与命名、四种基础类型、type() 查看类型、不要覆盖内置名。',
        'question_id': 'var-sum',
    },
    'lang-input': {
        'summary': '接收地面站传来的指令，用 input 读进来再转成需要的类型。',
        'detail': 'input 永远返回字符串、int()/float() 转换、非法输入的异常处理。',
        'question_id': 'var-product',
    },
    'seq-arith': {
        'summary': '校准飞船的计算核心：加减乘除、整除、取余与幂运算。',
        'detail': '+ - * / 与 // % **，除法结果恒为浮点，除零会报错。',
        'question_id': 'print-calc',
    },
    'seq-expr': {
        'summary': '把多个运算拼成一条表达式，先算谁后算谁要心里有数。',
        'detail': '比较运算、and / or / not、优先级、链式比较与短路求值。',
    },
    'seq-type': {
        'summary': '数据在舱段之间流转，需要在整数、小数与文本之间来回转换。',
        'detail': 'int()/float()/str()/bool() 转换、round 与截断的差别、转换失败的 ValueError。',
    },
    'branch-if': {
        'summary': '峡谷前的第一个岔路口：条件成立走这边，否则走那边。',
        'detail': 'if 与 if-else、条件表达式的真假、冒号与缩进。',
        'question_id': 'max-of-two',
    },
    'branch-elif': {
        'summary': '三条以上的岔路要用 elif 串起来，顺序决定结果。',
        'detail': 'if-elif-else 链、区间判断的书写顺序、else 兜底。',
    },
    'branch-nested': {
        'summary': '岔路里还有岔路，或者用 and / or 把条件合成一条。',
        'detail': '嵌套分支、复合条件、两种写法的相互改写、避免过深嵌套。',
        'question_id': 'capstone-fizz',
    },
    'loop-for': {
        'summary': '沿着环带跑固定圈数，for 配合 range 最省力。',
        'detail': 'for 遍历序列、range 的左闭右开、累加求和模式。',
        'question_id': 'sum-1-to-n',
    },
    'loop-while': {
        'summary': '条件成立就一直转，关键是想清楚什么时候停。',
        'detail': 'while 的循环条件、计数器与哨兵值、死循环的成因。',
        'question_id': 'loop-sum',
    },
    'loop-nested': {
        'summary': '一层环带套一层，外层管行内层管列。',
        'detail': '双重循环、打印图形与乘法表、循环次数的量级直觉。',
    },
    'loop-control': {
        'summary': '找到目标就提前跳出，遇到杂质就跳过这一轮。',
        'detail': 'break 与 continue、只影响最内层循环、for...else 的含义。',
        'question_id': 'fizz-n',
    },
    'array-basic': {
        'summary': '货舱用列表装货：按位置取、切一段、随时增删。',
        'detail': '创建列表、正负索引、切片、append / insert / pop / remove 与 len。',
        'question_id': 'list-max',
    },
    'array-traverse': {
        'summary': '清点整舱货物：遍历一遍就能求和、计数、找出最值。',
        'detail': 'for 遍历列表、enumerate 取下标、sum / max / min 内置函数。',
    },
    'array-2d': {
        'summary': '把货架堆成两层，用行列坐标定位每一格。',
        'detail': '嵌套列表表示表格与矩阵、grid[i][j]、二维列表的正确创建方式。',
    },
    'string-index': {
        'summary': '卫星传来的电文可以逐字取用，也能整段截取。',
        'detail': '按下标取字符、负索引、切片 s[a:b:c]、反转与字符串不可变。',
    },
    'string-method': {
        'summary': '电文需要清洗：拆分、拼接、替换、去空白、改大小写。',
        'detail': 'split / join / replace / strip / upper / lower / find，方法返回新串。',
    },
    'string-scan': {
        'summary': '逐字扫描整段电文，数出每个字符出现了几次。',
        'detail': '遍历字符串、count 统计、回文判断、大小写与空格归一化。',
    },
    'func-define': {
        'summary': '把常用的一段逻辑封进函数，之后一句话就能调用。',
        'detail': 'def 定义、函数名与调用、函数体缩进、docstring。',
    },
    'func-param': {
        'summary': '给函数递进去参数，让它把结果交回来。',
        'detail': '位置参数与默认参数、return 与 None、局部变量与作用域。',
    },
    'func-recursion': {
        'summary': '让函数调用它自己，但一定要留好出口。',
        'detail': '递归出口与递推、阶乘与斐波那契、递归深度与重复计算。',
    },
    'search-linear': {
        'summary': '从头到尾一个个比对，找到目标就停下。',
        'detail': '顺序查找、返回下标或 -1、in 运算符、O(n) 的代价。',
    },
    'search-binary': {
        'summary': '数据排好序后，每次砍掉一半，定位快得多。',
        'detail': '二分查找的有序前提、low / high / mid、循环边界与死循环。',
        'question_id': 'algo-binary-search',
    },
    'search-sort': {
        'summary': '把货物按大小排好：相邻交换，或每轮挑出最小的。',
        'detail': '冒泡排序与选择排序、双重循环结构、与内置 sorted 的关系。',
        'question_id': 'algo-bubble-sort',
    },
    'search-stat': {
        'summary': '给整批数据做一次体检：求和、计数、找最值、去掉重复。',
        'detail': '累加与计数、max / min、set 去重与保序去重、字典计数。',
    },
}


def ts(value) -> str:
    """按 TS 字面量输出（用 JSON 保证转义正确，单引号更贴近前端风格）。"""
    return json.dumps(value, ensure_ascii=False)


def check_coverage() -> None:
    missing = [e.kg_id for e in KNOWLEDGE_NODE_REGISTRY if e.kg_id not in NODE_NARRATIVE]
    if missing:
        raise SystemExit(f'NODE_NARRATIVE 缺少节点文案：{missing}')
    missing_domains = [d.key for d in KNOWLEDGE_DOMAINS if d.key not in DOMAIN_NARRATIVE]
    if missing_domains:
        raise SystemExit(f'DOMAIN_NARRATIVE 缺少大类文案：{missing_domains}')


def gen_node_registry() -> str:
    lines = [
        BANNER,
        '/** 与 backend/app/data/knowledge_node_registry.py 一一对应。 */',
        '',
        'export interface KnowledgeNodeRegistryEntry {',
        '  kg_id: string',
        '  label: string',
        '  domain_key: string',
        '  domain_title: string',
        '  /** 重排后星轨 id 与图谱 id 统一，保留字段只为兼容旧调用 */',
        '  star_path_id: string',
        '  knowledge_keys: string[]',
        '  level: string',
        '  default_difficulty: number',
        '  summary: string',
        '}',
        '',
        'export const KNOWLEDGE_NODE_REGISTRY: KnowledgeNodeRegistryEntry[] = [',
    ]
    for entry in KNOWLEDGE_NODE_REGISTRY:
        domain = get_domain(entry.domain_key)
        lines.append(
            '  { '
            f'kg_id: {ts(entry.kg_id)}, label: {ts(entry.label)}, '
            f'domain_key: {ts(entry.domain_key)}, domain_title: {ts(domain.title)}, '
            f'star_path_id: {ts(entry.kg_id)}, knowledge_keys: {ts(list(entry.knowledge_keys))}, '
            f'level: {ts(entry.level)}, default_difficulty: {entry.default_difficulty}, '
            f'summary: {ts(entry.summary)}'
            ' },'
        )
    lines += [
        ']',
        '',
        'const BY_ID = new Map(KNOWLEDGE_NODE_REGISTRY.map((e) => [e.kg_id, e]))',
        '',
        'const BY_LEGACY_KEY = new Map<string, KnowledgeNodeRegistryEntry>()',
        'for (const entry of KNOWLEDGE_NODE_REGISTRY) {',
        '  for (const key of entry.knowledge_keys) {',
        '    if (!BY_LEGACY_KEY.has(key)) BY_LEGACY_KEY.set(key, entry)',
        '  }',
        '}',
        '',
        'export function getKnowledgeNode(kgId: string): KnowledgeNodeRegistryEntry | undefined {',
        '  return BY_ID.get(kgId)',
        '}',
        '',
        '/** 把历史 knowledge_key（intro / loop / algo-sum …）解析成新节点 id。 */',
        'export function kgIdFromKey(key: string | null | undefined): string | undefined {',
        '  if (!key) return undefined',
        '  return BY_ID.get(key)?.kg_id ?? BY_LEGACY_KEY.get(key.toLowerCase())?.kg_id',
        '}',
        '',
        '/** 星轨 id 与图谱 id 已统一，保留以兼容旧调用。 */',
        'export function kgIdFromStarPath(starPathId: string): string | undefined {',
        '  return BY_ID.get(starPathId)?.kg_id',
        '}',
        '',
        'export function starPathIdFromKg(kgId: string): string | undefined {',
        '  return BY_ID.get(kgId)?.kg_id',
        '}',
        '',
    ]
    return '\n'.join(lines)


def gen_star_path_domains() -> str:
    lines = [
        BANNER,
        '/** 与 backend/app/data/knowledge_node_registry.py 对齐 · Python 八大学域 26 知识点 */',
        '',
        'export interface StarPathKnowledgePoint {',
        '  id: string',
        '  domainKey: string',
        '  title: string',
        '  summary: string',
        '  detail: string',
        '  tags: string[]',
        "  level: '入门' | '进阶' | '挑战'",
        '  /** 初识导引步骤（仅首个知识点） */',
        '  introSteps?: string[]',
        '  /** 关联 Python 试炼题 id（缺省则完全走接口取真题） */',
        '  questionId?: string',
        '}',
        '',
        'export interface StarPathDomainMeta {',
        '  key: string',
        '  title: string',
        '  description: string',
        '  focus: string',
        '  knowledgePoints: StarPathKnowledgePoint[]',
        '}',
        '',
        "export const STAR_PATH_TAB_ALL = 'all' as const",
        '',
        'export const STAR_PATH_TABS: Array<{ key: typeof STAR_PATH_TAB_ALL | string; label: string }> = [',
        "  { key: STAR_PATH_TAB_ALL, label: '全部阶段' },",
    ]
    for domain in KNOWLEDGE_DOMAINS:
        lines.append(f'  {{ key: {ts(domain.key)}, label: {ts(domain.title)} }},')
    lines += [']', '', 'export const STAR_PATH_DOMAINS: StarPathDomainMeta[] = [']

    for domain in KNOWLEDGE_DOMAINS:
        narrative = DOMAIN_NARRATIVE[domain.key]
        lines += [
            '  {',
            f'    key: {ts(domain.key)},',
            f'    title: {ts(domain.title)},',
            f'    description: {ts(narrative["description"])},',
            f'    focus: {ts(domain.focus)},',
            '    knowledgePoints: [',
        ]
        for entry in nodes_for_domain(domain.key):
            node = NODE_NARRATIVE[entry.kg_id]
            # tags[0] 必须是节点 id：练习题缓存按它回查接口
            tags = [entry.kg_id] + [
                key for key in entry.knowledge_keys if key != entry.kg_id
            ][:3]
            lines += [
                '      {',
                f'        id: {ts(entry.kg_id)},',
                f'        domainKey: {ts(domain.key)},',
                f'        title: {ts(entry.label)},',
                f'        summary: {ts(node["summary"])},',
                f'        detail: {ts(node["detail"])},',
            ]
            if node.get('intro_steps'):
                lines.append('        introSteps: [')
                for step in node['intro_steps']:
                    lines.append(f'          {ts(step)},')
                lines.append('        ],')
            lines.append(f'        tags: {ts(tags)},')
            lines.append(f'        level: {ts(LEVEL_LABEL[entry.level])},')
            if node.get('question_id'):
                lines.append(f'        questionId: {ts(node["question_id"])},')
            lines.append('      },')
        lines += ['    ],', '  },']

    lines += [
        ']',
        '',
        'export function getStarPathDomain(key: string): StarPathDomainMeta | undefined {',
        '  return STAR_PATH_DOMAINS.find((d) => d.key === key)',
        '}',
        '',
        'export function getKnowledgePointsForDomain(domainKey: string): StarPathKnowledgePoint[] {',
        '  return getStarPathDomain(domainKey)?.knowledgePoints ?? []',
        '}',
        '',
        'export function getStarPathKnowledgePoint(id: string) {',
        '  for (const domain of STAR_PATH_DOMAINS) {',
        '    const point = domain.knowledgePoints.find((p) => p.id === id)',
        '    if (point) return { domain, point }',
        '  }',
        '  return null',
        '}',
        '',
    ]
    return '\n'.join(lines)


def gen_knowledge_graph_data() -> str:
    lines = [
        BANNER,
        '/** 静态拓扑，与 backend/app/data/kg_topology.py 对齐，接口失败时作轻量回退。 */',
        '',
        "export type KgNodeStatus = 'mastered' | 'learning' | 'weak' | 'unlearned' | 'recommended'",
        '',
        'export interface KgNode {',
        '  id: string',
        '  label: string',
        '  domain: string',
        '  status: KgNodeStatus',
        '  description: string',
        "  level: 'basic' | 'intermediate' | 'advanced'",
        '  answered_count?: number',
        '  correct_count?: number',
        '  wrong_count?: number',
        '  accuracy?: number | null',
        '  fail_count?: number',
        '  weak_score?: number',
        '  affected_student_count?: number',
        '  student_count?: number',
        '  weak_count?: number',
        '  not_mastered_percent?: number',
        '  top_error_types?: Array<{ error_type: string; count: number }>',
        '  x?: number',
        '  y?: number',
        '}',
        '',
        "export type KgEdgeType = 'prerequisite' | 'related' | 'path' | 'advanced'",
        '',
        'export interface KgEdge {',
        '  id: string',
        '  source: string',
        '  target: string',
        '  type: KgEdgeType',
        '  label?: string',
        '}',
        '',
        'export const KG_NODE_STATUS_COLOR: Record<KgNodeStatus, string> = {',
        "  mastered: '#22c55e',",
        "  learning: '#38bdf8',",
        "  weak: '#f87171',",
        "  unlearned: '#475569',",
        "  recommended: '#a78bfa',",
        '}',
        '',
        'export const KG_NODE_STATUS_LABEL: Record<KgNodeStatus, string> = {',
        "  mastered: '已掌握',",
        "  learning: '学习中',",
        "  weak: '薄弱',",
        "  unlearned: '未学习',",
        "  recommended: '推荐学习',",
        '}',
        '',
        'export const KG_NODES: KgNode[] = [',
    ]
    for node in KG_NODES:
        lines.append(
            '  { '
            f'id: {ts(node["id"])}, label: {ts(node["label"])}, domain: {ts(node["domain"])}, '
            f"status: 'unlearned', level: {ts(node['level'])}, "
            f'description: {ts(node.get("description", ""))}, x: {node["x"]}, y: {node["y"]}'
            ' },'
        )
    lines += [']', '', 'export const KG_EDGES: KgEdge[] = [']
    for edge in KG_EDGES:
        label = edge.get('label') or ''
        lines.append(
            '  { '
            f'id: {ts(edge["id"])}, source: {ts(edge["source"])}, target: {ts(edge["target"])}, '
            f'type: {ts(edge["type"])}, label: {ts(label)}'
            ' },'
        )
    lines += [
        ']',
        '',
        'export function getStudentNodes(masteredIds: string[] = []): KgNode[] {',
        '  return KG_NODES.map((node) => ({',
        '    ...node,',
        "    status: masteredIds.includes(node.id) ? 'mastered' : node.status,",
        '  }))',
        '}',
        '',
    ]
    return '\n'.join(lines)


def gen_teacher_catalog() -> str:
    lines = [
        BANNER,
        '/** 与 backend/app/data/knowledge_catalog.py 对齐 */',
        '',
        'export interface KnowledgePointDef {',
        '  key: string',
        '  label: string',
        '}',
        '',
        'export interface KnowledgeDomainDef {',
        '  key: string',
        '  label: string',
        '  points: KnowledgePointDef[]',
        '}',
        '',
        'export const TEACHER_KNOWLEDGE_UNIVERSE: KnowledgeDomainDef[] = [',
    ]
    for domain in KNOWLEDGE_DOMAINS:
        lines += [
            '  {',
            f'    key: {ts(domain.key)},',
            f'    label: {ts(domain.title)},',
            '    points: [',
        ]
        for entry in nodes_for_domain(domain.key):
            lines.append(f'      {{ key: {ts(entry.kg_id)}, label: {ts(entry.label)} }},')
        lines += ['    ],', '  },']
    lines += [
        ']',
        '',
        'export function labelForKnowledgeKey(key: string): string {',
        '  for (const domain of TEACHER_KNOWLEDGE_UNIVERSE) {',
        '    const point = domain.points.find((p) => p.key === key)',
        '    if (point) return point.label',
        '  }',
        '  return key',
        '}',
        '',
    ]
    return '\n'.join(lines)


def main() -> None:
    check_coverage()
    outputs = {
        'knowledgeNodeRegistry.ts': gen_node_registry(),
        'starPathDomains.ts': gen_star_path_domains(),
        'knowledgeGraphData.ts': gen_knowledge_graph_data(),
        'teacherKnowledgeCatalog.ts': gen_teacher_catalog(),
    }
    for filename, content in outputs.items():
        path = FRONTEND_DATA / filename
        path.write_text(content, encoding='utf-8')
        print(f'写入 {path.relative_to(BACKEND_ROOT.parent)}（{len(content.splitlines())} 行）')


if __name__ == '__main__':
    main()
