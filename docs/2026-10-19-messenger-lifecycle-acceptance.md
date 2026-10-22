# Messenger 页面生命周期与引用弹窗验收

日期：2026-10-19

## 完成范围

- Messenger 被缓存页面停用时中止未完成请求，清理待展示回答和临时 UI 状态；重新激活后从服务端刷新会话，避免把隐藏页面中的迟到回复记成已展示。
- Tutor 与 Messenger 的知识来源弹窗共用 `useRagSourceDialog` 生命周期管理。关闭弹窗、切换来源/账号、离开页面或卸载组件时，旧请求不能回写内容；失败时允许显式重试。
- 补充了页面停用、恢复、迟到响应、来源弹窗竞态的回归覆盖。

## 验证

- `npm run test:tutor`：62 项通过，0 失败（`output/plex-messenger-lifecycle-tests-20261019.log`）。
- `npm run build`：成功，退出码 0（`output/plex-messenger-final-build-20261019.log`）。
- 浏览器实际恢复验收未完成：重新打开 QA Messenger 路由时，隔离 QA 浏览器当前落在登录页，因此无法在本轮继续核对页面返回后的实际视觉状态。未在登录页输入账号信息。
- 本地 QA 数据库快照 `output/plex-messenger-page-20261019/before-messenger.db` 中，student5 的初始计数为 `session_start=9`、`hint_displayed=1`、`submission_graded=2`、`counterexample_checked=1`。此快照用于记录基线，不代表本轮完成后的实时状态。

## 本轮边界

本记录仅覆盖 Messenger 生命周期与知识来源弹窗。此前列出的其他页面验收、用户试用及运营验证不属于本次收尾范围。
