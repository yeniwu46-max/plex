<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '../../stores/theme'
import { getEchartsTokens, buildCategoryAxis, buildValueAxis, buildTooltip, buildLegend } from '../../theme/echartsTheme'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    xData: string[]
    series: Array<{ name: string; data: number[]; color?: string }>
    horizontal?: boolean
    barMaxWidth?: number
  }>(),
  {
    horizontal: false,
    barMaxWidth: 32,
  },
)

const themeStore = useThemeStore()
const DEFAULT_COLORS = ['#f97316', '#fb923c', '#fdba74', '#fde68a']

const option = computed(() => {
  const tk = getEchartsTokens(themeStore.resolvedTheme)
  const catAxis = { type: 'category' as const, data: props.xData, ...buildCategoryAxis(tk) }
  const valAxis = { type: 'value' as const, ...buildValueAxis(tk) }

  return {
    backgroundColor: tk.backgroundColor,
    tooltip: {
      trigger: 'axis' as const,
      ...buildTooltip(tk, { axisPointer: { type: 'shadow' as const } }),
    },
    legend: {
      top: 4,
      right: 10,
      ...buildLegend(tk, { icon: 'roundRect', itemWidth: 10, itemHeight: 6 }),
    },
    grid: { top: 36, left: 12, right: 12, bottom: 16, containLabel: true },
    xAxis: props.horizontal ? valAxis : catAxis,
    yAxis: props.horizontal ? catAxis : valAxis,
    series: props.series.map((s, i) => {
      const color = s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]
      return {
        name: s.name,
        type: 'bar',
        data: s.data,
        barMaxWidth: props.barMaxWidth,
        barBorderRadius: [4, 4, 0, 0],
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color },
              { offset: 1, color: color + '88' },
            ],
          },
          borderRadius: props.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
        },
      }
    }),
  }
})
</script>

<template>
  <v-chart class="plex-bar-chart" :option="option" autoresize />
</template>

<style scoped>
.plex-bar-chart {
  width: 100%;
  height: 100%;
  min-height: 220px;
}
</style>
