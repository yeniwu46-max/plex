"""Build immutable AI-assisted review drafts; never execute candidate programs.

Expected cases below are explicitly authored from each statement, not harvested
from a candidate. They remain drafts until a real teacher checks them.
"""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.data.knowledge_node_registry import get_entry
from app.services.counterexample_contract import specification, candidate, digest

DESTINATION=ROOT/'app/data/counterexample_catalog_v1.json'
ROWS=[]
PERM=['permutation_invariant']
SUM=PERM+['append_zero_invariant','concatenation_additive']
PROPERTY_NAMES={'permutation_invariant':'重排不改变结果','duplicate_invariant':'加入已有元素不改变结果',
    'append_zero_invariant':'追加零不改变结果','concatenation_additive':'数组重复一遍使结果翻倍','result_is_member':'非空数组的结果来自输入元素'}


def function(body):
    return 'def solve(data):\n'+'\n'.join('    '+line for line in body.split('\n'))


def add(key,title,statement,concept,reference,fixed,buggy,explanation,tests,*,output=None,properties=(),exceptions=(),level='入门'):
    kind={'L':'loop_boundary','E':'empty_input','D':'duplicate_elements'}[key[0]]
    spec=specification({'title':title,'statement':statement,'concept_id':concept,
        'input_contract':{'type':'integer_array','minimum':-4,'maximum':4,'min_items':0,'max_items':8},
        'output_contract':output or {'type':'integer','minimum':-200,'maximum':200},
        'reference_code':function(reference),'tests':[{'input':i,'expected':o} for i,o in tests],
        'reference_note':f'AI 辅助编写待审草稿 {key}。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。',
        'allowed_bug_exceptions':list(exceptions),
        'verification':{'policy_version':'bounded-properties-v1','boundary_checks':True,'properties':list(properties),
            'rationale':'草稿性质依据：'+('题意要求 '+ '、'.join(PROPERTY_NAMES[key] for key in properties)+'；请教师确认其适用性。' if properties else '任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。')}})
    proposed=candidate({'buggy_code':function(buggy),'fixed_code':function(fixed),'bug_kind':kind,'explanation':explanation})
    assert get_entry(concept),concept
    row={'id':key,'revision':1,'difficulty':level,'objective':explanation,
         'provenance':'ai_assisted_draft','human_review_status':'pending','specification':spec,'candidate':proposed}
    row['content_hash']=digest(row)
    ROWS.append(row)


ARRAY={'type':'integer_array','minimum':-4,'maximum':4,'min_items':0,'max_items':8}
PREFIX={**ARRAY,'minimum':-32,'maximum':32}
BOOL={'type':'boolean'}
COUNT={'type':'integer','minimum':0,'maximum':28}

def build():
    ROWS.clear()
    add('L01','整数数组求和','返回数组所有元素之和；空数组返回 0。','loop-accumulator',
        'return sum(data)','total = 0\nfor value in data:\n    total += value\nreturn total',
        'total = 0\nfor i in range(len(data)-1):\n    total += data[i]\nreturn total',
        'range 的右边界不包含自身，少写一位会漏掉末尾元素。',
        [([],0),([3],3),([1,2],3),([-2,4],2),([0,0],0),([4,-4,2],2)],properties=SUM)
    add('L02','正数计数','统计严格大于 0 的元素个数；空数组返回 0。','loop-counter',
        'return sum(1 for value in data if value > 0)','count = 0\nfor value in data:\n    if value > 0:\n        count += 1\nreturn count',
        'count = 0\nfor i in range(1, len(data)):\n    if data[i] > 0:\n        count += 1\nreturn count',
        '下标从 1 开始会跳过第一项，第一项为正数时计数偏小。',
        [([],0),([2],1),([-2],0),([3,0,-1],1),([1,2,2],3),([0,4],1)],output=COUNT,properties=SUM)
    add('L03','查找首个零','返回第一次出现 0 的下标；没有 0 或输入为空时返回 -1。','search-linear',
        'return data.index(0) if 0 in data else -1','for i in range(len(data)):\n    if data[i] == 0:\n        return i\nreturn -1',
        'for i in range(len(data)-1):\n    if data[i] == 0:\n        return i\nreturn -1',
        '顺序查找漏掉末尾位置，会把只在最后出现的目标误判为不存在。',
        [([],-1),([0],0),([2,0],1),([0,2,0],0),([-1,3],-1),([3,2,0],2)])
    add('L04','包含当前位置的前缀和','返回每个位置及其之前元素之和构成的数组；空数组返回 []。','array-traverse',
        'return [sum(data[:i+1]) for i in range(len(data))]',
        'result = []\ntotal = 0\nfor value in data:\n    total += value\n    result.append(total)\nreturn result',
        'result = []\ntotal = 0\nfor i in range(len(data)-1):\n    total += data[i]\n    result.append(total)\nreturn result',
        '前缀和需要为每个输入位置生成一项，循环提前结束会缺少最后一项。',
        [([],[]),([3],[3]),([1,2],[1,3]),([-2,4,-1],[-2,2,1]),([0,0],[0,0])],output=PREFIX)
    add('L05','相邻递增对计数','统计相邻两项中后一项严格大于前一项的对数；不足两项返回 0。','loop-range-detail',
        'return sum(1 for i in range(1, len(data)) if data[i] > data[i-1])',
        'count = 0\nfor i in range(len(data)-1):\n    if data[i+1] > data[i]:\n        count += 1\nreturn count',
        'count = 0\nfor i in range(len(data)-2):\n    if data[i+1] > data[i]:\n        count += 1\nreturn count',
        '相邻对共 len(data)-1 个，错误循环又少迭代一次，遗漏最后一对。',
        [([],0),([1],0),([1,2],1),([3,2,4],1),([1,1,2],1),([-2,0,3],2)],output=COUNT)
    add('L06','数组逆序','返回原数组逆序后的数组；空数组返回 []。','array-slice',
        'return data[::-1]','result = []\nfor i in range(len(data)-1, -1, -1):\n    result.append(data[i])\nreturn result',
        'result = []\nfor i in range(len(data)-1, 0, -1):\n    result.append(data[i])\nreturn result',
        '负步长 range 仍不包含终点，终点设为 0 会漏掉下标 0。',
        [([],[]),([2],[2]),([1,3],[3,1]),([-2,0,4],[4,0,-2]),([1,1],[1,1])],output=ARRAY)
    add('L07','非递减序列判定','判断数组是否非递减，即每一项不小于前一项；空数组和单元素数组返回 true。','loop-control',
        'return all(data[i-1] <= data[i] for i in range(1, len(data)))',
        'for i in range(1, len(data)):\n    if data[i] < data[i-1]:\n        return False\nreturn True',
        'for i in range(2, len(data)):\n    if data[i] < data[i-1]:\n        return False\nreturn True',
        '从第二对才开始检查，会忽略最前面的下降相邻对。',
        [([],True),([3],True),([2,1],False),([3,1,2],False),([-1,0,0],True),([1,3,2],False)],output=BOOL)
    add('L08','按位置加权求和','返回各元素乘以其从 1 开始的位置后相加的值；空数组返回 0。','loop-enumerate',
        'return sum((i+1)*value for i, value in enumerate(data))',
        'total = 0\nfor i, value in enumerate(data):\n    total += (i+1)*value\nreturn total',
        'total = 0\nfor i in range(len(data)-1):\n    total += (i+1)*data[i]\nreturn total',
        '位置权重不能补偿缺失的遍历，最后一项及其权重都被遗漏。',
        [([],0),([3],3),([1,2],5),([2,-1,3],9),([0,0],0),([-2,1],0)])
    add('L09','相邻元素乘积和','把每对相邻元素的乘积相加；不足两项返回 0。','loop-zip',
        'return sum(a*b for a, b in zip(data, data[1:]))',
        'total = 0\nfor i in range(1, len(data)):\n    total += data[i-1]*data[i]\nreturn total',
        'total = 0\nfor i in range(1, len(data)-1):\n    total += data[i-1]*data[i]\nreturn total',
        '配对遍历必须包含最后一个右端位置，否则最后一对乘积不计入。',
        [([],0),([2],0),([2,3],6),([1,2,3],8),([-2,3,-1],-9),([0,4],0)])
    add('L10','偶数下标取值','按原顺序返回下标为 0、2、4 等偶数下标的元素；空数组返回 []。','loop-range-detail',
        'return data[::2]','result = []\nfor i in range(0, len(data), 2):\n    result.append(data[i])\nreturn result',
        'result = []\nfor i in range(0, len(data)-1, 2):\n    result.append(data[i])\nreturn result',
        '长度为奇数时末尾下标为偶数，终点少一位会漏掉应该保留的末尾元素。',
        [([],[]),([2],[2]),([1,2],[1]),([1,2,3],[1,3]),([4,3,2,1],[4,2])],output=ARRAY)

    add('E01','数组最大值','返回最大元素；空数组约定返回 0。','search-stat',
        'return sorted(data)[-1] if data else 0','return max(data) if data else 0','return max(data)',
        'max 没有给出空输入的默认值，会在合法空数组上抛出 ValueError。',
        [([],0),([-3],-3),([-4,-2],-2),([1,4,2],4),([0,0],0)],properties=PERM+['result_is_member'],exceptions=['ValueError'])
    add('E02','数组最小值','返回最小元素；空数组约定返回 0。','search-stat',
        'return sorted(data)[0] if data else 0','return min(data) if data else 0','return min(data)',
        'min 需要至少一个元素，遗漏空数组分支会抛出 ValueError。',
        [([],0),([3],3),([2,4],2),([-1,4,-3],-3),([0,0],0)],properties=PERM+['result_is_member'],exceptions=['ValueError'])
    add('E03','首元素查询','返回第一个元素；空数组返回 0。','array-basic',
        'return data[:1][0] if data else 0','if not data:\n    return 0\nreturn data[0]','return data[0]',
        '下标 0 只在数组非空时存在，必须先处理合法空输入。',
        [([],0),([3],3),([-2,4],-2),([0,1],0),([2,2],2)],properties=['result_is_member'],exceptions=['IndexError'])
    add('E04','末元素查询','返回最后一个元素；空数组返回 0。','array-basic',
        'return data[len(data)-1] if data else 0','if not data:\n    return 0\nreturn data[-1]','return data[-1]',
        '负下标也不能读取空数组，-1 并不自动提供缺省值。',
        [([],0),([3],3),([-2,4],4),([1,0],0),([2,2],2)],properties=['result_is_member'],exceptions=['IndexError'])
    add('E05','整数平均值','返回所有元素之和除以元素数后的向下取整结果；空数组返回 0。','seq-arith',
        'return sum(data)//len(data) if data else 0',
        'if not data:\n    return 0\ntotal = 0\nfor value in data:\n    total += value\nreturn total//len(data)',
        'total = 0\nfor value in data:\n    total += value\nreturn total//len(data)',
        '空数组的长度为 0，遗漏分支会使整除发生 ZeroDivisionError。',
        [([],0),([3],3),([1,2],1),([-2,-1],-2),([4,-4],0)],properties=PERM,exceptions=['ZeroDivisionError'])
    add('E06','极差计算','返回最大元素与最小元素的差；空数组返回 0。','search-stat',
        'ordered = sorted(data)\nreturn ordered[-1]-ordered[0] if ordered else 0',
        'return max(data)-min(data) if data else 0','return max(data)-min(data)',
        '非空时极值差有效，但空数组不能调用缺省参数下的 max/min。',
        [([],0),([3],0),([-2,4],6),([-4,-1],3),([2,2],0)],output=COUNT,properties=PERM+['duplicate_invariant'],exceptions=['ValueError'])
    add('E07','数组连乘','返回全部元素的乘积；空数组按空乘积约定返回 1。','loop-accumulator',
        'result = 1\nfor value in data:\n    result *= value\nreturn result',
        'product = 1\nfor i in range(len(data)):\n    product *= data[i]\nreturn product',
        'if not data:\n    return 0\nproduct = 1\nfor value in data:\n    product *= value\nreturn product',
        '空乘积的单位元是 1，照搬求和的空值 0 会违反题意。',
        [([],1),([3],3),([2,-2],-4),([0,4],0),([-1,-1,-1],-1)],
        output={'type':'integer','minimum':-65536,'maximum':65536},properties=PERM)
    add('E08','序列有序性','判断数组是否非递减；空数组及单元素数组均约定为有序。','loop-control',
        'return all(data[i-1] <= data[i] for i in range(1, len(data)))',
        'for i in range(1, len(data)):\n    if data[i-1] > data[i]:\n        return False\nreturn True',
        'if not data:\n    return False\nfor i in range(1, len(data)):\n    if data[i-1] > data[i]:\n        return False\nreturn True',
        '空输入没有违反相邻顺序的元素对，题意约定应返回 true 而不是 false。',
        [([],True),([2],True),([1,2,2],True),([2,1],False),([-2,-1,0],True)],output=BOOL)
    add('E09','连续重复压缩','把每段连续相同元素压缩成一个，保留段的顺序；空数组返回 []。','array-traverse',
        'return [value for i, value in enumerate(data) if i == 0 or value != data[i-1]]',
        'result = []\nfor value in data:\n    if not result or value != result[-1]:\n        result.append(value)\nreturn result',
        'result = [data[0]]\nfor value in data[1:]:\n    if value != result[-1]:\n        result.append(value)\nreturn result',
        '用第一项初始化结果前必须判断非空，否则合法空数组会抛出 IndexError。',
        [([],[]),([2],[2]),([1,1,2,2],[1,2]),([1,2,1],[1,2,1]),([0,0,0],[0])],output=ARRAY,exceptions=['IndexError'])
    add('E10','不含当前位置的前缀和','对每个位置返回其左侧全部元素的和，不包含当前位置；空数组返回 []。','array-traverse',
        'return [sum(data[:i]) for i in range(len(data))]',
        'result = []\ntotal = 0\nfor value in data:\n    result.append(total)\n    total += value\nreturn result',
        'result = [0]\ntotal = 0\nfor value in data[:-1]:\n    total += value\n    result.append(total)\nreturn result',
        '固定预放一个 0 只适用于非空输入，空数组不应凭空增加输出位置。',
        [([],[]),([3],[0]),([1,2],[0,1]),([-2,4,1],[0,-2,2]),([0,0],[0,0])],output=PREFIX)

    add('D01','不同数值求和','返回所有不同整数的和，每个数值只计一次；空数组返回 0。','array-set',
        'return sum(set(data))','seen = []\ntotal = 0\nfor value in data:\n    if value not in seen:\n        seen.append(value)\n        total += value\nreturn total',
        'return sum(data)','未去重直接累加会把同一数值计算多次。',
        [([],0),([2,2],2),([1,2,1],3),([-2,-2,4],2),([0,0],0),([1,2,3],6)],properties=PERM+['duplicate_invariant','append_zero_invariant'])
    add('D02','不同数值计数','返回不同整数的个数；空数组返回 0。','search-stat',
        'return len(set(data))','seen = []\nfor value in data:\n    if value not in seen:\n        seen.append(value)\nreturn len(seen)',
        'return len(data)','元素总数和不同数值个数不同，出现重复时不能直接使用数组长度。',
        [([],0),([2,2],1),([1,2,1],2),([-2,0,2],3),([0,0,0],1)],output=COUNT,properties=PERM+['duplicate_invariant'])
    add('D03','数组元素总和','返回全部元素的和，重复出现的数值每次都参与；空数组返回 0。','loop-accumulator',
        'return sum(data)','total = 0\nfor value in data:\n    total += value\nreturn total',
        'return sum(set(data))','去重会丢失出现次数，普通求和不能先转为集合。',
        [([],0),([2,2],4),([1,2,1],4),([-2,-2,4],0),([0,0],0)],properties=SUM)
    add('D04','零的出现次数','返回数值 0 出现的次数；空数组返回 0。','loop-counter',
        'return data.count(0)','count = 0\nfor value in data:\n    if value == 0:\n        count += 1\nreturn count',
        'return int(0 in data)','成员判断只回答有没有零，不能区分一次和多次出现。',
        [([],0),([0],1),([0,0],2),([1,0,2,0],2),([-1,2],0)],output=COUNT,properties=PERM+['concatenation_additive'])
    add('D05','重复元素判定','判断是否存在至少两个相等元素，位置不要求相邻；空数组返回 false。','array-set',
        'return len(set(data)) < len(data)','seen = []\nfor value in data:\n    if value in seen:\n        return True\n    seen.append(value)\nreturn False',
        'return any(data[i] == data[i-1] for i in range(1, len(data)))',
        '只检查相邻项会漏掉被其他元素隔开的重复值。',
        [([],False),([1],False),([1,1],True),([1,2,1],True),([-2,0,2],False)],output=BOOL,properties=PERM)
    add('D06','有序去重','将不同整数从小到大排列后返回，每个数值只保留一项；空数组返回 []。','search-sort',
        'return sorted(set(data))','result = []\nfor value in sorted(data):\n    if not result or value != result[-1]:\n        result.append(value)\nreturn result',
        'return sorted(data)','排序只改变位置，不会自动删除重复项。',
        [([],[]),([2,2],[2]),([3,1,3],[1,3]),([-2,0,-2],[-2,0]),([2,1],[1,2])],output=ARRAY,properties=PERM+['duplicate_invariant'])
    add('D07','保持顺序的去重','删除每个数值首次出现之后的所有重复项，保留第一次出现的顺序；空数组返回 []。','array-traverse',
        'return [value for i, value in enumerate(data) if value not in data[:i]]',
        'result = []\nfor value in data:\n    if value not in result:\n        result.append(value)\nreturn result',
        'result = []\nfor value in data:\n    if not result or value != result[-1]:\n        result.append(value)\nreturn result',
        '只与结果末尾比较只能压缩连续重复，不能删除较早位置出现过的数值。',
        [([],[]),([2,2],[2]),([1,2,1],[1,2]),([3,1,3,2,1],[3,1,2]),([-2,0,-2],[-2,0])],output=ARRAY,properties=['duplicate_invariant'])
    add('D08','筛选仅出现一次的元素','返回在整个数组中恰好出现一次的元素，保持原顺序；空数组返回 []。','search-stat',
        'return [value for value in data if data.count(value) == 1]',
        'result = []\nfor value in data:\n    count = 0\n    for other in data:\n        if other == value:\n            count += 1\n    if count == 1:\n        result.append(value)\nreturn result',
        'result = []\nfor value in data:\n    if value not in result:\n        result.append(value)\nreturn result',
        '去重保留一份与原本只出现一次不是同一条件，重复值应整类排除。',
        [([],[]),([2],[2]),([2,2],[]),([1,2,1,3],[2,3]),([-2,0,0,4],[-2,4])],output=ARRAY,level='进阶')
    add('D09','最高出现频次','返回某个整数在整个数组中出现次数的最大值；空数组返回 0。','search-stat',
        'return max([data.count(value) for value in data]) if data else 0',
        'best = 0\nfor value in data:\n    count = data.count(value)\n    if count > best:\n        best = count\nreturn best',
        'best = 0\nrun = 0\nprevious = None\nfor value in data:\n    run = run+1 if value == previous else 1\n    previous = value\n    if run > best:\n        best = run\nreturn best',
        '最长连续相同段不等于总出现次数，分散出现的同值仍应累计。',
        [([],0),([2],1),([2,2],2),([1,2,1,2,1],3),([3,1,3,2],2),([-1,0,2],1)],output=COUNT,properties=PERM+['concatenation_additive'],level='进阶')
    add('D10','相等元素配对计数','统计满足 i < j 且 data[i] 等于 data[j] 的下标对数；不足两项返回 0。','loop-nested',
        'return sum(1 for i in range(len(data)) for j in range(i+1, len(data)) if data[i] == data[j])',
        'count = 0\nfor i in range(len(data)):\n    for j in range(i+1, len(data)):\n        if data[i] == data[j]:\n            count += 1\nreturn count',
        'return len(data)-len(set(data))','重复元素数量不等于相等下标对数，同值出现三次时已有三对。',
        [([],0),([2],0),([2,2],1),([2,2,2],3),([1,2,1,2],2),([0,0,0,0],6)],output=COUNT,properties=PERM,level='进阶')
    assert len(ROWS)==30 and len({row['id'] for row in ROWS})==30
    catalog={'version':'counterexample-catalog-v1','provenance':'ai_assisted_draft','human_review_status':'pending','items':ROWS}
    catalog['catalog_hash']=digest(catalog)
    DESTINATION.write_bytes(json.dumps(catalog,ensure_ascii=False,indent=2).encode('utf-8'))
    print(f'Built {len(ROWS)} pending drafts; catalog hash {catalog["catalog_hash"]}')


if __name__=='__main__':build()
