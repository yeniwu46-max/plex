# 模块三：数据组织

本模块介绍字符串、列表、字典三种核心数据结构，以及用函数封装可复用逻辑。学完后应能组织批量数据，并对数据进行检索、统计与模块化处理。

## 9. 字符串
`document_id: python-stage3-string`

字符串 `str` 是不可变的字符序列，可用单引号、双引号或三引号书写。支持下标 `s[i]`、切片 `s[a:b]`、拼接与重复，以及 `strip`、`lower`、`upper`、`replace`、`split`、`join`、`find`、`count` 等方法。因为不可变，任何“修改”都会返回新字符串，必须重新赋值才保留结果：`s = s.strip()`。遍历可用 `for ch in s`。处理用户输入时，通常先规范化（去空白、统一大小写）再比较或统计。

- 概念：字符串是不可变字符序列，支持索引、切片和丰富的字符串方法。不可变意味着不能执行 `s[0] = "A"`，只能通过拼接或替换产生新串。切片遵循左闭右开；负索引从右侧计数。文本处理任务（回文、词频前处理、格式校验）几乎都从字符串方法开始，再进入列表或字典做聚合。掌握编码意识：源文件与 IO 建议统一 UTF-8，避免中文乱码。

### 正例代码

```python
raw = "  Alice "
name = raw.strip().lower()
print(name)  # alice

text = "Education"
vowels = set("aeiou")
count = sum(1 for ch in text.lower() if ch in vowels)
print(count)


def is_palindrome(s: str) -> bool:
    t = "".join(ch.lower() for ch in s if ch.isalnum())
    return t == t[::-1]
```

- 正例：`name.strip().lower()` 先去空白再转小写；用遍历统计元音；规范化后用切片反转判断回文。

### 反例与易错点

```python
text = "abc"
# text[0] = "A"  # TypeError：字符串不可变

s = " hi "
s.strip()
print(s)  # 仍是 " hi "，因为没有接住返回值
```

- 反例：`text[0] = "A"` 失败；调用 `strip()` 却不赋值，原字符串不变。
- 常见错误：索引越界、混淆字符与整数编码、忽略方法返回的新字符串、中英文空白未剔除导致比较失败。

### 练习

- 基础题：统计一句话中元音字母（a/e/i/o/u，大小写不敏感）的数量。
- 答案要点：转小写后逐字符判断是否属于元音集合；计数器放循环外。
- 进阶题：规范化用户输入（去非字母数字、统一小写）并判断是否为回文。
- 进阶答案要点：过滤后比较 `t == t[::-1]`；空串可定义为回文或按题意处理。

### 相关知识点

- 前置知识点：`var`（变量与类型）、`loop`（循环结构）。
- 后续知识点：`list`（列表）、`dict`（字典）、`algo-sum`（求和与统计）。
- 来源：Python 官方教程“Strings”。

## 10. 列表
`document_id: python-stage3-list`

列表 `list` 是可变、有序的元素序列，可容纳混合类型（初学建议保持类型一致）。通过下标访问与赋值，支持切片。常用方法：`append`、`extend`、`insert`、`pop`、`remove`、`sort`、`reverse`；也可用 `len`、`in`、`max`、`min`、`sum`。`append` 原地修改并返回 `None`，不要写成 `xs = xs.append(x)`。复制列表用 `xs.copy()` 或 `xs[:]`，直接 `ys = xs` 只是多个名字指向同一列表。遍历时删除元素应迭代副本或使用列表推导过滤。

- 概念：列表是可变有序容器，支持索引、切片、增删改和遍历。它是组织“一组成绩、一条记录序列”的首选结构，与 `for`/`range` 配合可完成扫描、筛选与聚合。可变性带来灵活，也带来别名共享的风险：函数内修改列表参数会影响调用方。切片赋值与推导式能写出更短的转换代码，但可读性应优先于炫技；复制列表时务必区分浅拷贝与引用赋值。

### 正例代码

```python
scores = [70, 88, 92]
scores.append(90)
print(scores[:3])  # 前三个

print(max(scores), min(scores))


def dedup_keep_order(items):
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result
```

- 正例：`scores.append(90)` 添加元素，`scores[:3]` 取切片；用集合辅助在不改原列表语义下保序去重。

### 反例与易错点

```python
xs = [1, 2, 3, 2]
for x in xs:
    if x == 2:
        xs.remove(x)  # 边遍历边删除，可能跳过元素

ys = xs.append(4)  # ys 为 None，xs 已变长
```

- 反例：遍历列表时直接删除当前元素，可能跳过数据；把 `append` 返回值赋回变量会得到 `None`。
- 常见错误：下标越界、浅拷贝误用、`append` 返回值误用、负数下标与切片边界混淆。

### 练习

- 基础题：找出整数列表中的最大值和最小值（可不用 `max`/`min` 手写一遍以理解遍历）。
- 答案要点：初始化为首元素，其后比较更新；空列表需单独处理。
- 进阶题：在不修改原列表的前提下去重并保持首次出现顺序。
- 进阶答案要点：新建结果列表；用集合记录已出现元素；遍历原列表按需追加。

### 相关知识点

- 前置知识点：`loop`（循环结构）、`range`（range）。
- 后续知识点：`dict`（字典）、`func`（函数）、`algo-search`（线性查找）。
- 来源：Python 官方教程“More on Lists”。

## 11. 字典
`document_id: python-stage3-dict`

字典 `dict` 保存键到值的映射，键必须可哈希（常用 `str`、`int`、`tuple`，不能用列表）。用 `d[key]` 读取或写入，键不存在时读取会 `KeyError`；`d.get(key, default)` 更安全。常用视图：`keys()`、`values()`、`items()`。统计词频、配置项、学号到成绩的映射都适合字典。遍历时不要随意增删键，可先拷贝键列表再改。嵌套字典可表达“学生 → {课程 → 分数}”等结构。

- 概念：字典保存键值映射，键必须可哈希；`get` 可安全读取缺失键。相比列表按位置找，字典按键直接定位，平均查找更快，适合索引与计数。更新计数的惯用写法是 `count[word] = count.get(word, 0) + 1`。理解“键唯一、后写覆盖先写”可避免数据静默丢失。与列表组合时，列表保序扫描，字典做聚合，是数据分析入门的典型模式。

### 正例代码

```python
count = {}
for ch in "banana":
    count[ch] = count.get(ch, 0) + 1
print(count)

student = {
    "name": "Lin",
    "scores": {"math": 90, "english": 86},
}
print(student["scores"]["math"])
```

- 正例：`count[word] = count.get(word, 0) + 1` 累计频次；嵌套字典保存学生多门成绩。

### 反例与易错点

```python
data = {"name": "Lin"}
# print(data["score"])  # KeyError

# 列表不能做键
# bad = {[1, 2]: "x"}  # TypeError

d = {"a": 1, "b": 2}
# for k in d:
#     del d[k]  # RuntimeError：遍历时改变大小
```

- 反例：直接读取不存在的 `data["score"]` 触发 `KeyError`；使用列表作为键会失败。
- 常见错误：使用列表作为键、遍历时改变字典大小、混淆键和值、覆盖已有键未察觉。

### 练习

- 基础题：统计字符串中每个字符出现次数，输出字典。
- 答案要点：空字典起步；`get` 或 `in` 判断后加一；最后 `print` 字典。
- 进阶题：用嵌套字典保存多名学生信息，并按某门成绩排序输出名单。
- 进阶答案要点：外层学号/姓名为键；`sorted(..., key=lambda ...)` 按嵌套分数排序。

### 相关知识点

- 前置知识点：`list`（列表）、`str`（字符串）。
- 后续知识点：`func`（函数）、`algo-sum`（求和与统计）、`file`（文件操作）。
- 来源：Python 官方教程“Dictionaries”。

## 12. 函数
`document_id: python-stage3-function`

函数用 `def` 定义，把一段逻辑命名并复用。参数接收输入，`return` 把结果交还调用方；若无 `return`，则返回 `None`。参数可分为位置参数与默认参数；默认值在定义时绑定，**可变对象（如列表）不宜作默认参数**，否则多次调用会共享同一对象。注意局部变量与全局变量的作用域：函数内赋值默认创建局部名。好的函数单一职责、名称动词化、通过返回值而非全局变量传递结果。先保证正确，再考虑拆分。

- 概念：函数封装可复用逻辑，通过参数接收输入，通过 `return` 返回结果。它降低重复、隔离细节，使主程序呈现“流水线”结构：读取、校验、计算、展示各司其职。调用方依赖返回值而不是函数内部的 `print`，这样结果还能继续参与运算或测试。文档字符串、类型注解（可选）与清晰的参数名共同提升可读性。掌握函数后，文件处理与算法题都能写成可测试的小单元。

### 正例代码

```python
def area(radius):
    """返回圆面积。"""
    return 3.14159 * radius ** 2


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


print(area(2))
print(is_prime(17))
```

- 正例：`def area(radius): return 3.14159 * radius ** 2` 计算并返回；素数判断用 `return` 给出布尔结果。

### 反例与易错点

```python
def bad_area(radius):
    result = 3.14159 * radius ** 2
    print(result)  # 只有打印，没有 return


value = bad_area(2)
print(value)  # None，调用方无法继续计算


def add_item(x, bucket=[]):  # 危险：可变默认参数
    bucket.append(x)
    return bucket
```

- 反例：函数只 `print(result)` 而调用方需要返回值，会得到 `None`；可变默认参数导致多次调用共享列表。
- 常见错误：参数数量不匹配、可变默认参数、局部变量作用域误解、把 `print` 当 `return`。

### 练习

- 基础题：编写函数 `is_prime(n)` 判断一个整数是否为素数，返回布尔值。
- 答案要点：`<2` 非素；试除到平方根；发现整除则 `False`，否则 `True`。
- 进阶题：将成绩分析程序拆为读取、校验、统计和展示四个函数，主程序只负责编排调用。
- 进阶答案要点：各函数有明确输入输出；统计函数返回字典或元组；展示函数只负责打印。

### 相关知识点

- 前置知识点：`var`（变量与类型）、`cond`（条件分支）、`loop`（循环结构）。
- 后续知识点：`file`（文件操作）、`except`（异常处理）、`algo-sum`（求和与统计）。
- 来源：Python 官方教程“Defining Functions”“More on Defining Functions”。
