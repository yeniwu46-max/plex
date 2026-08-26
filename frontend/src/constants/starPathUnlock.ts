/** 星轨 / 试炼解锁阈值（前后端需保持一致，变更时请同步 backend） */

/**
 * 全解锁开关：任何星域、知识点、试炼都可直接进入，不再校验前置。
 * 与 backend/app/constants/star_path_unlock.py 的 UNLOCK_ALL 保持一致，两边必须同时改。
 * 下面的阈值常量在开关关闭后仍然有效，故一并保留。
 */
export const UNLOCK_ALL = true

/** 知识点掌握判定：mastery_score >= 此值视为 done（原 0.8） */
export const MASTERY_THRESHOLD = 0.4

/** 星域解锁：前一域 progress >= 此百分比（原 85） */
export const DOMAIN_UNLOCK_PROGRESS = 40

/** 星域「已点亮」判定 progress >= 此百分比（原 85） */
export const DOMAIN_COMPLETE_PROGRESS = 60

/** 星轨节点解锁：前一节点至少 AC 题数（原需整节点掌握 80%） */
export const NODE_UNLOCK_MIN_AC = 1

/** 试炼场模式 requiredLevel（原 star-arena:5, echo-run:3, abyss:20） */
export const TRIAL_ARENA_LEVELS = {
  aiDuel: 1,
  starArena: 2,
  echoRun: 1,
  abyss: 5,
} as const
