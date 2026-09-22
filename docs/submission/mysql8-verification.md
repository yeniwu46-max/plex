# MySQL 8 验证环境

该环境用于关闭 990 命题的 MySQL 8 外部验收门槛。它与现有开发数据库隔离，默认映射到本机 `3307` 端口。

## 启动

在仓库根目录执行（密码只通过本机环境变量注入）：

```powershell
$env:PLEX_MYSQL_PASSWORD = '设置一个本地密码'
$env:PLEX_MYSQL_ROOT_PASSWORD = '设置一个本地根密码'
docker compose -f docker-compose.mysql8.yml up -d
```

启动后把后端的 `DATABASE_URL` 指向：

```text
mysql+pymysql://plex:设置一个本地密码@127.0.0.1:3307/plex_learning
```

先执行迁移/初始化，再验证版本：

```powershell
cd backend
python scripts/verify_mysql8_environment.py `
  --database-url 'mysql+pymysql://plex:设置一个本地密码@127.0.0.1:3307/plex_learning'
```

只有报告同时满足 `mysql_8=true`、连接成功且存在业务表，才可把 MySQL 8 门槛标为已验证。报告会对连接串中的密码脱敏。
