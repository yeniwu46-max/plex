<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

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

const DEFAULT_COLORS = ['#f97316', '#fb923c', '#fdba74', '#fde68a']

const option = computed(() => {
  const axis = {
    type: 'category' as const,
    data: props.xData,
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    axisTick: { show: false },
    axisLabel: { color: 'rgba(203,213,225,0.65)', fontSize: 11 },
    splitLine: { show: false },
  }
  const valueAxis = {
    type: 'value' as const,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: 'rgba(203,213,225,0.65)', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' as const } },
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(5,14,26,0.92)',
      borderColor: 'rgba(249,115,22,0.3)',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      axisPointer: { type: 'shadow' as const },
    },
    legend: {
      top: 4,
      right: 10,
      textStyle: { color: 'rgba(203,213,225,0.75)', fontSize: 11 },
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 6,
    },
    grid: { top: 36, left: 12, right: 12, bottom: 16, containLabel: true },
    xAxis: props.horizontal ? valueAxis : axis,
    yAxis: props.horizontal ? axis : valueAxis,
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
