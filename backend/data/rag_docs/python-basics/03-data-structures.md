# 模块三：数据组织

## 9. 字符串
`document_id: python-stage3-string`

- 概念：字符串是不可变字符序列，支持索引、切片和常用方法。
- 正例：`name.strip().lower()` 先去空白再转小写。
- 反例：`text[0] = "A"` 会失败，因为字符串不可变。
- 常见错误：索引越界、混淆字符和整数、忽略方法返回的新字符串。
- 基础题：统计一句话中元音字母数量。
- 进阶题：规范化用户输入并判断是否为回文。
- 来源：Python 官方教程“Strings”。

## 10. 列表
`document_id: python-stage3-list`

- 概念：列表是可变有序容器，支持索引、切片、增删改和遍历。
- 正例：`scores.append(90)` 添加元素，`scores[:3]` 获取切片。
- 反例：遍历列表时直接删除当前元素，可能跳过数据。
- 常见错误：下标越界、浅拷贝误用、把 `append` 返回值赋回列表。
- 基础题：找出列表中的最大值和最小值。
- 进阶题：在不修改原列表的前提下去重并保持顺序。
- 来源：Python 官方教程“More on Lists”。

## 11. 字典
`document_id: python-stage3-dict`

- 概念：字典保存键值映射，键必须可哈希；`get` 可安全读取缺失键。
- 正例：`count[word] = count.get(word, 0) + 1`。
- 反例：直接读取不存在的 `data["score"]` 会触发 `KeyError`。
- 常见错误：使用列表作为键、遍历时改变字典大小、混淆键和值。
- 基础题：统计字符串中每个字符出现次数。
- 进阶题：用嵌套字典保存学生信息并按成绩排序。
- 来源：Python 官方教程“Dictionaries”。

## 12. 函数
`document_id: python-stage3-function`

- 概念：函数封装可复用逻辑，通过参数接收输入，通过 `return` 返回结果。
- 正例：`def area(radius):\n    return 3.14159 * radius ** 2`。
- 反例：函数只执行 `print(result)` 而调用方需要返回值，会得到 `None`。
- 常见错误：参数数量不匹配、可变默认参数、局部变量作用域误解。
- 基础题：编写函数判断一个数是否为素数。
- 进阶题：将成绩分析程序拆为读取、校验、统计和展示函数。
- 来源：Python 官方教程“Defining Functions”“More on Defining Functions”。
