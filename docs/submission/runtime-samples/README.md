# 提交包运行体验资产

| 目录/文件 | 用途 |
|---|---|
| `frontend-dist/` | 预构建前端，启动时用 Python 静态服务 + `/api` 反代（无需 npm ci） |
| `python-wheels/` | CrewAI 等多智能体依赖离线 wheel |
| `docker-compose.neo4j.yml` | 可选 Neo4j 图谱服务 |

## Neo4j（可选）

```bat
cd runtime
docker compose -f docker-compose.neo4j.yml up -d
```

在 `source/backend/.env` 设置 `NEO4J_ENABLED=true` 后重启后端。
