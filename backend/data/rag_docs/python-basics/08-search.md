# 模块八：查找与搜索

本模块从基础查找与数据统计逐步进入算法思维：先用顺序查找建立“扫描—命中—返回”的套路，再通过复杂度和二分边界分析有序数据的效率；随后比较冒泡、选择、插入三种排序，学习哈希查找与双指针的适用条件，最后用 BFS 认识无权图的分层搜索。各主题都包含可运行示例、易错边界和递进练习；算法复杂度、排序稳定性和数据前提会明确说明。

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

## 5. 时间复杂度
`document_id: python-search-complexity`

分析复杂度不是给程序计时，而是观察输入规模 `n` 增大时，主要操作次数如何增长。它帮助我们比较算法的扩展性；同一复杂度下常数、数据分布、解释器和硬件也会影响实际运行时间，所以小样例的秒表结果不能代替复杂度分析。

- 概念：`O(1)` 表示操作数不随 `n` 增长（如列表按下标读取）；`O(log n)` 常见于每轮把候选范围减半的二分查找；`O(n)` 常见于一次完整扫描；两层各随 `n` 增长的循环通常是 `O(n²)`。多个顺序部分相加取增长更快的一项（`O(n)+O(n²)=O(n²)`），固定常数忽略。要说明“最坏/平均/最好”情形以及算法前提，例如二分的输入必须有序。空间复杂度另算额外存储量，不能和运行时间混为一谈。

### 正例代码

```python
def count_operations(n):
    constant = 1                         # O(1)
    linear = 0
    for _ in range(n):                   # O(n)
        linear += 1
    logarithmic = 0
    size = n
    while size > 1:                      # 每轮规模减半，O(log n)
        size //= 2
        logarithmic += 1
    quadratic = 0
    for _ in range(n):                   # 两层循环，O(n²)
        for _ in range(n):
            quadratic += 1
    return constant, linear, logarithmic, quadratic

print(count_operations(8))  # (1, 8, 3, 64)
```

- 正例：`n=8` 时一次扫描执行 8 次，双层循环执行 64 次，反复折半执行 3 次。代码用计数器展示增长趋势，不把微秒计时误当作复杂度证明；`n` 翻倍时，线性部分约翻倍、平方部分约变为 4 倍。

### 反例与易错点

```python
def misleading_search(values, target):
    # 错误地把二分查找直接用于未排序输入
    left, right = 0, len(values) - 1
    while left <= right:
        mid = (left + right) // 2
        if values[mid] == target:
            return mid
        if values[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

print(misleading_search([1, 9, 3, 7], 3))  # 可能误报未找到
```

- 反例：二分的 `O(log n)` 结论有“输入已排序”的前提。对乱序列表调用它，代码仍可能正常结束，却给出错误答案；若每次查找前都重新排序，则排序成本也要计入总成本，不能只报告查找部分。
- 常见错误：把 `O(log n)` 说成“每次少一个”；只数循环层数却忽略循环变量每轮增长方式；忽略顺序执行部分的主导项；用一次计时下结论；不说明最好、平均或最坏情形；把额外空间复杂度和时间复杂度混在一起。

### 练习

- 基础题：判断读取 `values[0]`、遍历列表一次、两层完整嵌套循环的时间复杂度，并解释判断依据。
- 答案要点：列表按下标访问为 `O(1)`；单次完整遍历为 `O(n)`；两层循环的迭代次数相乘为 `O(n²)`（假定每层各执行约 `n` 次）。
- 进阶题：比较顺序查找与二分查找在 1,000,000 个元素上的最坏比较次数，并说明排序数据的准备成本何时可以忽略。
- 进阶答案要点：顺序查找最坏约 `n` 次；二分约 `ceil(log2(n+1))` 次，百万规模约 20 次。若数据已排序或需重复查询，排序成本可由多次查询摊薄；单次查询且原数据无序时，应把排序成本计入整体方案。

### 相关知识点

- 前置知识点：`loop-nested`（嵌套循环）、`search-linear`（顺序查找）。
- 后续知识点：`search-binary`（二分查找）、`search-hash`（哈希查找）。
- 来源：Python 官方文档 [bisect](https://docs.python.org/3/library/bisect.html)；复杂度符号用于描述渐进增长，不等同于实际秒数。


## 6. 二分边界模板
`document_id: python-search-boundary`

二分边界题通常不是“找到任意一个相等元素”，而是找第一个满足条件的位置，例如第一个大于等于目标值的位置。重复元素因此必须定义返回语义。这里使用半开区间 `[left, right)`：左端包含、右端不包含；循环不变量是答案若存在，只会落在尚未排除的区间内。

- 概念：在升序列表中找下界（lower bound），即首个 `values[i] >= target` 的位置。初始 `[0, len(values))`，条件 `left < right`；若中点值小于目标，答案只能在右侧，令 `left = mid + 1`；否则保留中点并向左收缩，令 `right = mid`。退出时 `left == right`，它可能等于 `len(values)`，表示所有元素都小于目标。时间复杂度 `O(log n)`，额外空间 `O(1)`。Python 标准库 `bisect_left` 实现了相同的插入点语义。

### 正例代码

```python
def lower_bound(values, target):
    left, right = 0, len(values)  # 半开区间 [left, right)
    while left < right:
        mid = (left + right) // 2
        if values[mid] < target:
            left = mid + 1
        else:
            right = mid             # 保留 mid：它可能就是首个答案
    return left

data = [1, 2, 2, 2, 5]
print(lower_bound(data, 2))  # 1：重复值中的第一个
print(lower_bound(data, 4))  # 4：可插入位置
print(lower_bound(data, 9))  # 5：等于 len(data)，表示不存在更大元素
```

- 正例：`[1, 2, 2, 2, 5]` 中查 2 返回下标 1，而不是任意一个 2；查 4 返回插入点 4。右边界始终不参与取值，所以 `right = len(values)` 不会越界；收缩到单元素区间时仍会检查该候选。

### 反例与易错点

```python
def broken_lower_bound(values, target):
    left, right = 0, len(values) - 1
    while left < right:
        mid = (left + right) // 2
        if values[mid] < target:
            left = mid + 1
        else:
            right = mid - 1  # 错：可能跳过首个合法位置
    return left

print(broken_lower_bound([2, 4], 2))  # 可能返回 1，漏掉下标 0
```

- 反例：把闭区间里的 `right = mid - 1` 搬进半开区间模板，会把仍可能满足条件的 `mid` 一起丢掉；`right` 应更新为 `mid`。另一个常见错误是循环后直接索引 `values[left]`，当 `left == len(values)` 时会越界，应先判断是否到达末尾。
- 常见错误：混用闭区间与半开区间的循环条件和边界更新；对重复值只测中间位置；未处理空列表或目标大于全部元素；把插入点误解为“肯定找到目标”；对未排序数据做二分。

### 练习

- 基础题：实现 `lower_bound`，测试空列表、目标小于最小值、重复目标和目标大于最大值四种情况。
- 答案要点：返回范围始终是 `0` 到 `len(values)`；命中语义是首个大于等于目标的位置；目标不存在时返回插入点；空列表返回 0。
- 进阶题：基于 `lower_bound` 写出 `upper_bound`（首个严格大于目标的位置），再求目标在有序数组中的出现次数。
- 进阶答案要点：`upper_bound` 的判定改为 `values[mid] <= target` 时移动左边界；出现次数为 `upper_bound - lower_bound`，两个搜索各为 `O(log n)`。

### 相关知识点

- 前置知识点：`search-binary`（二分查找）、`loop-while`（while 循环）。
- 后续知识点：`search-stat`（统计与去重）。
- 来源：Python 标准库文档 [bisect — Array bisection algorithm](https://docs.python.org/3/library/bisect.html)。


## 7. 冒泡排序
`document_id: python-search-bubble`

冒泡排序反复比较相邻元素，把逆序的一对交换。升序排序的一轮结束后，当前未排序部分的最大值会到达末尾；因此下一轮可以少看一个位置。它适合用来理解比较、交换和循环边界，不适合大规模数据。

- 概念：标准实现平均和最坏时间复杂度为 `O(n²)`，额外空间为 `O(1)`；只交换严格逆序的相邻元素时具备稳定性。加入“本轮没有发生交换就提前结束”后，已升序数据的最好时间可降为 `O(n)`，最坏仍是 `O(n²)`。函数是否原地修改输入要明确，本例复制列表后返回新结果。

### 正例代码

```python
def bubble_sort(values):
    items = list(values)
    for end in range(len(items) - 1, 0, -1):
        swapped = False
        for i in range(end):
            if items[i] > items[i + 1]:
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True
        if not swapped:          # 一整轮未交换，说明已经有序
            break
    return items

print(bubble_sort([5, 1, 4, 2, 8]))  # [1, 2, 4, 5, 8]
print(bubble_sort([]))               # []
```

- 正例：内层循环只跑到 `end - 1`，确保 `items[i + 1]` 有效；每轮结束后末尾已有序；`swapped` 只在真正交换时设为真，因此已排序输入可提前结束。

### 反例与易错点

```python
def broken_bubble(values):
    for i in range(len(values)):
        if values[i] > values[i + 1]:  # 最后一次 i+1 越界
            values[i], values[i + 1] = values[i + 1], values[i]

broken_bubble([3, 1])  # IndexError
```

- 反例：`range(len(values))` 会让最后一轮访问 `values[len(values)]`。相邻比较的索引上限应是 `len(values) - 2`；缩短内层范围可避免越界，也避免重复比较已排好的尾部。
- 常见错误：循环范围多一格；交换拆成两次赋值导致数据覆盖；忘记复制而意外修改调用者列表；把“已排好尾部”误认为整表已排序；对大量数据使用平方级排序。

### 练习

- 基础题：手动跟踪 `[4, 1, 3]`，分别写出第一轮、第二轮后的列表。
- 答案要点：第一轮相邻比较后最大值 4 到达末尾，列表为 `[1, 3, 4]`；下一轮未交换即可停止。
- 进阶题：统计冒泡排序的比较次数和交换次数，并验证相同键记录的相对次序是否保持。
- 进阶答案要点：比较次数由实际执行轮数决定；交换次数等于输入序列中的逆序对数量；只在 `>` 时交换相邻元素，不会交换键相等记录，因此稳定。

### 相关知识点

- 前置知识点：`loop-nested`（嵌套循环）、`array-basic`（列表基础）。
- 后续知识点：`search-selection`（选择排序）、`search-insertion`（插入排序）。
- 来源：Python 官方文档 [Sorting Techniques](https://docs.python.org/3/howto/sorting.html)；冒泡排序用于教学比较，不是 Python 内置排序算法。


## 8. 选择排序
`document_id: python-search-selection`

选择排序把列表分成“已排序前缀”和“未排序后缀”。每轮扫描后缀找最小元素，再与后缀首位交换；这样已排序区每轮增长一个位置。它的交换次数少，但寻找最小值仍需扫描整个后缀。

- 概念：比较次数约为 `n(n-1)/2`，无论输入是否已经有序，时间复杂度都是 `O(n²)`；额外空间可为 `O(1)`（原地版）。每轮至多一次交换，交换次数不超过 `n-1`。标准选择排序通常不稳定：把远处最小值换到前面可能改变相等元素的相对次序。下面实现复制输入，因此对调用者列表无副作用。

### 正例代码

```python
def selection_sort(values):
    items = list(values)
    n = len(items)
    for start in range(n - 1):
        min_index = start
        for i in range(start + 1, n):
            if items[i] < items[min_index]:
                min_index = i
        if min_index != start:
            items[start], items[min_index] = items[min_index], items[start]
    return items

print(selection_sort([29, 10, 14, 37, 13]))  # [10, 13, 14, 29, 37]
```

- 正例：`min_index` 记录最小值的位置，扫描完整个未排序后缀后才交换；不能在每次发现更小元素时立刻交换，否则逻辑会变成另一种过程。长度为 0 或 1 时外层循环自然不执行。

### 反例与易错点

```python
def broken_selection(values):
    for start in range(len(values)):
        min_index = start
        for i in range(start + 1, len(values)):
            if values[i] < values[min_index]:
                min_index = i
        values[start], values[min_index] = values[min_index], values[start]
    return values

# 输入 [(2, 'A'), (2, 'B'), (1, 'C')] 时，键为 1 的元素交换到最前，
# 两个键为 2 的记录顺序可能反转，说明该算法不保证稳定。
```

- 反例：误把选择排序说成稳定排序，会导致多字段排序的解释错误；远距离交换确实可能跨过相等元素。另一个常见边界错误是把内层起点写成 `start`，造成当前位置与自己反复比较，虽然通常不影响结果，却多做无用比较。
- 常见错误：只比较当前位置和下一个元素（那不是选择最小值的完整扫描）；扫描后缀时误更新元素而非下标；对空列表访问 `items[0]`；把较少交换次数误解为总体复杂度低于 `O(n²)`。

### 练习

- 基础题：对 `[6, 3, 8, 2]` 逐轮写出选出的最小值及交换后的前缀。
- 答案要点：第一轮选 2 放到下标 0；第二轮在 `[3,8,6]` 选 3；第三轮在 `[8,6]` 选 6；结果 `[2,3,6,8]`。
- 进阶题：与冒泡排序比较比较次数、交换次数和稳定性，并说明选择排序在哪类成本模型下可能有优势。
- 进阶答案要点：标准选择排序比较次数固定为 `n(n-1)/2`，最多 `n-1` 次交换；冒泡交换数取决于逆序对且相邻交换、稳定。若写入操作昂贵而比较便宜，较少交换可能有价值，但一般 Python 列表排序应使用内置 `sort`/`sorted`。

### 相关知识点

- 前置知识点：`loop-nested`（嵌套循环）、`array-basic`（列表基础）。
- 后续知识点：`search-insertion`（插入排序）、`search-sort`（排序思想）。
- 来源：Python 官方文档 [Sorting Techniques](https://docs.python.org/3/howto/sorting.html)；复杂度与稳定性为算法性质说明。


## 9. 插入排序
`document_id: python-search-insertion`

插入排序像整理手中的扑克牌：左侧始终有序，取出右侧下一个元素作为 `key`，把左侧所有更大的元素右移，再把 `key` 放到空位。对于小规模或大体有序的数据，它的行为直观，且移动只发生在局部。

- 概念：最坏和平均时间复杂度 `O(n²)`，输入已升序时最好 `O(n)`；原地版本额外空间 `O(1)`。若只在前项严格大于 `key` 时右移，相等元素不会越过彼此，因此算法稳定。循环结束后，已处理前缀保持有序是核心不变量。

### 正例代码

```python
def insertion_sort(values):
    items = list(values)
    for i in range(1, len(items)):
        key = items[i]
        j = i - 1
        while j >= 0 and items[j] > key:
            items[j + 1] = items[j]  # 大元素右移，空位逐步左移
            j -= 1
        items[j + 1] = key
    return items

print(insertion_sort([5, 2, 4, 2, 1]))  # [1, 2, 2, 4, 5]
```

- 正例：从下标 1 开始逐个插入；`j >= 0` 防止访问负下标，`items[j] > key` 保留相等元素原有次序，最终插入位置是 `j + 1`。复制输入让本函数返回新列表，不改动原列表。

### 反例与易错点

```python
def broken_insertion(values):
    items = list(values)
    for i in range(1, len(items)):
        key = items[i]
        j = i - 1
        while j >= 0 and items[j] > key:
            items[j + 1] = items[j]
            j -= 1
        items[j] = key  # 错：应插到 j + 1
    return items

print(broken_insertion([2, 1]))  # 可能得到 [1, 1]，覆盖原值
```

- 反例：移动循环结束时 `j` 已经停在首个不大于 `key` 的位置，真正空出来的槽位是 `j + 1`；写到 `j` 会覆盖原元素，或在列表头部场景访问 `items[-1]`。
- 常见错误：漏掉 `items[j + 1] = key`；右移后没有递减 `j`；循环条件漏掉 `j >= 0`；将 `>` 改为 `>=` 后无意破坏稳定性；误以为逆序大列表上也比高效排序更快。

### 练习

- 基础题：对 `[4, 2, 3]` 跟踪每轮插入后的列表，并测试空列表和单元素列表。
- 答案要点：插入 2 后为 `[2,4,3]`；插入 3 后为 `[2,3,4]`；空表和单元素表均原样返回。
- 进阶题：把记录按分数升序排列，保持同分学生的原始顺序，并解释如何检查稳定性。
- 进阶答案要点：比较键只用 `score > key_score` 时移动，不能用 `>=`；给同分记录附上原始序号，检查排序后序号仍递增即可。

### 相关知识点

- 前置知识点：`array-traverse`（列表遍历）、`loop-while`（while 循环）。
- 后续知识点：`search-sort`（排序思想）、`search-binary`（二分查找，需排序后使用）。
- 来源：Python 官方文档 [Sorting Techniques](https://docs.python.org/3/howto/sorting.html)；插入排序性质按算法定义说明。


## 10. 哈希查找
`document_id: python-search-hash`

哈希查找用哈希函数把可哈希对象映射到内部存储位置。Python 的 `set` 适合回答“是否出现过”，`dict` 适合把键映射到位置、次数或其他信息。它们通常能把反复线性扫描改成一次构建加多次快速查询。

- 概念：集合和字典的查找、插入平均为期望 `O(1)`，发生大量哈希冲突时最坏可退化；不要把平均复杂度说成绝对保证。键必须可哈希：整数、字符串、元组（其元素也可哈希）可作键，列表和字典不可直接作键。集合没有面向业务的顺序保证，不能依赖遍历顺序。需要位置时可将值映射到下标；若同值可重复出现，还需定义保留首个、末个还是全部。

### 正例代码

```python
def two_sum(values, target):
    seen = {}  # 数值 -> 最早出现的下标
    for index, value in enumerate(values):
        needed = target - value
        if needed in seen:
            return seen[needed], index
        seen.setdefault(value, index)
    return None

print(two_sum([4, 7, 1, 9], 8))  # (0, 2)
print(7 in {4, 7, 1, 9})         # True
```

- 正例：每到一个数，先检查补数是否在已扫描前缀中，再记录当前值；因此不会把同一个元素用两次。字典记录下标，适用于题目要求返回位置。一次扫描平均 `O(n)` 时间，额外空间最坏 `O(n)`。

### 反例与易错点

```python
positions = {[1, 2]: 0}  # TypeError: unhashable type: 'list'

values = [4, 4]
seen = set()
for value in values:
    if value in seen:
        print("重复")
    seen.add(value)
# 若题目要求两个不同下标组成 target=8，仅用“先查再加”能正确识别；
# 若先 add 再查，就可能把当前元素与自己配对。
```

- 反例：列表不可哈希，不能作为 `set` 成员或字典键；需要时可转为元组（前提是内部元素也可哈希）。两数之和若先把当前值放入字典再查补数，目标为 `2 * value` 时可能错误地用当前下标配自己。
- 常见错误：误认为哈希查询始终严格 `O(1)`；使用列表等不可哈希键；在查找前插入导致自匹配；字典只保存一个下标却未确认重复元素语义；依赖集合遍历顺序；忽略额外空间成本。

### 练习

- 基础题：用集合判断一组整数中是否有重复值，并说明最多扫描多少次。
- 答案要点：遍历每个值，若已在 `seen` 中则存在重复，否则加入集合；最坏扫描 `n` 项，期望时间 `O(n)`、额外空间 `O(n)`。
- 进阶题：实现两数之和，返回所有满足条件的不同下标对，并处理重复值。
- 进阶答案要点：定义输出是否允许同一值的多个配对；可用映射 `值 -> 已出现下标列表`，先查询补数，再记录当前下标，避免自配；最坏输出本身可能有 `O(n²)` 个结果。

### 相关知识点

- 前置知识点：`dict-basic`（字典基础）、`set-basic`（集合基础）、`search-linear`（顺序查找）。
- 后续知识点：`search-stat`（统计与去重）、`search-two-pointer`（双指针搜索）。
- 来源：Python 官方教程 [Data Structures](https://docs.python.org/3/tutorial/datastructures.html#sets)；平均与最坏复杂度按哈希表算法分析说明。


## 11. 双指针搜索
`document_id: python-search-two-pointer`

双指针用两个位置共同维护搜索范围。左右指针常用于已排序数组：若两端之和太小，就移动左端增加和；若太大，就移动右端减小和。这个“每步都能安全排除一批候选”的理由依赖排序，不能把模板套在任意乱序数据上。

- 概念：在升序数组中查找和为 `target` 的一对不同下标，可令 `left=0, right=n-1`。和小于目标时，固定当前左端不可能与任何更靠左的数配成答案，故 `left += 1`；和大于目标时，固定当前右端也不可能，故 `right -= 1`。每轮至少移动一个指针，最多 `n` 轮，时间 `O(n)`、额外空间 `O(1)`。若要找全部组合或允许重复值，输出与去重规则需另行定义。

### 正例代码

```python
def two_sum_sorted(values, target):
    left, right = 0, len(values) - 1
    while left < right:  # 两个不同位置
        total = values[left] + values[right]
        if total == target:
            return left, right
        if total < target:
            left += 1
        else:
            right -= 1
    return None

print(two_sum_sorted([1, 2, 4, 7, 11], 9))  # (1, 3)
```

- 正例：列表升序是指针移动正确性的依据。当前和为 5 小于 9 时，左端 1 与任何更小的右端相加只会更小，所以安全移动左指针；命中后返回一对不同下标。

### 反例与易错点

```python
def wrong_two_sum(values, target):
    left, right = 0, len(values) - 1
    while left < right:
        total = values[left] + values[right]
        if total == target:
            return left, right
        if total < target:
            left += 1
        else:
            right -= 1
    return None

print(wrong_two_sum([7, 1, 5], 6))  # 乱序输入可能漏掉 (1, 2)
```

- 反例：`[7, 1, 5]` 未排序，算法先看到 7+5 过大并移动右端，可能跳过真正的 1+5。若原数据无序，可先排序但会增加成本且原始下标丢失；需保留下标时，常用哈希表更合适。
- 常见错误：未验证升序前提；条件写成 `left <= right` 导致同一元素被使用两次；和小就移动右端等方向写反；重复值场景没有定义返回一个还是全部；为了排序破坏了题目要求保留的原始位置。

### 练习

- 基础题：在有序列表 `[1, 3, 4, 6, 8]` 中找和为 10 的两个不同下标，列出每一步的左右指针。
- 答案要点：从 `(0,4)` 得 9，小于 10，左移到 `(1,4)` 得 11，大于 10，右移到 `(1,3)` 得 9，再左移到 `(2,3)` 得 10，返回 `(2,3)`。
- 进阶题：实现“有序列表中目标和是否存在”，并比较双指针与哈希表在时间、空间及排序前提上的差别。
- 进阶答案要点：双指针对已有序输入 `O(n)` 时间、`O(1)` 空间；哈希表期望 `O(n)` 时间、`O(n)` 空间，可处理乱序输入并直接返回原下标；若先排序，排序成本和下标映射必须计算。

### 相关知识点

- 前置知识点：`search-binary`（有序数据查找）、`search-hash`（哈希查找）。
- 后续知识点：`search-stat`（统计与去重）。
- 来源：双指针是基于有序性和单调性的算法技巧；复杂度为本例循环次数分析。


## 12. 广度优先搜索入门
`document_id: python-search-bfs`

广度优先搜索（BFS）从起点开始，先访问距离 1 条边的节点，再访问距离 2 条边的节点，依此按层推进。无权图中，首次到达一个节点时得到的边数就是从起点到它的最短距离。队列保存“接下来要扩展的节点”，访问集合避免重复入队。

- 概念：使用先进先出的队列（Python 推荐 `collections.deque`）实现。把节点标记为已访问应放在入队时，而不是出队时，这样同一节点不会被多个父节点重复加入。邻接表表示图时，遍历时间为 `O(V+E)`、额外空间为 `O(V)`。边有不同权重时，普通 BFS 不保证最低总权重路径，应使用适合权重模型的算法；在网格中也要检查边界和障碍。

### 正例代码

```python
from collections import deque

def shortest_distance(graph, start, target):
    queue = deque([(start, 0)])
    visited = {start}  # 入队时标记，避免重复排队
    while queue:
        node, distance = queue.popleft()
        if node == target:
            return distance
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))
    return None

graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
print(shortest_distance(graph, "A", "D"))  # 2
print(shortest_distance(graph, "D", "A"))  # None：不可达
```

- 正例：`deque.popleft()` 保持先进先出；A 的邻居先入队，之后才扩展下一层。B 和 C 都连接 D，但 D 在第一次入队时就加入 `visited`，所以不会重复排队；从 D 不可达 A 时返回 `None`。

### 反例与易错点

```python
from collections import deque

def slow_queue_search(graph, start):
    queue = [start]
    visited = {start}
    while queue:
        node = queue.pop(0)  # 错：列表头部删除需要搬移后续元素
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)
                # 错：未在这里标记，多个父节点可重复入队
```

- 反例：用列表 `pop(0)` 会导致每次出队搬移后续元素，队列操作可能额外累积到平方级；用 `deque.popleft()`。若只在出队后标记，菱形图中的同一节点会被多个前驱重复入队，增加工作量甚至造成错误的距离处理。
- 常见错误：把栈式 `pop()` 当队列；访问标记太晚；在有权图上把边数最少当作权重和最小；无向图只添加单向边；未处理起点等于终点或目标不可达；网格邻居越界。

### 练习

- 基础题：为图 `A-B, A-C, B-D, C-E, D-F, E-F` 写出从 A 开始的 BFS 层次，并求到 F 的最短边数。
- 答案要点：层次为 `{A}`、`{B,C}`、`{D,E}`、`{F}`，最短距离为 3；同层内部顺序由邻接表顺序决定，但层次距离不变。
- 进阶题：扩展函数返回一条最短路径（节点列表），并验证存在多条同长度路径时返回其中一条。
- 进阶答案要点：入队时记录 `parent[neighbor] = node`；找到目标后从目标沿 parent 回溯至起点，再反转；如需全部最短路径则需保留同层多个前驱，不能只保存一个。

### 相关知识点

- 前置知识点：`array-basic`（列表基础）、`loop-while`（while 循环）、`dict-basic`（字典基础）。
- 后续知识点：图的最短路径与图遍历算法。
- 来源：Python 标准库文档 [collections.deque](https://docs.python.org/3/library/collections.html#collections.deque)；BFS 的最短边数性质适用于无权图。
