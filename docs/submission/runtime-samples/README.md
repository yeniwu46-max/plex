# 提交包运行体验资产

| 目录/文件 | 用途 |
|---|---|
| `frontend-dist/` | 预构建前端，启动时用 Python 静态服务 + `/api` 反代（无需 npm ci） |
| `python/` | 可迁移的 Python 3.12 运行时，已含 Flask、数据库驱动、CrewAI 等依赖 |
| `python-wheels/` | 可选的依赖 wheel 缓存（便于二次安装） |
| `docker-compose.neo4j.yml` | 可选 Neo4j 图谱服务 |

## Neo4j（可选）

```bat
cd runtime
docker compose -f docker-compose.neo4j.yml up -d
```

在 `source/backend/.env` 设置 `NEO4J_ENABLED=true` 后重启后端。
