import type { TourStepConfig } from './types'

/**
 * 管理员端导览步骤
 * 全部在 /admin 页面内，通过 prepare 切换 activeNav tab
 */

type AdminNavKey = 'nexus' | 'agents' | 'observer' | 'governance'

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
    element: '[data-tour="admin-nexus-metrics"]',
    title: '核心指标概览',
    description:
      '「中央总控」页顶部的指标卡片展示活跃学习者、注册教师、运行试炼与系统健康度，帮助您快速掌握平台整体运行状态。',
    prepare: switchAdminTab('nexus'),
  },
  {
    element: '[data-tour="admin-notifications"]',
    title: '通知中心',
    description:
      '点击右上角通知图标查看待处理事项（如班级变更审批），点击通知可跳转到对应管理模块。',
    prepare: switchAdminTab('nexus'),
  },
  {
    element: '[data-tour="admin-agent-flow"]',
    title: '智能体编排',
    description:
      '在「智能体编排」中勾选检查智能体与学习流水线节点，保存后平台将按配置自动协同批改与学情分析。',
    prepare: switchAdminTab('agents'),
  },
  {
    element: '[data-tour="admin-trial-observatory"]',
    title: '试炼数据观测',
    description:
      '在「系统观测」中查看全校试炼发布、参与进度与题目正确率，可按班级筛选并钻取单场试炼详情。',
    prepare: switchAdminTab('observer'),
  },
  {
    element: '[data-tour="admin-system-monitor"]',
    title: '平台波动监测',
    description:
      '观测页下方展示近 7 日活跃度/健康度趋势与各端模块运行状态，便于发现异常波动。',
    prepare: switchAdminTab('observer'),
  },
  {
    element: '[data-tour="admin-permission-control"]',
    title: '系统公告',
    description:
      '在「权限与控制」发布面向教师、学生或全体用户的系统公告，登录后可在各端顶栏收到通知。',
    prepare: switchAdminTab('governance'),
  },
  {
    element: '[data-tour="admin-feature-flags"]',
    title: '系统设置',
    description:
      '配置试炼规则、AI 策略开关与通知偏好，保存后立即生效于全平台。',
    prepare: switchAdminTab('governance'),
  },
  {
    element: '[data-tour="admin-class-approval"]',
    title: '班级变更审批',
    description:
      '处理教师提交的新建/删除班级申请，审批通过后系统自动执行变更。',
    prepare: switchAdminTab('governance'),
  },
]
