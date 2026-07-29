import { reactive } from 'vue'
import type { StudentNavKey } from '../components/layout/PlexSidebar.vue'

export type StudentShellChrome = {
  activeNav: StudentNavKey
  pageTitle: string
  pageSubtitle: string
  searchPlaceholder: string
  hideSearch: boolean
  showViewSwitcher: boolean
}

const chrome = reactive<StudentShellChrome>({
  activeNav: 'home',
  pageTitle: 'PLEX',
  pageSubtitle: '每一步探索，都是成长的轨迹',
  searchPlaceholder: '搜索当前页面内容…',
  hideSearch: false,
  showViewSwitcher: false,
})

export function useStudentShellChrome() {
  return chrome
}

export function applyStudentShellChrome( partial: Partial<StudentShellChrome>) {
  Object.assign(chrome, partial)
}
