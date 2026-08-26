# 模块四：循环结构

本模块学习如何让计算机重复做事：用 `for` 配 `range` 处理次数已知的遍历与累加，用 `while` 处理次数事先未知的“条件成立就继续”，用嵌套循环处理行列二维结构，最后用 `break`、`continue` 精细控制循环的提前退出与跳轮。学完后应能写出求和、计数、查找、打印图形这类批处理程序。

## 1. for 与 range
`document_id: python-loop-for`

`for` 循环用来逐个取出可迭代对象中的元素：字符串、列表、`range` 都可以直接遍历。写法是 `for 变量 in 可迭代对象:`，每轮把一个元素绑定到变量上，执行一遍缩进的循环体，元素取完就自然结束。当需要“重复固定次数”或“生成一串整数”时，用 `range(start, stop, step)`，它的规则是**左闭右开**——包含 `start`，不包含 `stop`。初学者最容易卡在两点：一是误以为 `range(1, 5)` 包含 5，导致少循环一次；二是把累加器 `total = 0` 写进了循环体内部，每轮都被清零。

- 概念：`for` 遍历可迭代对象的每个元素，循环次数由对象长度决定，不需要手动维护计数器，因此比 `while` 更不容易出现死循环。`range(stop)` 从 0 开始；`range(start, stop)` 步长默认为 1；`range(start, stop, step)` 可指定步长，`step` 为负时递减，但不能为 0（否则抛 `ValueError`）。`range` 是惰性对象，`print(range(5))` 不会显示元素，需要 `list(range(5))` 才看到 `[0, 1, 2, 3, 4]`。累加求和是最常用的循环模式：在循环外初始化 `total = 0`，循环内 `total += 元素`，循环结束后 `total` 就是结果；计数、求最大值同理。遍历序列时若只需要元素本身，写 `for x in xs` 比 `for i in range(len(xs))` 更清晰；只有确实需要下标时才用后者，此时合法下标是 `0` 到 `len(xs) - 1`。

### 正例代码

```python
for i in range(1, 6):        # 左闭右开：1 2 3 4 5，不含 6
    print(i, end=" ")
print()

total = 0                    # 累加器必须初始化在循环外
for i in range(1, 101):
    total += i
print(total)                 # 5050

for ch in "Python":          # 逐个取出字符串中的字符
    print(ch, end="-")
print()

scores = [88, 92, 79]
for s in scores:             # 直接遍历元素，无需下标
    print(s, end=" ")
print()
print(list(range(10, 0, -2)))  # [10, 8, 6, 4, 2]，负步长递减
```

- 正例：`for i in range(1, 6):` 恰好取到 5，体现左闭右开；`total = 0` 放在循环之外、`total += i` 放在循环之内，构成标准累加模式；`for ch in "Python":` 与 `for s in scores:` 演示直接遍历字符串与列表。

### 反例与易错点

```python
# 错误：期望输出 1..5，实际只有 1..4
for i in range(1, 5):
    print(i, end=" ")
print()

total = 0
for x in [1, 2, 3]:
    total = 0                # 错误：累加器每轮被清零
    total += x
print(total)                 # 3，而不是 6

for i in range(1, 4, 0):     # ValueError: range() arg 3 must not be zero
    print(i)
```

- 反例：`range(1, 5)` 不含 5，想覆盖 1 到 5 必须写 `range(1, 6)`，这是最经典的 off-by-one 错误；把 `total = 0` 写进循环体会让结果只剩最后一个元素，正确做法是把初始化提到循环之前；步长写 0 会抛 `ValueError`。

- 常见错误：把 `stop` 当成包含在内导致少循环一次、累加器在循环内重复初始化、步长为 0 或负步长方向写反得到空序列、用 `range(len(xs))` 时下标越界抛 `IndexError`、在遍历列表的同时增删其元素。

### 练习

- 基础题：用 `for` 配 `range` 输出 1 到 100 中所有 3 的倍数。
- 答案要点：直接写 `for n in range(3, 101, 3):` 最简洁；或遍历 `range(1, 101)` 后用 `if n % 3 == 0:` 过滤；注意上界要写 101 才能包含 100。
- 进阶题：给定一个成绩列表，统计总分、平均分（保留一位小数）和及格人数，并输出最高分。
- 进阶答案要点：循环外初始化 `total = 0`、`passed = 0`、`highest = scores[0]`；循环内累加、条件计数、用 `if s > highest:` 更新最大值；平均分用 `total / len(scores)` 并注意列表为空时避免除零。

### 相关知识点

- 前置知识点：`seq-expr`（运算与表达式）、`branch-if`（单分支与双分支）。
- 后续知识点：`loop-while`（while 循环）、`array-traverse`（数组遍历）。
- 来源：Python 官方教程“4.2. for Statements”“4.3. The range() Function”。

## 2. while 循环
`document_id: python-loop-while`

`while` 的语义是“只要条件成立，就一直重复”。它先判断条件，为真则执行循环体，然后回到条件重新判断，直到条件为假才退出。与 `for` 最大的区别是：`for` 的次数由被遍历对象决定，而 `while` 的次数完全取决于循环体有没有把条件推向为假。这就带来了最大的坑——**死循环**：如果循环体里忘记更新条件涉及的变量，程序会永远卡在那里。因此写 `while` 时必须先想清楚两件事：循环变量在哪里初始化，以及循环体里哪一句让条件最终变假。

- 概念：`while 条件:` 在每轮开始前求值条件，为真执行循环体，为假立即退出，因此循环体可能一次都不执行。常见的两种控制方式是**计数器**和**哨兵值**：计数器在循环外初始化（如 `count = 1`），循环内自增（`count += 1`），条件写成 `count <= n`；哨兵值指约定一个特殊数据（如 `-1`、空字符串）表示“输入结束”，条件里检测它是否出现。选择 `for` 还是 `while` 的判据很简单：迭代对象或次数已经明确，就用 `for`，它自带终止保证；次数取决于运行时状态（读到结束标记、精度达到要求、用户选择退出），才用 `while`。`while True:` 配 `break` 是处理“先读入再判断”的惯用写法，但必须保证循环体内有能触发 `break` 的路径，否则就是无限循环。调试死循环时可在循环体内临时打印关键变量，观察它是否在朝着终止条件变化。

### 正例代码

```python
count = 1
while count <= 5:            # 计数器模式：条件成立就重复
    print(count, end=" ")
    count += 1               # 关键：让条件最终变为假
print()

data = [12, 7, -1, 9]
total, i = 0, 0
while i < len(data) and data[i] != -1:   # -1 作为结束哨兵值
    total += data[i]
    i += 1
print(total)                 # 19，读到 -1 就停下

n = 1
while n < 100:               # 次数事先未知，正适合 while
    n *= 3
print(n)                     # 243
```

- 正例：`count = 1` 在循环外初始化、`count += 1` 在循环内更新，缺了后者立刻变死循环；`while i < len(data) and data[i] != -1:` 先用短路的 `and` 保证下标不越界再取元素；`while n < 100: n *= 3` 展示了次数无法事先算出的场景。

### 反例与易错点

```python
count = 0
while count < 5:
    print(count)
    # 错误：忘记 count += 1，条件永远为真 → 死循环，只能 Ctrl+C 终止

x = 10
while x != 0:
    x -= 3                   # 10 7 4 1 -2 ...，永远跳不到 0 → 死循环
print("结束")

while True:
    pass                     # 错误：没有任何 break，无限循环
```

- 反例：第一段漏了 `count += 1`，条件恒为真，程序会一直打印 0 直到被强行中断；第二段用 `!=` 做终止判断，但步长 3 无法整除 10，`x` 会越过 0 继续变负，应改成 `while x > 0:` 这类不会被跨过的条件；`while True` 内没有 `break` 则永不退出。

- 常见错误：循环体内忘记更新条件变量导致死循环、用 `!=` 判断终止却被步长跨过、循环变量在循环内被重新初始化、`while True` 缺少 `break` 出口、误把 `while` 用在次数已知的场景（应用 `for`）。

### 练习

- 基础题：用 `while` 输出 1 到 10 的整数，并在循环结束后输出它们的和。
- 答案要点：循环外 `i = 1`、`total = 0`；循环条件 `i <= 10`；循环内先 `total += i` 再 `i += 1`，两句缺一不可。
- 进阶题：反复读取成绩，输入 `-1` 表示结束，最后输出有效成绩的个数与平均分；若没有任何有效成绩则提示“无有效数据”。
- 进阶答案要点：用 `while True:` 配 `if x == -1: break` 实现“先读入后判断”；用 `total` 与 `count` 分别累加与计数；输出前先判断 `count == 0` 以避免除零抛 `ZeroDivisionError`。

### 相关知识点

- 前置知识点：`loop-for`（for 与 range）、`branch-if`（单分支与双分支）。
- 后续知识点：`loop-nested`（嵌套循环）、`loop-control`（break 与 continue）。
- 来源：Python 官方教程“3.2. First Steps Towards Programming”，Python 官方语言参考“The while statement”。

## 3. 嵌套循环
`document_id: python-loop-nested`

把一个循环写进另一个循环的循环体里，就是嵌套循环。它的执行方式是：外层每走一轮，内层要完整地走完一整遍。处理二维结构时通常约定**外层控制行、内层控制列**，内层循环结束后用一个不带参数的 `print()` 换行，这样才能打印出矩形、三角形和九九乘法表。理解嵌套循环的关键是想清楚“内层的范围是否依赖外层变量”：范围固定就是矩形，范围写成 `range(1, i + 1)` 就是三角形。初学者最容易卡在换行 `print()` 放错缩进层级，以及内外层不小心用了同一个循环变量名。

- 概念：嵌套循环的总执行次数是各层次数的乘积：外层 `m` 轮、内层 `n` 轮，循环体共执行 `m * n` 次，这就是双重循环时间复杂度记作 O(n²) 的直观来源——数据规模翻倍，耗时约变成四倍，所以三层以上嵌套在大数据量下要格外谨慎。内层循环的上界可以引用外层变量，这是打印三角形与生成下三角乘法表的核心技巧。缩进决定了语句属于哪一层：写在内层循环体里的语句每轮列都执行，写在外层循环体里（与内层 `for` 同级）的语句每轮行执行一次，写在两层之外的语句整段只执行一次。内外层必须使用不同的循环变量名（惯例是 `i`、`j`），否则内层会覆盖外层变量的当前值，破坏外层逻辑。同理，跨行累计的变量要初始化在外层之外，只在本行内累计的变量才初始化在外层循环体内。

### 正例代码

```python
for i in range(1, 4):        # 外层控制行
    for j in range(1, 4):    # 内层控制列
        print(f"({i},{j})", end=" ")
    print()                  # 与内层 for 同级：每行结束换行

for i in range(1, 6):        # 直角三角形，第 i 行 i 个星号
    print("*" * i)

for i in range(1, 10):       # 九九乘法表（下三角）
    for j in range(1, i + 1):    # 内层上界依赖外层 i
        print(f"{j}*{i}={i * j}", end="\t")
    print()
```

- 正例：第一段中 `print()` 与内层 `for` 保持同一缩进级别，因此每完成一行才换行；九九乘法表的内层写成 `range(1, i + 1)`，让第 `i` 行只输出 `i` 个式子，`end="\t"` 保证同行输出并用制表符对齐。

### 反例与易错点

```python
for i in range(1, 4):
    for j in range(1, 4):
        print(f"({i},{j})", end=" ")
print()                      # 错误：换行退到了循环之外，9 个坐标挤在一行

for i in range(1, 4):
    for i in range(1, 4):    # 错误：内外层同名，外层的 i 被内层覆盖
        print(i, end=" ")
    print()

total = 0
for i in range(1, 4):
    total = 0                # 错误：跨行累计的变量被每行清零
    for j in range(1, 4):
        total += j
print(total)                 # 6，而不是 18
```

- 反例：把 `print()` 的缩进退到两层循环之外，只在最后换一次行，全部输出挤成一行，正确做法是与内层 `for` 同级；内外层共用变量名 `i` 会让外层的当前值在内层被改写，应改为 `j`；`total = 0` 写在外层循环体内相当于每行清零，最终只保留最后一行的和。

- 常见错误：换行 `print()` 缩进层级放错、内外层使用同一个循环变量名、内层上界该依赖外层却写成固定值（三角形变矩形）、跨层累计变量初始化位置不当、嵌套层数过多导致运行时间不可接受。

### 练习

- 基础题：用嵌套循环打印一个 4 行 5 列的星号矩形。
- 答案要点：外层 `for i in range(4):`，内层 `for j in range(5): print("*", end="")`，内层结束后与其同级写 `print()` 换行。
- 进阶题：打印完整的九九乘法表（9 行 9 列或下三角均可），要求每列对齐；再统计整张表中所有乘积之和。
- 进阶答案要点：外层 `i` 控制行、内层 `j` 控制列，下三角写 `range(1, i + 1)`；用 `end="\t"` 或 `f"{i*j:4d}"` 对齐；求和的 `total = 0` 必须放在两层循环之外，内层累加 `total += i * j`。

### 相关知识点

- 前置知识点：`loop-for`（for 与 range）、`loop-while`（while 循环）。
- 后续知识点：`array-2d`（二维数组）、`search-sort`（排序）。
- 来源：Python 官方教程“4.2. for Statements”“4.3. The range() Function”。

## 4. break 与 continue
`document_id: python-loop-control`

有时循环不该老老实实走完：在列表里找到目标就该立刻停下，遇到无效数据则应跳过继续。`break` 负责“提前跳出”——立即终止整个循环，后面的元素一个都不再处理；`continue` 负责“跳过本轮”——放弃循环体内剩下的语句，直接进入下一轮。两者都只作用于**最内层**的那个循环，在嵌套循环里用 `break` 并不能一次跳出所有层。此外 Python 的 `for` 和 `while` 还可以带 `else` 子句：只有循环**正常结束（没有被 break 打断）**时才执行它，这正好用来表达“查找失败”的情形。

- 概念：`break` 立即结束当前所在的那一层循环，控制流跳到该循环之后的第一条语句；`continue` 结束本轮迭代，跳回循环头继续下一轮。在嵌套循环中，它们只影响直接包含自己的那一层，要跳出多层需要借助标志变量或把内层循环封装成函数用 `return` 返回。循环的 `else` 子句语义容易误解：它不是“条件为假时执行”，而是“循环没有被 `break` 中断而自然结束时执行”，配合 `for ... break ... else` 可以优雅地写出“找到就处理、找不到就报告”的查找逻辑，避免额外维护一个 `found` 标志变量。特别注意 `continue` 用在 `while` 里的风险：如果计数器的自增语句写在 `continue` 之后，跳轮时就不会执行自增，条件永远不变，直接导致死循环；而 `for` 循环的变量由迭代器推进，所以不存在这个问题。

### 正例代码

```python
data = [3, 8, -1, 5]

for x in data:
    if x < 0:
        break                # 遇到负数立即跳出整个循环
    print(x, end=" ")
print()                      # 输出 3 8

for x in data:
    if x < 0:
        continue             # 跳过本轮剩余语句，进入下一轮
    print(x, end=" ")
print()                      # 输出 3 8 5

target = 7
for x in data:
    if x == target:
        print("找到了")
        break
else:                        # 循环未被 break 打断才执行
    print("没找到")
```

- 正例：`if x < 0: break` 在遇到 `-1` 时终止循环，因此 5 不会被输出；换成 `continue` 后只跳过 `-1` 这一轮，5 仍会输出；`for ... else` 中的 `else` 与 `for` 同级，因为没有元素等于 7 而执行，输出“没找到”。

### 反例与易错点

```python
for i in range(1, 4):
    for j in range(1, 4):
        if j == 2:
            break            # 只跳出内层，外层仍会走完三轮
    print(i, end=" ")        # 仍输出 1 2 3
print()

count = 0
while count < 5:
    if count == 2:
        continue             # 错误：自增写在后面，跳轮后 count 永不变 → 死循环
    print(count)
    count += 1
```

- 反例：嵌套循环中的 `break` 只终止内层，误以为能一次跳出两层会导致外层继续执行，需要用标志变量或封装函数配合 `return`；`while` 里 `continue` 跳过了 `count += 1`，条件恒为真形成死循环，正确写法是在 `continue` 之前先更新计数器。

- 常见错误：以为 `break` 能跳出所有嵌套层、`while` 中 `continue` 跳过了计数器自增导致死循环、把 `for...else` 的 `else` 理解成“条件为假”、`break`/`continue` 写在循环之外抛 `SyntaxError`、用 `break` 跳出后仍访问循环变量却忘记它停在中途。

### 练习

- 基础题：遍历一个整数列表，输出遇到的第一个负数并立即结束循环。
- 答案要点：循环内 `if x < 0: print(x); break`；`break` 保证只输出第一个；可再配 `else:` 分支提示“没有负数”。
- 进阶题：在一个列表中查找指定元素，找到就输出它的下标并停止，找不到则输出“未找到”；再统计该列表中所有正数之和，负数与 0 一律跳过。
- 进阶答案要点：查找用 `for i in range(len(xs)):` 配 `if xs[i] == target: break`，并用与 `for` 同级的 `else:` 输出“未找到”；求和用 `if x <= 0: continue` 过滤，累加器初始化在循环之外。

### 相关知识点

- 前置知识点：`loop-while`（while 循环）、`loop-nested`（嵌套循环）。
- 后续知识点：`search-linear`（线性查找）、`func-define`（函数定义）。
- 来源：Python 官方教程“4.4. break and continue Statements, and else Clauses on Loops”。
