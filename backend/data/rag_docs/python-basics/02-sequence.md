# 模块二：顺序结构

本模块把“读入—计算—输出”中间的“计算”讲透：算术运算符各自的语义与陷阱、比较与逻辑运算如何组合成表达式、运算优先级与短路求值的规则，以及基础类型之间的相互转换。学完本模块应能把一段中文描述的计算需求准确翻译成 Python 表达式，并预判它可能抛出的异常。

## 1. 算术运算
`document_id: python-seq-arith`

Python 的算术运算符包括加 `+`、减 `-`、乘 `*`、真除 `/`、整除 `//`、取余 `%` 和幂 `**`。其中最容易出错的是三处：第一，`/` 是真除法，**永远返回 float**，`6 / 3` 得到 `2.0` 而不是 `2`，想要整数结果必须用 `//`；第二，负数的整除向负无穷取整，`-7 // 2` 是 `-4` 而不是 `-3`，取余的符号则与除数一致，`-7 % 2` 是 `1`；第三，除数为 0 时 `/`、`//`、`%` 都会抛 `ZeroDivisionError`，必须先判断再除。另外 `**` 是右结合的，`2 ** 3 ** 2` 等于 `2 ** 9`。

- 概念：算术运算符作用于数值对象并产生新的数值对象。`+ - *` 在两个 `int` 之间运算结果仍是 `int`，一旦有一方是 `float` 结果就提升为 `float`；`/` 是唯一无条件返回 `float` 的运算符，`//` 做向下取整除法（floor division），`%` 返回与 `//` 配套的余数，二者恒满足 `a == (a // b) * b + a % b`，这正是负数结果“看起来奇怪”的根源。`**` 表示幂，右结合且优先级高于一元负号，`-2 ** 2` 等于 `-4`。`divmod(a, b)` 一次返回商与余数元组，适合做进制转换或时分秒拆分。取余最常见的用途是判断奇偶（`n % 2 == 0`）与周期性（`i % 3`），整除常用于求“有多少个整份”。任何除法运算前都应确认除数非零，否则程序会因 `ZeroDivisionError` 终止。

### 正例代码

```python
a, b = 7, 2
print(a + b, a - b, a * b)      # 9 5 14
print(a / b)                    # 3.5：真除法结果是 float
print(a // b, a % b)            # 3 1：整除商与余数
print(a ** b)                   # 49：幂运算
print(6 / 3, type(6 / 3))       # 2.0 <class 'float'>

print(-7 // 2)                  # -4：向负无穷取整
print(-7 % 2)                   # 1：余数符号随除数
print(divmod(-7, 2))            # (-4, 1)：商与余数一次取得

total_seconds = 3725
print(total_seconds // 3600, total_seconds % 3600 // 60)  # 1 2
```

- 正例：`print(a / b)` 与 `print(a // b, a % b)` 对比出真除与整除的差别，`print(6 / 3, type(6 / 3))` 直接证明 `/` 返回 `float`；`print(-7 // 2)` 与 `print(-7 % 2)` 展示负数取整方向；最后一行用 `total_seconds // 3600` 和 `total_seconds % 3600 // 60` 把秒数拆成小时与分钟，是整除与取余的典型配合。

### 反例与易错点

```python
n = 10
print(n / 0)          # ZeroDivisionError: division by zero
# print(n // 0)       # ZeroDivisionError: integer division or modulo by zero
# print(n % 0)        # ZeroDivisionError: integer division or modulo by zero

print(7 / 2)          # 3.5，想要整数商应写 7 // 2
print(-7 // 2)        # -4，不是 -3
print(2 ** 3 ** 2)    # 512，** 右结合，不等于 (2 ** 3) ** 2 == 64
print(-2 ** 2)        # -4，** 优先于一元负号，需要 (-2) ** 2 才得 4
```

- 反例：`n / 0` 抛 `ZeroDivisionError`，正确做法是先判断 `if b != 0:` 再做除法；把 `/` 当整除会得到带 `.0` 的浮点数，应改用 `//`；`2 ** 3 ** 2` 与 `-2 ** 2` 说明幂运算的结合性与优先级，需要别的顺序就必须加括号。
- 常见错误：混淆 `/` 与 `//`、忽略除数为 0 的判断、误判负数整除与取余的方向、忘记 `**` 是右结合且优先于一元负号。

### 练习

- 基础题：输入一个正整数秒数，输出它对应的“x 小时 y 分 z 秒”。
- 答案要点：小时 `s // 3600`，分钟 `s % 3600 // 60`，秒 `s % 60`；全程用整除与取余，不要用 `/`，否则会出现 `.0`。
- 进阶题：输入被除数与除数（均为整数），输出商与余数，并在除数为 0 时提示“除数不能为 0”。
- 进阶答案要点：先用 `if b == 0:` 拦截非法除数再计算，或用 `divmod(a, b)` 一次得到结果；注意负数时 `divmod` 的商向负无穷取整，余数符号与除数一致。

### 相关知识点

- 前置知识点：`lang-var`（变量与类型）、`lang-input`（输入 input）。
- 后续知识点：`seq-expr`（表达式与优先级）、`seq-type`（数据类型与转换）。
- 来源：Python 官方教程“Using Python as a Calculator”，Python 语言参考“Binary arithmetic operations”。

## 2. 表达式与优先级
`document_id: python-seq-expr`

表达式是能求出一个值的代码片段。比较运算符 `== != > >= < <=` 产生布尔值，逻辑运算符 `and`、`or`、`not` 把布尔值组合起来，构成后续分支与循环的条件。三条规则必须牢记：其一，优先级从高到低大致是「算术 → 比较 → `not` → `and` → `or`」，所以 `1 + 2 > 2 and True` 的求值顺序符合直觉，而 `a or b and c` 会先算 `b and c`；其二，Python 支持链式比较，`60 <= score <= 100` 合法且只对 `score` 求值一次；其三，`and` / `or` 是短路运算，左侧已能定胜负时右侧根本不执行，这既能提速，也能用来避免除零。凡是拿不准优先级的地方，都应该直接加括号。

- 概念：比较运算返回 `True` / `False`，可用于任意可比较对象；`==` 比较值，不要与赋值 `=` 混淆。逻辑运算符中 `not` 优先级最高、`and` 次之、`or` 最低，因此 `not a == b` 等价于 `not (a == b)`，`x or y and z` 等价于 `x or (y and z)`。链式比较 `a < b < c` 在语义上等价于 `a < b and b < c`，但中间的 `b` 只求值一次。短路求值意味着 `and` 遇到假值立即返回该值、`or` 遇到真值立即返回该值，返回的其实是操作数本身而不一定是布尔类型，所以 `"" or "默认值"` 得到 `"默认值"`，这是设置默认值的惯用法。真值判断遵循“空即为假”：`0`、`0.0`、`""`、空列表、`None` 为假，其余为真。写复杂条件时优先用括号表达意图，可读性比省几个字符重要得多。

### 正例代码

```python
score, age = 85, 20
print(score >= 60)                  # True：比较运算返回布尔值
print(score > 90 or age >= 18)      # True：or 只需一侧成立
print(not score == 100)             # True：not 作用于比较结果

print(60 <= score <= 100)           # True：链式比较，score 只求值一次

print(2 + 3 * 4)                    # 14：* 优先于 +
print((2 + 3) * 4)                  # 20：括号改变求值顺序
print(1 + 2 > 2 and 3 % 2 == 1)     # True：算术 → 比较 → 逻辑

n = 0
print(n != 0 and 10 / n > 1)        # False：短路，右侧不求值，不会除零
print("" or "默认值")                # 默认值：or 返回第一个为真的操作数
```

- 正例：`print(60 <= score <= 100)` 展示链式比较优于手写两个条件；`print((2 + 3) * 4)` 与上一行对比说明括号的作用；`print(n != 0 and 10 / n > 1)` 是短路求值的经典用法——左侧为假时右侧的除法根本不执行，从而避开 `ZeroDivisionError`；`print("" or "默认值")` 演示 `or` 返回操作数本身的惯用写法。

### 反例与易错点

```python
score = 85
# print(60 < score and < 100)     # SyntaxError：and 右侧必须是完整表达式
# if score = 60:                  # SyntaxError：比较应使用 ==，不是 =

print(True or False and False)     # True：and 先算，等价于 True or (False and False)
print((True or False) and False)   # False：加括号才是“先 or 再 and”

print(0 == False, 1 == True)       # True True：bool 是 int 的子类，容易误判
print(bool("False"))               # True：非空字符串恒为真，别用它判断用户输入
```

- 反例：`60 < score and < 100` 缺少左操作数抛 `SyntaxError`，应写 `60 < score < 100` 或 `60 < score and score < 100`；把 `=` 当比较号同样是 `SyntaxError`，条件里必须用 `==`；`True or False and False` 因为 `and` 优先级更高而返回 `True`，要“先 or”就必须写成 `(True or False) and False`。
- 常见错误：混淆 `=` 与 `==`、误以为 `or` 优先于 `and` 而漏写括号、忘记 `bool("False")` 为真、以为 `and`/`or` 一定返回 `True`/`False` 而非操作数本身。

### 练习

- 基础题：输入一个整数，用一个表达式判断它是否为「大于 0 且为偶数」，直接输出布尔结果。
- 答案要点：写成 `n > 0 and n % 2 == 0`；注意 `%` 优先级高于 `==`，无需额外括号，但加上括号更清晰。
- 进阶题：输入成绩与出勤率，输出是否满足“成绩不低于 60 且出勤率不低于 0.8，或成绩达到 90 分以上”这一条件。
- 进阶答案要点：翻译为 `(score >= 60 and rate >= 0.8) or score >= 90`，括号必须显式写出，否则 `and` 先结合会改变语义；出勤率用 `float(input(...))` 读入。

### 相关知识点

- 前置知识点：`seq-arith`（算术运算）、`lang-var`（变量与类型）。
- 后续知识点：`seq-type`（数据类型与转换）、`branch-if`（if 单分支）。
- 来源：Python 官方教程“More Control Flow Tools”，Python 语言参考“Operator precedence”。

## 3. 数据类型与转换
`document_id: python-seq-type`

类型转换是把一个对象“换一种类型重新表示”。显式转换用内置函数 `int()`、`float()`、`str()`、`bool()`，它们都返回新对象而不修改原对象；隐式转换只发生在数值混算时，比如 `1 + 2.5` 会先把 `1` 提升为 `float`。两个高频考点必须分清：`int(3.9)` 是**向零截断**得到 `3`，`int(-3.9)` 得到 `-3`；而 `round(3.9)` 是四舍五入得到 `4`，且 `round` 采用“银行家舍入”，`round(2.5)` 是 `2` 不是 `3`。另一个坑是字符串转数字：`int("abc")`、`int("3.5")`、`int("")` 都会抛 `ValueError`，要转小数字符串必须先 `float()` 再 `int()`。

- 概念：`int(x)` 接受整数形式的字符串或数值，对浮点数向零截断；`float(x)` 接受数字形式的字符串或数值；`str(x)` 把任意对象转成可读文本，是拼接输出前的必要步骤；`bool(x)` 遵循真值规则——`0`、`0.0`、`""`、空容器、`None` 为假，其余为真，注意 `bool("0")` 和 `bool("False")` 都是 `True`。`round(x)` 不带第二参数时返回 `int`，带第二参数 `round(x, n)` 返回保留 n 位小数的 `float`，其规则是四舍六入五取偶，与数学习惯略有差别，涉及金额时应使用 `decimal` 模块。隐式转换只在 `int` 与 `float`（以及 `bool` 参与算术，按 1/0 计算）之间发生，`str` 与数值之间**绝不会**自动转换，所以 `"分数：" + 90` 抛 `TypeError`，必须写 `"分数：" + str(90)` 或用 f-string。凡是来自 `input()`、文件、网络的文本，都应视为不可信数据并用 `try/except ValueError` 保护转换。

### 正例代码

```python
print(int("42"), float("3.14"))        # 42 3.14
print(str(42) + "分")                   # 42分：拼接前先转 str

print(int(3.9), int(-3.9))             # 3 -3：向零截断
print(round(3.9), round(-3.9))         # 4 -4：四舍五入到整数
print(round(2.5), round(3.5))          # 2 4：银行家舍入，取偶数
print(round(3.14159, 2))               # 3.14：保留两位小数，仍是 float

print(bool(0), bool(""), bool([]))     # False False False
print(bool(-1), bool("0"))             # True True：非空字符串一律为真
print(1 + True, 2.5 + 1)               # 2 3.5：bool 按 1/0 算，int 自动提升
print(int(float("3.5")))               # 3：小数字符串要两步转换
```

- 正例：`print(int(3.9), int(-3.9))` 与 `print(round(3.9), round(-3.9))` 并列，直观区分截断与四舍五入；`print(round(2.5), round(3.5))` 暴露银行家舍入；`print(str(42) + "分")` 说明拼接必须先转 `str`；`print(int(float("3.5")))` 给出小数字符串转整数的正确两步写法。

### 反例与易错点

```python
age = int("18岁")           # ValueError: invalid literal for int() with base 10: '18岁'
# print(int("3.5"))         # ValueError：int() 不接受小数形式的字符串
# print(int(""))            # ValueError：空字符串无法转换

print("分数：" + 90)         # TypeError：str 与 int 不能相加
print(str(3.14) * 2)        # 3.143.14：字符串重复，不是数值翻倍
print(int(2.99))            # 2：想四舍五入应用 round(2.99)
print(bool("False"))        # True：非空字符串恒为真，不能这样解析用户输入
```

- 反例：`int("18岁")` 抛 `ValueError`，应先清洗文本或用 `try/except ValueError` 兜底；`"分数：" + 90` 抛 `TypeError`，正确写法是 `"分数：" + str(90)` 或 `f"分数：{90}"`；`int(2.99)` 得到 `2` 而非 `3`，需要四舍五入必须改用 `round(2.99)`。
- 常见错误：用 `int()` 解析小数字符串、把 `int()` 截断当成四舍五入、字符串与数字直接相加、误以为 `bool("False")` 或 `bool("0")` 为假。

### 练习

- 基础题：输入一个小数形式的字符串（如 `3.7`），输出它截断后的整数与四舍五入后的整数。
- 答案要点：先 `x = float(input(...))`，截断用 `int(x)`，四舍五入用 `round(x)`；不能直接 `int("3.7")`，那会抛 `ValueError`。
- 进阶题：输入商品单价与数量，输出总价并保留两位小数；任一输入非法时提示“输入格式错误”且程序不崩溃。
- 进阶答案要点：`float(input(...))` 与 `int(input(...))` 一起放进 `try` 块，用 `except ValueError` 捕获；总价输出用 `f"{total:.2f}"` 而不是 `round` 后直接打印，以保证固定两位小数。

### 相关知识点

- 前置知识点：`seq-arith`（算术运算）、`seq-expr`（表达式与优先级）。
- 后续知识点：`branch-if`（if 单分支）、`string-method`（字符串常用方法）。
- 来源：Python 官方教程“Fancier Output Formatting”，Python 标准库“Built-in Functions”。
