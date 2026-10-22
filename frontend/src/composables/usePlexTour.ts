/**
 * usePlexTour — PLEX 分角色新手引导核心 composable
 */

import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '../stores/theme'
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

let activeDriver: ReturnType<typeof driver> | null = null
let stopFollowing: (() => void) | null = null

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
    /* ignore */
  }
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function cleanupDriverDom() {
  document.querySelectorAll('.driver-overlay, .driver-popover, #driver-dummy-element').forEach((el) => {
    el.remove()
  })
  document.body.classList.remove('driver-active', 'driver-no-scroll')
  document.documentElement.classList.remove('driver-active', 'driver-no-scroll')
}

/** 强制销毁导览，避免遮罩残留阻塞页面点击 */
export function destroyActiveTour() {
  stopFollowing?.()
  stopFollowing = null
  if (activeDriver) {
    try {
      activeDriver.destroy()
    } catch {
      /* ignore */
    }
    activeDriver = null
  }
  cleanupDriverDom()
  document.dispatchEvent(new Event('plex:tour-change'))
}

async function runStepPrepare(
  router: ReturnType<typeof useRouter>,
  step?: TourStepConfig,
) {
  if (!step) return
  if (step.prepareRoute && router.currentRoute.value.path !== step.prepareRoute) {
    await router.push(step.prepareRoute)
    await nextTick()
    await delay(320)
  }
  if (step.prepare) {
    await step.prepare()
    await nextTick()
    await delay(180)
  }
}

export function usePlexTour() {
  const router = useRouter()
  const themeStore = useThemeStore()

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
      /* ignore */
    }
  }

  function finishTour(role: TourRole, instance: ReturnType<typeof driver>) {
    markTourSeen(role)
    try {
      instance.destroy()
    } catch {
      /* ignore */
    }
    activeDriver = null
    cleanupDriverDom()
  }

  async function startTour(role: TourRole): Promise<void> {
    destroyActiveTour()

    const allSteps = TOUR_CONFIGS[role]
    if (!allSteps?.length) return

    const homeRoutes: Record<TourRole, string> = {
      student: '/student',
      teacher: '/teacher',
      admin: '/admin',
    }
    const currentPath = router.currentRoute.value.path
    if (!currentPath.startsWith(homeRoutes[role])) {
      await router.push(homeRoutes[role])
      await nextTick()
      await delay(400)
    }

    await runStepPrepare(router, allSteps[0])

    const validSteps = allSteps
    if (!validSteps.length) {
      markTourSeen(role)
      return
    }

    const total = validSteps.length
    let neverShowHandler: ((e: MouseEvent) => void) | null = null

    try {
      const driverInstance = driver({
        animate: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        showProgress: false,
        allowClose: true,
        overlayOpacity: 0.35,
        stagePadding: 6,
        stageRadius: 8,
        nextBtnText: '下一步',
        prevBtnText: '上一步',
        doneBtnText: '完成',
        popoverClass: role === 'student' && themeStore.isComic ? 'plex-comic-tour' : '',
        showButtons: ['next', 'previous', 'close'],
        onPopoverRender: (popover) => {
          popover.closeButton.setAttribute('aria-label', '关闭导览')
          popover.closeButton.setAttribute('title', '关闭导览')
          if (role === 'student' && themeStore.isComic) {
            const progress = popover.description.querySelector('.driver-step-progress')
            if (progress) popover.title.appendChild(progress)
          }
        },
        steps: validSteps.map((step, idx) => ({
          element: step.element,
          popover: {
            title: step.title,
            description: `
              <span class="driver-step-progress" style="display:block;font-size:0.73rem;color:rgba(170,190,210,0.72);margin-bottom:0.35rem">${idx + 1} / ${total}</span>
              ${step.description}
              ${idx === total - 1
                ? `<div style="margin-top:0.75rem">
                    <button id="plex-tour-never" type="button" style="background:transparent;border:1px solid rgba(170,190,210,0.3);border-radius:6px;color:rgba(170,190,210,0.72);cursor:pointer;font-size:0.75rem;padding:0.25rem 0.65rem">不再提示</button>
                   </div>`
                : ''}
            `,
          },
        })),
        onDestroyed: () => {
          stopFollowing?.()
          stopFollowing = null
          activeDriver = null
          cleanupDriverDom()
          document.dispatchEvent(new Event('plex:tour-change'))
          if (neverShowHandler) {
            document.removeEventListener('click', neverShowHandler)
            neverShowHandler = null
          }
        },
        onCloseClick: (_element, _step, { driver: d }) => {
          if ((window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow) {
            markNeverShow(role)
            delete (window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow
          }
          finishTour(role, d)
        },
        onNextClick: async (_element, _step, { driver: d, state }) => {
          const idx = state.activeIndex ?? 0
          if (idx >= total - 1) {
            if ((window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow) {
              markNeverShow(role)
              delete (window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow
            }
            finishTour(role, d)
          } else {
            await goTo((state.activeIndex ?? 0) + 1)
          }
        },
        onPrevClick: (_element, _step, { state }) => { void goTo(Math.max(0, (state.activeIndex ?? 0) - 1)) },
        onDestroyStarted: () => {
          if ((window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow) {
            markNeverShow(role)
            delete (window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow
          }
        },
      })

      activeDriver = driverInstance
      let moving = false
      let refreshFrame = 0
      const refresh = () => {
        if (!moving && activeDriver === driverInstance && !refreshFrame) {
          refreshFrame = requestAnimationFrame(() => { refreshFrame = 0; driverInstance.refresh() })
        }
      }
      const targetResize = new ResizeObserver(refresh)
      document.addEventListener('scroll', refresh, { passive: true, capture: true })
      window.addEventListener('resize', refresh)
      const removeRouteListener = router.afterEach(() => { if (!moving) destroyActiveTour() })
      stopFollowing = () => {
        targetResize.disconnect(); cancelAnimationFrame(refreshFrame)
        document.removeEventListener('scroll', refresh, true)
        window.removeEventListener('resize', refresh)
        removeRouteListener()
      }
      async function goTo(index: number) {
        if (moving) return
        moving = true
        try {
          await runStepPrepare(router, validSteps[index])
          targetResize.disconnect()
          let target: Element | null = null
          for (let n=0; n<40; n++) {
            if (activeDriver !== driverInstance) return
            target = document.querySelector(validSteps[index]!.element)
            if (target && target.getBoundingClientRect().height > 0 && target.getBoundingClientRect().width > 0) break
            target = null
            await delay(100)
          }
          if (activeDriver !== driverInstance) return
          if (target) {
            target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' })
            await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
            if (activeDriver !== driverInstance) return
            targetResize.observe(target)
          }
          const rect = target?.getBoundingClientRect()
          const side: 'left' | 'right' | 'top' | 'bottom' = !rect ? 'bottom'
            : innerWidth - rect.right >= 350 ? 'right'
            : rect.left >= 350 ? 'left'
            : innerHeight - rect.bottom >= 230 ? 'bottom' : rect.top >= 230 ? 'top' : 'bottom'
          const steps = validSteps.map((step, i) => ({
            element: i === index && !target ? undefined : step.element,
            popover: {side, align: 'start' as const, title: `${i+1} / ${total} · ${step.title}`, description: i === index && !target
              ? '模块尚未加载。<button id="plex-tour-retry" type="button">重试</button>，或点击下一步跳过。'
              : `${step.description}${i === total-1 ? '<p><button id="plex-tour-never" type="button">不再提示</button></p>' : ''}`}
          }))
          // setSteps resets Driver's DOM references; across routes this leaves
          // the old popover behind. Keep state while replacing the step config.
          driverInstance.setConfig({ ...driverInstance.getConfig(), steps })
          driverInstance.drive(index)
          document.dispatchEvent(new Event('plex:tour-change'))
        } finally { moving = false }
      }
      await goTo(0)

      neverShowHandler = (e: MouseEvent) => {
        const target = e.target as HTMLElement
        if (target.id === 'plex-tour-retry') void goTo(driverInstance.getActiveIndex() ?? 0)
        if (target.id === 'plex-tour-never') {
          ;(window as Window & { __plexTourNeverShow?: boolean }).__plexTourNeverShow = true
          markNeverShow(role)
          finishTour(role, driverInstance)
        }
      }
      document.addEventListener('click', neverShowHandler)
    } catch (err) {
      console.warn('[PlexTour] 导览初始化失败，已忽略', err)
      destroyActiveTour()
    }
  }

  return { startTour, resetTour, hasSeenTour, hasNeverShowTour, destroyActiveTour }
}
