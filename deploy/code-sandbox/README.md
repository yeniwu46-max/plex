# PLEX Python 隔离执行

从仓库根目录构建（Docker Desktop 使用 Linux containers）：

```sh
docker build -t plex-python-sandbox:1 deploy/code-sandbox
```

在 `backend/.env.execution.local` 或部署环境中配置，然后重启 Flask：

```dotenv
CODE_EXECUTION_BACKEND=docker
CODE_EXECUTION_DOCKER_IMAGE=plex-python-sandbox:1
```

本机覆盖文件不进入 Git。服务不会自动拉镜像、启动 Docker 或降级到宿主机 Python。缺少镜像、Docker 不可用或执行通道失败时返回 503，不产生正式作答结果。

容器由服务端生成名称并逐次创建，不挂载项目、密钥或 Docker socket。无网络，用户为 `65534:65534`，移除 capabilities，根目录只读，仅 `/tmp` 提供 16 MiB 临时空间；128 MiB 内存、32 个进程、0.5 CPU、2 秒 CPU 软上限/3 秒硬上限、8 秒墙钟时间，每个输出流最多 64 KiB。启用 init 进程以回收子进程并保留正确的 CPU 超时退出状态。单 Flask 进程最多同时执行两次，达到上限返回可重试错误。此数值是保护上限，不是并发性能测量。

代码及输入各不超过 64 KiB；一次自测 1–30 个用例，总预算 60 秒。当前每个用例分别创建容器。返回 `time/memory=null` 代表没有相应测量，不使用估算值冒充实际资源用量。

验收（在 `backend/` 下）：

```powershell
$env:PLEX_TEST_DOCKER='1'
../.venv/Scripts/python.exe -m pytest tests/test_execution_safety.py -q
```

不设置 `PLEX_TEST_DOCKER=1` 时，常规单元测试使用显式注入的执行适配器或验证禁用行为；真实容器测试单独标记跳过。真实容器测试覆盖中文标准输入输出、宿主机环境隔离、禁止网络、根目录不可写、CPU/墙钟超时、内存超限、输出上限与容器内 pytest。

远端 Judge0 使用 `CODE_EXECUTION_BACKEND=judge0`、`JUDGE0_API_URL` 和可选 `JUDGE0_AUTH_TOKEN`。接口传入无网络及资源限制；运营者还需在独立执行节点验证这些限制确实生效。不要把 Docker API 暴露给前端或不可信网络。公开多人试用前继续完成 P4 的并发、重启回收与部署验收。

`CODE_EXECUTION_BACKEND=disabled` 可以明确关闭执行。`auto` 仅在配置 Judge0 URL 时启用 Judge0，否则关闭。旧 `mock`、未验收的旧 `e2b` 配置均关闭执行，不存在自动回退。
