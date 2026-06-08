# 2026-06-08 赛前代码基线记录

## 基线信息

| 项目 | 值 |
|---|---|
| 工作分支 | `codex/pre-sprint-baseline-20260608` |
| 基础提交 | `a3c950964644c2f2c497590f7c0a26f555318c52` |
| 基础提交说明 | `feat: connect real stats APIs, fix sync gaps, and add phase-2 summary doc` |
| 受跟踪改动快照 | `refs/codex/snapshots/pre-sprint-20260608` |
| 快照提交 | `c4e281e93e684259025f85d1eec93923ecd218bc` |
| 仓库外快照 | `F:\homework\.codex-backups\coding6-20260608-pre-sprint` |

恢复受跟踪改动时可先检查快照：

```powershell
git show refs/codex/snapshots/pre-sprint-20260608
```

仓库外快照包含：

- `tracked-working-tree.patch`：受跟踪文件的工作区差异。
- `tracked-index.patch`：暂存区差异。
- `untracked/`：安全的未跟踪文件副本。
- `untracked-files.txt`：未跟踪文件清单。
- `git-status.txt`：创建快照时的 Git 状态。
- `MANIFEST.txt`：快照来源、提交和排除项。

## 工作区分类

创建快照前的粗略分类：

| 分类 | 数量 |
|---|---:|
| 后端 | 58 |
| 前端 | 94 |
| 文档与素材 | 4 |
| 仓库配置 | 10 |

该数量用于判断变更规模，不代表最终提交文件数。

## 明确排除

以下内容未进入 Git 待提交列表，也未复制到仓库外安全快照：

- `backend/.env`
- `backend/instance/`
- 上传文件目录
- `*.db`、`*.sqlite`、`*.sqlite3`
- `backend/.venv-crewai/`
- `node_modules/`
- `dist/`
- 缓存、日志和 CodeGraph 本地数据库

密钥扫描只发现 `.env.example` 和文档中的占位符，未发现待提交的真实 API Key。

## 验证基线

2026-06-07 已完成：

```text
后端：python -m unittest discover -s tests -v
结果：Ran 51 tests，OK

前端：npm run build
结果：vue-tsc 与 Vite 构建通过
```

已知非阻断项：

- SQLAlchemy `Query.get()` 弃用警告。
- `datetime.utcnow()` 弃用警告。
- 前端构建存在大 chunk 警告。
- `@vueuse/core` 的 pure annotation 构建警告。

## 后续提交原则

1. 不把当前所有变更一次性无审查提交。
2. 按后端、前端、文档和素材拆分提交。
3. 每次提交前检查 `git diff --cached`。
4. 不提交 `.env`、数据库、上传文件、虚拟环境和模型密钥。
5. 6 月 27 日功能冻结前建立候选版本标签。

