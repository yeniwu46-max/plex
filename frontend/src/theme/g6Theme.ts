/**
 * AntV G6 知识图谱主题工具 —— 根据 resolved 主题返回节点/边/tooltip 的颜色配置。
 */

export interface G6ThemeTokens {
  labelFill: string
  edgeOpacity: number
  canvasBg: string
  detailBg: string
  detailBorder: string
  detailTextColor: string
  detailMutedColor: string
  detailEdgeBg: string
  detailEdgeColor: string
  tooltipBg: string
  tooltipTextColor: string
  tooltipDescColor: string
  legendTextColor: string
}

const DARK_TOKENS: G6ThemeTokens = {
  labelFill: '#e2e8f0',
  edgeOpacity: 0.65,
  canvasBg: 'rgba(3, 10, 20, 0.96)',
  detailBg: 'rgba(5, 14, 26, 0.92)',
  detailBorder: 'rgba(130, 212, 255, 0.18)',
  detailTextColor: '#fff',
  detailMutedColor: 'rgba(148, 163, 184, 0.8)',
  detailEdgeBg: 'rgba(130, 212, 255, 0.1)',
  detailEdgeColor: '#7dd3fc',
  tooltipBg: '#0a1628',
  tooltipTextColor: '#94a3b8',
  tooltipDescColor: '#cbd5e1',
  legendTextColor: 'rgba(203, 213, 225, 0.65)',
}

const LIGHT_TOKENS: G6ThemeTokens = {
  labelFill: '#334155',
  edgeOpacity: 0.8,
  canvasBg: '#f1f5f9',
  detailBg: 'rgba(255, 255, 255, 0.97)',
  detailBorder: 'rgba(0, 0, 0, 0.1)',
  detailTextColor: '#0f172a',
  detailMutedColor: 'rgba(71, 85, 105, 0.75)',
  detailEdgeBg: 'rgba(8, 145, 178, 0.08)',
  detailEdgeColor: '#0891b2',
  tooltipBg: '#ffffff',
  tooltipTextColor: '#475569',
  tooltipDescColor: '#334155',
  legendTextColor: 'rgba(51, 65, 85, 0.7)',
}

export function getG6Tokens(resolvedTheme: 'dark' | 'light'): G6ThemeTokens {
  return resolvedTheme === 'light' ? LIGHT_TOKENS : DARK_TOKENS
}

/** 构建 G6 tooltip HTML（替换原来硬编码的样式字符串） */
export function buildG6TooltipHtml(
  label: string,
  domain: string,
  statusLabel: string,
  description: string,
  statusColor: string,
  tokens: G6ThemeTokens,
): string {
  return `<div style="padding:8px 12px;background:${tokens.tooltipBg};border:1px solid ${statusColor}33;border-radius:8px;max-width:220px;">
    <strong style="color:${statusColor};font-size:13px;">${label}</strong>
    <div style="color:${tokens.tooltipTextColor};font-size:11px;margin-top:4px;">${domain} · ${statusLabel}</div>
    <div style="color:${tokens.tooltipDescColor};font-size:12px;margin-top:6px;line-height:1.5;">${description}</div>
  </div>`
}
