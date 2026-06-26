# 最终冻结文件分组

当前工作树包含核心功能、工程加固、证据、文档和历史设计资产。最终冻结前按下列边界审查，禁止一次性无差别提交。

## 必须纳入

### 核心后端

- `backend/app/` 中画像、资源生成、学习效果、安全、权限与恢复逻辑。
- `backend/app/utils/time.py`。
- 课程知识数据与 `backend/data/rag_docs/`。
- 对应数据库迁移和 `backend/manage.py`。

### 核心前端

- 学生工作区、成长档案、资源中心、教师审核和管理员证据视图。
- `frontend/src/api/`、路由和共享状态。
- `frontend/vite.config.ts`、bundle budget 脚本与报告。

### 测试和验证

- 新增及修改的后端测试。
- `backend/scripts/verify_*.py`、评测脚本和密钥扫描。
- `backend/pytest.ini`。
- `.github/workflows/ci.yml`。

### 提交材料

- `docs/submission/01-14`。
- `backend/reports/a3-personalization-local/`。
- `backend/reports/a3-next-stage/`。
- `backend/reports/a3-submission/`，其中最终重新生成清单和就绪报告。
- `frontend/reports/bundle-budget.json`。
- `start.bat`、README、QUICKSTART、技术总纲和 API 文档。

### 最终交付物

- `docs/submission/artifacts/PLEX-A3-defense.pptx`。
- `docs/submission/artifacts/PLEX-A3-demo.mp4`。

## 必须排除

- `.venv*`、`node_modules`、`.npm-cache`。
- `.codegraph`、`.cursor`、`.agents`、`.codex` 和 `outputs` 临时工作区。
- `dist`、缓存、日志、SQLite 数据库、上传目录。
- `.env`、凭证、访问令牌和完整个人提示词。
- 未用于最终交付的临时截图、渲染中间文件和测试录像。

## 需要人工确认

- 根目录四个 `PLEX *.pdf` 是否属于赛题需求/原型依据；若仅为历史参考，移入归档目录并在提交包排除。
- `picture/` 下设计素材是否被正式前端引用；未引用素材不进入候选包。
- 当前大量既有修改是否属于同一功能阶段；不得误删用户已有工作。

## 建议提交顺序

1. 核心画像、资源、反馈闭环与安全实现。
2. 学生端、教师端、管理员端交互调整。
3. 测试、验证脚本、CI 和启动脚本。
4. 课程知识数据与可重复报告。
5. 提交文档、PPT、视频和最终清单。

每组提交后运行对应测试。全部提交完成后在干净工作树重新生成 `release-manifest.json`，最后运行 `verify_release_readiness.py --require-external`。
