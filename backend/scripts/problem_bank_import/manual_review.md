# 人工核对清单（题库导入）

本文件由脚本自动生成，请勿手工编辑；如需记录人工处理结果，请在业务系统/工单中跟踪，
或在本文件末尾新增"处理记录"小节。

> 已合并以下阶段的核对清单：manual_review_items_clean.json, manual_review_items_backgrounds.json

共 44 条待人工确认的记录。

## 表 `problem`（39 条）

| 主键 | 问题描述 | 处理建议 |
| --- | --- | --- |
| 5 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（python_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |
| 6 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（python_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |
| 7 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 26 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（java_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |
| 26 | 题目描述提到"用户输入"，但参考答案代码完全不读取任何输入，题面与代码行为不一致 | 需人工确认：是题面描述过时/表达随意，还是参考答案遗漏了输入逻辑；样例已按代码真实行为（不消费任何输入）生成 |
| 33 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 34 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 36 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 37 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 39 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 45 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 46 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 49 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 55 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 83 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 83 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（python_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |
| 84 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 84 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（python_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |
| 85 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 85 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 89 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 90 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 90 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 91 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 138 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 139 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 140 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 141 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 142 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 143 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 144 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 145 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 145 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 148 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 148 | 参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明 | 需人工补充 input_format_cn/input_format_en |
| 149 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 149 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（python_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |
| 150 | description (英文) 为占位符 'English Description'，原文缺失 | 已置空 description_en，如需英文版本需人工翻译补充 |
| 150 | 样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（python_executed_ok），建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况） | 建议复核；如需更多样例可在此基础上人工补充 |

## 表 `solution`（5 条）

| 主键 | 问题描述 | 处理建议 |
| --- | --- | --- |
| 147644 | content(提交代码) 为空/空白 | 丢弃：无代码内容，无法展示/评分 |
| 178721 | content(提交代码) 为空/空白 | 丢弃：无代码内容，无法展示/评分 |
| 193652 | content(提交代码) 为空/空白 | 丢弃：无代码内容，无法展示/评分 |
| 203446 | content(提交代码) 为空/空白 | 丢弃：无代码内容，无法展示/评分 |
| 208370 | content(提交代码) 为空/空白 | 丢弃：无代码内容，无法展示/评分 |

