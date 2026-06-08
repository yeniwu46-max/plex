# 模块一：Python 入门

## 1. 程序结构
`document_id: python-stage1-program-structure`

- 概念：Python 程序通常自上而下执行，代码块使用四个空格缩进；脚本入口可使用 `if __name__ == "__main__":`。
- 正例：`name = "PLEX"\nprint(name)`，先赋值再输出。
- 反例：在没有代码块的地方随意缩进，会触发 `IndentationError`。
- 常见错误：中英文标点混用、缩进不一致、变量使用前未定义。
- 基础题：编写程序依次输出姓名和专业。
- 进阶题：把输入、计算和输出分别封装为三个步骤。
- 来源：Python 官方教程“Whetting Your Appetite”“More Control Flow Tools”。

## 2. 注释
`document_id: python-stage1-comments`

- 概念：`#` 后为单行注释；文档字符串用于解释模块、函数或类，不等同于批量注释。
- 正例：`total = 0  # 累计分数`。
- 反例：用三引号包住大量代码会创建字符串对象，不能替代版本控制。
- 常见错误：注释与代码不一致、保留失效代码、泄露密钥。
- 基础题：为一个温度转换程序补充必要注释。
- 进阶题：为函数编写包含参数和返回值的文档字符串。
- 来源：Python 官方教程“An Informal Introduction to Python”，PEP 257。

## 3. 变量与类型
`document_id: python-stage1-variables-types`

- 概念：变量绑定对象；常用基础类型包括 `int`、`float`、`str`、`bool`。
- 正例：`age = 18\nheight = 1.72\npassed = True`。
- 反例：`score = "90"\nprint(score + 10)` 会产生类型错误，应先执行 `int(score)`。
- 常见错误：覆盖内置名、把 `=` 当作比较、浮点数直接判等。
- 基础题：读取两个整数并输出和与平均值。
- 进阶题：安全转换用户输入，输入非法时给出提示。
- 来源：Python 官方教程“Using Python as a Calculator”“Data Structures”。

## 4. 输入输出
`document_id: python-stage1-input-output`

- 概念：`input()` 始终返回字符串；`print()` 支持 `sep`、`end` 和 f-string。
- 正例：`age = int(input("年龄："))\nprint(f"明年 {age + 1} 岁")`。
- 反例：`input("数字：") + 1` 会把字符串与整数相加。
- 常见错误：忘记类型转换、格式化占位符错误、输出多余空格。
- 基础题：输入圆半径并输出保留两位小数的面积。
- 进阶题：输入三门成绩，输出总分、平均分和是否及格。
- 来源：Python 官方教程“Input and Output”。
