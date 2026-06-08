# 模块二：控制结构

## 5. 运算与表达式
`document_id: python-stage2-operators`

- 概念：算术、比较、逻辑运算共同组成表达式；括号优先于默认优先级。
- 正例：`eligible = age >= 18 and score >= 60`。
- 反例：`a > 0 & b > 0` 混用位运算和逻辑运算，语义容易错误。
- 常见错误：混淆 `/` 与 `//`、忘记 `%` 的用途、复杂表达式不加括号。
- 基础题：判断一个整数是否为偶数。
- 进阶题：计算阶梯折扣后的订单金额。
- 来源：Python 官方语言参考“Expressions”。

## 6. 条件分支
`document_id: python-stage2-condition`

- 概念：`if/elif/else` 按顺序匹配，第一个为真的分支执行。
- 正例：`if score >= 90: grade = "A"\nelif score >= 60: grade = "P"\nelse: grade = "F"`。
- 反例：先判断 `score >= 60` 再判断 `score >= 90`，高分会被前一分支截获。
- 常见错误：漏写冒号、缩进错误、边界条件遗漏。
- 基础题：判断年份是否为闰年。
- 进阶题：根据多个条件计算奖学金等级。
- 来源：Python 官方教程“if Statements”。

## 7. 循环结构
`document_id: python-stage2-loop`

- 概念：`for` 遍历可迭代对象，`while` 在条件为真时重复；`break` 结束循环，`continue` 跳过本轮。
- 正例：`total = 0\nfor value in numbers:\n    total += value`。
- 反例：`while count < 10:` 内不更新 `count` 会形成死循环。
- 常见错误：循环变量覆盖、累计值放在循环内重置、边界多一次或少一次。
- 基础题：输出 1 到 100 中所有 3 的倍数。
- 进阶题：读取若干成绩，输入 `-1` 时结束并输出平均分。
- 来源：Python 官方教程“for Statements”“break and continue Statements”。

## 8. range
`document_id: python-stage2-range`

- 概念：`range(start, stop, step)` 左闭右开，`stop` 不包含在序列中。
- 正例：`list(range(1, 6))` 得到 `[1, 2, 3, 4, 5]`。
- 反例：用 `range(1, 5)` 期待包含 5，会少执行一次。
- 常见错误：步长为零、负步长方向错误、索引范围与列表长度不匹配。
- 基础题：使用 `range` 输出 10 到 1。
- 进阶题：用嵌套 `range` 输出九九乘法表。
- 来源：Python 官方教程“The range() Function”。
