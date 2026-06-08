/**
 * ECharts 主题工具 —— 根据当前 resolved 主题返回各部件样式配置。
 * 在 chart 组件的 option computed 中调用，随 resolvedTheme 响应。
 */

export interface EchartsThemeTokens {
  axisColor: string
  splitLineColor: string
  tooltipBg: string
  tooltipBorderColor: string
  tooltipTextColor: string
  legendTextColor: string
  backgroundColor: string
}

const DARK_TOKENS: EchartsThemeTokens = {
  axisColor: 'rgba(203, 213, 225, 0.6)',
  splitLineColor: 'rgba(255, 255, 255, 0.05)',
  tooltipBg: 'rgba(5, 14, 26, 0.92)',
  tooltipBorderColor: 'rgba(130, 212, 255, 0.2)',
  tooltipTextColor: '#e2e8f0',
  legendTextColor: 'rgba(203, 213, 225, 0.75)',
  backgroundColor: 'transparent',
}

const LIGHT_TOKENS: EchartsThemeTokens = {
  axisColor: 'rgba(71, 85, 105, 0.7)',
  splitLineColor: 'rgba(0, 0, 0, 0.06)',
  tooltipBg: 'rgba(255, 255, 255, 0.97)',
  tooltipBorderColor: 'rgba(0, 0, 0, 0.1)',
  tooltipTextColor: '#0f172a',
  legendTextColor: 'rgba(51, 65, 85, 0.85)',
  backgroundColor: 'transparent',
}

export function getEchartsTokens(resolvedTheme: 'dark' | 'light'): EchartsThemeTokens {
  return resolvedTheme === 'light' ? LIGHT_TOKENS : DARK_TOKENS
}

/** 构建通用 xAxis / yAxis 对象（分类轴） */
export function buildCategoryAxis(tokens: EchartsThemeTokens) {
  return {
    axisLine: { lineStyle: { color: tokens.splitLineColor } },
    axisTick: { show: false },
    axisLabel: { color: tokens.axisColor, fontSize: 11 },
    splitLine: { show: false },
  }
}

/** 构建通用数值轴 */
export function buildValueAxis(tokens: EchartsThemeTokens, extra: object = {}) {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: tokens.axisColor, fontSize: 11 },
    splitLine: { lineStyle: { color: tokens.splitLineColor, type: 'dashed' } },
    ...extra,
  }
}

/** 构建 tooltip 配置 */
export function buildTooltip(tokens: EchartsThemeTokens, extra: object = {}) {
  return {
    backgroundColor: tokens.tooltipBg,
    borderColor: tokens.tooltipBorderColor,
    textStyle: { color: tokens.tooltipTextColor, fontSize: 12 },
    ...extra,
  }
}

/** 构建 legend 配置 */
export function buildLegend(tokens: EchartsThemeTokens, extra: object = {}) {
  return {
    textStyle: { color: tokens.legendTextColor, fontSize: 11 },
    icon: 'circle',
    itemWidth: 8,
    itemHeight: 8,
    ...extra,
  }
}
