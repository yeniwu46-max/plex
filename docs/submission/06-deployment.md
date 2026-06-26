# 部署与运行说明

推荐环境为 Windows 10/11 或 Linux、Python 3.12、Node.js 20、npm 和 MySQL 8。
本地演示可使用 SQLite。禁止使用 Python 3.14 运行当前 Flask 2.3 依赖组合。

Windows 在仓库根目录执行：

```bat
start.bat --check
start.bat
```

检查模式优先使用项目 `.venv`，执行依赖安装、数据库升级、演示数据、健康接口和
`student001`、`teacher001`、`admin` 三个账号检查，成功后返回 0 且不启动服务。

手动运行时先进入 `backend` 执行迁移与种子数据，再运行后端；进入 `frontend`
执行 `npm ci` 和 `npm run dev`。生产环境必须通过环境变量配置数据库和 JWT 密钥，
不得提交 `.env`、真实讯飞密码或包含个人数据的数据库。

MySQL 8 和在线 CI 工作流已经配置，但当前本机没有 Docker 且 GitHub CLI 未登录，
因此仍需外部运行链接作为最终证据。
