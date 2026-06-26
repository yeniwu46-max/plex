# 模块四：文件、异常与算法实践

## 13. 文件操作
`document_id: python-stage4-file`

- 概念：使用 `with open(..., encoding="utf-8")` 自动关闭文件；模式包括 `r/w/a`。
- 正例：`with open("data.txt", encoding="utf-8") as file:\n    text = file.read()`。
- 反例：写文件时使用 `w` 模式会覆盖原内容，应根据需求选择模式。
- 常见错误：相对路径理解错误、忘记编码、一次读取超大文件。
- 基础题：读取文本并统计行数和单词数。
- 进阶题：把学生成绩保存为 CSV，并能重新加载。
- 来源：Python 官方教程“Reading and Writing Files”。

## 14. 异常处理
`document_id: python-stage4-exception`

- 概念：`try/except` 处理可预期异常；应捕获具体异常并保留错误上下文。
- 正例：`try: value = int(text)\nexcept ValueError: print("请输入整数")`。
- 反例：`except: pass` 会吞掉所有错误，难以定位问题。
- 常见错误：捕获范围过宽、把正常流程全部放入 `try`、错误后继续使用无效变量。
- 基础题：实现安全除法，处理零除和非法输入。
- 进阶题：为文件读取程序分别处理不存在、编码和权限错误。
- 来源：Python 官方教程“Errors and Exceptions”。

## 15. 求和与统计
`document_id: python-stage4-sum-statistics`

- 概念：累计变量用于求和，计数器用于统计满足条件的元素；遍历一次通常为 `O(n)`。
- 正例：`total = 0\nfor value in values:\n    total += value`。
- 反例：把 `total = 0` 写在循环内部会导致每轮重置，无法得到总和。
- 常见错误：初始化位置错误、空集合除零、筛选条件边界遗漏。
- 基础题：统计列表中偶数的数量并计算它们的和。
- 进阶题：一次遍历同时计算数量、总和、平均值、最大值和最小值。
- 来源：Python 官方教程“More Control Flow Tools”“Data Structures”。

## 16. 线性查找
`document_id: python-stage4-linear-search`

- 概念：线性查找从头到尾比较元素，找到目标后返回位置，最坏时间复杂度为 `O(n)`。
- 正例：`for index, value in enumerate(values):\n    if value == target:\n        return index`。
- 反例：循环结束后无条件返回当前下标，会把“未找到”误报为最后一个位置。
- 常见错误：未定义未找到返回值、重复元素策略不清、索引和值混淆。
- 基础题：返回目标值第一次出现的索引，未找到时返回 `-1`。
- 进阶题：扩展为返回全部匹配位置，并比较提前结束与完整扫描的差异。
- 来源：Python 官方教程“Data Structures”，Python Wiki“TimeComplexity”。
