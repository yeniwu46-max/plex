import { computed, inject, ref, type InjectionKey, type Ref } from 'vue'
import type { SelectOption } from 'naive-ui'
import { fetchTeacherOverview, type TeacherOverview } from '../api/teacherOverview'

export type TeacherOverviewContext = ReturnType<typeof useTeacherOverview>

export const TEACHER_OVERVIEW_KEY: InjectionKey<TeacherOverviewContext> = Symbol('teacher-overview')
export const TEACHER_SHELL_SEARCH_KEY: InjectionKey<Ref<string>> = Symbol('teacher-shell-search')

export function useTeacherOverviewInjected(): TeacherOverviewContext {
  const ctx = inject(TEACHER_OVERVIEW_KEY)
  if (!ctx) {
    throw new Error('useTeacherOverviewInjected 必须在 TeacherDashboardShell 内使用')
  }
  return ctx
}

export function useTeacherOverview() {
  const overview = ref<TeacherOverview | null>(null)
  const loading = ref(true)
  const errorMessage = ref('')
  const selectedClassId = ref<number | null>(null)
  const period = ref<'week' | 'month'>('week')

  const classOptions = computed<SelectOption[]>(() =>
    (overview.value?.classes ?? []).map((item) => ({
      label: `${item.name} ${new Date().getFullYear()}`,
      value: item.id,
    })),
  )

  const metrics = computed(() => overview.value?.metrics)
  const students = computed(() => overview.value?.students ?? [])
  const attentionStudents = computed(() => overview.value?.attention_students ?? [])
  const activityScore = computed(() => metrics.value?.avg_today_completion ?? 0)
  const activeLineWidth = computed(() => `${Math.max(12, Math.min(100, activityScore.value))}%`)
  const hasSelectedClass = computed(() => Boolean(overview.value?.selected_class))

  const periodOptions: SelectOption[] = [
    { label: '本周', value: 'week' },
    { label: '本月', value: 'month' },
  ]

  async function loadOverview(classId = selectedClassId.value) {
    loading.value = true
    errorMessage.value = ''
    try {
      const data = await fetchTeacherOverview({ classId, period: period.value })
      overview.value = data
      selectedClassId.value = data.selected_class?.id ?? null
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '教师端数据加载失败'
    } finally {
      loading.value = false
    }
  }

  function changeClass(value: string | number | null) {
    const nextValue = value === null ? null : Number(value)
    selectedClassId.value = nextValue
    void loadOverview(nextValue)
  }

  function changePeriod(value: string | number) {
    period.value = value === 'month' ? 'month' : 'week'
    void loadOverview()
  }

  return {
    overview,
    loading,
    errorMessage,
    selectedClassId,
    period,
    classOptions,
    metrics,
    students,
    attentionStudents,
    activityScore,
    activeLineWidth,
    hasSelectedClass,
    periodOptions,
    loadOverview,
    changeClass,
    changePeriod,
  }
}
