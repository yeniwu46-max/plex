<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

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

const DEFAULT_COLORS = ['#22c55e', '#38bdf8', '#a78bfa', '#fb923c']

const option = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(5,14,26,0.92)',
    borderColor: 'rgba(130,212,255,0.2)',
    textStyle: { color: '#e2e8f0', fontSize: 12 },
    axisPointer: { type: 'line', lineStyle: { color: 'rgba(130,212,255,0.2)' } },
  },
  legend: {
    top: 6,
    right: 12,
    textStyle: { color: 'rgba(203,213,225,0.75)', fontSize: 11 },
    icon: 'circle',
    itemWidth: 8,
    itemHeight: 8,
  },
  grid: { top: 40, left: 16, right: 16, bottom: 24, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.xData,
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    axisTick: { show: false },
    axisLabel: { color: 'rgba(203,213,225,0.6)', fontSize: 11 },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    name: props.yName,
    nameTextStyle: { color: 'rgba(203,213,225,0.55)', fontSize: 10 },
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: 'rgba(203,213,225,0.6)', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' } },
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
}))
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
