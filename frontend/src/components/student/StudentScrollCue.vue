<script setup lang="ts">
import { onMounted, onBeforeUnmount, onActivated, onDeactivated, ref } from 'vue'
// The shell instance also covers teleported student reading dialogs.
const cues = ref<Array<{ id: number; element: HTMLElement; left: number; top: number; z: number }>>([])
const ids = new WeakMap<HTMLElement, number>()
let serial = 0, frame = 0, attached = false
let resize: ResizeObserver | undefined, mutations: MutationObserver | undefined
const observed = new Set<Element>()
const areas = '.main-body,.student-trial,.resource-page,.chat-thread,.messenger-stage,.class-arena,.class-arena__top5,.knowledge-map,.content-rendered,.content-markdown,.content-raw,.resource-list,.resource-stat-modal__body,.trash-list,.plex-reading-modal>.n-card-content,.resource-material-modal>.n-card-content,.resource-detail,.n-drawer-body-content-wrapper,[data-student-scroll]'
function visible(el: HTMLElement) {
  const r = el.getBoundingClientRect(), s = getComputedStyle(el)
  return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'
}
function layer(el: HTMLElement) { return Number(getComputedStyle(el.closest('.n-modal-container') || el).zIndex) || 2000 }
function update() {
  frame = 0
  if (!attached || document.body.classList.contains('driver-active')) { cues.value = []; return }
  const overlays = [...document.querySelectorAll<HTMLElement>('.n-modal-body-wrapper,.n-drawer,[aria-modal="true"]')].filter(visible)
  overlays.sort((a,b) => layer(a) - layer(b))
  const overlay = overlays.at(-1)
  const root = overlay || document.querySelector<HTMLElement>('.main-body')
  if (!root) { cues.value = []; return }
  const candidates = [root,...root.querySelectorAll<HTMLElement>(areas)].filter(el => visible(el) && /(auto|scroll)/.test(getComputedStyle(el).overflowY) && el.scrollHeight - el.clientHeight > 24)
  for (const el of [...observed]) if (!candidates.includes(el as HTMLElement)) { resize?.unobserve(el); observed.delete(el) }
  const next: typeof cues.value = []
  for (const el of candidates) {
    if (!observed.has(el)) { observed.add(el); resize?.observe(el) }
    if (!el.hasAttribute('tabindex')) el.tabIndex = 0
    if (el.scrollHeight - el.clientHeight - el.scrollTop <= 24) continue
    if (candidates.some(child => child !== el && el.contains(child))) continue
    const r = el.getBoundingClientRect()
    let left = Math.max(r.left, 0), right = Math.min(r.right, innerWidth)
    let top = Math.max(r.top, 0), bottom = Math.min(r.bottom, innerHeight)
    for (let parent = el.parentElement; parent; parent = parent.parentElement) {
      if (/(auto|scroll|hidden|clip)/.test(getComputedStyle(parent).overflowY + getComputedStyle(parent).overflowX)) {
        const rect = parent.getBoundingClientRect()
        left = Math.max(left, rect.left); right = Math.min(right, rect.right)
        top = Math.max(top, rect.top); bottom = Math.min(bottom, rect.bottom)
      }
    }
    if (right - left < 180 || bottom - top < 120) continue
    if (!ids.has(el)) ids.set(el, ++serial)
    next.push({ id: ids.get(el)!, element: el, left: (left + right) / 2, top: bottom - 44, z: overlay ? layer(overlay) + 1 : 25 })
  }
  cues.value = next
}
function schedule() { if (attached && !frame) frame = requestAnimationFrame(update) }
function advance(el: HTMLElement) { el.scrollBy({ top: el.clientHeight * .7, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }) }
function detach() {
  attached = false; cancelAnimationFrame(frame); frame = 0; cues.value = []
  document.removeEventListener('scroll', schedule, true); window.removeEventListener('resize', schedule)
  document.removeEventListener('transitionend', schedule); document.removeEventListener('plex:tour-change', schedule)
  resize?.disconnect(); mutations?.disconnect(); observed.clear()
}
function attach() {
  if (attached) return
  attached = true
  resize = new ResizeObserver(schedule)
  mutations = new MutationObserver(records => {
    if (records.some(record => !(record.target as Element).closest?.('.scroll-cue'))) schedule()
  })
  mutations.observe(document.body, { childList: true, subtree: true, characterData: true })
  document.addEventListener('scroll', schedule, { passive: true, capture: true })
  document.addEventListener('transitionend', schedule); document.addEventListener('plex:tour-change', schedule)
  window.addEventListener('resize', schedule); schedule()
}
onMounted(attach); onActivated(attach); onDeactivated(detach); onBeforeUnmount(detach)
</script>
<template><Teleport to="body"><div v-for="cue in cues" :key="cue.id" class="scroll-cue" :style="{left:`${cue.left}px`,top:`${cue.top}px`,zIndex:cue.z}"><button type="button" aria-label="继续向下浏览当前内容" @click="advance(cue.element)">继续浏览 <span aria-hidden="true">⌄</span></button></div></Teleport></template>
<style scoped>
.scroll-cue{position:fixed;transform:translateX(-50%);pointer-events:none;padding:4px 14px;background:radial-gradient(ellipse at bottom,var(--plex-bg-base,#10202e),transparent 72%)}
button{pointer-events:auto;border:1px solid var(--plex-border,#45b8b3);border-radius:24px;background:var(--plex-bg-card,#142c3c);color:var(--plex-text,#eef7ff);padding:6px 14px;cursor:pointer;box-shadow:0 3px 15px #0002;animation:cue-arrive .6s ease-out;font-size:12px}
button:focus-visible{outline:2px solid var(--plex-primary,#55eee9);outline-offset:3px}span{margin-left:8px}
:global(html[data-plex-style='comic'][data-plex-persona='student'] .scroll-cue button){border-width:2px;border-radius:10px;box-shadow:2px 2px 0 var(--comic-ink)}
@keyframes cue-arrive{from{translate:0 -5px;opacity:0}to{translate:0 0;opacity:1}}@media(prefers-reduced-motion:reduce){button{animation:none}}
</style>
