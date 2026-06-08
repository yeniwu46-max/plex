/**
 * usePlexTour — PLEX 分角色新手引导核心 composable
 *
 * API:
 *   startTour(role)     启动指定角色的导览
 *   resetTour(role)     重置该角色的完成状态
 *   hasSeenTour(role)   查询该角色是否已看过导览
 */

import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { studentTour, teacherTour, adminTour } from '../config/tour'
import type { TourStepConfig } from '../config/tour'

export type TourRole = 'student' | 'teacher' | 'admin'

const LS_KEYS: Record<TourRole, string> = {
  student: 'plex_tour_seen_student',
  teacher: 'plex_tour_seen_teacher',
  admin: 'plex_tour_seen_admin',
}

const TOUR_CONFIGS: Record<TourRole, TourStepConfig[]> = {
  student: studentTour,
  teacher: teacherTour,
  admin: adminTour,
}

// 安全 localStorage
function lsGet(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function lsSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // 忽略：不可用时导览状态不持久化，但不影响功能
  }
}

// 单例导览实例（避免重复创建）
let activeDriver: ReturnType<typeof driver> | null = null

export function usePlexTour() {
  const router = useRouter()

  function hasSeenTour(role: TourRole): boolean {
    return lsGet(LS_KEYS[role]) === 'true'
  }

  function hasNeverShowTour(role: TourRole): boolean {
    return lsGet(LS_KEYS[role] + '_never') === 'true'
  }

  function markTourSeen(role: TourRole): void {
    lsSet(LS_KEYS[role], 'true')
  }

  function markNeverShow(role: TourRole): void {
    lsSet(LS_KEYS[role], 'true')
    lsSet(LS_KEYS[role] + '_never', 'true')
  }

  function resetTour(role: TourRole): void {
    try {
      localStorage.removeItem(LS_KEYS[role])
      localStorage.removeItem(LS_KEYS[role] + '_never')
    } catch {
      // ignore
    }
  }

  /** 过滤掉当前 DOM 中不存在的步骤，避免报错 */
  function filterExistingSteps(steps: TourStepConfig[]): TourStepConfig[] {
    return steps.filter((step) => {
      const el = document.querySelector(step.element)
      if (!el) {
        console.warn(`[PlexTour] 导览目标元素不存在，已跳过：${step.element}`)
        return false
      }
      return true
    })
  }

  async function startTour(role: TourRole): Promise<void> {
    // 已销毁旧实例
    if (activeDriver) {
      try { activeDriver.destroy() } catch { /* ignore */ }
      activeDriver = null
    }

    const allSteps = TOUR_CONFIGS[role]
    if (!allSteps?.length) return

    // 跳转到该角色的首页（若当前路由不符）
    const homeRoutes: Record<TourRole, string> = {
      student: '/student',
      teacher: '/teacher',
      admin: '/admin',
    }
    const currentPath = router.currentRoute.value.path
    if (!currentPath.startsWith(homeRoutes[role])) {
      await router.push(homeRoutes[role])
      await nextTick()
      await new Promise((r) => setTimeout(r, 400))
    }

    // 逐步处理 prepare（按需跳转/切 tab），再收集最终存在的 steps
    // 为了让 driver.js 的 onHighlightStarted 中切 tab 后再 highlight，
    // 我们把 prepare 封装到 driver 的 onHighlightStarted 回调里
    const total = allSteps.length
    let currentStepIndex = 0

    try {
      const driverInstance = driver({
        animate: true,
        showProgress: false,
        allowClose: true,
        overlayOpacity: 0.72,
        stagePadding: 6,
        stageRadius: 8,
        nextBtnText: '下一步',
        prevBtnText: '上一步',
        doneBtnText: '完成',
        // 关闭按钮显示
        showButtons: ['next', 'previous', 'close'],
        steps: allSteps.map((step, idx) => ({
          element: step.element,
          popover: {
            title: step.title,
            description: `
              <span class="driver-step-progress" style="display:block;font-size:0.73rem;color:rgba(170,190,210,0.72);margin-bottom:0.35rem">${idx + 1} / ${total}</span>
              ${step.description}
              ${idx === total - 1
                ? `<div style="margin-top:0.75rem">
                    <button id="plex-tour-never" style="background:transparent;border:1px solid rgba(170,190,210,0.3);border-radius:6px;color:rgba(170,190,210,0.72);cursor:pointer;font-size:0.75rem;padding:0.25rem 0.65rem">不再提示</button>
                   </div>`
                : ''}
            `,
          },
        })),
        onHighlightStarted: async (_element, _step, options) => {
          currentStepIndex = options.state.activeIndex ?? 0
          const config = allSteps[currentStepIndex]
          if (config?.prepare) {
            try {
              await config.prepare()
            } catch (e) {
              console.warn('[PlexTour] prepare 执行失败', e)
            }
          }
        },
        onDestroyed: () => {
          markTourSeen(role)
          activeDriver = null
        },
        onCloseClick: () => {
          markTourSeen(role)
        },
        onDestroyStarted: () => {
          // 检查「不再提示」按钮是否曾被点击（通过 data 属性标记）
          if ((window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow) {
            markNeverShow(role)
            delete (window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow
          }
        },
      })

      activeDriver = driverInstance

      // 先执行第一步的 prepare
      const firstConfig = allSteps[0]
      if (firstConfig?.prepare) {
        try {
          await firstConfig.prepare()
          await nextTick()
          await new Promise((r) => setTimeout(r, 200))
        } catch (e) {
          console.warn('[PlexTour] 第一步 prepare 失败', e)
        }
      }

      // 过滤当前存在的步骤（prepare 执行后再检查 DOM）
      const validSteps = filterExistingSteps(allSteps)
      if (!validSteps.length) {
        console.warn('[PlexTour] 无可用导览步骤，已跳过')
        markTourSeen(role)
        return
      }

      driverInstance.drive()

      // 绑定「不再提示」按钮事件（使用事件委托）
      document.addEventListener('click', function neverShowHandler(e: MouseEvent) {
        const target = e.target as HTMLElement
        if (target.id === 'plex-tour-never') {
          ;(window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow = true
          markNeverShow(role)
          try { driverInstance.destroy() } catch { /* ignore */ }
          document.removeEventListener('click', neverShowHandler)
        }
        // 自动清理：导览结束后移除
        if (!activeDriver) {
          document.removeEventListener('click', neverShowHandler)
        }
      })
    } catch (err) {
      console.warn('[PlexTour] 导览初始化失败，已忽略', err)
      markTourSeen(role)
    }
  }

  return { startTour, resetTour, hasSeenTour, hasNeverShowTour }
}
