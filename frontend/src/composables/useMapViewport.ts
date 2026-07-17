import { computed, onBeforeUnmount, ref, type Ref } from 'vue'

const MIN_SCALE = 0.55
const MAX_SCALE = 2.4

export function useMapViewport(containerRef: Ref<HTMLElement | null>) {
  const scale = ref(1)
  const panX = ref(0)
  const panY = ref(0)
  const isDragging = ref(false)

  let dragStartX = 0
  let dragStartY = 0
  let panStartX = 0
  let panStartY = 0

  const transformStyle = computed(() => ({
    transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
  }))

  function clampScale(value: number) {
    return Math.min(MAX_SCALE, Math.max(MIN_SCALE, value))
  }

  function onWheel(event: WheelEvent) {
    const delta = event.deltaY > 0 ? -0.08 : 0.08
    const next = clampScale(scale.value + delta)
    const container = containerRef.value
    if (!container) {
      scale.value = next
      return
    }
    const rect = container.getBoundingClientRect()
    const offsetX = event.clientX - rect.left - rect.width / 2
    const offsetY = event.clientY - rect.top - rect.height / 2
    const ratio = next / scale.value
    panX.value = offsetX - (offsetX - panX.value) * ratio
    panY.value = offsetY - (offsetY - panY.value) * ratio
    scale.value = next
  }

  function onPointerDown(event: PointerEvent) {
    if (event.button !== 0) return
    isDragging.value = true
    dragStartX = event.clientX
    dragStartY = event.clientY
    panStartX = panX.value
    panStartY = panY.value
    containerRef.value?.setPointerCapture(event.pointerId)
  }

  function onPointerMove(event: PointerEvent) {
    if (!isDragging.value) return
    panX.value = panStartX + (event.clientX - dragStartX)
    panY.value = panStartY + (event.clientY - dragStartY)
  }

  function onPointerUp(event: PointerEvent) {
    if (!isDragging.value) return
    isDragging.value = false
    containerRef.value?.releasePointerCapture(event.pointerId)
  }

  function resetView() {
    scale.value = 1
    panX.value = 0
    panY.value = 0
  }

  function fitView() {
    scale.value = 0.82
    panX.value = 0
    panY.value = 0
  }

  onBeforeUnmount(() => {
    isDragging.value = false
  })

  return {
    scale,
    panX,
    panY,
    isDragging,
    transformStyle,
    onWheel,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    resetView,
    fitView,
  }
}
