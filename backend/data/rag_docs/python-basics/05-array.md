# 模块五：数组

本模块讲解 Python 中最常用的批量数据容器——列表（在算法语境中常被称作“数组”）。内容覆盖列表的创建与增删改查、用循环对列表做遍历统计，以及用嵌套列表表示表格与矩阵。学完后应能把“一组成绩、一张表格”组织成结构化数据，并对其完成求和、计数、找极值等基础处理。

## 1. 列表基础
`document_id: python-array-basic`

列表 `list` 是可变、有序的元素序列，用方括号书写：`scores = [70, 88, 92]`。它通过下标访问元素，下标从 0 开始，`s[-1]` 表示最后一个元素；切片 `s[a:b]` 遵循左闭右开，取出的是新列表。增删元素靠 `append`（末尾追加）、`insert`（指定位置插入）、`pop`（弹出并返回）、`remove`（按值删除），元素个数用 `len()` 获取。初学者最容易卡住的有两处：一是把下标当成“第几个”而越界；二是误以为 `b = a` 复制了列表——其实两个名字指向同一对象，改动一个另一个也会变。

- 概念：列表是可变有序容器，支持索引、切片、增删改与遍历，是组织“一组同类数据”的首选结构。可变意味着列表对象能被原地修改，因此 `append`、`insert`、`remove` 都返回 `None` 而非新列表，不能写成 `xs = xs.append(x)`。赋值语句只是给同一对象再起一个名字，所以 `b = a` 之后二者共享内容，称为别名或引用共享；`b = a[:]`（或 `a.copy()`）才会创建内容相同的新列表。切片始终左闭右开，负索引从右往左数，两者叠加时容易越界误判。

### 正例代码

```python
scores = [70, 88, 92, 65]
print(scores[0])                # 70，下标从 0 开始
print(scores[-1])               # 65，负索引表示最后一个
print(scores[1:3])              # [88, 92]，切片左闭右开
print(len(scores))              # 4

scores.append(100)              # 末尾追加
scores.insert(1, 75)            # 在下标 1 处插入
last = scores.pop()             # 弹出并返回末尾元素 100
scores.remove(65)               # 按值删除第一个 65
print(scores, last)             # [70, 75, 88, 92] 100

alias = scores                  # 别名：与 scores 是同一个列表
copy = scores[:]                # 复制：内容相同的新列表
alias.append(60)
print(scores[-1], len(copy))    # 60 4
```

- 正例：`scores[1:3]` 取下标 1、2 两个元素，体现左闭右开；`last = scores.pop()` 说明 `pop` 会把删掉的值交还给调用方；`copy = scores[:]` 与 `alias = scores` 的对比是本节关键——`alias.append(60)` 改了原列表，而 `copy` 的长度仍是 4。

### 反例与易错点

```python
nums = [1, 2, 3]
# print(nums[3])          # IndexError：合法下标只有 0、1、2
# nums = nums.append(4)   # append 返回 None，nums 会被覆盖成 None

a = [1, 2, 3]
b = a                     # 只是起了别名，并没有复制
b.append(4)
print(a)                  # [1, 2, 3, 4]，原列表被改动了

print(a[1:99])            # [2, 3, 4]：切片越界不报错，容易掩盖逻辑错误
```

- 反例：`nums[3]` 会抛 `IndexError`，因为长度为 3 的列表最大合法下标是 2；`nums = nums.append(4)` 让 `nums` 变成 `None`，正确写法是单独调用 `nums.append(4)`；`b = a` 之后 `b.append(4)` 连带改动了 `a`，若要独立副本应写 `b = a[:]` 或 `b = a.copy()`。
- 常见错误：下标越界（把 `len(xs)` 当成合法下标）、把 `append`/`sort` 的返回值 `None` 赋回变量、用 `b = a` 当作复制列表、混淆负索引与切片边界（如误以为 `xs[0:-1]` 包含最后一个元素）。

### 练习

- 基础题：创建一个含五个整数的列表，输出它的第一个元素、最后一个元素和中间三个元素组成的切片。
- 答案要点：首元素用 `xs[0]`，末元素用 `xs[-1]`；中间三个用 `xs[1:4]`，注意右端下标取不到。
- 进阶题：给定一个成绩列表，在不改变原列表的前提下得到一个“去掉最低分后按原顺序排列”的新列表。
- 进阶答案要点：先 `result = scores[:]` 复制，再用 `result.remove(min(scores))` 删掉一个最低分；空列表要单独处理，避免 `min` 抛 `ValueError`。

### 相关知识点

- 前置知识点：`lang-var`（变量与赋值）、`seq-type`（数据类型）。
- 后续知识点：`array-traverse`（遍历与统计）、`array-2d`（二维列表）。
- 来源：Python 官方教程“An Informal Introduction to Python — Lists”“Data Structures — More on Lists”。

## 2. 遍历与统计
`document_id: python-array-traverse`

拿到一个列表后，最常做的事就是从头到尾扫一遍，顺路完成求和、计数、找最大最小值。`for score in scores:` 直接取出每个元素，写法最简洁；若同时需要下标，用 `enumerate(scores)` 一次拿到 `(下标, 元素)`，比 `for i in range(len(scores))` 再取 `scores[i]` 更清晰。Python 还提供 `sum`、`max`、`min`、`len`，能一行得到结果。初学者最容易卡在两点：累加器写在循环体内导致每轮被清零；以及遍历过程中删除元素，导致后面的元素被“跳过”。

- 概念：遍历统计的通用模式是“循环外初始化累加器，循环内更新，循环后使用结果”。求和用 `total += x`；计数用满足条件才 `count += 1`；找极值应用首元素初始化 `best = xs[0]`，而不是用 0 或某个猜测的大数，否则遇到全负数的列表会出错。`enumerate(xs, start=1)` 能让下标从 1 开始，适合输出“第几名”。内置的 `sum`/`max`/`min` 更快也更易读，但对空列表 `max`/`min` 会抛 `ValueError`，需先判断 `if xs:`。列表在遍历期间被增删会改变长度与位置的对应关系，正确做法是遍历副本或用新列表收集结果。

### 正例代码

```python
scores = [70, 88, 92, 65, 88]

total = 0
best = scores[0]                 # 用首元素初始化，而不是用 0
worst = scores[0]
high_count = 0
for score in scores:
    total += score
    if score > best:
        best = score
    if score < worst:
        worst = score
    if score >= 85:
        high_count += 1
print(total, best, worst, high_count)   # 403 92 65 3

for rank, score in enumerate(scores, start=1):
    print(f"第 {rank} 位：{score}")

print(sum(scores), max(scores), min(scores), len(scores))   # 403 92 65 5
```

- 正例：`total`、`best`、`high_count` 都在 `for` 之前初始化，循环内只做更新；`best = scores[0]` 避免了用 0 当初值的隐患；`enumerate(scores, start=1)` 同时取到序号与成绩；最后一行用 `sum`/`max`/`min` 复核手写结果。

### 反例与易错点

```python
nums = [1, 2, 2, 3]
for x in nums:
    if x == 2:
        nums.remove(x)      # 边遍历边删除，指针错位
print(nums)                 # [1, 2, 3]：还剩一个 2，没删干净

for x in nums:
    total = 0               # 累加器被写进循环，每轮清零
    total += x
print(total)                # 3，只等于最后一个元素

# print(max([]))            # ValueError：空序列没有最大值
# print(nums[len(nums)])    # IndexError：最大下标是 len(nums) - 1
```

- 反例：在 `for` 中调用 `nums.remove(x)` 会使后续元素前移，循环下标却继续前进，于是漏掉一个 2，正确写法是遍历副本 `for x in nums[:]` 或用列表推导 `nums = [x for x in nums if x != 2]`；把 `total = 0` 写进循环体会每轮清零，初始化必须放在循环之前。
- 常见错误：累加器初始化写在循环内、找极值时用 0 或固定值当初值、遍历时增删元素导致漏项、对空列表直接调用 `max`/`min` 抛 `ValueError`。

### 练习

- 基础题：不使用 `sum` 与 `len`，用 `for` 循环求一个整数列表的总和与平均值。
- 答案要点：循环外置 `total = 0` 与 `count = 0`，循环内同时累加；平均值用 `total / count`，并先判断 `count > 0` 防止除零。
- 进阶题：给定成绩列表，输出最高分及其名次（下标从 1 开始计数），若有并列取第一次出现的位置。
- 进阶答案要点：用 `enumerate(scores, start=1)` 遍历，仅在 `score > best` 时才更新 `best` 与 `best_rank`（用严格大于保证取首次出现）；先判断列表非空。

### 相关知识点

- 前置知识点：`array-basic`（列表基础）、`loop-for`（for 循环）。
- 后续知识点：`array-2d`（二维列表）、`search-linear`（线性查找）、`search-stat`（统计与计数）。
- 来源：Python 官方教程“Data Structures — Looping Techniques”“Built-in Functions”。

## 3. 二维列表
`document_id: python-array-2d`

当数据天然是“行 × 列”的表格时——比如多名学生的多门成绩、棋盘、矩阵——就用“列表的列表”来表示：`grid = [[1, 2, 3], [4, 5, 6]]`。此时 `grid[i]` 是第 i 行（本身是列表），`grid[i][j]` 才是一个元素；行数是 `len(grid)`，列数是 `len(grid[0])`。遍历要用双重循环：外层走行，内层走列。最容易踩的坑是用 `[[0] * 3] * 3` 创建全零表格——`*` 只是把同一个行对象重复三次，改一个格子会看到三行同时变化。

- 概念：二维列表是“元素本身也是列表”的嵌套结构，通过两级下标定位一个格子，第一级选行、第二级选列，顺序不能颠倒。表格类数据通常每行等长，列数取 `len(grid[0])`。遍历有两种写法：`for row in grid:` 嵌套 `for value in row:` 关注元素本身；用 `range(len(grid))` 与 `range(len(grid[i]))` 则同时掌握位置，适合按坐标读写。构造时必须区分“重复引用”与“重复创建”：`[[0] * 3] * 3` 得到三个指向同一列表的引用，而 `[[0] * 3 for _ in range(3)]` 每次循环都新建一行，互不干扰。

### 正例代码

```python
grid = [
    [1, 2, 3],
    [4, 5, 6],
]
print(grid[0][2])                 # 3：第 0 行第 2 列
print(len(grid), len(grid[0]))    # 2 3：行数与列数

for row in grid:                  # 外层走行
    for value in row:             # 内层走列
        print(value, end=" ")
    print()                       # 每行结束后换行

total = 0
for i in range(len(grid)):
    for j in range(len(grid[i])):
        total += grid[i][j]       # 按坐标累加
print(total)                      # 21

zeros = [[0] * 3 for _ in range(3)]   # 每行都是新建的列表
zeros[0][0] = 9
print(zeros)                      # [[9, 0, 0], [0, 0, 0], [0, 0, 0]]
```

- 正例：`grid[0][2]` 展示两级下标的先行后列顺序；内层 `print(value, end=" ")` 配合外层 `print()` 打出整齐的表格；`zeros = [[0] * 3 for _ in range(3)]` 是创建二维列表的标准写法，赋值 `zeros[0][0] = 9` 后只有第一行改变。

### 反例与易错点

```python
wrong = [[0] * 3] * 3       # 三行其实是同一个列表对象
wrong[0][0] = 9
print(wrong)                # [[9, 0, 0], [9, 0, 0], [9, 0, 0]]：三行全变

grid = [[1, 2, 3], [4, 5, 6]]
print(grid[1])              # [4, 5, 6]：漏写第二个下标，拿到的是整行
# print(grid[2][0])         # IndexError：只有 2 行，行下标最大为 1
# print(grid[0][3])         # IndexError：每行只有 3 列，列下标最大为 2
# print(grid[0, 2])         # TypeError：列表不支持逗号形式的多维下标
```

- 反例：`[[0] * 3] * 3` 复制的是引用而非内容，修改 `wrong[0][0]` 会让三行同时变成 `[9, 0, 0]`，应改用 `[[0] * 3 for _ in range(3)]`；`grid[0, 2]` 这种写法是 NumPy 的语法，普通列表会抛 `TypeError`，必须写成 `grid[0][2]`。
- 常见错误：用 `[[0] * n] * m` 创建二维列表导致行共享、行列下标写反（`grid[j][i]`）、把 `len(grid)` 当成列数、漏写第二级下标而误把整行当元素使用。

### 练习

- 基础题：用嵌套循环输出一个 3 行 4 列的二维列表，每行元素以空格分隔、行末换行。
- 答案要点：外层 `for row in grid`，内层 `print(value, end=" ")`，内层结束后补一个空的 `print()` 换行。
- 进阶题：给定一个学生成绩表（每行一名学生的多门成绩），输出每名学生的总分，以及每门课程的平均分。
- 进阶答案要点：每名学生的总分对每一行做 `sum(row)`；课程平均分需按列累加，用 `for j in range(len(grid[0]))` 外层走列、内层走行取 `grid[i][j]`，再除以 `len(grid)`。

### 相关知识点

- 前置知识点：`array-traverse`（遍历与统计）、`loop-nested`（嵌套循环）。
- 后续知识点：`search-linear`（线性查找）、`func-define`（函数定义）。
- 来源：Python 官方教程“Data Structures — Nested List Comprehensions”。
