<script setup lang="ts">
/**
 * PlexGuideTour — 分角色新手引导挂载组件
 * 放置在 App.vue 或各端布局中，按 role + autoStart 决定是否自动启动导览
 */
import { onMounted, onBeforeUnmount } from 'vue'
import { usePlexTour, type TourRole } from '../../composables/usePlexTour'

const props = withDefaults(
  defineProps<{
    role: TourRole
    autoStart?: boolean
  }>(),
  { autoStart: true },
)

const { startTour, resetTour, hasSeenTour, hasNeverShowTour } = usePlexTour()

async function restartTour() {
  resetTour(props.role)
  await startTour(props.role)
}

defineExpose({ restartTour })

onMounted(async () => {
  if (!props.autoStart) return
  if (hasSeenTour(props.role)) return
  if (hasNeverShowTour(props.role)) return
  // 延迟 650ms 等页面布局与数据加载稳定
  await new Promise((r) => setTimeout(r, 650))
  await startTour(props.role)
})

onBeforeUnmount(() => {
  // 路由切换时不强制销毁，让 driver 自然完成
})
</script>

<template>
  <!-- 纯逻辑组件，无 DOM 输出 -->
</template>
