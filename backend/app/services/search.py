"""全局搜索服务

当前实现：返回占位空数据，供前端联调验证接口格式。

== Meilisearch 接入步骤（后期扩展）==
1. pip install meilisearch
2. client = meilisearch.Client('http://127.0.0.1:7700', 'MASTER_KEY')
3. 按 scope 建立三个 index:
     student_search、teacher_search、admin_search
4. 推送文档时用 SearchItem 格式（id/title/subtitle/category/route/query/keywords）
5. 配置 filterableAttributes: ['category', 'scope']
6. 在 search_items() 中：
     results = client.index(f'{scope}_search').search(
         q, {'filter': f'scope = {scope}', 'limit': limit, 'attributesToHighlight': ['title']}
     )
     将 results['hits'] 按 category 分组后返回 SearchGroup[] 格式
"""

from typing import Optional


CATEGORY_LABELS = {
    # student
    'course': '课程',
    'knowledge': '知识点',
    'exercise': '练习题',
    'mistake': '错题',
    'path': '学习路径',
    # teacher
    'student': '学生',
    'class': '班级',
    'assignment': '作业',
    'question': '题目',
    # admin
    'agent': '智能体',
    'kg_node': '知识图谱',
    'user': '用户',
    'permission': '权限',
    'module': '系统模块',
}

SCOPE_CATEGORIES = {
    'student': ['course', 'knowledge', 'exercise', 'mistake', 'path'],
    'teacher': ['student', 'class', 'assignment', 'question', 'knowledge'],
    'admin': ['agent', 'kg_node', 'user', 'permission', 'module'],
}


def search_items(q: str, scope: str, limit: int = 20) -> list[dict]:
    """返回 SearchGroup[] 格式（groups 数组）。

    后期替换为 Meilisearch 调用时，只需修改此函数内部实现，
    路由层与响应格式保持不变。
    """
    # 占位：返回空分组（前端 Fuse 本地搜索兜底）
    categories = SCOPE_CATEGORIES.get(scope, [])
    groups = [
        {'category': cat, 'label': CATEGORY_LABELS.get(cat, cat), 'items': []}
        for cat in categories
    ]
    return groups
