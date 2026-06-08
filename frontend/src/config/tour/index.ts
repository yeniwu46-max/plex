/**
 * PLEX 分角色新手引导 — 配置入口
 *
 * 功能说明（答辩用）：
 * PLEX 引入分角色新手引导机制，根据学生、教师、管理员三类用户的使用场景，提供渐进式功能导览。
 * 该功能基于 Driver.js 实现，在不改变原有 UI 架构的前提下，通过高亮关键模块和上下文说明，
 * 帮助用户快速理解学习路径、代码练习、AI 助手、班级分析、智能体编排和系统观测等核心功能，
 * 降低系统学习成本，也提升答辩演示时的可理解性。
 */

export { studentTour } from './studentTour'
export { teacherTour } from './teacherTour'
export { adminTour } from './adminTour'
export type { TourStepConfig } from './types'
