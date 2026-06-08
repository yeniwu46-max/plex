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

/** 角色浅色主色映射 */
const PERSONA_LIGHT_PRIMARY: Record<string, string> = {
  student: '#16a34a',
  teacher: '#ea580c',
  admin: '#6366f1',
  default: '#0891b2',
}

const PERSONA_LIGHT_HOVER: Record<string, string> = {
  student: '#15803d',
  teacher: '#c2410c',
  admin: '#4f46e5',
  default: '#0e7490',
}

const PERSONA_LIGHT_PRESSED: Record<string, string> = {
  student: '#166534',
  teacher: '#9a3412',
  admin: '#4338ca',
  default: '#155e75',
}

/** 深色模式 Naive overrides（保留原始风格） */
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

/** 浅色模式 Naive overrides */
function getLightOverrides(persona: string) {
  const primary = PERSONA_LIGHT_PRIMARY[persona] ?? PERSONA_LIGHT_PRIMARY.default
  const hover = PERSONA_LIGHT_HOVER[persona] ?? PERSONA_LIGHT_HOVER.default
  const pressed = PERSONA_LIGHT_PRESSED[persona] ?? PERSONA_LIGHT_PRESSED.default
  return {
    primaryColor: primary,
    primaryColorHover: hover,
    primaryColorPressed: pressed,
    primaryColorSuppl: primary,
    bodyColor: '#0f172a',
    textColor1: '#0f172a',
    textColor2: '#475569',
    textColor3: '#64748b',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    popoverColor: '#ffffff',
    tableColor: '#ffffff',
    tableHeaderColor: '#f8fafc',
    inputColor: '#f8fafc',
    actionColor: '#f1f5f9',
    borderColor: 'rgba(0, 0, 0, 0.1)',
    borderRadius: '10px',
  }
}

/**
 * 根据当前 resolved 主题和角色返回 Naive themeOverrides。
 * 在 App.vue 的 computed 中调用。
 */
export function getPlexNaiveOverrides(
  resolved: 'dark' | 'light',
  persona: string,
): { common: Record<string, string> } {
  const common =
    resolved === 'light'
      ? getLightOverrides(persona)
      : { ...plexNaiveCommonOverrides }
  return { common }
}
