<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { CloseOutline } from '@vicons/ionicons5'
import { NIcon } from 'naive-ui'
import { attachMermaidControls, mermaidDiagramToolbarHtml } from '../../utils/mermaidDiagramControls'

const props = defineProps<{
  show: boolean
  svgHtml: string
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const bodyRef = ref<HTMLElement | null>(null)
let detachControls: (() => void) | null = null

function close() {
  emit('update:show', false)
}

function onBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) close()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

async function mountDiagram() {
  detachControls?.()
  detachControls = null
  if (!props.show || !props.svgHtml) return
  await nextTick()
  if (!bodyRef.value) await nextTick()
  if (!bodyRef.value) return
  bodyRef.value.innerHTML = `
    ${mermaidDiagramToolbarHtml(false)}
    <div class="mermaid-viewport" tabindex="0">
      <div class="mermaid-canvas">${props.svgHtml}</div>
    </div>
  `
  await nextTick()
  requestAnimationFrame(() => {
    if (!bodyRef.value || !props.show) return
    detachControls = attachMermaidControls(bodyRef.value, { enablePan: true, fitOnMount: true })
  })
}

watch(
  () => [props.show, props.svgHtml] as const,
  () => {
    void mountDiagram()
  },
  { immediate: true, flush: 'post' },
)

onBeforeUnmount(() => {
  detachControls?.()
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="mermaid-diagram-modal"
      role="dialog"
      aria-modal="true"
      aria-label="知识图全屏查看"
      @click="onBackdropClick"
      @keydown="onKeydown"
    >
      <div class="mermaid-diagram-modal__panel">
        <header class="mermaid-diagram-modal__head">
          <h3>知识图</h3>
          <button type="button" class="mermaid-diagram-modal__close" aria-label="关闭" @click="close">
            <n-icon :component="CloseOutline" />
          </button>
        </header>
        <div
          ref="bodyRef"
          class="mermaid-diagram-modal__diagram mermaid-diagram"
          role="group"
          aria-label="知识图，可缩放与平移"
        />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.mermaid-diagram-modal {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: grid;
  place-items: center;
  padding: 1.25rem;
  background: rgba(2, 8, 16, 0.72);
  backdrop-filter: blur(10px);
}

.mermaid-diagram-modal__panel {
  display: flex;
  flex-direction: column;
  width: min(960px, 96vw);
  min-height: min(72vh, 680px);
  max-height: min(88vh, 820px);
  border-radius: 16px;
  border: 1px solid rgba(110, 228, 255, 0.22);
  background:
    linear-gradient(145deg, rgba(37, 245, 238, 0.06), transparent 42%),
    rgba(4, 18, 28, 0.92);
  box-shadow:
    0 24px 64px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.mermaid-diagram-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(110, 228, 255, 0.12);
}

.mermaid-diagram-modal__head h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
  color: rgba(235, 247, 255, 0.95);
  letter-spacing: 0.04em;
}

.mermaid-diagram-modal__close {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border: 1px solid rgba(110, 228, 255, 0.25);
  border-radius: 8px;
  background: rgba(8, 32, 48, 0.85);
  color: #d9f6ff;
  cursor: pointer;
}

.mermaid-diagram-modal__close:hover {
  border-color: rgba(37, 245, 238, 0.5);
}

.mermaid-diagram-modal__diagram {
  flex: 1 1 auto;
  min-height: min(60vh, 560px);
  margin: 0;
  padding: 0.65rem 0.85rem 0.85rem;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-viewport) {
  max-height: min(72vh, 640px);
  min-height: 320px;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-toolbar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.45rem;
  flex-wrap: wrap;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-toolbar__hint) {
  font-size: 0.75rem;
  color: rgba(180, 220, 235, 0.62);
}

.mermaid-diagram-modal__diagram :deep(.mermaid-toolbar__actions) {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-zoom-btn) {
  min-width: 1.85rem;
  height: 1.85rem;
  padding: 0 0.4rem;
  border-radius: 6px;
  border: 1px solid rgba(110, 228, 255, 0.28);
  background: rgba(8, 36, 48, 0.9);
  color: #d9f6ff;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-zoom-btn--text) {
  font-size: 0.78rem;
  min-width: auto;
  padding: 0 0.55rem;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-zoom-label) {
  min-width: 2.6rem;
  text-align: center;
  font-size: 0.78rem;
  color: rgba(210, 240, 250, 0.85);
}

.mermaid-diagram-modal__diagram :deep(.mermaid-viewport) {
  overflow: auto;
  border-radius: 10px;
  background: rgba(2, 12, 20, 0.55);
  outline: none;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-canvas) {
  display: inline-block;
  min-width: 100%;
  transform-origin: top left;
}

.mermaid-diagram-modal__diagram :deep(.mermaid-canvas svg) {
  display: block;
  margin: 0 auto;
}
</style>
