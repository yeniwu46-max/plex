/**
 * 导览步骤配置类型
 */
export interface TourStepConfig {
  /** CSS 选择器，建议用 [data-tour="xxx"] */
  element: string
  title: string
  description: string
  /** 进入该步骤前执行（跳转路由、切换 tab 等） */
  prepare?: () => Promise<void>
}
