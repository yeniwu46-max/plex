# 模块一：语言入门

本模块建立 Python 程序最基本的读写习惯：如何用 `print` 把结果告诉使用者、如何用注释向阅读代码的人说明意图、如何用变量保存数据并理解它的类型，以及如何用 `input` 读入用户输入。学完本模块应能独立写出“读入—计算—输出”的短脚本，并看懂解释器抛出的常见错误提示。

## 1. print 输出与注释
`document_id: python-lang-print`

程序的第一件事是“把话说出来”。`print()` 负责把对象写到标准输出，默认多个参数之间用空格分隔、末尾自动换行，可用 `sep` 与 `end` 改变这两个行为；f-string（形如 `f"你好 {name}"`）能把变量与表达式直接嵌进字符串，可读性远好于反复拼接。注释则是写给人看的：`#` 之后到行末被解释器忽略，函数或模块开头的三引号字符串是文档字符串（docstring），可用 `help()` 查看。同时要记住 Python 自上而下顺序执行，代码块靠**缩进**界定而非花括号，官方风格是每层四个空格。初学者最常卡在两处：把中文全角标点写进代码，以及在不需要代码块的地方随意缩进。

- 概念：`print()` 是内置输出函数，它先把每个参数转成字符串，再用 `sep`（默认一个空格）连接、用 `end`（默认换行符 `\n`）收尾，因此 `print("a", "b")` 与 `print("a", "b", sep="")` 输出不同。f-string 在字符串前加 `f`，花括号内可写变量、算式甚至函数调用，格式说明符如 `{x:.2f}` 控制小数位。注释不参与运算：`#` 用于解释单行意图，docstring 用于说明模块、函数的用途与参数，二者都不能替代版本控制去“保存废弃代码”。缩进是语法的一部分，同一逻辑块必须严格对齐，且不要混用 Tab 与空格，否则会触发 `IndentationError` 或 `TabError`。这三件事共同决定了代码能否被机器执行、能否被同伴读懂。

### 正例代码

```python
def describe_student():
    """输出一名学员的基本信息。

    无参数；仅用于演示 print 的常用写法。
    """
    name = "PLEX"
    major = "软件工程"
    print(name, major)                  # 默认空格分隔、末尾换行
    print(name, major, sep=" | ")       # sep 改变分隔符
    print("加载中", end="...")           # end 取消换行
    print("完成")                        # 紧接上一行输出
    print(f"{name} 就读于 {major}")      # f-string 嵌入变量
    print(f"课时 {45 / 2:.1f} 小时")     # 花括号内可写表达式与格式


if __name__ == "__main__":
    describe_student()
```

- 正例：`print(name, major, sep=" | ")` 用 `sep` 自定义分隔符，`print("加载中", end="...")` 用 `end` 让下一次输出接在同一行；`print(f"课时 {45 / 2:.1f} 小时")` 说明 f-string 花括号内既能算式也能带格式说明符；函数开头的三引号字符串是 docstring，而非被注释掉的代码。

### 反例与易错点

```python
# 错误：用三引号“注释掉”一段代码，实际创建了未被使用的字符串对象
"""
print("旧逻辑")
"""

Print("hello")            # NameError: name 'Print' is not defined（区分大小写）
print("world"）           # SyntaxError：使用了全角括号
print("a" "b", sep="-")   # 输出 ab，相邻字面量已先拼接，sep 不起作用
print("world")
    print("oops")         # IndentationError: unexpected indent
```

- 反例：`Print("hello")` 因大小写不符抛 `NameError`，正确写法是 `print`；把全角括号或冒号写进代码会抛 `SyntaxError`；在没有 `if`/`for`/`def` 的地方缩进 `print("oops")` 会抛 `IndentationError`，删掉多余空格即可。
- 常见错误：中英文标点混用、把三引号当成批量注释、忘记 f-string 前缀 `f` 导致花括号原样输出、缩进层级不一致或 Tab 与空格混用。

### 练习

- 基础题：用一条 `print` 语句输出“姓名 | 专业”这样以竖线分隔的一行信息，并为该行加一句说明用途的注释。
- 答案要点：`print(name, major, sep=" | ")` 或 `print(f"{name} | {major}")`；注释用 `#` 写在行尾或上一行，说明“为什么”而非逐字翻译语法。
- 进阶题：写一个函数输出三行进度提示，要求第一行不换行（后面接“完成”），并为函数补一段包含用途说明的 docstring。
- 进阶答案要点：用 `end=""` 或 `end="..."` 抑制换行；docstring 放在函数体首行；入口逻辑写在 `if __name__ == "__main__":` 之下，保证被导入时不自动执行。

### 相关知识点

- 前置知识点：无（本课起点）。
- 后续知识点：`lang-var`（变量与类型）、`lang-input`（输入 input）。
- 来源：Python 官方教程“An Informal Introduction to Python”“Input and Output”，PEP 257。

## 2. 变量与类型
`document_id: python-lang-var`

变量是对象的名字。赋值语句 `age = 18` 并不是“把 18 装进盒子”，而是把名字 `age` 绑定到整数对象 18 上，因此不需要事先声明类型，同一个名字先后绑定不同类型的对象也完全合法。初学阶段需要熟练掌握四种基础类型：整数 `int`、浮点数 `float`、字符串 `str`、布尔值 `bool`，并用 `type(x)` 随时确认某个名字当前指向什么。类型决定了可执行的运算：`"90" + 10` 会抛 `TypeError`，必须先 `int("90")`。命名要有意义、用小写加下划线，且不要覆盖 `list`、`str`、`sum` 等内置名。最容易踩的坑是浮点判等——`0.1 + 0.2 == 0.3` 为 `False`。

- 概念：Python 中“名字”与“对象”是分离的，赋值即绑定，变量本身没有固定类型，类型属于它所指向的对象。`int` 表示任意大的整数，`float` 是双精度浮点数，`str` 是不可变的文本序列，`bool` 只有 `True` 与 `False` 两个值且是 `int` 的子类（`True == 1`）。`type(x)` 返回对象的类型，调试时非常有用。命名规范遵循 PEP 8：小写字母加下划线（`total_score`），标识符不能以数字开头、不能使用关键字，也应避免遮蔽内置名，否则后续无法再调用同名内置函数。由于浮点数以二进制存储，`0.1`、`0.2` 都不能被精确表示，比较两个浮点计算结果时应判断差值是否小于某一阈值，而不是直接用 `==`。这一节是所有后续运算与转换的基础。

### 正例代码

```python
age = 18            # int：整数
height = 1.72       # float：浮点数
passed = True       # bool：只有 True / False
label = "学员"       # str：文本

print(type(age), type(height))      # <class 'int'> <class 'float'>
print(type(passed), type(label))    # <class 'bool'> <class 'str'>

score_text = "90"
score = int(score_text)             # 需要运算前先显式转换
print(score + 10)                   # 100

total = 0.1 + 0.2
print(total == 0.3)                 # False：浮点存在精度误差
print(abs(total - 0.3) < 1e-9)      # True：用差值阈值判断
```

- 正例：`age = 18`、`height = 1.72`、`passed = True`、`label = "学员"` 依次绑定四种基础类型，并用 `type()` 打印确认；`score = int(score_text)` 说明字符串参与算术前必须显式转换；判等改用 `abs(total - 0.3) < 1e-9` 规避浮点误差。

### 反例与易错点

```python
score = "90"
print(score + 10)          # TypeError: can only concatenate str (not "int") to str

list = [1, 2, 3]           # 危险：覆盖内置名 list
# print(list(range(3)))    # TypeError: 'list' object is not callable

# 2nd_score = 95           # SyntaxError：标识符不能以数字开头

print(0.1 + 0.2 == 0.3)    # False：不要对浮点结果直接判等
print(total_score)         # NameError：使用了尚未赋值的名字
```

- 反例：`score = "90"` 后 `score + 10` 抛 `TypeError`，应写成 `int(score) + 10`；把 `list` 当变量名会遮蔽内置类型，之后 `list(range(3))` 抛 `TypeError`；引用未赋值的名字抛 `NameError`，要先赋值再使用。
- 常见错误：忘记把字符串转成数值、覆盖内置名（`list`/`str`/`sum`）、把赋值 `=` 当作相等比较 `==`、对浮点结果直接用 `==` 判等。

### 练习

- 基础题：定义姓名、年龄、身高三个变量并分别用 `type()` 输出它们的类型。
- 答案要点：姓名用带引号的 `str`，年龄用整数字面量，身高用带小数点的 `float`；`print(type(x))` 逐个输出，注意变量名不要与内置名冲突。
- 进阶题：给定两个通过计算得到的浮点数，判断它们在允许误差 1e-9 内是否相等，并输出结论。
- 进阶答案要点：不要写 `a == b`，改用 `abs(a - b) < 1e-9`；理解误差来自二进制表示，必要时可改用 `round(a, 9) == round(b, 9)` 或标准库 `math.isclose`。

### 相关知识点

- 前置知识点：`lang-print`（print 输出与注释）。
- 后续知识点：`lang-input`（输入 input）、`seq-type`（数据类型与转换）。
- 来源：Python 官方教程“Using Python as a Calculator”，PEP 8。

## 3. 输入 input
`document_id: python-lang-input`

`input(prompt)` 从标准输入读取一行，把可选的 `prompt` 原样显示在同一行作为提示，然后**永远返回字符串**——即使用户输入的是 `18`，拿到的也是 `"18"` 而不是整数。这条规则是初学者最高频的错误来源：`input("年龄：") + 1` 会抛 `TypeError`，必须写成 `int(input("年龄："))`；需要小数则用 `float(...)`。更进一步，用户可能输入“十八”或空行，此时 `int()` 会抛 `ValueError`，健壮的程序应把转换语句放进 `try/except ValueError`，给出友好提示而不是直接崩溃。把提示语交给 `input` 的参数，而不是先 `print` 再裸调 `input()`，光标才会停在提示语后面。

- 概念：`input()` 会去掉行尾换行符并返回 `str` 类型，返回值的类型与用户键入的内容无关，因此“读入即转换”应成为固定习惯：整数用 `int()`，小数用 `float()`，文本则保持原样。`prompt` 参数只负责显示，不会自动加冒号或空格，需要自己写全。当字符串不能被解析成目标数值时，`int()` / `float()` 抛 `ValueError`（注意 `int("3.5")` 也会失败，需先 `float` 再 `int`）；用 `try/except ValueError` 包住转换语句即可捕获，并在 `except` 分支里提示重输或设默认值。若程序需要反复索取合法输入，可把 `try/except` 放进循环，这属于后续循环模块的内容。输入校验是“读入—计算—输出”模式的第一道关口，直接决定程序面对真实用户时是否可用。

### 正例代码

```python
raw = input("请输入年龄：")            # 无论输入什么，raw 都是 str
print(type(raw))                      # <class 'str'>

age = int(raw)                        # 显式转换后才能参与算术
print(f"明年 {age + 1} 岁")

height = float(input("请输入身高（米）："))
print(f"身高约 {height:.2f} 米")

try:
    score = int(input("请输入成绩："))  # 非法输入会抛 ValueError
except ValueError:
    print("输入不是整数，已按 0 分处理")
    score = 0
print(f"最终成绩：{score}")
```

- 正例：`raw = input("请输入年龄：")` 后先用 `print(type(raw))` 确认返回的是 `str`，再用 `age = int(raw)` 显式转换；提示语直接作为 `input` 的参数传入；`try: score = int(input(...)) except ValueError:` 把转换包起来，非法输入时回退到默认值而不崩溃。

### 反例与易错点

```python
age = input("请输入年龄：")
print(age + 1)              # TypeError: can only concatenate str (not "int") to str

count = int(input("数量："))  # 用户输入 "3.5" 时 ValueError: invalid literal for int()

# 错误：提示语单独 print，光标跑到下一行，用户不知道该在哪里输入
print("请输入姓名：")
name = input()

value = int(input("整数："))   # 没有 try/except，非法输入直接终止程序
```

- 反例：`age + 1` 把 `str` 与 `int` 相加抛 `TypeError`，正确写法是 `int(age) + 1`；`int(input())` 遇到 `"3.5"` 抛 `ValueError`，需要小数就改用 `float()`，或先 `float()` 再 `int()` 截断；缺少 `try/except ValueError` 时任何非法输入都会让程序中断。
- 常见错误：忘记 `int()`/`float()` 转换、用 `int()` 去解析小数字符串、把提示语写成单独的 `print` 导致光标换行、不做异常捕获导致用户输错就崩溃。

### 练习

- 基础题：输入圆的半径，输出保留两位小数的面积（π 取 3.14159）。
- 答案要点：`radius = float(input("半径："))`，面积 `3.14159 * radius ** 2`，输出用 `print(f"{area:.2f}")`；切记不能对 `input()` 的返回值直接做乘方。
- 进阶题：输入两个整数并输出它们的和，要求任意一个输入非法时提示“请输入整数”且程序不崩溃。
- 进阶答案要点：把两次 `int(input(...))` 一起放进同一个 `try` 块，用 `except ValueError` 捕获并打印提示；如需重试，可把 `try/except` 放入 `while True` 循环，成功后 `break`。

### 相关知识点

- 前置知识点：`lang-var`（变量与类型）、`lang-print`（print 输出与注释）。
- 后续知识点：`seq-arith`（算术运算）、`seq-type`（数据类型与转换）。
- 来源：Python 官方教程“Input and Output”“Errors and Exceptions”。
