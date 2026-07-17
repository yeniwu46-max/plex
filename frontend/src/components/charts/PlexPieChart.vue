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
    sciFi?: boolean
  }>(),
  {
    title: '',
    donut: true,
    sciFi: false,
  },
)

const themeStore = useThemeStore()
const DEFAULT_COLORS = ['#38bdf8', '#818cf8', '#a78bfa', '#c084fc', '#fb923c', '#34d399']
const SCI_FI_COLORS = ['#34e6c5', '#818cf8', '#7bf8ff', '#c084fc', '#fb923c', '#34d399']

const totalValue = computed(() => props.data.reduce((sum, item) => sum + item.value, 0))

const option = computed(() => {
  const tk = getEchartsTokens(themeStore.resolvedTheme)
  const borderColor = themeStore.isDark ? 'rgba(5,14,26,0.9)' : 'rgba(255,255,255,0.9)'
  const palette = props.sciFi ? SCI_FI_COLORS : DEFAULT_COLORS
  const glowColor = props.sciFi ? 'rgba(52,230,197,0.45)' : 'rgba(0,0,0,0.4)'

  return {
    backgroundColor: tk.backgroundColor,
    tooltip: {
      trigger: 'item' as const,
      ...buildTooltip(tk, {
        borderColor: props.sciFi ? 'rgba(52,230,197,0.35)' : 'rgba(129,140,248,0.3)',
        formatter: '{b}: {c} ({d}%)',
      }),
    },
    legend: {
      orient: 'vertical' as const,
      right: 8,
      top: 'center',
      itemGap: 10,
      ...buildLegend(tk, props.sciFi ? { textStyle: { color: 'rgba(214,230,244,0.82)', fontSize: 12 } } : {}),
    },
    graphic: props.sciFi && props.donut
      ? [
          {
            type: 'text',
            left: '34%',
            top: '44%',
            style: {
              text: String(totalValue.value),
              fill: '#edf8fb',
              font: '700 22px JetBrains Mono, Consolas, monospace',
              textAlign: 'center',
            },
          },
          {
            type: 'text',
            left: '35%',
            top: '56%',
            style: {
              text: '错题',
              fill: 'rgba(136,163,181,0.85)',
              font: '500 11px sans-serif',
              textAlign: 'center',
            },
          },
        ]
      : undefined,
    series: [
      {
        type: 'pie',
        radius: props.donut ? ['45%', '72%'] : ['0%', '72%'],
        center: ['40%', '50%'],
        padAngle: props.sciFi ? 3 : 0,
        data: props.data.map((item, i) => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: item.color ?? palette[i % palette.length],
            borderWidth: props.sciFi ? 3 : 2,
            borderColor,
            shadowBlur: props.sciFi ? 14 : 0,
            shadowColor: props.sciFi ? glowColor : undefined,
          },
        })),
        emphasis: {
          scale: props.sciFi,
          scaleSize: 6,
          itemStyle: {
            shadowBlur: props.sciFi ? 22 : 12,
            shadowColor: glowColor,
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
