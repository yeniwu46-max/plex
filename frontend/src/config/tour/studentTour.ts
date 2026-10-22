import type { TourStepConfig } from './types'
export const studentTour: TourStepConfig[] = [
  {element: '[data-tour="student-home"]', prepareRoute: '/student', title: '学生首页', description: '查看今日学习任务、学习进度与近期反馈，从这里决定今天的第一步。'},
  {element: '[data-tour="student-discovery"]', prepareRoute: '/student/discovery', prepare: async () => { document.querySelector<HTMLButtonElement>('[data-tour="discovery-trial-tab"]')?.click() }, title: '探索舱', description: '在班级太空站查看同学动态、发起对战或进入模拟考试。'},
  {element: '[data-tour="student-path"]', prepareRoute: '/student/star-path', title: '学习路径', description: '选择学域与知识点，查看先修关系和下一步推荐。'},
  {element: '[data-tour="student-trials"]', prepareRoute: '/student/trials', title: '试炼中枢', description: '按知识点、难度、作答状态筛选题目，收藏想再练的内容。'},
  {element: '[data-tour="student-resources"]', prepareRoute: '/student/star-path/resources', title: '个性化资源', description: '选择知识点生成资料；查看、删除或从七天回收站恢复资源。'},
  {element: '[data-tour="student-messenger"]', prepareRoute: '/student/messenger', title: '小E 学习助手', description: '随心提问，或关联当前题目与自己的历史作答获得帮助。'},
  {element: '[data-tour="student-profile"]', prepareRoute: '/student/me/profile', title: '学习画像', description: '通过探索地图查看知识证据与复习建议，补充自述资料。'},
  {element: '[data-tour="student-settings"]', prepareRoute: '/student/me/settings', title: '个人设置', description: '调整经典或漫画外观、明暗模式与账户设置。'},
]
