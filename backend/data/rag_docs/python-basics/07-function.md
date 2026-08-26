# 模块七：函数与递归

本模块把散落的语句收拢成函数：先用 `def` 定义并调用，再掌握参数传递与返回值，最后进入“函数调用自己”的递归思路。学完后应能把一段长脚本重构为若干职责单一、可复用、可单独验证的函数。

## 1. 定义与调用
`document_id: python-func-define`

函数是给一段逻辑起名字并打包起来，之后随处可用。定义形式为 `def 函数名(参数列表):`，冒号后换行、缩进四个空格的部分才是函数体；调用形式为 `函数名(实参)`，括号不能省略。解释器读到 `def` 时只是“登记”这个名字，并不执行函数体，所以必须先定义后调用。函数体第一行可写三引号文档字符串（docstring），说明这个函数做什么。初学者最容易卡在三处：把调用写在定义之前、函数体忘记缩进、以及漏写括号导致只是引用了函数对象而没有真正执行。

- 概念：`def` 语句创建一个函数对象并绑定到函数名上，此时函数体一行都不会执行；只有写出 `函数名(...)` 这样的调用表达式，解释器才跳进函数体逐行运行，运行完再回到调用处继续。函数体依靠缩进界定，同一函数体内缩进必须一致，否则触发 `IndentationError`。函数名遵循变量命名规则，推荐小写加下划线，且不要覆盖 `print`、`sum` 等内置名。docstring 紧跟在 `def` 行之后，用来写清用途、参数与返回值，可用 `help(函数名)` 查看。把重复出现的代码收进函数，就能做到一处修改、处处生效，这是摆脱复制粘贴式代码、进而学习参数与递归的前提。

### 正例代码

```python
def greet(name):
    """打印一句问候语。

    参数:
        name: 学员姓名，字符串。
    """
    print(f"你好，{name}！")


def area_of_circle(radius):
    """返回半径为 radius 的圆面积（π 取 3.14159）。"""
    return 3.14159 * radius ** 2


if __name__ == "__main__":
    greet("PLEX")                       # 你好，PLEX！
    print(f"{area_of_circle(2):.2f}")   # 12.57
```

- 正例：两个函数都先用 `def` 定义、再在入口处调用，例如 `greet("PLEX")` 与 `area_of_circle(2)`；`area_of_circle` 的 docstring 写在 `def` 行的下一行，函数体统一缩进四个空格。

### 反例与易错点

```python
# 错误一：先调用后定义，NameError: name 'greet' is not defined
greet("PLEX")


def greet(name):
    print(f"你好，{name}！")


# 错误二：函数体没有缩进，IndentationError: expected an indented block
# def show():
# print("hi")

# 错误三：漏写括号，只是引用了函数对象，并没有执行
print(greet)  # <function greet at 0x...>
```

- 反例：把 `greet("PLEX")` 写在 `def greet` 之前时名字还没绑定，抛 `NameError`，应把调用移到定义之后或放进 `if __name__ == "__main__":`；`print(greet)` 打印的是函数对象，想执行必须写成 `greet("PLEX")`。
- 常见错误：先调用后定义、函数体忘记缩进或缩进不一致、调用时漏写括号、函数名覆盖内置名、`def` 行末尾漏写英文冒号。

### 练习

- 基础题：定义函数 `greet(name)`，打印“你好，某某！”，并在文件末尾调用两次传入不同姓名。
- 答案要点：`def greet(name):` 后缩进写 `print(f"你好，{name}！")`；调用语句必须在定义之后；两次调用传入不同实参。
- 进阶题：把“输入半径、计算圆面积、格式化输出”拆成 `read_radius()` 与 `area_of_circle(radius)` 两个函数，主流程只负责串起来，并为每个函数补写 docstring。
- 进阶答案要点：读入函数里用 `float(input(...))`；计算函数只做算术、不打印；主流程在 `if __name__ == "__main__":` 下调用，用 `{value:.2f}` 控制小数位。

### 相关知识点

- 前置知识点：`lang-var`（变量与类型）、`lang-print`（输出）、`branch-if`（条件分支）。
- 后续知识点：`func-param`（参数与返回值）、`func-recursion`（递归）。
- 来源：Python 官方教程“Defining Functions”，PEP 257（Docstring Conventions）。

## 2. 参数与返回值
`document_id: python-func-param`

参数是函数的输入口，返回值是它的输出口。调用时按位置一一对应的是位置参数；在 `def` 行写成 `score=60` 的是默认参数，调用时可省略；调用时写成 `prefix="同学"` 的是关键字参数，可以不管顺序。`return` 把结果交回调用处并立即结束函数；函数体没有 `return`（或只写 `return`）时返回 `None`。函数内部赋值的变量是局部变量，函数结束就消失。初学者最容易踩的两个坑是：把只负责 `print` 的函数当成有返回值来用，以及用列表当默认参数导致多次调用互相污染。

- 概念：形参是函数定义中的名字，实参是调用时传入的值；传参本质是把实参对象绑定到形参名上。默认参数必须排在无默认参数之后，且它的值在 `def` 执行时只计算一次，因此可变对象（列表、字典）作默认值会在多次调用间被共享，标准写法是默认给 `None`、进函数后再新建。关键字参数按名字匹配，可提升可读性并允许乱序。`return` 既传值又终止函数，可返回元组实现“多返回值”；没有 `return` 时结果是 `None`，对它做算术会抛 `TypeError`。函数内赋值的名字默认是局部的，想读外层变量就不要在函数里对它赋值，否则触发 `UnboundLocalError`。

### 正例代码

```python
def make_label(name, score=60, prefix="学员"):
    """拼接一行成绩标签；score 与 prefix 都是默认参数。"""
    return f"{prefix}{name}：{score} 分"


def append_score(score, scores=None):
    """把 score 追加进 scores；默认值用 None 而不是 []。"""
    if scores is None:
        scores = []
    scores.append(score)
    return scores


print(make_label("PLEX"))                  # 学员PLEX：60 分
print(make_label("PLEX", 95))              # 位置参数 → 学员PLEX：95 分
print(make_label("PLEX", prefix="同学"))    # 关键字参数 → 同学PLEX：60 分
print(make_label(score=88, name="ANN"))    # 全用关键字，顺序可换
print(append_score(90), append_score(80))  # [90] [80]，两次互不影响
```

- 正例：`make_label` 的 `score=60`、`prefix="学员"` 是默认参数，调用时可省略也可用 `prefix="同学"` 按名字覆盖；`append_score(score, scores=None)` 进入函数后再 `scores = []`，因此 `append_score(90)` 与 `append_score(80)` 各自得到独立列表。

### 反例与易错点

```python
def add_score(score, scores=[]):  # 危险：默认列表只在定义时创建一次
    scores.append(score)
    return scores


print(add_score(90))  # [90]
print(add_score(80))  # [90, 80]：上一次调用的数据被带了过来


def show(value):
    print(value)      # 只打印，没有 return

result = show(5)
print(result + 1)     # TypeError: 'NoneType' 与 'int' 不能相加
```

- 反例：`scores=[]` 这个列表在函数定义时创建、被所有调用共享，第二次调用就出现脏数据，正确写法是默认 `None` 再在函数内新建；`show` 没有 `return`，`result` 是 `None`，`result + 1` 抛 `TypeError`，需要结果就必须 `return`。
- 常见错误：可变对象作默认参数、把只 `print` 的函数当作有返回值使用、默认参数写在必填参数前面导致 `SyntaxError`、实参个数与形参不匹配、在函数内给外层变量赋值触发 `UnboundLocalError`。

### 练习

- 基础题：编写 `average(numbers)` 返回列表平均值，空列表时返回 `None` 而不是报错。
- 答案要点：先用 `if not numbers: return None` 挡住空表；再 `return sum(numbers) / len(numbers)`；调用处判断结果是否为 `None`。
- 进阶题：编写 `make_report(name, scores, passline=60)`，返回 `(总分, 平均分, 是否及格)` 三元组，并演示用关键字参数调整 `passline`。
- 进阶答案要点：`return total, avg, avg >= passline` 自动打包成元组；调用处用 `total, avg, ok = make_report(...)` 解包；`make_report("ANN", data, passline=70)` 覆盖默认值。

### 相关知识点

- 前置知识点：`func-define`（定义与调用）、`array-basic`（列表基础）、`seq-expr`（表达式）。
- 后续知识点：`func-recursion`（递归）、`search-stat`（统计与去重）。
- 来源：Python 官方教程“More on Defining Functions”（Default Argument Values、Keyword Arguments），PEP 8。

## 3. 递归
`document_id: python-func-recursion`

递归是函数在自己的函数体里再次调用自己，把大问题拆成同类型的小问题。写递归只需想清两件事：出口条件（base case）——规模小到什么程度可以直接给出答案；递推关系——如何用更小规模的同一函数拼出当前答案，并且保证每次调用规模都在缩小、最终撞上出口。阶乘 `n! = n × (n-1)!` 与斐波那契 `F(n) = F(n-1) + F(n-2)` 是两个标准例子。初学者最常见的两个坑是：忘记出口或规模不减小，导致 `RecursionError`；以及朴素斐波那契重复计算，`n` 稍大就慢得离谱。

- 概念：每次函数调用都会在调用栈上压入一层，保存各自的局部变量；返回时逐层弹出，所以递归的结果是“先层层深入到出口，再层层往回相乘或相加”。合法的递归必须同时具备出口条件和向出口收敛的递推，缺一个就会无限递归，Python 达到默认约 1000 层的递归上限时抛 `RecursionError`（上限可用 `sys.setrecursionlimit` 调整，但通常说明该改写成循环）。递归与循环表达能力等价：线性递归（如阶乘）改写成 `for` 循环更省栈；分叉递归（如斐波那契、树形结构）用递归更贴近问题本身，但要用字典缓存已算过的结果，把指数级的重复计算降回线性。

### 正例代码

```python
def factorial(n):
    if n <= 1:            # 出口条件：0! 和 1! 都等于 1
        return 1
    return n * factorial(n - 1)   # 规模每次减 1，必然收敛到出口


def fib(n, cache=None):
    """返回第 n 项斐波那契数，用字典缓存避免重复计算。"""
    if cache is None:
        cache = {}
    if n < 2:             # 出口条件：F(0)=0, F(1)=1
        return n
    if n in cache:
        return cache[n]
    cache[n] = fib(n - 1, cache) + fib(n - 2, cache)
    return cache[n]


print(factorial(5), fib(30))   # 120 832040
```

- 正例：`factorial` 用 `if n <= 1: return 1` 作出口，递推式 `return n * factorial(n - 1)` 让实参每层减 1；`fib` 在递推前先查 `if n in cache`，把同一个 `cache` 字典一路传下去，因此 `fib(30)` 瞬间得到 832040。

### 反例与易错点

```python
def countdown(n):
    print(n)
    countdown(n - 1)   # 缺出口条件，RecursionError: maximum recursion depth exceeded


def bad_factorial(n):
    if n == 0:
        return 1
    return n * bad_factorial(n)  # 实参没变小，同样无限递归


def slow_fib(n):
    if n < 2:
        return n
    return slow_fib(n - 1) + slow_fib(n - 2)  # 结果正确但重复计算，n=40 就明显卡顿
```

- 反例：`countdown` 没有出口条件，`bad_factorial` 传的还是 `n` 而不是 `n - 1`，两者都会一直压栈直到 `RecursionError`；`slow_fib` 逻辑正确但同一个 `n` 被反复计算，复杂度约 `O(2**n)`，必须加缓存或改写成循环。
- 常见错误：忘写出口条件、递归调用时规模没有减小、递归分支里忘记 `return` 导致结果变成 `None`、把一个用循环就能解决的线性问题写成深递归、朴素斐波那契不加缓存。

### 练习

- 基础题：用递归实现 `factorial(n)` 计算非负整数 `n` 的阶乘，并验证 `factorial(0)` 等于 1。
- 答案要点：出口写 `if n <= 1: return 1`；递推写 `return n * factorial(n - 1)`；负数输入应提前判断并提示或返回 `None`。
- 进阶题：分别用朴素递归和带字典缓存的递归实现斐波那契，比较 `n = 30` 时两者的耗时，并再写一个 `for` 循环版本。
- 进阶答案要点：缓存版先查表再计算、算完写回字典；循环版用两个变量滚动更新 `a, b = b, a + b`；用 `time.perf_counter()` 前后取差计时，说明重复计算是慢的根源。

### 相关知识点

- 前置知识点：`func-param`（参数与返回值）、`branch-if`（条件分支）、`loop-while`（while 循环）。
- 后续知识点：`search-binary`（二分查找）、`search-sort`（排序思想）。
- 来源：Python 官方教程“Defining Functions”，Python 标准库文档“sys.setrecursionlimit”。
