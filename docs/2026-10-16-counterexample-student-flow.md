# 反例挑战：学生作答与解释核对

本轮属于四模块智能化改造的 P3 接续。学生可在「试炼关卡 → 反例实验室」查看本班已发布题目，提交测试输入、自己推算的正确输出与原因说明。正式数据中没有自动发布开发验收题。

## 使用流程

1. 教师在「试炼中枢 → 反例工作台」建立题意、输入输出范围、参考实现与独立预期测试，提交错误版和修正版；通过隔离验证并完成教学审核后发布。
2. 学生阅读错误代码，输入合法 JSON 数据与预期输出，说明这组数据为什么能触发错误。
3. 执行器分别核对三份程序，界面分别展示是否找到差异、预期输出是否一致，以及这一个输入对应的输出。
4. 有效反例且预期正确时，小 E 核对学生解释。模型不确定或暂不可用时提示教师核对；教师可在反例工作台追加解释意见，不改变实际执行结果。
5. 本人最近 20 条当前版本提交可恢复；断网重试保留原请求编号和输入。页面只缓存编号，账号切换或切题会取消客户端请求并丢弃迟到响应。

当新输入暴露参考版与修正版不一致等材料问题时，系统暂停该版本。学生不会因此被记为答错；教师须把仍合法的问题输入加入独立测试，再提交修订版验证。

## 学习证据的含义

反例成功表示“本次输入确实揭示差异，且预期输出与参考/修正程序一致”。它不证明算法在所有输入上正确，也不等于学生已掌握整个知识点。

实践次数与成功次数单独保存。正式掌握估计、测验成绩、积分和误概念计数不受它直接影响。成功后安排一天后的独立迁移练习提醒，后续同知识点独立正式答对可以解除。这个间隔是可调整的工程规则，还没有教学效果实验支持。

## 实现位置

- 后端：`backend/app/services/counterexample_attempt.py`、`counterexample_explanation.py`。
- 状态：`backend/app/services/learner_state.py`、`learner_decision.py`。
- API：`backend/app/routes/counterexample.py`，契约见仓库 `backend_api_design.md`。
- 前端：`frontend/src/views/StudentCounterexampleView.vue`、`frontend/src/composables/useCounterexampleAttempt.ts`。
- 迁移：`backend/migrations/versions/20261016_0024_counterexample_attempts.py`。

两套样式保持独立：经典沿用现有 Naive UI 深浅色变量；漫画只在 `data-plex-style="comic"` 下增加分镜边框和硬阴影，没有修改经典主题的全局样式。

## 验证与复现

在 `backend/` 下：

```powershell
../.venv/Scripts/python.exe -m pytest tests/test_counterexample_attempts.py tests/test_counterexample_gates.py tests/test_learner_state.py tests/test_learning_decisions.py -q
../.venv/Scripts/python.exe scripts/test_learner_state_mysql.py -k counterexample
../.venv/Scripts/python.exe scripts/check_counterexample_attempts.py --real-model
```

前两条使用测试数据；MySQL 脚本只创建和清理随机命名的独立测试库。第三条使用临时 SQLite、真实 Docker 和本机已配置模型，需本机执行器可用；`--real-model` 会产生一次解释核对调用，可省略以只验收执行流程。脚本模拟的教师审核不代表真实教师质量审阅。

在 `frontend/` 下：

```powershell
npm run test:counterexample
npm run build
```

本轮证据：

- SQLite 状态、决策、反例相关回归 74 项通过：`output/plex-p3-attempts-regression.log`。其后补充历史接口，反例两文件 46 项通过：`output/plex-p3-attempts-final-tests.log`；最后新增同班隐私和修复基准检查，作答专项 18 项通过：`output/plex-p3-attempts-last-tests.log`。
- 随机独立 MySQL 库 46 项通过：`output/plex-p3-attempts-mysql.log`；后补同班隐私/修复回归 2 项通过：`output/plex-p3-attempts-ownership-mysql.log`。计数存在重复，不累加为独立用例数量。
- 实际 Vue 会话逻辑测试 7 项通过：`output/plex-p3-attempts-frontend.log`；生产文案、类型、构建与包预算检查通过：`output/plex-p3-attempts-build.log`。
- 真实 HTTP + Docker + DeepSeek 验收：`output/plex-p3-attempts-live.json`。本次输入 `[2,3]` 的错误输出为 2、参考/修正输出为 5；原请求重试和恢复一致；教师解释更新不改变执行事实。另一个三元素输入暴露合成题修正版问题，题目自动暂停且没有新增作答事件。
- 真实执行采用 Python 3.12.15，镜像内容 ID 与发布基准一致。单次学生执行约 5.468 秒、解释核对约 1.207 秒，模型报告总用量 416 tokens；仅为该样例观测，不是 P95、成本或准确率结论。
- 本机 MySQL 从 `20261016_0023` 严格迁移到 `20261016_0024`，未重置学习数据或运行 seed：`output/plex-p3-attempts-migration.log`。

## 尚未完成

浏览器工具此前被 URL 安全策略阻止，本轮没有绕过。四种主题与 1440/1024/768/390px 的实际浏览器排版、键盘和交互验收仍待完成；脚本测试及构建不能替代视觉验收。

教师出题/解释审核页面已接入，使用与恢复规则见 `2026-10-16-counterexample-teacher-workbench.md`。后台模型候选生成、自动教学审核、首批约 30 道真实教师审阅题和性质/变形测试仍在 P3 后续范围。配额、取消向执行层传播、正式用量观测和真实试用属于 P4；不能将本轮学生闭环当作四模块全部完成。
