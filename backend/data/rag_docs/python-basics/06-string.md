# 模块六：字符串

本模块系统整理字符串的用法：按下标与切片取出片段、用内置方法完成拆分拼接与清洗、逐字符遍历完成统计与回文判断。字符串是程序与人交互的主要载体，用户输入、文件内容、日志记录都是文本。学完后应能对一段中英文文本做规范化、检索与统计处理。

## 1. 索引与切片
`document_id: python-string-index`

字符串 `str` 是不可变的字符序列，可以像列表那样按下标取出单个字符：`s[0]` 是第一个字符，`s[-1]` 是最后一个。切片 `s[a:b:c]` 中 `a` 是起点（含）、`b` 是终点（不含）、`c` 是步长，三者都可省略；`s[::-1]` 把步长设为 -1，正是反转字符串的惯用写法。初学者最容易卡在两点：下标越界会报 `IndexError`，而切片越界只会自动截断、悄悄返回短串；想像修改列表那样写 `s[0] = "J"`，但字符串不可变，这行会抛 `TypeError`。

- 概念：字符串是不可变的字符序列，索引和切片都不会改变原对象，而是返回字符或一个新字符串。索引取单个字符，合法范围是 `0` 到 `len(s) - 1`，负索引 `-1` 到 `-len(s)` 等价于从右往左计数，越界访问抛 `IndexError`。切片遵循左闭右开，越界时自动收缩到边界，因此 `s[2:99]` 安全但不报错；当起点在终点右侧（如 `s[4:2]`）会得到空串，这常是循环边界写错时的“静默失败”。不可变性带来两个后果：不能按下标赋值，且所有“修改类”方法都必须接住返回值（`s = s.replace(...)`），否则原串纹丝不动。

### 正例代码

```python
s = "Python"
print(s[0], s[5])       # P n：合法下标是 0 到 5
print(s[-1], s[-6])     # n P：负索引从右往左数
print(len(s))           # 6

print(s[0:3])           # Pyt：左闭右开，取不到下标 3
print(s[:3], s[3:])     # Pyt hon：省略端点表示到头/到尾
print(s[::2])           # Pto：步长为 2，取下标 0、2、4
print(s[::-1])          # nohtyP：步长为 -1，即整串反转

s = s.replace("P", "J")  # 字符串不可变，只能重新绑定名字
print(s)                 # Jython
```

- 正例：`s[0:3]` 得到 `"Pyt"` 而非 `"Pyth"`，说明右端下标取不到；`s[::-1]` 是反转字符串的标准写法；最后 `s = s.replace("P", "J")` 用重新赋值代替“原地修改”，这是操作不可变对象的唯一途径。

### 反例与易错点

```python
s = "Python"
# s[0] = "J"        # TypeError：'str' object does not support item assignment
# print(s[6])       # IndexError：string index out of range

print(s[2:99])      # thon：切片越界不报错，自动截断到末尾
print(s[4:2])       # 空串：起点在终点右侧，得到 ""
s.upper()
print(s)            # Python：方法返回新串，原串没有任何变化
```

- 反例：`s[0] = "J"` 抛 `TypeError`，因为字符串不支持下标赋值，应写 `s = "J" + s[1:]`；`s[6]` 抛 `IndexError`；`s.upper()` 单独成句等于白算一次，结果被丢弃，必须写成 `s = s.upper()`。
- 常见错误：按下标给字符串赋值、下标越界（把 `len(s)` 当合法下标）、误以为切片越界会报错、调用方法后忘记接住返回值、把切片的右端点当作“包含”。

### 练习

- 基础题：输入一个单词，输出它的首字符、末字符和反转后的结果。
- 答案要点：首字符 `s[0]`、末字符 `s[-1]`、反转 `s[::-1]`；空串要先用 `if s:` 判断，否则 `s[0]` 会越界。
- 进阶题：编写逻辑把一个字符串的首字母改为大写而其余部分保持原样（不使用 `capitalize`）。
- 进阶答案要点：利用不可变性，用拼接构造新串 `s[0].upper() + s[1:]`；先判断字符串非空；注意不能写 `s[0] = ...`。

### 相关知识点

- 前置知识点：`seq-type`（数据类型）、`array-basic`（列表基础）。
- 后续知识点：`string-method`（常用方法）、`string-scan`（遍历与统计）。
- 来源：Python 官方教程“An Informal Introduction to Python — Strings”。

## 2. 常用方法
`document_id: python-string-method`

字符串自带一批高频方法，几乎覆盖日常文本处理：`split` 按分隔符拆成列表、`join` 把列表拼回字符串、`replace` 替换子串、`strip` 去两端空白、`upper`/`lower` 统一大小写、`find` 查找位置、`startswith` 判断前缀。它们都遵守同一条铁律：**返回新字符串，绝不修改原串**。初学者最常见的错误就是写下 `s.strip()` 却不赋值，然后奇怪“为什么空格还在”。另一个坑是 `find` 找不到时返回 `-1` 而不是 `None`。

- 概念：字符串方法是对文本的查询与变换操作，因字符串不可变，所有变换类方法都返回新对象，需用 `s = s.方法()` 或链式调用接住结果。`split(sep)` 按 `sep` 拆分并返回列表，不传参数时按任意空白拆分并自动忽略连续空白；`sep.join(可迭代对象)` 是它的逆操作，但要求每个元素都是字符串，混入数字会抛 `TypeError`。`strip` 只处理两端而不动中间的空白。`find` 返回首次出现的下标，找不到返回 `-1`，而找到在开头时返回 `0`，判断存在性更稳妥的写法是 `if x in s:`。链式调用如 `raw.strip().lower()` 是文本规范化的常用起手式。

### 正例代码

```python
raw = "  Alice , Bob , Cindy  "
names = [name.strip() for name in raw.strip().split(",")]
print(names)                            # ['Alice', 'Bob', 'Cindy']
print("-".join(names))                  # Alice-Bob-Cindy

text = "Hello Python"
print(text.upper(), text.lower())       # HELLO PYTHON hello python
print(text.replace("Python", "World"))  # Hello World
print(text.find("Python"))              # 6：首次出现的下标
print(text.find("Java"))                # -1：找不到返回 -1
print(text.startswith("Hello"))         # True

print(text)                             # Hello Python：原串始终未被修改
```

- 正例：`raw.strip().split(",")` 先去两端空白再按逗号拆分，链式调用读起来就是处理顺序；`"-".join(names)` 把列表拼回字符串；结尾 `print(text)` 印证了 `upper`、`replace` 都没有改动 `text` 本身。

### 反例与易错点

```python
s = "  hello  "
s.strip()
print(repr(s))          # '  hello  '：没接住返回值，原串没变

parts = "a,b,c".split()             # 忘了传分隔符，按空白拆
print(parts)                        # ['a,b,c']：整串成了唯一元素

# print("-".join([1, 2, 3]))        # TypeError：join 只能拼接字符串
print("-".join(str(x) for x in [1, 2, 3]))   # 1-2-3：先转成字符串

print("abc".find("a"))   # 0：找到却是假值，不能写 if s.find(x):
```

- 反例：`s.strip()` 不赋值等于丢弃结果，应写 `s = s.strip()`；`"a,b,c".split()` 漏传分隔符，得到只含一个元素的列表，应写 `split(",")`；`"-".join([1, 2, 3])` 抛 `TypeError`，需先用 `str(x)` 转换；`"abc".find("a")` 返回 `0`，在 `if` 中会被当成假，判断存在性应改用 `if "a" in "abc":`。
- 常见错误：调用方法后不接住返回值、`split` 漏传分隔符或误以为它会原地修改、`join` 直接拼接非字符串元素、用 `if s.find(x):` 判断子串是否存在。

### 练习

- 基础题：给定一行以逗号分隔的姓名（两端和分隔符旁可能有空格），输出去掉多余空格后的姓名列表。
- 答案要点：先 `raw.strip().split(",")` 拆分，再对每个元素调用 `strip()`（可用列表推导）；空元素可按需过滤。
- 进阶题：把用户输入的一句英文标准化为“单词之间只有一个空格、全部小写”的形式。
- 进阶答案要点：`text.lower().split()` 不传分隔符即可按任意空白拆分并自动去掉连续空格，再用 `" ".join(words)` 拼回；注意 `split()` 与 `split(" ")` 的差别。

### 相关知识点

- 前置知识点：`string-index`（索引与切片）、`array-basic`（列表基础）。
- 后续知识点：`string-scan`（遍历与统计）、`func-define`（函数定义）。
- 来源：Python 官方教程“Input and Output — Fancier Output Formatting”，标准库文档“Text Sequence Type — String Methods”。

## 3. 遍历与统计
`document_id: python-string-scan`

字符串是可迭代对象，`for ch in text:` 会依次取出每个字符，不需要下标。这让统计类任务变得直观：数元音、数字、空格只要逐字符判断并累加；统计每个字符出现的次数可以用字典 `freq[ch] = freq.get(ch, 0) + 1`；若只关心某个子串出现几次，直接用 `text.count(sub)` 更省事。判断回文则先把文本归一化——统一小写、去掉空格与标点——再比较 `t == t[::-1]`。初学者最容易忽略的正是这一步归一化：忘了 `lower()` 会让大写字母被漏计。

- 概念：遍历字符串就是逐字符扫描，配合计数器完成统计，模式与列表遍历一致：循环外初始化，循环内更新。判断字符属于哪一类可用 `ch in "aeiou"` 这类成员测试，或用 `isalpha`、`isdigit`、`isalnum`、`isspace` 等判定方法，它们返回布尔值。`count(sub)` 统计不重叠出现次数。归一化是文本比较的前置步骤：`lower()` 消除大小写差异，`strip()` 去两端空白，`"".join(ch for ch in s if ch.isalnum())` 滤掉空格与标点；只有在同一套标准下比较才有意义。回文判断的核心就是“归一化后与自身反转相等”。

### 正例代码

```python
text = "Was it a car or a cat I saw"

vowel_count = 0
for ch in text.lower():          # 先统一小写，避免漏掉大写字母
    if ch in "aeiou":
        vowel_count += 1
print(vowel_count)               # 9

freq = {}
for ch in text.lower():
    if ch.isalpha():             # 只统计字母，跳过空格
        freq[ch] = freq.get(ch, 0) + 1
print(freq["a"])                 # 6
print(text.lower().count("a"))   # 6：count 直接给出出现次数

cleaned = "".join(ch for ch in text.lower() if ch.isalnum())
print(cleaned)                   # wasitacaroracatisaw
print(cleaned == cleaned[::-1])  # True：归一化后判断回文
```

- 正例：`for ch in text.lower():` 把归一化放在循环的数据源上，循环体内只管判断；`freq[ch] = freq.get(ch, 0) + 1` 是字典计数的惯用写法，`get` 的默认值 0 免去了“键是否存在”的判断；`cleaned == cleaned[::-1]` 在过滤掉空格后才成立，正是回文判断的关键两步。

### 反例与易错点

```python
text = "Hello"
# for i in range(len(text)):
#     text[i] = text[i].lower()   # TypeError：字符串不可变，不能按下标赋值

count = 0
for ch in "Level":
    if ch == "l":                 # 没统一大小写，开头的大写 L 被漏掉
        count += 1
print(count)                      # 1，而忽略大小写时应为 2

s = "Was it a car or a cat I saw"
print(s == s[::-1])               # False：空格与大小写未归一化
```

- 反例：想“逐字符改小写”而按下标赋值会抛 `TypeError`，字符串不可变，正确做法是 `text = text.lower()` 或用 `"".join(...)` 生成新串；`ch == "l"` 漏掉大写 `L`，应先 `for ch in "Level".lower():`；直接用 `s == s[::-1]` 判断句子回文会因空格和大小写而得到 `False`，必须先过滤非字母数字并统一小写。
- 常见错误：忘记 `lower()` 导致大小写不一致漏计、忘记过滤空格与标点导致回文误判、计数器写在循环体内每轮被清零、把字符与它的编码值混淆（需要时应显式用 `ord`/`chr`）。

### 练习

- 基础题：统计一句英文中元音字母（a/e/i/o/u，大小写不敏感）的数量。
- 答案要点：计数器在循环外初始化；遍历 `text.lower()`，用 `if ch in "aeiou"` 判断后累加。
- 进阶题：判断一句话在忽略大小写、空格和标点的情况下是否为回文。
- 进阶答案要点：先用 `"".join(ch for ch in s.lower() if ch.isalnum())` 归一化，再比较 `t == t[::-1]`；空串可按题意约定为回文。

### 相关知识点

- 前置知识点：`string-index`（索引与切片）、`loop-for`（for 循环）。
- 后续知识点：`search-stat`（统计与计数）、`func-define`（函数定义）。
- 来源：Python 官方教程“Data Structures — Looping Techniques”，标准库文档“Text Sequence Type — str”。
