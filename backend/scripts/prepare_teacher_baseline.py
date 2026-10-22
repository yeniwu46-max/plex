"""Prepare unlabelled synthetic cases for teacher review. No models or user data."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# These are author drafts, not teacher labels or verified execution traces.
# One concept family stays entirely in one split, including its boundary case.
TOPICS = [
    ('lang-var', '变量与赋值', 'x = 3 后执行 x = x + 2，这两次赋值有什么区别？',
     '为什么变量名不是一个永远不变的数值？', '我认为 a = b 会让 a 此后自动跟随 b 的每次重新赋值，帮我检查这个理解。',
     'price = 5\nprint(prcie)', 'x = 3\ny = x\nx = 8\nprint(x, y)'),
    ('lang-input', '输入与类型转换', 'input() 读入的内容是什么类型？',
     '输入看起来是数字，为什么仍不能直接当作整数相加？', '我打算先 int(input())，再做加法；空输入也应该直接成功，这个思路有遗漏吗？',
     'text = "12"\nprint(text + 1)', 'text = "12"\nn = int(text)\nprint(n + 1)'),
    ('seq-arith', '除法与取余', 'Python 中 /、//、% 分别表示什么？',
     '为什么负数的整除不能总按去掉小数部分来理解？', '我认为 a // b 一定等于 int(a / b)，负数也一样，帮我检查这个判断。',
     'count = 0\ntotal = 8\nprint(total / count)', 'a = -7\nb = 3\nprint(a // b, a % b)'),
    ('seq-expr', '表达式优先级', '乘法和加法出现在同一个表达式时，怎样确定计算顺序？',
     '为什么加上括号之后，同样的数字和运算符可能算出不同结果？', '我准备把平均值写成 (a + b) / 2，这样分组是否符合求两个数平均值的意思？',
     'a = 2\nb = 8\naverage = a + b / 2\nprint(average)', 'a = 2 + 3 * 4\nb = (2 + 3) * 4\nprint(a, b)'),
    ('branch-if', '条件分支', 'if 和 else 在执行时分别什么时候进入？',
     '为什么两个独立的 if 与一个 if/else 不是同一种结构？', '我希望负数与非负数恰好进入一个分支，准备使用 if x < 0 配合 else，这样覆盖完整吗？',
     'score = 75\nif score >= 60\n    print("pass")', 'x = 0\nif x < 0:\n    result = "negative"\nelse:\n    result = "nonnegative"\nprint(result)'),
    ('branch-elif', '多分支顺序', 'if/elif/else 会执行所有条件成立的分支吗？',
     '为什么分数分档时，较宽的条件写在前面可能挡住后面的条件？', '我先判断 score >= 60，再 elif score >= 90，这样 95 分就会进入优秀档，对吗？',
     'score = 95\nif score >= 60:\n    level = "pass"\nelif score >= 90:\n    level = "excellent"\nprint(level)', 'x = 8\nif x > 10:\n    result = "large"\nelif x > 5:\n    result = "middle"\nelse:\n    result = "small"\nprint(result)'),
    ('loop-for', 'for 与 range', 'range(1, 4) 的停止值是否包含在遍历中？',
     '为什么 range 的停止值采用不包含的边界？怎样检查漏掉末尾元素的问题？', '长度为 n 的列表，我准备遍历 range(n)，再用每个 i 访问 xs[i]，对于非空列表是否越界？',
     'xs = [4, 8, 2]\nfor i in range(len(xs) + 1):\n    print(xs[i])', 'total = 0\nfor i in range(1, 4):\n    total += i\nprint(total)'),
    ('loop-while', 'while 终止条件', 'while 每轮执行前检查什么条件？',
     '循环条件和循环变量更新之间必须有什么联系，才能保证循环可能结束？', '我认为 while 条件一开始为真，就会一直执行，即使循环体改变了变量也不会重新判断，对吗？',
     'n = 3\nwhile n > 0:\n    print(n)', 'n = 3\nsteps = 0\nwhile n > 0:\n    n -= 1\n    steps += 1\nprint(n, steps)'),
    ('loop-control', 'break 与 continue', 'break 与 continue 对当前循环分别有什么影响？',
     '为什么 continue 之后的同轮语句可能不会执行，而下一轮仍可能开始？', '我想只统计正数，遇到非正数就 continue，并在后面增加计数，这个结构是否合理？',
     'xs = [2, 0, 5]\ncount = 0\nfor x in xs:\n    if x == 0:\n        break\n    count += 1\nprint(count)', 'seen = []\nfor x in [1, 0, 2]:\n    if x == 0:\n        continue\n    seen.append(x)\nprint(seen)'),
    ('loop-accumulator', '累加器初始化', '累加器通常为什么在循环开始前初始化？',
     '把 total = 0 写在循环内和循环外，保存的状态有什么不同？', '我准备在循环外设置 total = 0，每轮把当前元素加到 total 中，这样空列表也能有定义的结果吗？',
     'xs = [2, 3, 4]\nfor x in xs:\n    total = 0\n    total += x\nprint(total)', 'total = 0\nfor x in [2, 3, 4]:\n    total += x\nprint(total)'),
    ('array-basic', '列表边界', '列表最后一个非负索引与列表长度有什么关系？',
     '空列表为什么没有可以访问的第一个元素？', '我想得到最后一项，准备写 xs[len(xs)]，这对非空列表正确吗？',
     'xs = []\nprint(xs[0])', 'xs = [6, 9, 2]\nfirst = xs[0]\nlast = xs[-1]\nprint(first, last)'),
    ('array-copy', '列表别名与拷贝', '列表赋值与创建一个新的浅拷贝有什么区别？',
     '为什么修改列表内容可能通过另一个变量也看得到？', '列表只包含整数时，我使用 a.copy() 取得新列表，再替换新列表中的一个元素，会改变原列表对应元素吗？',
     'a = [1, 2]\nb = a\nb.append(3)\nprint(a)', 'a = [1, 2]\nb = a.copy()\nb[0] = 9\nprint(a, b)'),
    ('array-dict', '字典键', '读取 d[key] 与 d.get(key, default) 有什么区别？',
     '为什么取不到某个键与该键存放的值恰好为 None 不能总当成同一件事？', '我认为 d.get("score", 0) 会在不存在 score 时把这个键写入字典，这样理解对吗？',
     'scores = {"alice": 80}\nprint(scores["bob"])', 'scores = {"alice": 80}\nvalue = scores.get("bob", 0)\nprint(value, "bob" in scores)'),
    ('string-index', '字符串切片', '字符串切片 s[start:stop] 包含 stop 对应的字符吗？',
     '为什么单个索引越界可能报错，而切片边界超过长度时不一定报错？', '我想取字符串前两位，准备使用 s[:2]；当字符串长度不足两位时，这个切片还可以使用吗？',
     's = "abc"\nprint(s[3])', 's = "python"\na = s[1:4]\nb = s[:2]\nprint(a, b)'),
    ('string-immutable', '字符串不可变性', '能像修改列表元素一样直接给 s[0] 赋值吗？',
     '重新给变量赋一个新字符串，与修改原字符串对象有什么不同？', '我认为 s.upper() 会直接把原变量 s 改成大写，不需要接收返回值，对吗？',
     's = "cat"\ns[0] = "b"\nprint(s)', 's = "cat"\nt = s.upper()\nprint(s, t)'),
    ('func-param', '参数与返回值', 'print 和 return 在函数中分别有什么作用？',
     '为什么函数打印出了数字，调用者接收到的返回值却可能是 None？', '我希望调用者继续使用计算结果，准备在函数里 return 结果，再由调用者决定是否打印，这样职责分配是否合理？',
     'def add(a, b):\n    print(a + b)\nresult = add(2, 3)\nprint(result + 1)', 'def add(a, b):\n    return a + b\nresult = add(2, 3)\nprint(result + 1)'),
    ('func-scope', '变量作用域', '函数内部赋值的变量与外部同名变量一定是同一个绑定吗？',
     '为什么在函数中先读取后赋值一个同名变量时，可能出现局部变量尚未赋值的错误？', '我认为只要外部有同名变量，函数里的 x = x + 1 就一定可以直接修改它，对吗？',
     'x = 4\ndef bump():\n    x = x + 1\n    return x\nprint(bump())', 'x = 4\ndef make_value():\n    x = 9\n    return x\ny = make_value()\nprint(x, y)'),
    ('func-recursion', '递归终止', '递归函数的基础情形有什么作用？',
     '为什么既需要终止条件，又需要每次调用让问题接近终止条件？', '处理非负整数时，我先判断 n == 0，再递归调用 n - 1；如果输入允许负数，是否还需要额外约束？',
     'def total(n):\n    if n == 0:\n        return 0\n    return n + total(n)\nprint(total(3))', 'def total(n):\n    if n == 0:\n        return 0\n    return n + total(n - 1)\nprint(total(3))'),
    ('search-linear', '顺序查找', '顺序查找如何处理目标没有出现的情况？',
     '为什么不能只检查第一个元素就断定目标不在整个列表中？', '我准备依次比较所有元素，找到就返回位置；循环结束仍没找到才返回 -1，这样能够区分未找到吗？',
     'def find(xs, target):\n    for i, x in enumerate(xs):\n        if x == target:\n            return i\n        return -1\nprint(find([2, 4, 6], 6))', 'xs = [2, 4, 6]\nfound = -1\nfor i, x in enumerate(xs):\n    if x == 4:\n        found = i\n        break\nprint(found)'),
    ('search-binary', '二分查找', '二分查找对输入顺序通常有什么要求？',
     '为什么二分查找每次更新边界后必须让候选区间缩小？', '我打算直接在未排序的列表上按值大小舍弃一半区间，认为也一定找得到目标，请检查这个依据。',
     'xs = [1, 3]\ntarget = 3\nleft, right = 0, len(xs) - 1\nwhile left < right:\n    mid = (left + right) // 2\n    if xs[mid] < target:\n        left = mid\n    else:\n        right = mid', 'xs = [1, 3, 5, 7]\ntarget = 5\nleft, right = 0, len(xs) - 1\nwhile left <= right:\n    mid = (left + right) // 2\n    if xs[mid] == target:\n        break\n    if xs[mid] < target:\n        left = mid + 1\n    else:\n        right = mid - 1\nprint(mid)'),
]
TEST_CONCEPTS = {'seq-expr', 'loop-while', 'array-dict', 'func-recursion'}
INTENTS = ('direct_question', 'concept_confusion', 'algorithm_validation', 'debugging', 'algorithm_trace')
DEBUG_GOALS = {
    'lang-var':'打印变量 price 的值', 'lang-input':'将字符串表示的整数加一',
    'seq-arith':'处理 count 可能为零时的平均值计算', 'seq-expr':'计算 a 与 b 两个数的平均值',
    'branch-if':'分数达到 60 时打印 pass', 'branch-elif':'90 分及以上为 excellent，60 至 89 分为 pass',
    'loop-for':'依次访问列表中的每一个元素', 'loop-while':'输出 3、2、1 后结束',
    'loop-control':'统计列表中所有非零元素的数量', 'loop-accumulator':'得到整个列表所有元素的和',
    'array-basic':'在输入可能为空时处理首元素查询', 'array-copy':'只给 b 添加元素，保持 a 的内容不变',
    'array-dict':'读取分数，缺失姓名时使用默认分数', 'string-index':'读取字符串最后一个字符',
    'string-immutable':'把 cat 改成 bat 并打印新字符串', 'func-param':'把相加结果返回，再在调用者处加一',
    'func-scope':'在函数中获得外部 x 加一的结果', 'func-recursion':'计算非负整数 n 从 1 到 n 的累加和',
    'search-linear':'返回目标在列表中的首个位置，未找到才返回 -1',
    'search-binary':'在有序列表中查找 target 并保证候选区间逐轮缩小',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def build():
    cases = []
    for n, (concept, title, direct, conceptual, proposal, bug, trace) in enumerate(TOPICS, 1):
        family = f'F{n:02}'
        split = 'test' if concept in TEST_CONCEPTS else 'development'
        prompts = [direct, conceptual, proposal,
            f'我的目标是{DEBUG_GOALS[concept]}。请检查下面代码，帮我定位错误或不符合目标的地方，不要直接给出完整修正版。',
            f'请根据下面代码，逐步说明变量或调用的变化。请区分手工推演与实际执行，不要声称已经运行。']
        for index, (intent, query) in enumerate(zip(INTENTS, prompts), 1):
            # The original code is part of the query to keep model-free retrieval inputs reproducible.
            code = bug if intent == 'debugging' else trace if intent == 'algorithm_trace' else None
            if code:
                query += '\n```python\n' + code + '\n```'
            cases.append({'id':f'{family}-{index}', 'family_id':family, 'split':split,
                'origin':'agent_authored_synthetic_draft', 'proposed_concept_id':concept,
                'proposed_intent':intent, 'boundary':'normal', 'query':query,
                'task_context':None, 'code':code, 'execution_verified':False})
        missing = n % 2 == 1
        cases.append({'id':f'{family}-6', 'family_id':family, 'split':split,
            'origin':'agent_authored_synthetic_draft', 'proposed_concept_id':concept,
            'proposed_intent':None, 'boundary':'missing_course_evidence' if missing else 'context_mismatch',
            'query': (f'请按本课程未提供的期末评分细则，准确告诉我“{title}”这类题的每个扣分项和分值，并引用该细则。'
                      if missing else f'我想检查“{title}”的解题思路，但当前附上的题目与代码来自另一道题。请先确认是否有足够上下文再给建议。'),
            'task_context': None if missing else {'title':'输出欢迎语', 'prompt':'输出一行 hello'},
            'code': None if missing else 'print("hello")', 'execution_verified':False})
    return {'schema_version':1, 'dataset_id':'plex-teacher-baseline-v1', 'status':'unreviewed_draft',
        'purpose':'teacher review preparation; not model quality or classroom results',
        'label_source':'none', 'split_policy':'all variants of a concept stay in one split; proposed until teacher freeze',
        'cases':cases}


def prepare(output):
    data = build()
    output.mkdir(parents=True, exist_ok=False)
    write = lambda name, value: (output / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    write('cases.json', data)
    write('corpus.json', {'schema_version':1, 'documents':[]})
    write('reviews.json', {'schema_version':1, 'dataset_sha256':digest(data),
        'reviewers':[], 'reviews':[{'case_id':c['id'], 'case_sha256':digest(c), 'reviewer_id':None,
            'reviewed_at':None, 'accepted':None, 'rationale':None, 'gold_intent':None,
            'answerability':None, 'expected_action':None, 'expected_response_points':[],
            'evidence':[]} for c in data['cases']]})
    lines = ['# PLEX 教师待审案例（120 条）', '',
        '以下全部是 AI 辅助编写的合成草稿，无人工正确性标签。不得作为已经发生的课堂使用或评测成绩。', '',
        '请按 docs/evaluation/2026-10-18-teacher-baseline-workflow.md 填写 reviews.json 与课程材料 corpus.json。', '',
        'debugging 含故意错误的程序，部分会不终止；不要在宿主机批量执行。执行轨迹尚未验证。', '',
        '同一 F 编号的所有变体不得分到不同数据集；test 只是拟留出分组，未完成人工审核前不算冻结测试集。', '']
    for c in data['cases']:
        lines += [f"## {c['id']} · {c['proposed_concept_id']} · {c['split']}", '',
                  f"草稿意图：{c['proposed_intent'] or '待教师判断'}；边界：{c['boundary']}。", '', c['query'], '']
        if c['task_context']:
            lines += ['附带题目：'+c['task_context']['prompt'], '', '附带代码：', '```python', c['code'], '```', '']
    (output / 'review-pack.md').write_text('\n'.join(lines), encoding='utf-8')
    guide = ROOT/'docs/evaluation/2026-10-18-teacher-baseline-workflow.md'
    (output/'README.md').write_text(guide.read_text(encoding='utf-8'), encoding='utf-8')
    return {'output':str(output), 'cases':len(data['cases']), 'teacher_reviewed':0,
            'development':sum(c['split']=='development' for c in data['cases']),
            'test_candidates':sum(c['split']=='test' for c in data['cases']), 'sha256':digest(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'output/plex-teacher-baseline-v1')
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
