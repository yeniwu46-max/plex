import type { TourStepConfig } from './types'

/**
 * 学生端导览步骤
 * 混合策略：侧栏入口指代跨页功能，知识图谱/学习报告跳转对应页面
 */
export const studentTour: TourStepConfig[] = [
  {
    element: '[data-tour="student-learning-path"]',
    title: '学习路径',
    description: '这里展示你的个性化学习路线，系统会根据掌握情况推荐下一步学习内容。',
  },
  {
    element: '[data-tour="student-code-practice"]',
    title: '代码练习',
    description: '在这里完成 Python 编程练习，系统会根据运行结果给出反馈。',
  },
  {
    element: '[data-tour="student-knowledge-graph"]',
    title: '知识图谱',
    description: '知识图谱会展示知识点之间的关系，帮助你发现薄弱环节和前置知识。',
  },
  {
    element: '[data-tour="student-ai-assistant"]',
    title: 'AI 学习助手',
    description: '遇到问题时，可以向 AI 助手提问，它会结合你的学习记录给出分层提示。',
  },
  {
    element: '[data-tour="student-learning-report"]',
    title: '学习报告',
    description: '这里会汇总你的练习表现、能力画像和学习趋势，帮助你了解自己的成长变化。',
  },
]
