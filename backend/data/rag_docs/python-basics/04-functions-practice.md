# 模块四：函数与实践

## 13. 函数
`document_id: python-stage4-function`

- 概念：函数封装可复用逻辑，通过参数接收输入，通过 `return` 返回结果。
- 正例：`def area(radius):\n    return 3.14159 * radius ** 2`。
- 反例：函数只执行 `print(result)` 而调用方需要返回值，会得到 `None`。
- 常见错误：参数数量不匹配、可变默认参数、局部变量作用域误解。
- 基础题：编写函数判断一个数是否为素数。
- 进阶题：将成绩分析程序拆为读取、校验、统计和展示函数。
- 来源：Python 官方教程“Defining Functions”“More on Defining Functions”。

## 14. 异常处理
`document_id: python-stage4-exception`

- 概念：`try/except` 处理可预期异常；应捕获具体异常并保留错误上下文。
- 正例：`try: value = int(text)\nexcept ValueError: print("请输入整数")`。
- 反例：`except: pass` 会吞掉所有错误，难以定位问题。
- 常见错误：捕获范围过宽、把正常流程全部放入 `try`、错误后继续使用无效变量。
- 基础题：实现安全除法，处理零除和非法输入。
- 进阶题：为文件读取程序分别处理不存在、编码和权限错误。
- 来源：Python 官方教程“Errors and Exceptions”。

## 15. 文件操作
`document_id: python-stage4-file`

- 概念：使用 `with open(..., encoding="utf-8")` 自动关闭文件；模式包括 `r/w/a`。
- 正例：`with open("data.txt", encoding="utf-8") as file:\n    text = file.read()`。
- 反例：写文件时使用 `w` 模式会覆盖原内容，应根据需求选择模式。
- 常见错误：相对路径理解错误、忘记编码、一次读取超大文件。
- 基础题：读取文本并统计行数和单词数。
- 进阶题：把学生成绩保存为 CSV，并能重新加载。
- 来源：Python 官方教程“Reading and Writing Files”。

## 16. 简单算法
`document_id: python-stage4-algorithm`

- 概念：算法是解决问题的明确步骤；入门重点包括累计、计数、线性查找、排序和去重。
- 正例：`for value in values: total += value` 的时间复杂度为 `O(n)`。
- 反例：未处理空列表就计算平均值会产生零除错误。
- 常见错误：循环边界错误、初始化错误、在可用内置函数时重复实现不可靠逻辑。
- 基础题：实现线性查找，返回目标值首次出现的位置。
- 进阶题：比较列表去重与集合去重在顺序和复杂度上的差异。
- 来源：Python 官方教程“Data Structures”，Python Wiki“TimeComplexity”。
