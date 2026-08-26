import { computed, inject, ref, type InjectionKey, type Ref } from 'vue'
import type { SelectOption } from 'naive-ui'
import { fetchTeacherOverview, type TeacherOverview } from '../api/teacherOverview'

export type TeacherOverviewContext = ReturnType<typeof useTeacherOverview>

export const TEACHER_OVERVIEW_KEY: InjectionKey<TeacherOverviewContext> = Symbol('teacher-overview')
export const TEACHER_SHELL_SEARCH_KEY: InjectionKey<Ref<string>> = Symbol('teacher-shell-search')

const CLASS_STORAGE_KEY = 'plex_teacher_selected_class_id'

function readStoredClassId(): number | null {
  try {
    const raw = localStorage.getItem(CLASS_STORAGE_KEY)
    const value = raw ? Number(raw) : NaN
    return Number.isFinite(value) && value > 0 ? value : null
  } catch {
    return null
  }
}

function persistClassId(classId: number | null) {
  try {
    if (classId) localStorage.setItem(CLASS_STORAGE_KEY, String(classId))
    else localStorage.removeItem(CLASS_STORAGE_KEY)
  } catch {
    /* ignore quota / private mode */
  }
}

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
  const selectedClassId = ref<number | null>(readStoredClassId())
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

  async function applyOverview(data: TeacherOverview) {
    overview.value = data
    selectedClassId.value = data.selected_class?.id ?? null
    persistClassId(selectedClassId.value)
  }

  async function loadOverview(classId = selectedClassId.value ?? readStoredClassId()) {
    loading.value = true
    errorMessage.value = ''
    try {
      const data = await fetchTeacherOverview({ classId, period: period.value })
      await applyOverview(data)
    } catch (error) {
      // 本地缓存的 class_id 在库重建后失效时，清缓存并回落到服务端默认班级
      if (classId != null) {
        persistClassId(null)
        selectedClassId.value = null
        try {
          const data = await fetchTeacherOverview({ classId: null, period: period.value })
          await applyOverview(data)
          errorMessage.value = ''
          return
        } catch (retryError) {
          errorMessage.value = retryError instanceof Error ? retryError.message : '教师端数据加载失败'
          return
        }
      }
      errorMessage.value = error instanceof Error ? error.message : '教师端数据加载失败'
    } finally {
      loading.value = false
    }
  }

  function changeClass(value: string | number | null) {
    const nextValue = value === null ? null : Number(value)
    selectedClassId.value = nextValue
    persistClassId(nextValue)
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
