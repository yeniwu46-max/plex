/**
 * 导览步骤配置类型
 */
export interface TourStepConfig {
  /** CSS 选择器，建议用 [data-tour="xxx"] */
  element: string
  title: string
  description: string
  /** 进入该步骤前先跳转的路由（相对路径） */
  prepareRoute?: string
  /** 进入该步骤前执行（切换 tab、等待渲染等） */
  prepare?: () => Promise<void>
}
