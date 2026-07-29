# 模块四：文件、异常与算法实践

本模块把前面的语法组合到实践场景：读写文本文件、用异常处理应对可预期失败，并练习求和统计与线性查找两类基础算法思维。

## 13. 文件操作
`document_id: python-stage4-file`

文件操作让程序持久化数据。推荐 `with open(path, mode, encoding="utf-8") as f:`，离开 `with` 块会自动关闭文件，避免资源泄漏。模式：`r` 读、`w` 写（覆盖）、`a` 追加、`r+` 读写等；文本模式默认按字符，二进制用 `b`。常用方法：`read`、`readline`、`readlines`、`write`、`writelines`。路径相对于当前工作目录，不清楚时打印或使用绝对路径。大文件避免一次性 `read()` 进内存，可按行迭代：`for line in f:`。CSV 可用逗号分隔自行拼接，或后续学习 `csv` 模块。

- 概念：使用 `with open(..., encoding="utf-8")` 自动关闭文件；常见模式包括 `r/w/a`。读文件得到字符串（文本模式），写文件需传入字符串。编码不一致是中文场景下乱码的主因，课程中统一 UTF-8。理解相对路径与工作目录，才能找到“明明有文件却 FileNotFoundError”的原因。文件是连接输入输出与数据结构的桥梁：读入后拆成列表/字典，处理完再写回，形成完整数据闭环。

### 正例代码

```python
# 写入
with open("demo.txt", "w", encoding="utf-8") as file:
    file.write("hello\n")
    file.write("python\n")

# 读取
with open("demo.txt", encoding="utf-8") as file:
    text = file.read()
print(text)

# 按行统计
with open("demo.txt", encoding="utf-8") as file:
    lines = [line.strip() for line in file if line.strip()]
print("行数", len(lines))
```

- 正例：`with open("data.txt", encoding="utf-8") as file: text = file.read()` 安全读取；写文件同样包在 `with` 中。

### 反例与易错点

```python
# w 模式会清空已有内容
with open("scores.csv", "w", encoding="utf-8") as f:
    f.write("name,score\n")  # 若本意追加，应使用 "a"

# 忘记 encoding，在部分系统上读写中文可能异常或乱码
# open("中文.txt")
```

- 反例：写文件时误用 `w` 会覆盖原内容，应根据需求选择 `a` 或先读后写；路径写错会找不到文件。
- 常见错误：相对路径理解错误、忘记编码、一次读取超大文件、打开后不关闭（不用 `with`）、混淆文本与二进制模式。

### 练习

- 基础题：读取一个文本文件，统计非空行数与单词数（单词可用空白分隔近似）。
- 答案要点：`with open` 按行迭代；非空行计数；`line.split()` 累加单词；注意编码。
- 进阶题：把学生姓名与成绩保存为 CSV，并编写对称的加载函数还原为列表或字典。
- 进阶答案要点：写表头与数据行；读时跳过表头；`strip` 与 `split(",")`；成绩转 `int/float`。

### 相关知识点

- 前置知识点：`str`（字符串）、`list`（列表）、`func`（函数）。
- 后续知识点：`except`（异常处理）、`algo-sum`（求和与统计）。
- 来源：Python 官方教程“Reading and Writing Files”。

## 14. 异常处理
`document_id: python-stage4-exception`

异常表示运行时的错误事件。`try` 包裹可能失败的语句，`except` 捕获并处理；可指定具体异常类型如 `ValueError`、`ZeroDivisionError`、`FileNotFoundError`。`else` 在无异常时执行，`finally` 无论是否异常都会执行（常用于清理）。应捕获**可预期且能恢复**的异常，并给出对用户有意义的提示；避免裸 `except:` 或 `except Exception: pass` 吞掉错误。不要用异常代替普通的事前校验，但输入转换、文件 IO、网络调用等场景非常适合。

- 概念：`try/except` 处理可预期异常；应捕获具体异常并保留错误上下文。它让程序在失败时优雅降级，而不是直接崩溃。教学上先掌握“转换失败提示重输”“除数为零提示”“文件不存在提示”三类。记录异常信息（或打印 `Exception` 消息）有助于调试；重新抛出可用 `raise`。异常处理与函数结合时，让函数返回明确状态或抛给上层统一处理，保持层次清晰。

### 正例代码

```python
text = "12a"
try:
    value = int(text)
except ValueError:
    print("请输入整数")
    value = None


def safe_div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        print("除数不能为 0")
        return None
    except TypeError:
        print("请提供数值类型")
        return None
```

- 正例：`try: value = int(text)`，`except ValueError: print("请输入整数")`；除法分别处理零除与类型错误。

### 反例与易错点

```python
try:
    value = int(text)
    result = 100 / value
except:
    pass  # 吞掉所有错误，难以定位

# 异常后仍使用未赋值变量
try:
    value = int("x")
except ValueError:
    print("非法")
# print(value + 1)  # 若失败则 value 可能未定义
```

- 反例：`except: pass` 会吞掉所有错误；捕获后继续使用可能未赋值的变量会再引发异常。
- 常见错误：捕获范围过宽、把正常流程全部塞进 `try`、错误后继续使用无效变量、用异常控制纯粹的业务分支。

### 练习

- 基础题：实现安全除法函数，处理零除和非法输入（非数值），返回结果或提示。
- 答案要点：`try` 中转换并相除；分别 `except ZeroDivisionError` 与 `ValueError`/`TypeError`。
- 进阶题：为文件读取程序分别处理文件不存在、编码错误与权限错误，给出不同提示。
- 进阶答案要点：捕获 `FileNotFoundError`、`UnicodeDecodeError`、`PermissionError`；提示中包含文件名。

### 相关知识点

- 前置知识点：`io`（输入输出）、`file`（文件操作）、`func`（函数）。
- 后续知识点：`algo-sum`（求和与统计）、综合项目练习。
- 来源：Python 官方教程“Errors and Exceptions”。

## 15. 求和与统计
`document_id: python-stage4-sum-statistics`

求和与统计是数据扫描的基本模式：准备累计变量（总和、计数、最值），遍历序列，按条件更新，最后输出或返回结果。一次遍历完成多项统计的时间复杂度通常为 `O(n)`，优于多次重复扫描。空序列求平均会除零，必须先判断计数。可用内置 `sum`、`len`、`max`、`min`，也建议手写以巩固循环不变量。筛选类统计（如偶数之和）把条件放在更新之前。

- 概念：累计变量用于求和，计数器用于统计满足条件的元素；遍历一次通常为 `O(n)`。初始化位置必须在循环外，更新在循环内，这是所有聚合算法的骨架。扩展到平均值、最值、方差时，仍遵循“初始化—扫描—收尾”三步。该模式直接迁移到文件逐行统计与字典计数。理解复杂度有助于日后对比更优算法，但课程阶段正确性与边界处理优先。

### 正例代码

```python
values = [1, 2, 3, 4, 5]
total = 0
for value in values:
    total += value
print(total)

even_sum = 0
even_count = 0
for value in values:
    if value % 2 == 0:
        even_sum += value
        even_count += 1


def summarize(nums):
    if not nums:
        return None
    total = 0
    lo = hi = nums[0]
    for x in nums:
        total += x
        if x < lo:
            lo = x
        if x > hi:
            hi = x
    return {
        "count": len(nums),
        "sum": total,
        "avg": total / len(nums),
        "min": lo,
        "max": hi,
    }
```

- 正例：`total = 0` 后循环 `total += value`；一次遍历同时维护计数、总和与最值。

### 反例与易错点

```python
values = [1, 2, 3]
total = 0
for value in values:
    total = 0  # 错误：每轮重置
    total += value
print(total)  # 只剩 3

# 空列表直接求平均
nums = []
# avg = sum(nums) / len(nums)  # ZeroDivisionError
```

- 反例：把 `total = 0` 写在循环内部会导致每轮重置；空集合除零未防护。
- 常见错误：初始化位置错误、空集合除零、筛选条件边界遗漏、最值初始化用 0 导致全负数组出错。

### 练习

- 基础题：统计列表中偶数的数量并计算它们的和。
- 答案要点：两变量计数与累加；`value % 2 == 0` 时更新；最后输出两个结果。
- 进阶题：一次遍历同时计算数量、总和、平均值、最大值和最小值，封装为函数返回字典。
- 进阶答案要点：空列表提前返回；最值用首元素初始化；平均在循环结束后计算。

### 相关知识点

- 前置知识点：`loop`（循环结构）、`list`（列表）、`func`（函数）。
- 后续知识点：`algo-search`（线性查找）、`file`（文件操作）。
- 来源：Python 官方教程“More Control Flow Tools”“Data Structures”。

## 16. 线性查找
`document_id: python-stage4-linear-search`

线性查找（顺序查找）从左到右依次比较元素与目标：命中则返回位置或元素，扫描结束仍未命中则返回约定值（如 `-1` 或 `None`）。最坏与平均时间复杂度为 `O(n)`，空间 `O(1)`。实现时常用 `enumerate` 同时获得下标与值。若只需判断是否存在，可用 `target in seq`（内部仍是扫描）。有多个重复目标时，要明确返回“第一次”“最后一次”还是“全部位置”。提前 `return`/`break` 可在最好情况下更快结束。

- 概念：线性查找从头到尾比较元素，找到目标后返回位置，最坏时间复杂度为 `O(n)`。它不要求数据有序，实现简单、适用范围广，是理解“算法=明确步骤+复杂度”的第一课。正确区分“未找到”与“找到最后一个”至关重要：循环结束才返回失败哨兵。后续有序数据可学习二分查找，但必须先保证线性查找的边界与返回约定完全正确。

### 正例代码

```python
def linear_search(values, target):
    for index, value in enumerate(values):
        if value == target:
            return index
    return -1


def find_all(values, target):
    return [i for i, v in enumerate(values) if v == target]


data = ["a", "b", "c", "b"]
print(linear_search(data, "b"))  # 1（第一次出现）
print(find_all(data, "b"))       # [1, 3]
print(linear_search(data, "z"))  # -1
```

- 正例：`for index, value in enumerate(values):` 命中则 `return index`；未找到返回 `-1`。

### 反例与易错点

```python
def broken_search(values, target):
    for index, value in enumerate(values):
        if value == target:
            found = index
    return found  # 未找到时 found 未定义；或误返回最后一次循环的 index


def broken_search2(values, target):
    for index, value in enumerate(values):
        if value == target:
            break
    return index  # 未找到时仍返回最后下标，假阳性
```

- 反例：循环结束后无条件返回当前下标，会把“未找到”误报为最后一个位置；未定义失败返回值导致异常或逻辑错误。
- 常见错误：未定义未找到返回值、重复元素策略不清、索引和值混淆、在空列表上假设一定有元素。

### 练习

- 基础题：编写函数返回目标值第一次出现的索引，未找到时返回 `-1`。
- 答案要点：`enumerate` 扫描；命中立即 `return`；循环结束 `return -1`。
- 进阶题：扩展为返回全部匹配位置列表，并比较“找到首个即停”与“完整扫描”在最好/最坏情况下的差异。
- 进阶答案要点：收集列表；首个即停复杂度最好 `O(1)` 最坏 `O(n)`；全扫描恒为 `O(n)`。

### 相关知识点

- 前置知识点：`loop`（循环结构）、`list`（列表）、`algo-sum`（求和与统计）。
- 后续知识点：简单排序思想（拓展）、二分查找（拓展，需有序）。
- 来源：Python 官方教程“Data Structures”，Python Wiki“TimeComplexity”。
