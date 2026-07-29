# 《Python 程序设计基础》课程知识库

## 用途

本目录是 PLEX 中国软件杯版本的初始课程知识库，限定为一门完整课程，供以下能力使用：

- 学生画像中的知识基础判断。
- 多智能体资源生成。
- 驿站 RAG 辅导。
- 个性化路径和资源推荐。
- 内容引用与防幻觉审核。

## 课程结构

| 模块 | 文件 | 知识点（knowledge_key → document_id） |
|---|---|---|
| Python 入门 | `01-python-intro.md` | `intro` 程序结构、`comment` 注释、`var` 变量与类型、`io` 输入输出 |
| 控制结构 | `02-control-flow.md` | `ops` 运算与表达式、`cond` 条件分支、`loop` 循环结构、`range` range |
| 数据组织 | `03-data-structures.md` | `str` 字符串、`list` 列表、`dict` 字典、`func` 函数 |
| 文件与算法实践 | `04-functions-practice.md` | `file` 文件操作、`except` 异常处理、`algo-sum` 求和统计、`algo-search` 线性查找 |

共 4 个模块、16 个知识点。每个知识点为完整讲义段落，包含概念讲解、正例代码、反例/易错点、练习与答案要点、前置/后续知识点，并保留稳定的 `document_id` 与必填字段行。

## 每个知识点的内容结构

- [x] 概念讲解（讲义段落 + `- 概念：` 契约字段，150 字以上）
- [x] 正确示例（代码块 + `- 正例：`）
- [x] 错误示例（代码块 + `- 反例：`）
- [x] 常见错误（`- 常见错误：`）
- [x] 基础练习与答案要点（`- 基础题：`）
- [x] 进阶练习与答案要点（`- 进阶题：`）
- [x] 相关前置/后续知识点
- [x] 资料来源（`- 来源：`）

## 完整性状态

16 个知识点均已有独立章节、稳定且唯一的 `document_id`，并包含概念、正反例、常见错误、基础题、进阶题和来源。运行以下命令验证契约：

```bash
python scripts/verify_knowledge_base.py
```

仍需继续增强的内容：在真实环境中执行文档代码样例、将文档加载到真实 RAG 索引并评测检索命中率。

## ID 契约说明

- `knowledge_key` 与 `document_id` 的映射以 `app/data/course_knowledge.py` 中 `COURSE_KNOWLEDGE_SOURCES` 为准。
- 新增知识点必须同步更新该映射与知识目录，禁止私自编造冲突的 `document_id`。
- 章节标题格式保持为 `## <序号>. <标题>`，正文中保留 `` `document_id: ...` ``。

## 推荐来源

- [Python 3 官方教程](https://docs.python.org/3/tutorial/)
- [Python 3 标准库](https://docs.python.org/3/library/)
- 团队自编课程讲义、题库和课堂案例

引用外部资料时应改写为团队课程内容，记录来源，不复制大段受版权保护内容。
