import { reactive } from 'vue'
import type { TeacherNavKey } from '../components/layout/TeacherSidebar.vue'

export type TeacherShellChrome = {
  activeNav: TeacherNavKey
  pageTitle: string
  pageSubtitle: string
  searchPlaceholder: string
  hideSearch: boolean
  hideToolbar: boolean
  showViewSwitcher: boolean
  toolbarLabel: string
  showPeriod: boolean
  showActivity: boolean
  showRefresh: boolean
}

const chrome = reactive<TeacherShellChrome>({
  activeNav: 'navigator',
  pageTitle: '教师端',
  pageSubtitle: '观察整个知识宇宙的成长轨迹',
  searchPlaceholder: '搜索班级、学生…',
  hideSearch: false,
  hideToolbar: false,
  showViewSwitcher: false,
  toolbarLabel: '教师端筛选与状态',
  showPeriod: false,
  showActivity: true,
  showRefresh: true,
})

export function useTeacherShellChrome() {
  return chrome
}

export function applyTeacherShellChrome(partial: Partial<TeacherShellChrome>) {
  Object.assign(chrome, partial)
}
