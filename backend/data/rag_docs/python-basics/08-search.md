# 模块八：查找与搜索

本模块进入算法入门：先用顺序查找建立“扫描—命中—返回”的基本套路，再用二分查找体会有序数据带来的效率飞跃，接着借冒泡与选择排序理解双重循环，最后回到求和、找最值、去重与计数这类最常见的数据处理任务。

## 1. 顺序查找
`document_id: python-search-linear`

顺序查找（线性查找）是最朴素的查找方法：从第一个元素开始逐个和目标比较，一旦相等就返回它的下标，整个序列扫描完仍没命中就返回约定的失败值 `-1`。它不要求数据有序，任何可迭代对象都能用，实现时通常配合 `for` 加 `enumerate` 同时拿到下标和值。若只关心“在不在”，可以直接用 `in` 运算符。初学者最容易卡在返回约定上：把 `return -1` 误写进循环里，导致第一个不匹配就直接失败；或者循环结束后无条件返回当前下标，把“没找到”报成最后一个位置。

- 概念：顺序查找从头到尾依次比较元素与目标，命中就返回位置、扫完仍未命中才返回失败哨兵，最坏与平均时间复杂度都是 `O(n)`，额外空间 `O(1)`。关键点在于两个 `return` 的位置：`return index` 在 `if` 命中的分支里，`return -1` 必须缩进到与 `for` 同级，表示循环正常结束都没找到。当序列中存在多个相同目标时，要事先约定返回第一次出现、最后一次出现还是全部位置，用列表推导式即可一次收集全部。`target in seq` 内部同样是线性扫描，写起来更短但拿不到下标。它对数据没有任何前置要求，因此是二分查找（要求有序）之前必须先掌握的基准方法。

### 正例代码

```python
def linear_search(values, target):
    """返回 target 第一次出现的下标，找不到返回 -1。"""
    for index, value in enumerate(values):
        if value == target:
            return index      # 命中立即返回，后面不再扫
    return -1                 # 循环正常结束才算失败


def find_all(values, target):
    """返回全部命中位置组成的列表。"""
    return [i for i, v in enumerate(values) if v == target]


names = ["李雷", "韩梅梅", "张三", "韩梅梅"]
print(linear_search(names, "韩梅梅"))   # 1（第一次出现）
print(linear_search(names, "王五"))     # -1
print(find_all(names, "韩梅梅"))        # [1, 3]
print("张三" in names)                  # True：只判断存在与否时更简洁
```

- 正例：`for index, value in enumerate(values):` 一次拿到下标与值，命中时 `return index`；`return -1` 与 `for` 同级，只有循环跑完才会执行，因此 `linear_search(names, "王五")` 正确返回 `-1`。

### 反例与易错点

```python
def broken_search(values, target):
    for index, value in enumerate(values):
        if value == target:
            break
    return index        # 未找到时返回最后一个下标，假阳性


def broken_search2(values, target):
    for index in range(len(values)):
        if values[index] == target:
            return values[index]   # 返回的是值不是下标，值为 0 时还会被误判
    return -1


print(broken_search([1, 2, 3], 9))  # 2，可是 9 根本不存在
```

- 反例：`broken_search` 在循环外无条件 `return index`，没找到时会把最后一个位置当成答案，且空列表下 `index` 未定义会抛 `UnboundLocalError`；`broken_search2` 混淆了下标与元素值，正确写法是命中时 `return index`、循环结束后 `return -1`。
- 常见错误：没有约定“未找到”的返回值、把 `return -1` 写进循环体内、下标与元素值混淆、忘记空列表这种边界、用 `values.index(target)` 却不捕获 `ValueError`。

### 练习

- 基础题：编写 `linear_search(values, target)`，返回目标第一次出现的下标，找不到返回 `-1`。
- 答案要点：`for index, value in enumerate(values)` 扫描；命中立即 `return index`；`return -1` 与 `for` 同级缩进。
- 进阶题：扩展为返回全部匹配下标的列表，并说明“找到首个即停”与“完整扫描”在最好、最坏情况下的复杂度差别。
- 进阶答案要点：用列表推导式收集 `[i for i, v in enumerate(values) if v == target]`；首个即停最好 `O(1)`、最坏 `O(n)`，全扫描恒为 `O(n)`；没有匹配时返回空列表而不是 `-1`。

### 相关知识点

- 前置知识点：`loop-for`（for 循环）、`array-basic`（列表基础）、`array-traverse`（列表遍历）。
- 后续知识点：`search-binary`（二分查找）、`search-stat`（统计与去重）。
- 来源：Python 官方教程“Data Structures”，Python Wiki“TimeComplexity”。

## 2. 二分查找
`document_id: python-search-binary`

二分查找的前提是数据已经按顺序排好。思路是每次取中间位置比较：相等就命中；中间值比目标小，说明目标只可能在右半边，把左边界移到 `mid + 1`；中间值比目标大，就把右边界移到 `mid - 1`。每比较一次就淘汰一半候选，因此 1000 个元素最多比较 10 次左右，时间复杂度为 `O(log n)`。写二分的难点全在边界：`low`、`high`、`mid` 三个变量与循环条件必须自洽，边界更新漏了 `+1` 或 `-1` 会死循环，`high` 初值取成 `len(values)` 会越界，`mid` 用 `/` 而不是 `//` 会得到浮点下标。

- 概念：二分查找在有序序列上维护一个候选区间，本文采用闭区间写法：`low = 0`、`high = len(values) - 1`，循环条件 `while low <= high`，`mid = (low + high) // 2`。命中返回 `mid`；`values[mid] < target` 时 `low = mid + 1`，否则 `high = mid - 1`；循环结束说明区间已空，返回 `-1`。三处细节必须成套出现：闭区间配 `<=`、整除保证下标是整数、边界跨过 `mid` 保证区间严格缩小。若数据无序，二分会给出错误答案却不报错，这比崩溃更危险，所以要么先排序要么确认调用方保证有序。标准库 `bisect` 模块提供了工业级实现，但手写一遍是理解“淘汰一半”的必要练习。

### 正例代码

```python
def binary_search(values, target):
    """在升序列表 values 中查找 target，返回下标，找不到返回 -1。"""
    low, high = 0, len(values) - 1      # 闭区间 [low, high]
    while low <= high:                  # 等号不能漏，否则漏查单元素区间
        mid = (low + high) // 2         # 必须整除，下标只能是整数
        if values[mid] == target:
            return mid
        if values[mid] < target:
            low = mid + 1               # 左半边连 mid 一起淘汰
        else:
            high = mid - 1              # 右半边连 mid 一起淘汰
    return -1


data = [1, 3, 5, 7, 9, 11]
print(binary_search(data, 9))   # 4
print(binary_search(data, 1))   # 0
print(binary_search(data, 4))   # -1
```

- 正例：`low, high = 0, len(values) - 1` 与 `while low <= high` 配套构成闭区间；`mid = (low + high) // 2` 用整除，`low = mid + 1` 和 `high = mid - 1` 都跨过 `mid`，保证区间每轮真正变小，因此查 `4` 能正常退出并返回 `-1`。

### 反例与易错点

```python
def broken_binary(values, target):
    low, high = 0, len(values)      # 错误：闭区间的 high 应为 len - 1，否则越界
    while low < high:               # 与闭区间不匹配，会漏查最后一个元素
        mid = (low + high) / 2      # 错误：真除法得到 float 下标
        if values[mid] == target:
            return mid
        elif values[mid] < target:
            low = mid               # 错误：漏了 +1，low 不变时死循环
        else:
            high = mid
    return -1


print(broken_binary([1, 3, 5], 5))  # TypeError: list indices must be integers
```

- 反例：`(low + high) / 2` 得到浮点数，`values[mid]` 立刻抛 `TypeError: list indices must be integers or slices, not float`，应改成 `//`；`low = mid` 在只剩两个元素时区间不再缩小造成死循环，必须写 `low = mid + 1`；`high = len(values)` 配 `while low <= high` 还会 `IndexError`。
- 常见错误：对无序数据直接二分导致结果错误、`mid` 用 `/` 得到浮点下标、边界更新漏 `+1`/`-1` 死循环、`high` 初值取 `len(values)` 越界、闭区间循环条件误写成 `low < high`。

### 练习

- 基础题：在升序列表 `[1, 3, 5, 7, 9]` 上实现 `binary_search`，分别查找存在的 5 与不存在的 4，验证返回 `2` 和 `-1`。
- 答案要点：`low, high = 0, len(values) - 1`；`while low <= high`；`mid = (low + high) // 2`；三分支分别 `return mid`、`low = mid + 1`、`high = mid - 1`。
- 进阶题：在循环里打印每轮的 `low`、`high`、`mid`，统计查找 1000 个元素最多需要几次比较，并与顺序查找的次数对比。
- 进阶答案要点：每轮候选数量减半，比较次数约为 `log2(n)` 向上取整，1000 个元素约 10 次，而顺序查找最坏 1000 次；打印三个指针能直观看出区间是否在缩小，是排查死循环的最快手段。

### 相关知识点

- 前置知识点：`search-linear`（顺序查找）、`loop-while`（while 循环）、`seq-arith`（算术运算）。
- 后续知识点：`search-sort`（排序思想）、`search-stat`（统计与去重）。
- 来源：Python 标准库文档“bisect — Array bisection algorithm”，Python 官方教程“Data Structures”。

## 3. 排序思想
`document_id: python-search-sort`

排序是把数据整理成有序的过程，也是二分查找的前置条件。冒泡排序的思路是相邻两个元素比较，逆序就交换，一轮下来最大值会“浮”到末尾，重复 `n-1` 轮即可完成；选择排序的思路是每一轮在未排序区间里找出最小值的下标，再和该区间的第一个位置交换。两者都是典型的双重循环：外层控制进行到第几轮，内层负责本轮的比较，时间复杂度都是 `O(n²)`。初学者最容易卡在交换写法和内层循环范围上：用两次普通赋值交换会丢数据，内层范围多算一格会索引越界。

- 概念：冒泡与选择排序都由外层“轮次”和内层“比较”两重循环构成，外层跑 `n-1` 轮，内层的范围随轮次收缩，总比较次数约 `n²/2`，因此都是 `O(n²)`，只适合小数据量或教学演示。Python 交换两个元素要用元组解包 `a[i], a[j] = a[j], a[i]`，一条语句先算右侧再整体赋值，绝不能拆成两次赋值。实际开发中直接用内置的 `sorted(iterable)`（返回新列表）或 `list.sort()`（原地排序），底层是高度优化的 Timsort，复杂度 `O(n log n)` 且是稳定排序：值相等的元素保持原有先后顺序，因此可以先按次要字段排、再按主要字段排来实现多级排序。冒泡（只交换相邻逆序对）天然稳定，而选择排序的远距离交换会打乱相等元素的相对次序，不稳定。

### 正例代码

```python
def bubble_sort(values):
    items = values[:]                        # 复制一份，不改动调用方的列表
    for i in range(len(items) - 1):          # 一共 n-1 轮
        for j in range(len(items) - 1 - i):  # 尾部已排好，不再参与比较
            if items[j] > items[j + 1]:      # 相邻逆序就交换
                items[j], items[j + 1] = items[j + 1], items[j]
    return items


def selection_sort(values):
    items = values[:]
    for i in range(len(items) - 1):
        min_index = i                        # 先假定当前位置就是最小
        for j in range(i + 1, len(items)):
            if items[j] < items[min_index]:
                min_index = j
        items[i], items[min_index] = items[min_index], items[i]
    return items

print(bubble_sort([5, 2, 9, 1]), selection_sort([5, 2, 9, 1]))  # [1, 2, 5, 9] [1, 2, 5, 9]
```

- 正例：两个函数都先 `items = values[:]` 复制再排序，避免副作用；交换统一写成 `items[j], items[j + 1] = items[j + 1], items[j]` 一条语句；冒泡内层范围 `range(len(items) - 1 - i)` 既避开已排好的尾部，也保证 `items[j + 1]` 不越界。

### 反例与易错点

```python
values = [5, 2, 9, 1]

# 错误：交换写成两次赋值，第一步就把原值覆盖了
for j in range(len(values) - 1):
    if values[j] > values[j + 1]:
        values[j] = values[j + 1]
        values[j + 1] = values[j]   # 两个位置变成同一个值
print(values)                       # [2, 2, 1, 1]，数据被破坏

# 错误：内层写成 range(len(values)) 时 values[j + 1] 越界，IndexError: list index out of range

# 错误：sorted 返回新列表，不会改动原列表
nums = [3, 1, 2]
sorted(nums)
print(nums)                         # [3, 1, 2]
```

- 反例：两次赋值交换会先丢掉 `values[j]`，结果出现重复值、原数据被破坏，必须写成 `values[j], values[j + 1] = values[j + 1], values[j]`；`sorted(nums)` 的返回值被丢弃等于什么都没做，想原地排序应调用 `nums.sort()` 或写成 `nums = sorted(nums)`。
- 常见错误：交换拆成两次赋值、内层循环范围多一格导致 `IndexError`、外层轮数少一轮导致没排完、混淆 `sorted()` 与 `list.sort()` 的返回值、在遍历列表的同时增删元素。

### 练习

- 基础题：用冒泡排序把 `[5, 2, 9, 1]` 排成升序并打印每一轮结束后的列表。
- 答案要点：双重循环，外层 `range(len(items) - 1)`，内层 `range(len(items) - 1 - i)`；交换用元组解包；在外层循环末尾 `print(items)` 观察大数逐轮“冒”到尾部。
- 进阶题：实现选择排序，并与 `sorted()` 的结果逐项比对；再给一批 `(姓名, 分数)` 元组按分数降序排列。
- 进阶答案要点：选择排序每轮记录 `min_index` 后再交换；用 `my_result == sorted(data)` 验证正确性；元组排序用 `sorted(data, key=lambda item: item[1], reverse=True)`，借助稳定性可先按姓名排再按分数排实现多级排序。

### 相关知识点

- 前置知识点：`loop-nested`（嵌套循环）、`array-basic`（列表基础）、`search-linear`（顺序查找）。
- 后续知识点：`search-binary`（二分查找）、`search-stat`（统计与去重）。
- 来源：Python 官方文档“Sorting Techniques”（Sorting HOW TO），Python 官方教程“Data Structures”。

## 4. 统计与去重
`document_id: python-search-stat`

统计是最常见的数据处理任务：求和、计数、找最大最小、算平均值。套路固定为三步——循环外初始化累计变量，循环内按条件更新，循环后收尾输出，一次遍历就能同时完成多项统计，复杂度 `O(n)`。去重则有两种需求：不在乎顺序时用 `set(data)` 最简洁；要保持首次出现顺序就用 `list(dict.fromkeys(data))`。统计每个值出现了几次用字典计数，`counter.get(key, 0) + 1` 是最稳的写法。初学者最容易踩的坑是空列表求平均导致 `ZeroDivisionError`，以及把最值初始化成 0，遇到全是负数的数据就得到错误结果。

- 概念：聚合统计的骨架是“初始化—扫描—收尾”：累计变量必须在循环外初始化，写进循环体就会每轮被重置；最值变量应该用序列的第一个元素初始化（如 `highest = scores[0]`），初始化成 0 在全负数据上必然出错；平均值要在循环结束后才计算，并且先用 `if not scores` 挡住空序列，否则除零抛 `ZeroDivisionError`。内置的 `sum`、`len`、`max`、`min` 更简洁，但手写一遍能巩固循环不变量的概念。`set` 是无序且元素唯一的集合，去重最快却会丢失顺序，也不支持下标访问；从 Python 3.7 起字典保持插入顺序，因此 `dict.fromkeys` 成了“保序去重”的标准技巧。字典计数则把这套模式从数值扩展到任意可哈希的键，是词频、成绩分布等任务的基础。

### 正例代码

```python
scores = [88, 95, 72, 95, 60]

total = 0
highest = scores[0]                # 用首元素初始化，避免负数场景出错
for score in scores:               # 一次遍历同时求和与找最大值
    total += score
    if score > highest:
        highest = score
print(total, highest, total / len(scores))     # 410 95 82.0

print(sum(scores), max(scores), min(scores))   # 410 95 60

unique = set(scores)                           # 去重，但顺序不确定
ordered = list(dict.fromkeys(scores))          # 去重且保持首次出现顺序
print(len(unique), ordered)                    # 4 [88, 95, 72, 60]

counter = {}
for score in scores:                           # 字典计数
    counter[score] = counter.get(score, 0) + 1
print(counter)   # {88: 1, 95: 2, 72: 1, 60: 1}
```

- 正例：`total = 0` 与 `highest = scores[0]` 写在循环外，循环内只做 `total += score` 和条件更新；平均值 `total / len(scores)` 在循环结束后计算；`list(dict.fromkeys(scores))` 得到保序去重结果，`counter.get(score, 0) + 1` 让首次出现的键也能安全计数。

### 反例与易错点

```python
scores = []
# print(sum(scores) / len(scores))   # ZeroDivisionError: division by zero

nums = [-5, -2, -9]
biggest = 0                          # 错误：最值初始化成 0
for n in nums:
    if n > biggest:
        biggest = n
print(biggest)                       # 0，可是列表里根本没有 0

data = [3, 1, 3]
print(set(data)[0])                  # TypeError: 'set' object is not subscriptable
```

- 反例：空列表求平均会抛 `ZeroDivisionError`，应先 `if not scores: return None`；`biggest = 0` 在全负数据上返回了不存在的 0，正确写法是 `biggest = nums[0]`；集合无序也不支持下标，要按位置取值必须先 `sorted(set(data))` 或 `list(set(data))`。
- 常见错误：累计变量初始化写进循环体、空序列除零、最值初始化成 0 或任意常数、对 `set` 使用下标或依赖其顺序、字典计数时直接 `counter[key] += 1` 触发 `KeyError`。

### 练习

- 基础题：给定成绩列表，统计及格（≥60）人数与及格成绩的平均分。
- 答案要点：循环外初始化 `count = 0` 与 `total = 0`；循环内 `if score >= 60` 时同时累加两者；循环后先判断 `count > 0` 再算 `total / count`。
- 进阶题：给定一批学生 `(姓名, 分数)`，一次遍历输出人数、总分、平均分、最高分及其姓名，并对成绩做保序去重后统计每个分数出现的次数。
- 进阶答案要点：空列表提前返回；最高分与姓名一起用首个元素初始化并同步更新；平均分在循环后计算并用 `{avg:.1f}` 格式化；保序去重用 `list(dict.fromkeys(...))`，次数统计用 `counter.get(key, 0) + 1`，结果可封装成字典返回。

### 相关知识点

- 前置知识点：`array-traverse`（列表遍历）、`loop-for`（for 循环）、`func-param`（参数与返回值）。
- 后续知识点：无（本模块终点）。
- 来源：Python 官方教程“Data Structures”（Sets、Dictionaries），Python 标准库文档“collections.Counter”。
