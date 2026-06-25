import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchStudentOverview, type StudentOverview } from '../api/studentOverview'
import { fetchStudentLearningReport, type LearningReportResult } from '../api/learningReport'
import { fetchStudentRecommendations, type StudentRecommendationsResult } from '../api/recommendations'

const CACHE_TTL = 30_000

export const useStudentWorkspaceStore = defineStore('student-workspace', () => {
  const overview = ref<StudentOverview | null>(null)
  const overviewLoadedAt = ref(0)
  const reports = ref<Partial<Record<'7d' | '30d', LearningReportResult>>>({})
  const reportLoadedAt = ref<Partial<Record<'7d' | '30d', number>>>({})
  const recommendations = ref<Partial<Record<'7d' | '30d', StudentRecommendationsResult>>>({})
  const recommendationLoadedAt = ref<Partial<Record<'7d' | '30d', number>>>({})

  function isFresh(timestamp = 0) {
    return Date.now() - timestamp < CACHE_TTL
  }

  async function loadOverview(force = false) {
    if (!force && overview.value && isFresh(overviewLoadedAt.value)) return overview.value
    overview.value = await fetchStudentOverview()
    overviewLoadedAt.value = Date.now()
    return overview.value
  }

  async function loadLearningReport(period: '7d' | '30d' = '7d', force = false) {
    const cached = reports.value[period]
    if (!force && cached && isFresh(reportLoadedAt.value[period])) return cached
    const result = await fetchStudentLearningReport(period)
    reports.value[period] = result
    reportLoadedAt.value[period] = Date.now()
    return result
  }

  async function loadRecommendations(period: '7d' | '30d' = '7d', force = false) {
    const cached = recommendations.value[period]
    if (!force && cached && isFresh(recommendationLoadedAt.value[period])) return cached
    const result = await fetchStudentRecommendations(period)
    recommendations.value[period] = result
    recommendationLoadedAt.value[period] = Date.now()
    return result
  }

  function invalidateOverview() {
    overviewLoadedAt.value = 0
  }

  return {
    overview,
    reports,
    recommendations,
    loadOverview,
    loadLearningReport,
    loadRecommendations,
    invalidateOverview,
  }
})
