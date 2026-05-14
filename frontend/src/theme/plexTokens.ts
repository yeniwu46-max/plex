/**
 * PLEX 品牌与节点语义色（与 picture 品牌/图标规范对齐）。
 * Naive `themeOverrides.common` 使用此处色值；全局布局请用 `styles/plex-theme.css` 中的同名 CSS 变量。
 */
export const plexColors = {
  bg: '#07111F',
  bgElevated: '#0b1628',
  bgGlass: 'rgba(11, 22, 40, 0.72)',
  accent: '#10F0C0',
  accentHover: '#5fffe8',
  accentPressed: '#0d9a7f',
  text: '#FFFFFF',
  muted: '#8EA3B8',
  border: 'rgba(16, 240, 192, 0.18)',
  nodeTeal: '#10B9B1',
  nodeGreen: '#34D399',
  nodePurple: '#AA55F7',
  nodeBlue: '#06B6D4',
  nodeOrange: '#F59E0B',
  nodeGray: '#64748B',
} as const

/** Naive UI `themeOverrides` 的 `common` 段（暗色主题下卡片/输入等基底） */
export const plexNaiveCommonOverrides = {
  primaryColor: plexColors.accent,
  primaryColorHover: plexColors.accentHover,
  primaryColorPressed: plexColors.accentPressed,
  primaryColorSuppl: plexColors.accent,
  bodyColor: plexColors.text,
  textColor1: plexColors.text,
  textColor2: plexColors.muted,
  textColor3: '#64748b',
  cardColor: plexColors.bgElevated,
  modalColor: plexColors.bgElevated,
  popoverColor: plexColors.bgElevated,
  tableColor: plexColors.bgElevated,
  tableHeaderColor: '#0d1a2d',
  inputColor: '#0d1a2d',
  actionColor: '#132032',
  borderColor: plexColors.border,
  borderRadius: '10px',
} as const
