import type { TourStepConfig } from './types'

/**
 * 管理员端导览步骤
 * 全部在 /admin 页面内，通过 prepare 切换 activeNav tab
 */

type AdminNavKey = 'nexus' | 'agents' | 'knowledge' | 'observer' | 'governance'

/** 通过全局挂载的 plexAdminNavSetter 切换 tab（由 AdminHomeView provide） */
function switchAdminTab(tab: AdminNavKey): () => Promise<void> {
  return async () => {
    const setter = (window as Window & { __plexAdminNavSetter?: (key: AdminNavKey) => void }).__plexAdminNavSetter
    if (setter) {
      setter(tab)
      // 等待 Vue 渲染完成
      await new Promise((r) => setTimeout(r, 180))
    }
  }
}

export const adminTour: TourStepConfig[] = [
  {
    element: '[data-tour="admin-agent-flow"]',
    title: '智能体编排',
    description: '这里展示学习诊断、知识检索、路径推荐和反馈生成等智能体的协同流程。',
    prepare: switchAdminTab('agents'),
  },
  {
    element: '[data-tour="admin-system-monitor"]',
    title: '系统观测',
    description: '管理员可以在这里查看平台运行状态、服务调用量和异常情况。',
    prepare: switchAdminTab('observer'),
  },
  {
    element: '[data-tour="admin-knowledge-maintenance"]',
    title: '知识图谱维护',
    description: '这里用于维护知识点、前置关系和学习路径，是平台自适应推荐的重要基础。',
    prepare: switchAdminTab('knowledge'),
  },
  {
    element: '[data-tour="admin-permission-control"]',
    title: '权限管理',
    description: '管理员可以在这里配置用户角色、功能权限和不同端的访问范围。',
    prepare: switchAdminTab('governance'),
  },
  {
    element: '[data-tour="admin-feature-flags"]',
    title: '功能开关',
    description: '这里可以控制 AI 反馈、知识图谱推荐等功能是否开放。',
    prepare: switchAdminTab('governance'),
  },
]
