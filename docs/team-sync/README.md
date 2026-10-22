# 队友同步本地 PLEX（2026-10-22）

团队统一使用 GitHub 默认分支 **master**。本轮同步认证与首次入驻、学习状态与辅导、资源生成与用量、隔离判题、六题模拟考试、题库收藏、七天回收站及三端布局修正。新增接口与迁移必须随源码一起更新；版本范围、验收及公网维护方式见 [10 月 22 日发布交接](../2026-10-22-release-and-handoff.md)。此前双主题、设计资料、ICAN 材料和硬件模型继续保留。

## 拉取同一份源代码与资料

先保存或提交自己工作区的改动，再执行：

```powershell
git fetch origin
git switch master
git pull --ff-only origin master
git rev-parse HEAD
git rev-parse origin/master
git diff --exit-code origin/master -- frontend/src backend/app backend/agents
```

两次提交 ID 应相同，最后一条命令应无差异。新电脑可先 `git clone https://github.com/yeniwu46-max/plex.git`，进入 `plex` 目录再继续。

大型模型和演示视频沿用仓库已有的 GitHub Releases，不重复塞入 Git 历史。本轮已将本地 ZIP 与 GitHub 提供的 SHA-256 逐个比对；恢复清单还记录每个解包文件的 SHA-256。需要这些资料时，在仓库根目录执行 Python 3.12：

```powershell
py -3.12 scripts/restore_team_assets.py
py -3.12 scripts/restore_team_assets.py --check
```

脚本从该仓库下载三个硬件包与三分钟视频，校验后恢复到与本机相同的相对路径。已有内容不相同会报错，避免覆盖队友修改的模型。两份与原发布包不同的 3MF 文件直接随 Git 提交，脚本不会覆盖它们。完整清单见 [release-assets.json](release-assets.json)。

## 启动与两套主题

安装 Python 3.12、Node.js 20.19+，在仓库根目录执行 `start.bat`；详细配置见 [项目 README](../../README.md) 与 [后端快速开始](../../backend/QUICKSTART.md)。依赖使用 `frontend/package-lock.json` 和 `backend/requirements.txt`。开发前端为 `http://localhost:5180`，后端为 `http://127.0.0.1:5100`。

学生端右上角外观菜单 → 界面风格，可选 **经典太空 / 太空漫画**。无已有设置时默认经典太空与黑夜；要看到漫画界面请选择太空漫画。深色、浅色和跟随系统独立设置。登录后的外观偏好按账号保存并跨设备恢复，浏览器存储只作缓存；Git 不携带个人偏好。

已有数据库更新前先备份；开发数据库可执行 `python manage.py upgrade`。公网已有数据使用发布交接中的 `strict-migrate.py`，不要运行演示初始化或用本地数据库覆盖。新增考试与资源回收站依赖 `20261022_0035` 迁移。Python 正式评分依赖配置好的隔离执行服务，不能以本机 Python 子进程替代。

设计及说明入口：

- [双主题实现与验证](../2026-10-13-student-visual-themes.md)
- [五区域效果图、独立交互页与完整提示词](../design/plex-space-comic-preview-v2/README.md)
- [实际双主题截图和响应式检查](../design/plex-dual-theme-2026-10-13/)
- [第一轮漫画设计资料](../design/plex-comic-2026-10-12/README.md)
- [ICAN 提交材料](../ican-submission/PLEX-ICAN-上传清单.md)
- [展板 v02](../market-materials/exhibition-board-v02/README.md)
- [小 E 模型与下载](../../hardware-prototypes/README.md)

## “一致”的范围

本次同步源代码、接口定义、依赖清单、可分享的文档、图像、预览源文件和项目模型。GitHub 是公开仓库，因此不会包含本机 `.env` 密钥、登录令牌、个人数据库、向量索引、签名密钥、上传媒体、虚拟环境或 `node_modules`。模型 API 凭据需通过项目约定的私密渠道单独配置；不要把密钥放进 Git。

本地学习记录、XP、聊天历史和已生成资源来自数据库或浏览器存储，**仅拉取代码不代表这些运行数据与原电脑相同**。`start.bat` 能初始化演示环境；若必须复现原电脑的具体数据，应另行通过私密渠道迁移经过确认的数据备份与媒体，并核验目标环境，不从公开 GitHub 获取个人数据。

本地 `_qa*`、`tmp/`、渲染中间文件、Blender `.blend1` 自动备份及已被替代的旧压缩包不作为正式交付。已确认的 UI 预览和验收截图已从被忽略的 `output/` 归档到 `docs/design/`。本地已删除的旧提交附件同步从当前版本移除，历史版本仍可从 Git 历史找回。

## 提交前检查

双主题已完成浏览器交互与响应式验证，详见上方记录。检查新提交及 ZIP/Office 内部内容未发现匹配本机 API 凭据、常见 API token 或私钥标记。前端执行生产文案检查、TypeScript 检查、Vite 构建和 bundle budget 检查。

附件恢复脚本的 6 项测试已通过：首次下载与解包、重复执行、只读检查、损坏文件拒绝写入、本地修改保护、路径与下载来源限制；测试使用临时目录和模拟网络，已加入 GitHub CI。执行命令为 `python -m unittest discover -s scripts/tests -p test_restore_team_assets.py -v`。本机清单校验结果为 172 个文件、0 项缺失或差异。

仓库要求的 Continue `/check` 安装源 `continuedev/skills` 本次返回访问失败，GitHub API 返回 404；已按 `.continue/checks/` 中 Vue 栈、Flask API、数据库可移植性与密钥卫生三项手工审查，并在 PR 中记录此限制。
