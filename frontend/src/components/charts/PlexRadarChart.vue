<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, RadarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, RadarChart, TooltipComponent, LegendComponent, RadarComponent])

const props = withDefaults(
  defineProps<{
    dimensions: string[]
    values: number[]
    maxValue?: number
    title?: string
    color?: string
  }>(),
  {
    maxValue: 100,
    title: '能力雷达',
    color: '#22c55e',
  },
)

const option = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(5,14,26,0.92)',
    borderColor: props.color + '44',
    textStyle: { color: '#e2e8f0', fontSize: 12 },
  },
  radar: {
    indicator: props.dimensions.map((name) => ({ name, max: props.maxValue })),
    shape: 'polygon',
    splitNumber: 4,
    axisName: {
      color: 'rgba(203,213,225,0.75)',
      fontSize: 12,
    },
    splitLine: {
      lineStyle: { color: 'rgba(255,255,255,0.06)' },
    },
    splitArea: {
      areaStyle: {
        color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.01)'],
      },
    },
    axisLine: {
      lineStyle: { color: 'rgba(255,255,255,0.1)' },
    },
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: props.values,
          name: props.title,
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { color: props.color, width: 2 },
          itemStyle: { color: props.color },
          areaStyle: {
            color: {
              type: 'radial',
              x: 0.5,
              y: 0.5,
              r: 0.5,
              colorStops: [
                { offset: 0, color: props.color + '55' },
                { offset: 1, color: props.color + '11' },
              ],
            },
          },
        },
      ],
    },
  ],
}))
</script>

<template>
  <v-chart class="plex-radar-chart" :option="option" autoresize />
</template>

<style scoped>
.plex-radar-chart {
  width: 100%;
  height: 100%;
  min-height: 260px;
}
</style>
