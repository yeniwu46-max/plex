import type { TourStepConfig } from './types'

/**
 * 教师端导览步骤
 */
export const teacherTour: TourStepConfig[] = [
  {
    element: '[data-tour="teacher-class-dashboard"]',
    title: '班级看板',
    description: '这里汇总班级整体学习情况，包括完成率、正确率和活跃度等核心指标。',
  },
  {
    element: '[data-tour="teacher-assignment-analysis"]',
    title: '作业分析',
    description: '系统会自动统计作业提交情况和高频错误，帮助教师快速定位教学难点。',
  },
  {
    element: '[data-tour="teacher-student-profile"]',
    title: '星域观测',
    description: '在星域观测页查看班级知识掌握、薄弱点与需关注学生，配合 AI 学情诊断制定干预方案。',
    prepareRoute: '/teacher/starfield',
  },
  {
    element: '[data-tour="teacher-weak-points"]',
    title: '知识薄弱点',
    description: '这里展示班级共性的薄弱知识点，为后续讲解和分层辅导提供依据。',
  },
  {
    element: '[data-tour="teacher-ai-suggestion"]',
    title: 'AI 教学建议',
    description: 'AI 会根据班级数据生成教学建议，辅助教师调整教学节奏和讲解重点。',
    prepareRoute: '/teacher/starfield',
  },
]
