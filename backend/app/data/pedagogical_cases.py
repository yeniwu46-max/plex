"""Curated real-world Python development cases per knowledge point."""
from __future__ import annotations

PEDAGOGICAL_CASES: dict[str, list[dict]] = {
    'intro': [
        {
            'title': 'CLI 问候脚本',
            'scenario': '运维同学写脚本向服务器日志输出启动确认信息，使用 print() 打印时间戳与状态。',
            'why_real': '部署脚本、CI 日志、自动化运维均依赖标准输出。',
            'key_idea': 'print 是最基础的程序输出方式，可配合 f-string 格式化。',
        },
        {
            'title': '成绩公示单行输出',
            'scenario': '教务小工具读取变量后一次性 print 学号与分数，供教师快速核对。',
            'why_real': '批处理脚本常通过控制台输出结果而非 GUI。',
            'key_idea': '多个 print 或一次 print 多参数均可完成格式化输出。',
        },
    ],
    'comment': [
        {
            'title': '代码审查标注',
            'scenario': '团队 review 时在复杂逻辑旁加 # TODO 与说明，便于后续维护。',
            'why_real': '开源项目与团队协作普遍用注释记录意图与待办。',
            'key_idea': '注释不参与执行，应解释“为什么”而非复述代码。',
        },
        {
            'title': '临时禁用调试语句',
            'scenario': '排查 bug 时注释掉 print 调试行，修复后再删除或恢复。',
            'why_real': '开发中频繁开关调试输出是常见做法。',
            'key_idea': '单行 # 可快速屏蔽语句而不改程序结构。',
        },
    ],
    'var': [
        {
            'title': '订单金额计算',
            'scenario': '电商脚本用 int/float 变量保存单价与数量，再计算总价。',
            'why_real': '业务系统中变量承载状态是基本模式。',
            'key_idea': '变量名应语义化，注意 int 与 float 的精度差异。',
        },
        {
            'title': '用户输入类型转换',
            'scenario': '表单脚本将 input 得到的字符串转为 int 再参与运算。',
            'why_real': 'input 返回 str，计算前必须显式转换。',
            'key_idea': 'type() 与 int()/float() 是处理用户数据的第一步。',
        },
    ],
    'io': [
        {
            'title': '命令行猜数字游戏',
            'scenario': '小游戏循环用 input() 读取玩家猜测，与随机数比较。',
            'why_real': '交互式 CLI 工具依赖 input 获取用户决策。',
            'key_idea': 'input 返回字符串，比较前需类型转换。',
        },
        {
            'title': '批量录入成绩',
            'scenario': '教师助手脚本逐行 input 学号与分数，直到输入空行结束。',
            'why_real': '轻量数据录入场景无需数据库即可用 input 完成。',
            'key_idea': '用循环配合 input 可收集多组数据。',
        },
    ],
    'ops': [
        {
            'title': '折扣价计算',
            'scenario': '用算术与比较运算判断满减条件，计算最终应付金额。',
            'why_real': '定价逻辑是电商与收银系统的核心片段。',
            'key_idea': '// 整除、% 取余与比较运算组合表达业务规则。',
        },
        {
            'title': '权限布尔组合',
            'scenario': '用 and/or 组合多个布尔条件判断用户是否有操作权限。',
            'why_real': '访问控制常基于逻辑运算短路求值。',
            'key_idea': '逻辑运算结果可直接用于 if 条件。',
        },
    ],
    'cond': [
        {
            'title': '成绩等级判定',
            'scenario': '根据分数区间用 if-elif-else 输出优/良/及格/不及格。',
            'why_real': '报表与学籍系统大量依赖分支逻辑。',
            'key_idea': '互斥区间应使用 elif 避免重复判断。',
        },
        {
            'title': '登录校验',
            'scenario': '比对用户名密码，正确则 print 欢迎，否则提示重试。',
            'why_real': '认证流程是最典型的条件分支应用。',
            'key_idea': '先处理边界与错误分支，再处理主路径。',
        },
    ],
    'loop': [
        {
            'title': '班级成绩统计',
            'scenario': '用 for 遍历 scores 列表累加总分并计算平均分。',
            'why_real': '数据分析入门几乎都会遇到累加与均值。',
            'key_idea': '累加变量应在循环外初始化，循环内更新。',
        },
        {
            'title': '猜数字直到正确',
            'scenario': 'while 循环配合 input，直到猜中目标数才退出。',
            'why_real': '交互式游戏与重试逻辑常用 while。',
            'key_idea': '循环体内必须更新条件相关变量，避免死循环。',
        },
    ],
    'range': [
        {
            'title': '九九乘法表',
            'scenario': '嵌套 range 生成行列索引，格式化输出乘法表。',
            'why_real': '嵌套 range 是表格型输出的经典练手题。',
            'key_idea': 'range 左闭右开，stop 不包含在序列中。',
        },
        {
            'title': '批量文件序号',
            'scenario': '用 range(1, n+1) 为导出文件生成连续编号后缀。',
            'why_real': '批处理脚本常用 range 控制迭代次数。',
            'key_idea': 'break/continue 可精细控制循环流程。',
        },
    ],
    'str': [
        {
            'title': '日志关键词统计',
            'scenario': '遍历日志字符串统计 ERROR 出现次数或提取子串。',
            'why_real': '运维与数据分析常做文本模式匹配。',
            'key_idea': 'str 不可变，切片与方法如 count/split 很常用。',
        },
        {
            'title': 'CSV 行解析',
            'scenario': '按逗号 split 一行 CSV，strip 空格后取字段。',
            'why_real': '轻量数据处理不总是需要 pandas。',
            'key_idea': 'split 与 strip 组合可清洗简单文本数据。',
        },
    ],
    'list': [
        {
            'title': '购物车商品列表',
            'scenario': '用 list 保存商品名，append 添加、remove 删除、遍历结算。',
            'why_real': '有序集合是业务列表页面的自然建模。',
            'key_idea': '索引从 0 开始，负索引可访问尾部元素。',
        },
        {
            'title': '成绩排序榜单',
            'scenario': '对 scores 列表 sorted 或 sort 后输出前三名。',
            'why_real': '排行榜与报表依赖列表排序。',
            'key_idea': 'sort 原地修改，sorted 返回新列表。',
        },
    ],
    'dict': [
        {
            'title': '学生信息查询',
            'scenario': '用学号作 key、姓名与分数作 value 的字典，O(1) 查找。',
            'why_real': '键值映射是缓存与索引的基础结构。',
            'key_idea': 'dict.get 可安全访问缺失键。',
        },
        {
            'title': '词频统计',
            'scenario': '遍历单词列表，用 dict 累计每个词出现次数。',
            'why_real': '文本分析与自然语言预处理常见词频表。',
            'key_idea': 'dict[key] = dict.get(key, 0) + 1 是经典模式。',
        },
    ],
    'func': [
        {
            'title': ' reusable 格式化输出',
            'scenario': '定义 format_score(name, score) 统一打印成绩单行。',
            'why_real': '函数消除重复代码，提升可测试性。',
            'key_idea': '参数与 return 明确边界，单一职责。',
        },
        {
            'title': '单元测试友好函数',
            'scenario': '将 “两数之和” 封装为 add(a, b) 便于 pytest 断言。',
            'why_real': '可测试函数是工程化代码的起点。',
            'key_idea': '纯函数无副作用，输入输出清晰。',
        },
    ],
    'file': [
        {
            'title': '日志文件归档',
            'scenario': '用 with open 读取 app.log，过滤 ERROR 行写入 error.log。',
            'why_real': '运维脚本日常处理文本日志文件。',
            'key_idea': 'with 语句自动关闭文件，避免资源泄漏。',
        },
        {
            'title': '配置文件读取',
            'scenario': '逐行读取 settings.txt，解析 key=value 到 dict。',
            'why_real': '轻量项目常用文本配置而非数据库。',
            'key_idea': 'readlines 与 strip 组合处理行文本。',
        },
    ],
    'except': [
        {
            'title': '安全整数转换',
            'scenario': 'input 转 int 时用 try-except 捕获 ValueError 并提示重输。',
            'why_real': '健壮 CLI 必须处理非法输入。',
            'key_idea': '只捕获预期异常，给出可操作的错误信息。',
        },
        {
            'title': '文件缺失处理',
            'scenario': '打开可能不存在的 data.txt，FileNotFoundError 时创建默认内容。',
            'why_real': '首次运行脚本时常需优雅降级。',
            'key_idea': 'try/except/else/finally 分工明确。',
        },
    ],
    'algo-sum': [
        {
            'title': '销售日报汇总',
            'scenario': '遍历当日订单列表求 total、count、max、min。',
            'why_real': '报表系统核心就是聚合统计。',
            'key_idea': '单次遍历可同时维护多个聚合变量。',
        },
        {
            'title': '传感器读数平均',
            'scenario': '累加采样值并除以样本数，注意空列表边界。',
            'why_real': '物联网与实验数据采集常见均值计算。',
            'key_idea': '除法前检查 count>0 避免 ZeroDivisionError。',
        },
    ],
    'algo-search': [
        {
            'title': '通讯录查找',
            'scenario': '在线性列表中按姓名查找电话号码，找到即返回索引。',
            'why_real': '小规模数据线性查找简单可靠。',
            'key_idea': '从头到尾比较，最坏 O(n)。',
        },
        {
            'title': '库存 SKU 检索',
            'scenario': '遍历 products 列表匹配 sku 字段，未找到返回 -1。',
            'why_real': '仓储脚本常用顺序查找。',
            'key_idea': '提前 break 可节省不必要的比较。',
        },
    ],
}


def cases_for_knowledge(knowledge_key: str, limit: int = 2) -> list[dict]:
    rows = PEDAGOGICAL_CASES.get(knowledge_key) or []
    return [dict(item) for item in rows[:limit]]
