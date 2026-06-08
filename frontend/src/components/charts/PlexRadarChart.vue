<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, RadarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '../../stores/theme'
import { getEchartsTokens, buildTooltip } from '../../theme/echartsTheme'

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

const themeStore = useThemeStore()

const option = computed(() => {
  const tk = getEchartsTokens(themeStore.resolvedTheme)
  const splitLineOpacity = themeStore.isDark ? 0.06 : 0.12
  const splitAreaOpacity1 = themeStore.isDark ? 0.02 : 0.03
  const splitAreaOpacity2 = themeStore.isDark ? 0.01 : 0.015
  const axisLineOpacity = themeStore.isDark ? 0.1 : 0.15

  return {
    backgroundColor: tk.backgroundColor,
    tooltip: {
      trigger: 'item',
      ...buildTooltip(tk, { borderColor: props.color + '44' }),
    },
    radar: {
      indicator: props.dimensions.map((name) => ({ name, max: props.maxValue })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: tk.legendTextColor,
        fontSize: 12,
      },
      splitLine: {
        lineStyle: { color: `rgba(${themeStore.isDark ? '255,255,255' : '0,0,0'}, ${splitLineOpacity})` },
      },
      splitArea: {
        areaStyle: {
          color: [
            `rgba(${themeStore.isDark ? '255,255,255' : '0,0,0'}, ${splitAreaOpacity1})`,
            `rgba(${themeStore.isDark ? '255,255,255' : '0,0,0'}, ${splitAreaOpacity2})`,
          ],
        },
      },
      axisLine: {
        lineStyle: { color: `rgba(${themeStore.isDark ? '255,255,255' : '0,0,0'}, ${axisLineOpacity})` },
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
                x: 0.5, y: 0.5, r: 0.5,
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
  }
})
</script>

<template>
  <v-chart class="plex-radar-chart" :option="option" autoresize />
</template>

<style scoped>
.plex-radar-chart {
  width: 100%;
  height: 100%;
  min-height: 220px;
}
</style>
