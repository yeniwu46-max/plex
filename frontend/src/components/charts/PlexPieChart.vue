<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '../../stores/theme'
import { getEchartsTokens, buildTooltip, buildLegend } from '../../theme/echartsTheme'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    data: Array<{ name: string; value: number; color?: string }>
    title?: string
    donut?: boolean
  }>(),
  {
    title: '',
    donut: true,
  },
)

const themeStore = useThemeStore()
const DEFAULT_COLORS = ['#38bdf8', '#818cf8', '#a78bfa', '#c084fc', '#fb923c', '#34d399']

const option = computed(() => {
  const tk = getEchartsTokens(themeStore.resolvedTheme)
  const borderColor = themeStore.isDark ? 'rgba(5,14,26,0.9)' : 'rgba(255,255,255,0.9)'

  return {
    backgroundColor: tk.backgroundColor,
    tooltip: {
      trigger: 'item' as const,
      ...buildTooltip(tk, {
        borderColor: 'rgba(129,140,248,0.3)',
        formatter: '{b}: {c} ({d}%)',
      }),
    },
    legend: {
      orient: 'vertical' as const,
      right: 8,
      top: 'center',
      itemGap: 10,
      ...buildLegend(tk),
    },
    series: [
      {
        type: 'pie',
        radius: props.donut ? ['45%', '72%'] : ['0%', '72%'],
        center: ['40%', '50%'],
        data: props.data.map((item, i) => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: item.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length],
            borderWidth: 2,
            borderColor,
          },
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 12,
            shadowColor: 'rgba(0,0,0,0.4)',
          },
        },
        label: { show: false },
        labelLine: { show: false },
      },
    ],
  }
})
</script>

<template>
  <v-chart class="plex-pie-chart" :option="option" autoresize />
</template>

<style scoped>
.plex-pie-chart {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
