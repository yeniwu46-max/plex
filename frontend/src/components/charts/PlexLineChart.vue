<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '../../stores/theme'
import { getEchartsTokens, buildCategoryAxis, buildValueAxis, buildTooltip, buildLegend } from '../../theme/echartsTheme'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const props = withDefaults(
  defineProps<{
    xData: string[]
    series: Array<{ name: string; data: number[]; color?: string }>
    title?: string
    yName?: string
  }>(),
  {
    title: '',
    yName: '',
  },
)

const themeStore = useThemeStore()
const DEFAULT_COLORS = ['#22c55e', '#38bdf8', '#a78bfa', '#fb923c']

const option = computed(() => {
  const tk = getEchartsTokens(themeStore.resolvedTheme)
  return {
    backgroundColor: tk.backgroundColor,
    tooltip: {
      trigger: 'axis',
      ...buildTooltip(tk, { axisPointer: { type: 'line', lineStyle: { color: tk.tooltipBorderColor } } }),
    },
    legend: {
      top: 6,
      right: 12,
      ...buildLegend(tk),
    },
    grid: { top: 40, left: 16, right: 16, bottom: 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: props.xData,
      ...buildCategoryAxis(tk),
    },
    yAxis: {
      type: 'value',
      name: props.yName,
      nameTextStyle: { color: tk.axisColor, fontSize: 10 },
      ...buildValueAxis(tk),
    },
    series: props.series.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: { color: s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length], width: 2.5 },
      itemStyle: { color: s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length] },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: (s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]) + '33' },
            { offset: 1, color: (s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]) + '05' },
          ],
        },
      },
    })),
  }
})
</script>

<template>
  <v-chart class="plex-line-chart" :option="option" autoresize />
</template>

<style scoped>
.plex-line-chart {
  width: 100%;
  height: 100%;
  min-height: 220px;
}
</style>
