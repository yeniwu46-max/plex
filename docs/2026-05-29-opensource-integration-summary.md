# 2026-05-29 开源项目接入沉淀

**主题**：PLEX 开源项目升级 —— 七大集成落地  
**分支状态**：所有变更已完成，前后端服务均可正常运行

---

## 一、本次升级概览

根据《PLEX 开源项目接入方案》，本次对前端和后端进行了模块化集成，保持现有 PLEX 视觉风格不变，新增以下七项能力：

| # | 集成方向 | 技术选型 | 状态 |
|---|---------|---------|------|
| 1 | 代码编辑器升级 | `@guolao/vue-monaco-editor` 替换 vue-codemirror | ✅ 完成 |
| 2 | 在线判题（Mock） | 后端 `/api/v1/code/*` + 前端 `codeRunner.ts` | ✅ 完成 |
| 3 | 知识图谱可视化 | `@antv/g6` + `PlexKnowledgeGraph.vue` | ✅ 完成 |
| 4 | 学习数据图表 | `echarts` + `vue-echarts`，四类图表组件 | ✅ 完成 |
| 5 | 多智能体流程图 | `@vue-flow/core` + `PlexAgentFlow.vue` | ✅ 完成 |
| 6 | 知识库问答（Mock） | 后端 `/api/v1/knowledge-base/*` | ✅ 完成 |
| 7 | 多智能体协作（Mock） | 后端 `/api/v1/agent/*` | ✅ 完成 |

---

## 二、新增文件清单

### 前端

| 文件 | 说明 |
|------|------|
| `src/components/trial/PlexCodeEditor.vue` | Monaco 编辑器封装，自定义 `plex-dark` 主题，macOS 风格标题栏 |
| `src/data/knowledgeGraphData.ts` | 知识图谱节点/边类型定义及 mock 数据（计算思维学域） |
| `src/components/shared/PlexKnowledgeGraph.vue` | AntV G6 知识图谱可视化，支持 student/teacher/admin 三种主题色 |
| `src/components/charts/PlexRadarChart.vue` | ECharts 雷达图（学生能力画像） |
| `src/components/charts/PlexLineChart.vue` | ECharts 折线图（学习趋势） |
| `src/components/charts/PlexBarChart.vue` | ECharts 柱状图（班级掌握度对比） |
| `src/components/charts/PlexPieChart.vue` | ECharts 饼图（错题类型分布） |
| `src/components/charts/PlexLearningDashboard.vue` | 组合仪表盘（四图汇总） |
| `src/components/admin/PlexAgentFlow.vue` | Vue Flow 多智能体编排可视化，含模拟运行与日志面板 |
| `src/api/codeRunner.ts` | Judge0 mock 接口封装 |

### 后端

| 文件 | 说明 |
|------|------|
| `backend/app/routes/code.py` | Mock Judge0：`run`、`submit`、`result`、`languages` 四端点，JWT 鉴权 |
| `backend/app/routes/knowledge_base.py` | Mock RAGFlow：`upload`、`query`、`documents`、`status` 四端点 |
| `backend/app/routes/agent_service.py` | Mock CrewAI/VoltAgent：`diagnose`、`recommend-path`、`analyze-code`、`generate-feedback`、`teacher-suggestion`、`status` 六端点 |

---

## 三、修改文件说明

### 前端关键修改

- **`PythonTrialWorkspace.vue`**：编辑器由 CodeMirror → Monaco（`PlexCodeEditor`）
- **`AdminKnowledgeNexusPanel.vue`**：静态占位 → `PlexKnowledgeGraph` 动态图谱
- **`AdminAgentOrchestrationPanel.vue`**：静态文本 → `PlexAgentFlow` 交互式流程图
- **`StudentControlView.vue`**：新增雷达图（能力画像）+ 折线图（7 日学习趋势）
- **`TeacherHomeView.vue`**：新增柱状图（知识域掌握度）+ 饼图（错题分布）
- **`AdminTrialObservatoryPanel.vue`**：新增折线图（平台活跃度）+ 柱状图（班级完成率）
- **`StarPathLabView.vue`**：新增"知识图谱"视图模式，可与星轨地图切换

### 后端关键修改

- **`routes/__init__.py`**：注册 `code_bp`、`kb_bp`、`agent_bp` 三个蓝图

---

## 四、依赖变更

```json
// frontend/package.json 新增
"@guolao/vue-monaco-editor": "^1.x",
"@antv/g6": "^5.x",
"echarts": "^5.x",
"vue-echarts": "^7.x",
"@vue-flow/core": "^1.x",
"@vue-flow/background": "^1.x",
"@vue-flow/controls": "^1.x",
"@vue-flow/minimap": "^1.x"
```

---

## 五、已知问题与说明

1. **后端服务为 Mock**：Judge0、RAGFlow、CrewAI 均为本地 mock，无需外部服务即可演示，真实接入时替换对应端点实现即可。
2. **Vue 运行时警告**：`ClassArenaHub.vue` 中图标对象被放入响应式数组，产生 `markRaw` 相关警告，属存量问题，不影响功能。
3. **Monaco 类型声明**：`monaco-editor` 类型包以 `any` 断言规避，后续可补装 `@types/monaco-editor`。

---

## 六、启动方式

```bash
# 后端
cd backend
python -m flask --app "app:create_app" run --host=127.0.0.1 --port=5000

# 前端
cd frontend
pnpm dev
# 访问 http://localhost:5173
```

---

*文档生成时间：2026-05-29*
