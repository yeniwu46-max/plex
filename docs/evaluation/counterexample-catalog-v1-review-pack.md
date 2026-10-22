# PLEX 首批反例草稿：教师审核材料

仅供教师审核。含修正程序、参考程序、隐藏测试和错误解释，不应直接提供给学生。

30 道题均为 AI 辅助编写的待审草稿；开发执行通过不等于真实教师审阅。本文不预填审核人、结论或课堂效果。

版本：`counterexample-catalog-v1`；目录摘要：`c93cbc48fc9c3cf39c3e24e0a85d048d8ec0e1ea900bb9a2740cad5a784e49a4`。

审核流程：先独立阅读题意并推算预期，再对照参考/修正程序与错误说明；检查范围、性质和难度。在教师反例工作台选择班级，载入草稿，修改后保存、重新隔离验证，完成四项教学审核后发布。本材料中的笔记不会自动回写产品审核状态，真实发布以工作台中的版本和报告为准。

| 编号 | 标题 | 类型 | 难度 | 教师审核状态 |
|---|---|---|---|---|
| L01 | 整数数组求和 | 循环边界 | 入门 | 待审 |
| L02 | 正数计数 | 循环边界 | 入门 | 待审 |
| L03 | 查找首个零 | 循环边界 | 入门 | 待审 |
| L04 | 包含当前位置的前缀和 | 循环边界 | 入门 | 待审 |
| L05 | 相邻递增对计数 | 循环边界 | 入门 | 待审 |
| L06 | 数组逆序 | 循环边界 | 入门 | 待审 |
| L07 | 非递减序列判定 | 循环边界 | 入门 | 待审 |
| L08 | 按位置加权求和 | 循环边界 | 入门 | 待审 |
| L09 | 相邻元素乘积和 | 循环边界 | 入门 | 待审 |
| L10 | 偶数下标取值 | 循环边界 | 入门 | 待审 |
| E01 | 数组最大值 | 空输入 | 入门 | 待审 |
| E02 | 数组最小值 | 空输入 | 入门 | 待审 |
| E03 | 首元素查询 | 空输入 | 入门 | 待审 |
| E04 | 末元素查询 | 空输入 | 入门 | 待审 |
| E05 | 整数平均值 | 空输入 | 入门 | 待审 |
| E06 | 极差计算 | 空输入 | 入门 | 待审 |
| E07 | 数组连乘 | 空输入 | 入门 | 待审 |
| E08 | 序列有序性 | 空输入 | 入门 | 待审 |
| E09 | 连续重复压缩 | 空输入 | 入门 | 待审 |
| E10 | 不含当前位置的前缀和 | 空输入 | 入门 | 待审 |
| D01 | 不同数值求和 | 重复元素 | 入门 | 待审 |
| D02 | 不同数值计数 | 重复元素 | 入门 | 待审 |
| D03 | 数组元素总和 | 重复元素 | 入门 | 待审 |
| D04 | 零的出现次数 | 重复元素 | 入门 | 待审 |
| D05 | 重复元素判定 | 重复元素 | 入门 | 待审 |
| D06 | 有序去重 | 重复元素 | 入门 | 待审 |
| D07 | 保持顺序的去重 | 重复元素 | 入门 | 待审 |
| D08 | 筛选仅出现一次的元素 | 重复元素 | 进阶 | 待审 |
| D09 | 最高出现频次 | 重复元素 | 进阶 | 待审 |
| D10 | 相等元素配对计数 | 重复元素 | 进阶 | 待审 |


## L01 · 整数数组求和

固定修订：1；内容摘要：`7780e624c36e1eef4b270fceb653861a4e4ac2ded06caf2f856ed15f3f76e387`。

知识点：`loop-accumulator`；建议难度：入门（待教师确认）。

### 给学生的任务

返回数组所有元素之和；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    total = 0
    for i in range(len(data)-1):
        total += data[i]
    return total
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(data)
```


修正实现：


```python
def solve(data):
    total = 0
    for value in data:
        total += value
    return total
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      1,
      2
    ],
    "expected": 3
  },
  {
    "input": [
      -2,
      4
    ],
    "expected": 2
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 0
  },
  {
    "input": [
      4,
      -4,
      2
    ],
    "expected": 2
  }
]
```


基准说明：AI 辅助编写待审草稿 L01。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：range 的右边界不包含自身，少写一位会漏掉末尾元素。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "append_zero_invariant",
    "concatenation_additive",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、追加零不改变结果、数组重复一遍使结果翻倍；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:22:33.657830Z`；验证器 `differential-properties-v2`。

报告摘要：`0a2e0f2ebb925465786e0d30647c903e9622aa18c4dc2bb70d7b7c6fac898794`。计划 33 个不同输入，24 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L02 · 正数计数

固定修订：1；内容摘要：`b0a830089e0f4a6800d24e08820b551042a4b0924d2c774ec443cc102e9de536`。

知识点：`loop-counter`；建议难度：入门（待教师确认）。

### 给学生的任务

统计严格大于 0 的元素个数；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    count = 0
    for i in range(1, len(data)):
        if data[i] > 0:
            count += 1
    return count
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(1 for value in data if value > 0)
```


修正实现：


```python
def solve(data):
    count = 0
    for value in data:
        if value > 0:
            count += 1
    return count
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2
    ],
    "expected": 1
  },
  {
    "input": [
      -2
    ],
    "expected": 0
  },
  {
    "input": [
      3,
      0,
      -1
    ],
    "expected": 1
  },
  {
    "input": [
      1,
      2,
      2
    ],
    "expected": 3
  },
  {
    "input": [
      0,
      4
    ],
    "expected": 1
  }
]
```


基准说明：AI 辅助编写待审草稿 L02。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：下标从 1 开始会跳过第一项，第一项为正数时计数偏小。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "append_zero_invariant",
    "concatenation_additive",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、追加零不改变结果、数组重复一遍使结果翻倍；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:22:48.167193Z`；验证器 `differential-properties-v2`。

报告摘要：`2e8693a23763a2d45efcc543e879783813163d06869b07cbcd311004ad2e9900`。计划 33 个不同输入，19 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L03 · 查找首个零

固定修订：1；内容摘要：`03b2d6cebbc18efa9f82d9b900801d3c45002e7fdaa7125e2d34bc14d15b9fc2`。

知识点：`search-linear`；建议难度：入门（待教师确认）。

### 给学生的任务

返回第一次出现 0 的下标；没有 0 或输入为空时返回 -1。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    for i in range(len(data)-1):
        if data[i] == 0:
            return i
    return -1
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return data.index(0) if 0 in data else -1
```


修正实现：


```python
def solve(data):
    for i in range(len(data)):
        if data[i] == 0:
            return i
    return -1
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": -1
  },
  {
    "input": [
      0
    ],
    "expected": 0
  },
  {
    "input": [
      2,
      0
    ],
    "expected": 1
  },
  {
    "input": [
      0,
      2,
      0
    ],
    "expected": 0
  },
  {
    "input": [
      -1,
      3
    ],
    "expected": -1
  },
  {
    "input": [
      3,
      2,
      0
    ],
    "expected": 2
  }
]
```


基准说明：AI 辅助编写待审草稿 L03。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：顺序查找漏掉末尾位置，会把只在最后出现的目标误判为不存在。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:22:55.636718Z`；验证器 `differential-properties-v2`。

报告摘要：`ff3ba4f942b9b2543fe4c89ee52b42c095092aaff15a04af8e9fe6157960e7e5`。计划 21 个不同输入，3 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L04 · 包含当前位置的前缀和

固定修订：1；内容摘要：`bfdb23cf9745a2794a919e2974e392ebaf8dd5e34d94819dc092d4b1532af459`。

知识点：`array-traverse`；建议难度：入门（待教师确认）。

### 给学生的任务

返回每个位置及其之前元素之和构成的数组；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -32,
    "maximum": 32,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = []
    total = 0
    for i in range(len(data)-1):
        total += data[i]
        result.append(total)
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return [sum(data[:i+1]) for i in range(len(data))]
```


修正实现：


```python
def solve(data):
    result = []
    total = 0
    for value in data:
        total += value
        result.append(total)
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      3
    ],
    "expected": [
      3
    ]
  },
  {
    "input": [
      1,
      2
    ],
    "expected": [
      1,
      3
    ]
  },
  {
    "input": [
      -2,
      4,
      -1
    ],
    "expected": [
      -2,
      2,
      1
    ]
  },
  {
    "input": [
      0,
      0
    ],
    "expected": [
      0,
      0
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 L04。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：前缀和需要为每个输入位置生成一项，循环提前结束会缺少最后一项。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:02.878905Z`；验证器 `differential-properties-v2`。

报告摘要：`b43d82c9f53449c06c0f1af5629e95ee6de1d0e900f40d3888adfba5d0a7075d`。计划 20 个不同输入，19 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L05 · 相邻递增对计数

固定修订：1；内容摘要：`dfa021fb288e6b5acc410bc010fe1ef9fbdda470e51117eff4b1925f080c4664`。

知识点：`loop-range-detail`；建议难度：入门（待教师确认）。

### 给学生的任务

统计相邻两项中后一项严格大于前一项的对数；不足两项返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    count = 0
    for i in range(len(data)-2):
        if data[i+1] > data[i]:
            count += 1
    return count
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(1 for i in range(1, len(data)) if data[i] > data[i-1])
```


修正实现：


```python
def solve(data):
    count = 0
    for i in range(len(data)-1):
        if data[i+1] > data[i]:
            count += 1
    return count
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      1
    ],
    "expected": 0
  },
  {
    "input": [
      1,
      2
    ],
    "expected": 1
  },
  {
    "input": [
      3,
      2,
      4
    ],
    "expected": 1
  },
  {
    "input": [
      1,
      1,
      2
    ],
    "expected": 1
  },
  {
    "input": [
      -2,
      0,
      3
    ],
    "expected": 2
  }
]
```


基准说明：AI 辅助编写待审草稿 L05。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：相邻对共 len(data)-1 个，错误循环又少迭代一次，遗漏最后一对。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:09.961630Z`；验证器 `differential-properties-v2`。

报告摘要：`ec36db8a4363ce0352205a1c5506c7cefc0ab45d014af86dc28dd1a1ecb37fcd`。计划 20 个不同输入，7 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L06 · 数组逆序

固定修订：1；内容摘要：`3ea50421f09d35bbfc1a6482ca52304ff950c82850c92e7debdf0b43e950be03`。

知识点：`array-slice`；建议难度：入门（待教师确认）。

### 给学生的任务

返回原数组逆序后的数组；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = []
    for i in range(len(data)-1, 0, -1):
        result.append(data[i])
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return data[::-1]
```


修正实现：


```python
def solve(data):
    result = []
    for i in range(len(data)-1, -1, -1):
        result.append(data[i])
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      2
    ],
    "expected": [
      2
    ]
  },
  {
    "input": [
      1,
      3
    ],
    "expected": [
      3,
      1
    ]
  },
  {
    "input": [
      -2,
      0,
      4
    ],
    "expected": [
      4,
      0,
      -2
    ]
  },
  {
    "input": [
      1,
      1
    ],
    "expected": [
      1,
      1
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 L06。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：负步长 range 仍不包含终点，终点设为 0 会漏掉下标 0。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:17.163445Z`；验证器 `differential-properties-v2`。

报告摘要：`0a0356ef2959c2df7448516141942a58a2e075f1a3e3ad6bda54f3d4f110518b`。计划 20 个不同输入，19 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L07 · 非递减序列判定

固定修订：1；内容摘要：`05b000de5509e03da477c5e88ebc6dd39c504e92e3e06373a894013dd79f2b84`。

知识点：`loop-control`；建议难度：入门（待教师确认）。

### 给学生的任务

判断数组是否非递减，即每一项不小于前一项；空数组和单元素数组返回 true。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "boolean"
  }
}
```


错误程序：


```python
def solve(data):
    for i in range(2, len(data)):
        if data[i] < data[i-1]:
            return False
    return True
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return all(data[i-1] <= data[i] for i in range(1, len(data)))
```


修正实现：


```python
def solve(data):
    for i in range(1, len(data)):
        if data[i] < data[i-1]:
            return False
    return True
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": true
  },
  {
    "input": [
      3
    ],
    "expected": true
  },
  {
    "input": [
      2,
      1
    ],
    "expected": false
  },
  {
    "input": [
      3,
      1,
      2
    ],
    "expected": false
  },
  {
    "input": [
      -1,
      0,
      0
    ],
    "expected": true
  },
  {
    "input": [
      1,
      3,
      2
    ],
    "expected": false
  }
]
```


基准说明：AI 辅助编写待审草稿 L07。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：从第二对才开始检查，会忽略最前面的下降相邻对。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:24.544202Z`；验证器 `differential-properties-v2`。

报告摘要：`7d5cd049406cc7819ad2f02a3cbb6f38d7022701e55588fd030911f794c9b695`。计划 21 个不同输入，3 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L08 · 按位置加权求和

固定修订：1；内容摘要：`44881afdd176288073db2486b301ef9e9a8e3323dc2cbe50d03ea49d638bbf17`。

知识点：`loop-enumerate`；建议难度：入门（待教师确认）。

### 给学生的任务

返回各元素乘以其从 1 开始的位置后相加的值；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    total = 0
    for i in range(len(data)-1):
        total += (i+1)*data[i]
    return total
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum((i+1)*value for i, value in enumerate(data))
```


修正实现：


```python
def solve(data):
    total = 0
    for i, value in enumerate(data):
        total += (i+1)*value
    return total
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      1,
      2
    ],
    "expected": 5
  },
  {
    "input": [
      2,
      -1,
      3
    ],
    "expected": 9
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 0
  },
  {
    "input": [
      -2,
      1
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 L08。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：位置权重不能补偿缺失的遍历，最后一项及其权重都被遗漏。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:31.748262Z`；验证器 `differential-properties-v2`。

报告摘要：`7bf0571958b5d942b766bcc230c1d5408c53c079ee6ee3b9710076307fabcbc1`。计划 21 个不同输入，17 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L09 · 相邻元素乘积和

固定修订：1；内容摘要：`d9d0035ddbf717249180a813a735245d9629cafa7a7d19909ef53d2f32d405c2`。

知识点：`loop-zip`；建议难度：入门（待教师确认）。

### 给学生的任务

把每对相邻元素的乘积相加；不足两项返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    total = 0
    for i in range(1, len(data)-1):
        total += data[i-1]*data[i]
    return total
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(a*b for a, b in zip(data, data[1:]))
```


修正实现：


```python
def solve(data):
    total = 0
    for i in range(1, len(data)):
        total += data[i-1]*data[i]
    return total
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2
    ],
    "expected": 0
  },
  {
    "input": [
      2,
      3
    ],
    "expected": 6
  },
  {
    "input": [
      1,
      2,
      3
    ],
    "expected": 8
  },
  {
    "input": [
      -2,
      3,
      -1
    ],
    "expected": -9
  },
  {
    "input": [
      0,
      4
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 L09。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：配对遍历必须包含最后一个右端位置，否则最后一对乘积不计入。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:39.260419Z`；验证器 `differential-properties-v2`。

报告摘要：`e442cefcf181718cdccc7b941dbb4813b30f4059a2cfdbed1a4e6139899e9a8e`。计划 21 个不同输入，13 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## L10 · 偶数下标取值

固定修订：1；内容摘要：`4842ec592d2ec0f667799f6193b1d1340753a0c24256b7a785aba873f53c6e35`。

知识点：`loop-range-detail`；建议难度：入门（待教师确认）。

### 给学生的任务

按原顺序返回下标为 0、2、4 等偶数下标的元素；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = []
    for i in range(0, len(data)-1, 2):
        result.append(data[i])
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return data[::2]
```


修正实现：


```python
def solve(data):
    result = []
    for i in range(0, len(data), 2):
        result.append(data[i])
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      2
    ],
    "expected": [
      2
    ]
  },
  {
    "input": [
      1,
      2
    ],
    "expected": [
      1
    ]
  },
  {
    "input": [
      1,
      2,
      3
    ],
    "expected": [
      1,
      3
    ]
  },
  {
    "input": [
      4,
      3,
      2,
      1
    ],
    "expected": [
      4,
      2
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 L10。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：长度为奇数时末尾下标为偶数，终点少一位会漏掉应该保留的末尾元素。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

开发检查：通过；时间 `2026-10-16T16:23:47.405269Z`；验证器 `differential-properties-v2`。

报告摘要：`972277e38cca645007ed208e5ff72eb7a7decd85cf205005a0a0a9b52c0b67b7`。计划 20 个不同输入，9 个差异见证；有限检查不证明全部输入正确。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E01 · 数组最大值

固定修订：1；内容摘要：`264202698b2b22c5f06f3138ff90b670cc8daa5fb61c8732d5d1efd8c2a6e95f`。

知识点：`search-stat`；建议难度：入门（待教师确认）。

### 给学生的任务

返回最大元素；空数组约定返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    return max(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sorted(data)[-1] if data else 0
```


修正实现：


```python
def solve(data):
    return max(data) if data else 0
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      -3
    ],
    "expected": -3
  },
  {
    "input": [
      -4,
      -2
    ],
    "expected": -2
  },
  {
    "input": [
      1,
      4,
      2
    ],
    "expected": 4
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 E01。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：max 没有给出空输入的默认值，会在合法空数组上抛出 ValueError。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "permutation_invariant",
    "result_is_member"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、非空数组的结果来自输入元素；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：ValueError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E02 · 数组最小值

固定修订：1；内容摘要：`138ac0395c666eb7fac64be82dea9d1490dd47b1cc74f11a90bee7a09bd9bcb7`。

知识点：`search-stat`；建议难度：入门（待教师确认）。

### 给学生的任务

返回最小元素；空数组约定返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    return min(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sorted(data)[0] if data else 0
```


修正实现：


```python
def solve(data):
    return min(data) if data else 0
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      2,
      4
    ],
    "expected": 2
  },
  {
    "input": [
      -1,
      4,
      -3
    ],
    "expected": -3
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 E02。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：min 需要至少一个元素，遗漏空数组分支会抛出 ValueError。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "permutation_invariant",
    "result_is_member"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、非空数组的结果来自输入元素；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：ValueError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E03 · 首元素查询

固定修订：1；内容摘要：`2cc504859397feb68776ebe7c26aeec086f29fe4cd1b09540942fae2fad97339`。

知识点：`array-basic`；建议难度：入门（待教师确认）。

### 给学生的任务

返回第一个元素；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    return data[0]
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return data[:1][0] if data else 0
```


修正实现：


```python
def solve(data):
    if not data:
        return 0
    return data[0]
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      -2,
      4
    ],
    "expected": -2
  },
  {
    "input": [
      0,
      1
    ],
    "expected": 0
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 2
  }
]
```


基准说明：AI 辅助编写待审草稿 E03。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：下标 0 只在数组非空时存在，必须先处理合法空输入。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "result_is_member"
  ],
  "rationale": "草稿性质依据：题意要求 非空数组的结果来自输入元素；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：IndexError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E04 · 末元素查询

固定修订：1；内容摘要：`08bfd00544bb32df8df6168373c3e2c22446c8420cabb049b9c544e08987a23c`。

知识点：`array-basic`；建议难度：入门（待教师确认）。

### 给学生的任务

返回最后一个元素；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    return data[-1]
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return data[len(data)-1] if data else 0
```


修正实现：


```python
def solve(data):
    if not data:
        return 0
    return data[-1]
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      -2,
      4
    ],
    "expected": 4
  },
  {
    "input": [
      1,
      0
    ],
    "expected": 0
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 2
  }
]
```


基准说明：AI 辅助编写待审草稿 E04。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：负下标也不能读取空数组，-1 并不自动提供缺省值。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "result_is_member"
  ],
  "rationale": "草稿性质依据：题意要求 非空数组的结果来自输入元素；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：IndexError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E05 · 整数平均值

固定修订：1；内容摘要：`d1d74cc6b28f2850c33f478409d77e94d33da1cb5c407b375fba07b424685a92`。

知识点：`seq-arith`；建议难度：入门（待教师确认）。

### 给学生的任务

返回所有元素之和除以元素数后的向下取整结果；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    total = 0
    for value in data:
        total += value
    return total//len(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(data)//len(data) if data else 0
```


修正实现：


```python
def solve(data):
    if not data:
        return 0
    total = 0
    for value in data:
        total += value
    return total//len(data)
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      1,
      2
    ],
    "expected": 1
  },
  {
    "input": [
      -2,
      -1
    ],
    "expected": -2
  },
  {
    "input": [
      4,
      -4
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 E05。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：空数组的长度为 0，遗漏分支会使整除发生 ZeroDivisionError。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：ZeroDivisionError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E06 · 极差计算

固定修订：1；内容摘要：`2b3562fcaf69698abe6250216fba77b646f1c76b2c8a5116ffc3b3047954ed3f`。

知识点：`search-stat`；建议难度：入门（待教师确认）。

### 给学生的任务

返回最大元素与最小元素的差；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    return max(data)-min(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    ordered = sorted(data)
    return ordered[-1]-ordered[0] if ordered else 0
```


修正实现：


```python
def solve(data):
    return max(data)-min(data) if data else 0
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      3
    ],
    "expected": 0
  },
  {
    "input": [
      -2,
      4
    ],
    "expected": 6
  },
  {
    "input": [
      -4,
      -1
    ],
    "expected": 3
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 E06。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：非空时极值差有效，但空数组不能调用缺省参数下的 max/min。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "duplicate_invariant",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、加入已有元素不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：ValueError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E07 · 数组连乘

固定修订：1；内容摘要：`35c49f189b72909851c6c4a5902fadd6584e0c65052b5ec56e54392c16e58cb7`。

知识点：`loop-accumulator`；建议难度：入门（待教师确认）。

### 给学生的任务

返回全部元素的乘积；空数组按空乘积约定返回 1。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -65536,
    "maximum": 65536
  }
}
```


错误程序：


```python
def solve(data):
    if not data:
        return 0
    product = 1
    for value in data:
        product *= value
    return product
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    result = 1
    for value in data:
        result *= value
    return result
```


修正实现：


```python
def solve(data):
    product = 1
    for i in range(len(data)):
        product *= data[i]
    return product
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 1
  },
  {
    "input": [
      3
    ],
    "expected": 3
  },
  {
    "input": [
      2,
      -2
    ],
    "expected": -4
  },
  {
    "input": [
      0,
      4
    ],
    "expected": 0
  },
  {
    "input": [
      -1,
      -1,
      -1
    ],
    "expected": -1
  }
]
```


基准说明：AI 辅助编写待审草稿 E07。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：空乘积的单位元是 1，照搬求和的空值 0 会违反题意。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E08 · 序列有序性

固定修订：1；内容摘要：`a8f64256a271fec079c63a5348aa740c5bed9f63e6c256ca645ffb81ad1c798b`。

知识点：`loop-control`；建议难度：入门（待教师确认）。

### 给学生的任务

判断数组是否非递减；空数组及单元素数组均约定为有序。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "boolean"
  }
}
```


错误程序：


```python
def solve(data):
    if not data:
        return False
    for i in range(1, len(data)):
        if data[i-1] > data[i]:
            return False
    return True
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return all(data[i-1] <= data[i] for i in range(1, len(data)))
```


修正实现：


```python
def solve(data):
    for i in range(1, len(data)):
        if data[i-1] > data[i]:
            return False
    return True
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": true
  },
  {
    "input": [
      2
    ],
    "expected": true
  },
  {
    "input": [
      1,
      2,
      2
    ],
    "expected": true
  },
  {
    "input": [
      2,
      1
    ],
    "expected": false
  },
  {
    "input": [
      -2,
      -1,
      0
    ],
    "expected": true
  }
]
```


基准说明：AI 辅助编写待审草稿 E08。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：空输入没有违反相邻顺序的元素对，题意约定应返回 true 而不是 false。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E09 · 连续重复压缩

固定修订：1；内容摘要：`5f039d5442a2ae37d6c3678aa229800d2dff0747d599af3dadccc15af92405fc`。

知识点：`array-traverse`；建议难度：入门（待教师确认）。

### 给学生的任务

把每段连续相同元素压缩成一个，保留段的顺序；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = [data[0]]
    for value in data[1:]:
        if value != result[-1]:
            result.append(value)
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return [value for i, value in enumerate(data) if i == 0 or value != data[i-1]]
```


修正实现：


```python
def solve(data):
    result = []
    for value in data:
        if not result or value != result[-1]:
            result.append(value)
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      2
    ],
    "expected": [
      2
    ]
  },
  {
    "input": [
      1,
      1,
      2,
      2
    ],
    "expected": [
      1,
      2
    ]
  },
  {
    "input": [
      1,
      2,
      1
    ],
    "expected": [
      1,
      2,
      1
    ]
  },
  {
    "input": [
      0,
      0,
      0
    ],
    "expected": [
      0
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 E09。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：用第一项初始化结果前必须判断非空，否则合法空数组会抛出 IndexError。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：IndexError。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## E10 · 不含当前位置的前缀和

固定修订：1；内容摘要：`d0afcc844068f66d9557daf854352f5e32da0e62ed37dffef6f1ee03c7885b5f`。

知识点：`array-traverse`；建议难度：入门（待教师确认）。

### 给学生的任务

对每个位置返回其左侧全部元素的和，不包含当前位置；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -32,
    "maximum": 32,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = [0]
    total = 0
    for value in data[:-1]:
        total += value
        result.append(total)
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return [sum(data[:i]) for i in range(len(data))]
```


修正实现：


```python
def solve(data):
    result = []
    total = 0
    for value in data:
        result.append(total)
        total += value
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      3
    ],
    "expected": [
      0
    ]
  },
  {
    "input": [
      1,
      2
    ],
    "expected": [
      0,
      1
    ]
  },
  {
    "input": [
      -2,
      4,
      1
    ],
    "expected": [
      0,
      -2,
      2
    ]
  },
  {
    "input": [
      0,
      0
    ],
    "expected": [
      0,
      0
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 E10。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：固定预放一个 0 只适用于非空输入，空数组不应凭空增加输出位置。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D01 · 不同数值求和

固定修订：1；内容摘要：`471776b7f628f8f56d21b7854364d10bd090a3ae009dae2a6654ea9446d7eb03`。

知识点：`array-set`；建议难度：入门（待教师确认）。

### 给学生的任务

返回所有不同整数的和，每个数值只计一次；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    return sum(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(set(data))
```


修正实现：


```python
def solve(data):
    seen = []
    total = 0
    for value in data:
        if value not in seen:
            seen.append(value)
            total += value
    return total
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 2
  },
  {
    "input": [
      1,
      2,
      1
    ],
    "expected": 3
  },
  {
    "input": [
      -2,
      -2,
      4
    ],
    "expected": 2
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 0
  },
  {
    "input": [
      1,
      2,
      3
    ],
    "expected": 6
  }
]
```


基准说明：AI 辅助编写待审草稿 D01。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：未去重直接累加会把同一数值计算多次。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "append_zero_invariant",
    "duplicate_invariant",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、加入已有元素不改变结果、追加零不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D02 · 不同数值计数

固定修订：1；内容摘要：`11406efbe7095184ec872a9bb569bf497624be70136c0876628de57ec9f19910`。

知识点：`search-stat`；建议难度：入门（待教师确认）。

### 给学生的任务

返回不同整数的个数；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    return len(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return len(set(data))
```


修正实现：


```python
def solve(data):
    seen = []
    for value in data:
        if value not in seen:
            seen.append(value)
    return len(seen)
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 1
  },
  {
    "input": [
      1,
      2,
      1
    ],
    "expected": 2
  },
  {
    "input": [
      -2,
      0,
      2
    ],
    "expected": 3
  },
  {
    "input": [
      0,
      0,
      0
    ],
    "expected": 1
  }
]
```


基准说明：AI 辅助编写待审草稿 D02。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：元素总数和不同数值个数不同，出现重复时不能直接使用数组长度。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "duplicate_invariant",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、加入已有元素不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D03 · 数组元素总和

固定修订：1；内容摘要：`eb30911859371a905cc148b8666f33841640240f139ed5658493b87ec557860b`。

知识点：`loop-accumulator`；建议难度：入门（待教师确认）。

### 给学生的任务

返回全部元素的和，重复出现的数值每次都参与；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": -200,
    "maximum": 200
  }
}
```


错误程序：


```python
def solve(data):
    return sum(set(data))
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(data)
```


修正实现：


```python
def solve(data):
    total = 0
    for value in data:
        total += value
    return total
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 4
  },
  {
    "input": [
      1,
      2,
      1
    ],
    "expected": 4
  },
  {
    "input": [
      -2,
      -2,
      4
    ],
    "expected": 0
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 D03。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：去重会丢失出现次数，普通求和不能先转为集合。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "append_zero_invariant",
    "concatenation_additive",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、追加零不改变结果、数组重复一遍使结果翻倍；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D04 · 零的出现次数

固定修订：1；内容摘要：`1ac9500098b68369f03e470f2f6e5d483f97f8193cbb0037f5b8f839701491e3`。

知识点：`loop-counter`；建议难度：入门（待教师确认）。

### 给学生的任务

返回数值 0 出现的次数；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    return int(0 in data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return data.count(0)
```


修正实现：


```python
def solve(data):
    count = 0
    for value in data:
        if value == 0:
            count += 1
    return count
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      0
    ],
    "expected": 1
  },
  {
    "input": [
      0,
      0
    ],
    "expected": 2
  },
  {
    "input": [
      1,
      0,
      2,
      0
    ],
    "expected": 2
  },
  {
    "input": [
      -1,
      2
    ],
    "expected": 0
  }
]
```


基准说明：AI 辅助编写待审草稿 D04。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：成员判断只回答有没有零，不能区分一次和多次出现。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "concatenation_additive",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、数组重复一遍使结果翻倍；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D05 · 重复元素判定

固定修订：1；内容摘要：`d3f0a3cf2c29f307598e148046689347753f8e60d9a2e80c619a15fae2a5f6d8`。

知识点：`array-set`；建议难度：入门（待教师确认）。

### 给学生的任务

判断是否存在至少两个相等元素，位置不要求相邻；空数组返回 false。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "boolean"
  }
}
```


错误程序：


```python
def solve(data):
    return any(data[i] == data[i-1] for i in range(1, len(data)))
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return len(set(data)) < len(data)
```


修正实现：


```python
def solve(data):
    seen = []
    for value in data:
        if value in seen:
            return True
        seen.append(value)
    return False
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": false
  },
  {
    "input": [
      1
    ],
    "expected": false
  },
  {
    "input": [
      1,
      1
    ],
    "expected": true
  },
  {
    "input": [
      1,
      2,
      1
    ],
    "expected": true
  },
  {
    "input": [
      -2,
      0,
      2
    ],
    "expected": false
  }
]
```


基准说明：AI 辅助编写待审草稿 D05。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：只检查相邻项会漏掉被其他元素隔开的重复值。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D06 · 有序去重

固定修订：1；内容摘要：`f9bc77fe85b69461b6c65fcdaaa9d4071fbdf100ea86e073b167acf53e65fbf4`。

知识点：`search-sort`；建议难度：入门（待教师确认）。

### 给学生的任务

将不同整数从小到大排列后返回，每个数值只保留一项；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    return sorted(data)
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sorted(set(data))
```


修正实现：


```python
def solve(data):
    result = []
    for value in sorted(data):
        if not result or value != result[-1]:
            result.append(value)
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      2,
      2
    ],
    "expected": [
      2
    ]
  },
  {
    "input": [
      3,
      1,
      3
    ],
    "expected": [
      1,
      3
    ]
  },
  {
    "input": [
      -2,
      0,
      -2
    ],
    "expected": [
      -2,
      0
    ]
  },
  {
    "input": [
      2,
      1
    ],
    "expected": [
      1,
      2
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 D06。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：排序只改变位置，不会自动删除重复项。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "duplicate_invariant",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、加入已有元素不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D07 · 保持顺序的去重

固定修订：1；内容摘要：`cff687e3707289f68cb23209a509127ee401170599a5ff643187a2f7e6f75c3e`。

知识点：`array-traverse`；建议难度：入门（待教师确认）。

### 给学生的任务

删除每个数值首次出现之后的所有重复项，保留第一次出现的顺序；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = []
    for value in data:
        if not result or value != result[-1]:
            result.append(value)
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return [value for i, value in enumerate(data) if value not in data[:i]]
```


修正实现：


```python
def solve(data):
    result = []
    for value in data:
        if value not in result:
            result.append(value)
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      2,
      2
    ],
    "expected": [
      2
    ]
  },
  {
    "input": [
      1,
      2,
      1
    ],
    "expected": [
      1,
      2
    ]
  },
  {
    "input": [
      3,
      1,
      3,
      2,
      1
    ],
    "expected": [
      3,
      1,
      2
    ]
  },
  {
    "input": [
      -2,
      0,
      -2
    ],
    "expected": [
      -2,
      0
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 D07。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：只与结果末尾比较只能压缩连续重复，不能删除较早位置出现过的数值。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "duplicate_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 加入已有元素不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D08 · 筛选仅出现一次的元素

固定修订：1；内容摘要：`539b18ed0f70c2744b72f2e79153c99eacf4c797d42945a12840222e0de1fd7e`。

知识点：`search-stat`；建议难度：进阶（待教师确认）。

### 给学生的任务

返回在整个数组中恰好出现一次的元素，保持原顺序；空数组返回 []。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  }
}
```


错误程序：


```python
def solve(data):
    result = []
    for value in data:
        if value not in result:
            result.append(value)
    return result
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return [value for value in data if data.count(value) == 1]
```


修正实现：


```python
def solve(data):
    result = []
    for value in data:
        count = 0
        for other in data:
            if other == value:
                count += 1
        if count == 1:
            result.append(value)
    return result
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": []
  },
  {
    "input": [
      2
    ],
    "expected": [
      2
    ]
  },
  {
    "input": [
      2,
      2
    ],
    "expected": []
  },
  {
    "input": [
      1,
      2,
      1,
      3
    ],
    "expected": [
      2,
      3
    ]
  },
  {
    "input": [
      -2,
      0,
      0,
      4
    ],
    "expected": [
      -2,
      4
    ]
  }
]
```


基准说明：AI 辅助编写待审草稿 D08。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：去重保留一份与原本只出现一次不是同一条件，重复值应整类排除。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [],
  "rationale": "草稿性质依据：任务依赖顺序或没有选定通用关系，仅核对合法边界及两份正确程序的一致性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D09 · 最高出现频次

固定修订：1；内容摘要：`77331ee2f01222e8f32b2f66e799f78d41dbcebb5ac70a04f27d964f870a4820`。

知识点：`search-stat`；建议难度：进阶（待教师确认）。

### 给学生的任务

返回某个整数在整个数组中出现次数的最大值；空数组返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    best = 0
    run = 0
    previous = None
    for value in data:
        run = run+1 if value == previous else 1
        previous = value
        if run > best:
            best = run
    return best
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return max([data.count(value) for value in data]) if data else 0
```


修正实现：


```python
def solve(data):
    best = 0
    for value in data:
        count = data.count(value)
        if count > best:
            best = count
    return best
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2
    ],
    "expected": 1
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 2
  },
  {
    "input": [
      1,
      2,
      1,
      2,
      1
    ],
    "expected": 3
  },
  {
    "input": [
      3,
      1,
      3,
      2
    ],
    "expected": 2
  },
  {
    "input": [
      -1,
      0,
      2
    ],
    "expected": 1
  }
]
```


基准说明：AI 辅助编写待审草稿 D09。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：最长连续相同段不等于总出现次数，分散出现的同值仍应累计。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "concatenation_additive",
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果、数组重复一遍使结果翻倍；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：


## D10 · 相等元素配对计数

固定修订：1；内容摘要：`7fcbedf1143afd44c5f058ba1b5f780a449255308ebc0aece97e2a0529c3b56c`。

知识点：`loop-nested`；建议难度：进阶（待教师确认）。

### 给学生的任务

统计满足 i < j 且 data[i] 等于 data[j] 的下标对数；不足两项返回 0。

输入与输出范围：


```json
{
  "input": {
    "type": "integer_array",
    "minimum": -4,
    "maximum": 4,
    "min_items": 0,
    "max_items": 8
  },
  "output": {
    "type": "integer",
    "minimum": 0,
    "maximum": 28
  }
}
```


错误程序：


```python
def solve(data):
    return len(data)-len(set(data))
```


### 教师核对资料

独立参考实现：


```python
def solve(data):
    return sum(1 for i in range(len(data)) for j in range(i+1, len(data)) if data[i] == data[j])
```


修正实现：


```python
def solve(data):
    count = 0
    for i in range(len(data)):
        for j in range(i+1, len(data)):
            if data[i] == data[j]:
                count += 1
    return count
```


独立预期测试（按题意预先列出，仍需人工核对，不由运行结果生成）：


```json
[
  {
    "input": [],
    "expected": 0
  },
  {
    "input": [
      2
    ],
    "expected": 0
  },
  {
    "input": [
      2,
      2
    ],
    "expected": 1
  },
  {
    "input": [
      2,
      2,
      2
    ],
    "expected": 3
  },
  {
    "input": [
      1,
      2,
      1,
      2
    ],
    "expected": 2
  },
  {
    "input": [
      0,
      0,
      0,
      0
    ],
    "expected": 6
  }
]
```


基准说明：AI 辅助编写待审草稿 D10。参考实现和显式预期按题意分别编写，未用候选运行结果生成预期；请教师逐项核对并补充真实审阅说明。

教学说明：重复元素数量不等于相等下标对数，同值出现三次时已有三对。

补充边界与性质约定：


```json
{
  "policy_version": "bounded-properties-v1",
  "boundary_checks": true,
  "properties": [
    "permutation_invariant"
  ],
  "rationale": "草稿性质依据：题意要求 重排不改变结果；请教师确认其适用性。"
}
```


允许错误版作为反例的异常：无。

未找到与当前草稿摘要和验证器一致的开发记录。

### 人工审核记录（留空待填写）

- 审核人、日期与适用班级：

- [ ] 题意、合法范围和预期结果独立核对正确

- [ ] 错误单一清楚，参考与修正实现合理

- [ ] 性质关系符合题意，见证能说明错误原因

- [ ] 难度合适，学生题面没有直接泄露错误位置

- 结论（通过 / 修改后复核 / 不采用）：

- 需修改内容及理由：

- 工作台挑战编号、版本、当前验证报告编号：
