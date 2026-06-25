# 学生端质量闭环优化技术总结

日期：2026-06-25

## 背景

本轮目标是在不重做视觉语言、不引入 React、不改核心学习业务模型的前提下，对学生端进行一次质量闭环优化。重点处理移动端可用性、空操作、重复入口、资源长列表、页面默认空状态、控制台 404 和演示口径不清等问题。

## 改动范围

### 全局 Shell 与导览

- `App.vue` 将 `app-root` class 下沉到真实 DOM 容器，避免 `NMessageProvider` 透传 class 的 Vue warning。
- 首页不再自动弹出功能导览，导览只保留为用户主动入口，避免首次进入学生首页时遮挡主线任务。
- `PlexTopbar` 调整移动端标题布局，避免 390px 宽度下标题竖排或与右侧状态区挤压。
- `PlexSidebar` 调整移动端导航尺寸与可访问名称，保留底部图标导航，同时改善触控区和 active 状态。

### 学生端主线与入口去重

- 学生首页保持“今日主线 + 下一步行动”的定位，子页面通过 `StudentSectionTabs` 提供学习区和个人区的局部导航，减少重复入口堆叠。
- 探索舱定位为地图与状态页；星轨定位为知识点与资源入口；试炼保留做题与提交；驿站保留解释推荐原因与行动建议。
- 清理学生端空链接和非语义交互：`href="#"` 改为真实 `RouterLink` 或 `<button>`。

### 页面级完善

- 探索舱移除前端 heartbeat 轮询依赖，在线人数改用 overview 返回的 `class_online_count`，清除当前运行后端下的 `/api/v1/student/presence/heartbeat` 404。
- 星轨默认选中第一个知识点，移动端隐藏大面积机器人插画，详情区改为更紧凑的响应式布局。
- 个性化资源中心按知识点与资源类型去重分组，新增类型筛选、生成任务折叠、加载/失败/空状态和资源详情面板。
- 成长档案紧急任务记录按日期与知识点分组，并用语义按钮展开“查看作答与解析”。
- 学习画像用页面内弹窗替代 `window.prompt`，保留人工修正能力。
- 设置页去掉“本地保存演示”口径，明确通知、专注模式和主题偏好保存到当前浏览器。

### 共享前端能力

- 新增 `StudentSectionTabs`：为星轨/资源、成长档案/画像/设置提供统一局部导航。
- 新增 `studentWorkspace` Pinia store：缓存学生 overview、学习报告和推荐结果，减少学生端页面切换时的重复请求。

## 验证结果

### 构建与预算

执行：

```bash
cd frontend
npm run build
```

结果：

- `vue-tsc -b` 通过。
- Vite production build 通过。
- `scripts/verify-bundle.mjs` 通过。
- 首屏 gzip：`111899` bytes，小于 `153600` bytes 预算。
- 最大 lazy gzip：`399872` bytes，小于 `460800` bytes 预算。

### 静态扫描

学生端 Vue 文件扫描结果清零：

- 无 `href="#"`。
- 无 `window.prompt`。
- 无 `@click.prevent` 空操作。
- 无“本地演示 / 本地保存演示”文案。
- 无 `heartbeatStudentPresence` 或 `presencePollTimer` 页面依赖。

### 浏览器烟测

使用本机 Chrome + Playwright，在 `390×844` 移动端视口，以 `student001/student123` 登录后覆盖：

- `/student`
- `/student/discovery`
- `/student/star-path`
- `/student/star-path/resources`
- `/student/trials`
- `/student/messenger`
- `/student/me/growth`
- `/student/me/profile`
- `/student/me/settings`

结果：

- 所有页面顶栏标题横排显示，标题框约 `358×28`，未出现竖排。
- 所有页面自动弹窗数量为 `0`，首页导览不再自动遮挡。
- 网络 4xx 响应为 `0`。
- Console error 为 `0`。

## 注意事项

- 后端源码路由表中已存在 `/api/v1/student/presence/heartbeat`，但当前运行服务对该接口返回 404。本轮前端已移除探索舱对该轮询接口的依赖，若后续要恢复实时在线人数，应先确认运行后端加载的是最新路由并补充接口测试。
- 当前仓库工作区仍有大量既有未提交改动，本轮提交只应包含学生端质量闭环相关文件，不代表全仓库 freeze clean。
- `StudentSectionTabs` 与 `studentWorkspace` 已被多个学生端页面依赖，后续调整学生端导航或缓存策略时应优先复用这两个入口。
