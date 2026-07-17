import type { Router } from 'vue-router'
import { nextTick } from 'vue'

export async function scrollToHashAnchor(hash: string, behavior: ScrollBehavior = 'smooth') {
  const id = hash.replace(/^#/, '').trim()
  if (!id) return
  await nextTick()
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ behavior, block: 'start' })
  })
}

export async function navigateAndScroll(
  router: Router,
  target: string | { path: string; hash?: string; query?: Record<string, string> },
) {
  if (typeof target === 'string') {
    const [path, hash = ''] = target.split('#')
    await router.push(hash ? { path, hash: `#${hash}` } : path)
    if (hash) await scrollToHashAnchor(`#${hash}`)
    return
  }
  await router.push(target)
  if (target.hash) await scrollToHashAnchor(target.hash)
}
