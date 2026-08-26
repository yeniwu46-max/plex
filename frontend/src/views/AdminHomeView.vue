<script setup lang="ts">
import { computed, defineAsyncComponent, h, onMounted, onUnmounted, ref, watch } from 'vue'
import { usePlexTour } from '../composables/usePlexTour'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NDropdown, NBadge, NEmpty, NIcon, NInput, NModal, NPopover, NSelect, useMessage, type DropdownOption, type SelectOption } from 'naive-ui'
import {
  AlertCircleOutline,
  AnalyticsOutline,
  AppsOutline,
  BookOutline,
  ChevronDownOutline,
  ExitOutline,
  GitNetworkOutline,
  HardwareChipOutline,
  PeopleOutline,
  PersonCircleOutline,
  PlanetOutline,
  RefreshOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import {
  createAdminAnnouncement,
  deleteAdminAnnouncement,
  fetchAdminAnnouncements,
  updateAdminAnnouncement,
} from '../api/adminAnnouncements'
import AdminGovernanceComboPanel from '../components/admin/AdminGovernanceComboPanel.vue'
import AdminPeopleDrilldown from '../components/admin/AdminPeopleDrilldown.vue'
import AdminRunningTrialsDrilldown from '../components/admin/AdminRunningTrialsDrilldown.vue'
import PlexThemeSwitcher from '../components/shared/PlexThemeSwitcher.vue'
import PlexGuideTour from '../components/common/PlexGuideTour.vue'
import { fetchClassRequests, type ClassChangeRequest } from '../api/classRequests'

const AdminAgentOrchestrationPanel = defineAsyncComponent(
  () => import('../components/admin/AdminAgentOrchestrationPanel.vue'),
)
const AdminTrialObservatoryPanel = defineAsyncComponent(
  () => import('../components/admin/AdminTrialObservatoryPanel.vue'),
)
import type { SystemAnnouncement } from '../api/teacherAnnouncements'
import { fetchAdminDashboard, type AdminDashboardResult } from '../api/adminSettings'
import { fetchAgentOrchestration, type AgentOrchestrationResult } from '../api/agentOrchestration'
import { fetchAgentsStatus, type AgentStatusItem } from '../api/agentService'
import { useThemeStore } from '../stores/theme'

type NavKey = 'nexus' | 'agents' | 'observer' | 'governance'
type Tone = 'purple' | 'amber' | 'green' | 'red'

interface MetricCard {
  label: string
  value: string
  sub: string
  icon: typeof PeopleOutline
  tone: Tone
}

interface ProgressMetric {
  label: string
  value: number
  delta: string
  icon: typeof AnalyticsOutline
}

interface AgentRow {
  name: string
  status: string
}

interface FeedItem {
  title: string
  desc: string
  time: string
  tone: Tone
  icon: typeof SparklesOutline
}

interface AlertItem {
  title: string
  desc: string
  time: string
  level: '高' | '中' | '低'
  tone: Tone
}

const now = ref(new Date())
let clockTimer: ReturnType<typeof setInterval> | undefined

function formatDateTime(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const currentTimeText = computed(() => `当前时间 ${formatDateTime(now.value)}`)
const currentYear = computed(() => now.value.getFullYear())

const activeNav = ref<NavKey>('nexus')

const { startTour, resetTour } = usePlexTour()
async function restartAdminTour() {
  resetTour('admin')
  await startTour('admin')
}

// 挂载 plexAdminNavSetter 供导览 prepare 使用（window 全局临时挂载）
onMounted(() => {
  const w = window as Window & { __plexAdminNavSetter?: (key: NavKey) => void }
  w.__plexAdminNavSetter = (key: NavKey) => { activeNav.value = key }
})
onUnmounted(() => {
  delete (window as Window & { __plexAdminNavSetter?: (key: NavKey) => void }).__plexAdminNavSetter
})
const period = ref<'today' | 'week' | 'month'>('month')
const trendRange = ref<'7' | '30' | '90'>('7')
const showStorageDetail = ref(false)
const showRunningTrialsDrill = ref(false)
const showPeopleDrill = ref(false)
const peopleDrillMode = ref<'students' | 'teachers'>('students')
const showAgentsDetail = ref(false)
const showFeedDetail = ref(false)
const showAlertsDetail = ref(false)
const agentsStatusLoading = ref(false)
const agentsStatusRows = ref<AgentStatusItem[]>([])
const agentsStatusMeta = ref<{ backend?: string; checked_at?: string; service?: string }>({})
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const message = useMessage()

const adminDisplayName = computed(() => auth.profile?.real_name || auth.profile?.username || '平台管理员')

const userMenuOptions = computed<DropdownOption[]>(() => [
  {
    label: '重新查看功能导览',
    key: 'restart-tour',
    icon: () => h(NIcon, null, { default: () => h(RefreshOutline) }),
  },
  { type: 'divider', key: 'menu-divider' },
  {
    label: '退出登录',
    key: 'logout',
    icon: () => h(NIcon, null, { default: () => h(ExitOutline) }),
  },
])

const announcementTitle = ref('')
const announcementBody = ref('')
const announcementTarget = ref<'teacher' | 'student' | 'all'>('teacher')
const postingAnnouncement = ref(false)
const recentAnnouncements = ref<SystemAnnouncement[]>([])

const editingAnnouncement = ref<SystemAnnouncement | null>(null)
const showEditAnnouncementModal = ref(false)
const editAnnouncementTitle = ref('')
const editAnnouncementBody = ref('')
const editAnnouncementTarget = ref<'teacher' | 'student' | 'all'>('teacher')
const savingAnnouncement = ref(false)
const deletingAnnouncementId = ref<number | null>(null)

const adminThemeStore = useThemeStore()
void adminThemeStore

const dashboardData = ref<AdminDashboardResult | null>(null)
const dashboardLoading = ref(false)

const announcementTargetOptions: SelectOption[] = [
  { label: '全体教师', value: 'teacher' },
  { label: '全体学生', value: 'student' },
  { label: '全体用户', value: 'all' },
]

const navItems = [
  { key: 'nexus' as const, label: '中央总控', sub: 'Central Nexus', icon: SettingsOutline },
  { key: 'agents' as const, label: '智能体编排', sub: 'Agent Orchestration', icon: PeopleOutline },
  { key: 'observer' as const, label: '系统观测', sub: 'System Observatory', icon: AppsOutline },
  { key: 'governance' as const, label: '权限与控制', sub: 'Governance Center', icon: ShieldCheckmarkOutline },
]

const periodOptions: SelectOption[] = [
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
]

const metricCards: MetricCard[] = [
  { label: '活跃学习者', value: '—', sub: '近 7 日有作答记录', icon: PeopleOutline, tone: 'purple' },
  { label: '注册教师', value: '—', sub: '平台教师账号', icon: BookOutline, tone: 'amber' },
  { label: '运行试炼', value: '—', sub: '当前进行中', icon: HardwareChipOutline, tone: 'purple' },
  { label: '系统健康度', value: '—', sub: '状态良好', icon: ShieldCheckmarkOutline, tone: 'purple' },
]

async function loadDashboard() {
  dashboardLoading.value = true
  try {
    dashboardData.value = await fetchAdminDashboard(period.value)
  } catch {
    dashboardData.value = null
  } finally {
    dashboardLoading.value = false
  }
}

watch(period, () => {
  void loadDashboard()
})

const liveMetricCards = computed<MetricCard[]>(() => {
  const m = dashboardData.value?.metrics
  if (!m) return metricCards
  return [
    {
      label: '活跃学习者',
      value: String(m.active_students),
      sub: `共 ${m.total_students} 名学生`,
      icon: PeopleOutline,
      tone: 'purple',
    },
    {
      label: '注册教师',
      value: String(m.active_teachers),
      sub: '平台教师账号',
      icon: BookOutline,
      tone: 'amber',
    },
    {
      label: '运行试炼',
      value: String(m.running_trials),
      sub: `共 ${m.total_trials} 场试炼`,
      icon: HardwareChipOutline,
      tone: 'purple',
    },
    {
      label: '系统健康度',
      value: `${m.health_score}%`,
      sub: '状态良好',
      icon: ShieldCheckmarkOutline,
      tone: 'purple',
    },
  ]
})

const liveProgressMetrics = computed<ProgressMetric[]>(() => {
  const p = dashboardData.value?.progress
  if (!p) return progressMetrics
  return [
    { label: '学习任务完成率', value: p.task_completion_rate, delta: '实时', icon: SettingsOutline },
    { label: '试炼参与率', value: p.trial_participation_rate, delta: '实时', icon: BookOutline },
    { label: '知识掌握率', value: p.knowledge_mastery_rate, delta: '实时', icon: ShieldCheckmarkOutline },
    { label: '学习活跃度', value: p.activity_rate, delta: '实时', icon: SparklesOutline },
  ]
})

const observerMetricCards = computed<MetricCard[]>(() => {
  const ops = dashboardData.value?.resource_operations
  if (!ops) {
    return [
      { label: '资源任务成功率', value: '—', sub: '等待运行数据', icon: AnalyticsOutline, tone: 'purple' },
      { label: '平均任务耗时', value: '—', sub: '等待运行数据', icon: HardwareChipOutline, tone: 'purple' },
      { label: '备用引擎占比', value: '—', sub: '等待运行数据', icon: AlertCircleOutline, tone: 'purple' },
      { label: '待审核资源', value: '—', sub: '等待运行数据', icon: ShieldCheckmarkOutline, tone: 'purple' },
    ]
  }
  return [
    { label: '资源任务成功率', value: `${ops.success_rate}%`, sub: `${ops.completed_count}/${ops.task_count} 已完成`, icon: AnalyticsOutline, tone: 'purple' },
    { label: '平均任务耗时', value: ops.average_latency_ms == null ? '—' : `${ops.average_latency_ms}ms`, sub: '生成任务端到端耗时', icon: HardwareChipOutline, tone: 'purple' },
    { label: '备用引擎占比', value: `${ops.fallback_rate}%`, sub: ops.backend_distribution.map((item) => `${item.backend} ${item.count}`).join(' · '), icon: AlertCircleOutline, tone: ops.fallback_rate > 50 ? 'amber' : 'purple' },
    { label: '待审核资源', value: String(ops.pending_review_count), sub: `${ops.failed_count} 个失败任务`, icon: ShieldCheckmarkOutline, tone: ops.pending_review_count ? 'amber' : 'green' },
  ]
})

const agentOrchestrationData = ref<AgentOrchestrationResult | null>(null)

const agentsMetricCardsLive = computed<MetricCard[]>(() => {
  const data = agentOrchestrationData.value
  const runtime = data?.runtime
  const config = data?.config
  const enabledCount =
    (config?.grading_agents?.length ?? 0) + (config?.learning_pipeline?.length ?? 0)
  const backend = data?.agent_backend ?? 'rules'
  const backendLabel = backend === 'mock' || backend === 'rules' ? '规则引擎' : backend
  const avgMs = runtime?.avg_latency_ms
  const avgLabel = avgMs == null ? '—' : avgMs >= 1000 ? `${(avgMs / 1000).toFixed(1)}s` : `${avgMs}ms`
  const successRate = runtime?.success_rate ?? 100
  const orchestrationOn = config?.enabled ?? false
  return [
    {
      label: '运行智能体',
      value: String(enabledCount),
      sub: orchestrationOn ? `${backendLabel} · 已启用编排` : '编排已关闭',
      icon: HardwareChipOutline,
      tone: 'purple',
    },
    {
      label: '注册智能体',
      value: String(runtime?.registered_agent_count ?? data?.runtime_status?.length ?? 0),
      sub: `检查 ${config?.grading_agents?.length ?? 0} · 流水线 ${config?.learning_pipeline?.length ?? 0}`,
      icon: GitNetworkOutline,
      tone: 'purple',
    },
    {
      label: '平均响应延迟',
      value: avgLabel,
      sub: runtime?.ready_for_llm ? 'AI 增强已就绪' : runtime?.api_key_configured ? 'LLM 增强可用' : '规则引擎运行中',
      icon: AnalyticsOutline,
      tone: runtime?.ready_for_llm ? 'green' : 'amber',
    },
    {
      label: '协同成功率',
      value: `${successRate}%`,
      sub: runtime?.degraded_reason === 'missing_api_key'
        ? '未配置 API Key'
        : runtime?.degraded_reason === 'missing_crewai_venv'
          ? '缺少 CrewAI venv'
          : '基于最近运行态',
      icon: ShieldCheckmarkOutline,
      tone: successRate >= 95 ? 'green' : 'amber',
    },
  ]
})

const progressMetrics: ProgressMetric[] = [
  { label: '学习任务完成率', value: 78.6, delta: '↑ 6.2%', icon: SettingsOutline },
  { label: '试炼参与率', value: 65.3, delta: '↑ 4.8%', icon: BookOutline },
  { label: '知识掌握率', value: 72.1, delta: '↑ 5.3%', icon: ShieldCheckmarkOutline },
  { label: '学习活跃度', value: 83.7, delta: '↑ 7.1%', icon: SparklesOutline },
]

function agentStatusLabel(status: string) {
  if (status === 'running') return '运行中'
  if (status === 'success') return '最近成功'
  if (status === 'error') return '异常'
  return '待命'
}

function formatAgentTime(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function shortAgentName(name: string) {
  return name.replace(/智能体$/u, '')
}

const liveAgentStatusSource = computed<AgentStatusItem[]>(() => {
  if (agentsStatusRows.value.length) return agentsStatusRows.value
  const runtime = agentOrchestrationData.value?.runtime_status
  if (!runtime?.length) return []
  return runtime.map((row) => ({
    id: row.id,
    name: row.name,
    role: row.role,
    status: (row.status as AgentStatusItem['status']) || 'idle',
    lastRunAt: row.lastRunAt ?? undefined,
    avgLatency: row.avgLatency ?? undefined,
  }))
})

const agentRows = computed<AgentRow[]>(() => {
  const preferred = [
    'learning_diagnosis',
    'code_analysis',
    'path_recommendation',
    'feedback',
    'teacher_assistant',
  ]
  const source = liveAgentStatusSource.value
  if (!source.length) {
    return [
      { name: '学习诊断', status: '待命' },
      { name: '代码分析', status: '待命' },
      { name: '路径推荐', status: '待命' },
      { name: '反馈生成', status: '待命' },
      { name: '检查智能体', status: '待命' },
    ]
  }
  const byId = new Map(source.map((row) => [row.id, row]))
  const picked = preferred
    .map((id) => byId.get(id))
    .filter((row): row is AgentStatusItem => Boolean(row))
  const rows = (picked.length ? picked : source).slice(0, 5)
  return rows.map((row) => ({
    name: shortAgentName(row.name),
    status: agentStatusLabel(row.status),
  }))
})

const feedItems = computed<FeedItem[]>(() => {
  const items: FeedItem[] = []
  const pendingCount = adminNotifications.value.length
  if (pendingCount > 0) {
    const first = adminNotifications.value[0]
    items.push({
      title: '班级变更待审',
      desc: first?.body || `有 ${pendingCount} 条班级申请等待审批`,
      time: formatAgentTime(first?.createdAt),
      tone: 'purple',
      icon: BookOutline,
    })
  }

  const ops = dashboardData.value?.resource_operations
  if (ops) {
    items.push({
      title: '资源任务运行',
      desc: `完成 ${ops.completed_count}/${ops.task_count}，失败 ${ops.failed_count}，成功率 ${ops.success_rate}%`,
      time: ops.average_latency_ms == null ? '实时' : `${ops.average_latency_ms}ms`,
      tone: ops.failed_count > 0 ? 'amber' : 'purple',
      icon: HardwareChipOutline,
    })
  }

  const recentAgent = [...liveAgentStatusSource.value]
    .filter((row) => row.lastRunAt)
    .sort((a, b) => String(b.lastRunAt).localeCompare(String(a.lastRunAt)))[0]
  if (recentAgent) {
    items.push({
      title: '智能体任务调度',
      desc: `${recentAgent.name} ${agentStatusLabel(recentAgent.status)}${recentAgent.avgLatency != null ? ` · 平均 ${recentAgent.avgLatency}ms` : ''}`,
      time: formatAgentTime(recentAgent.lastRunAt),
      tone: recentAgent.status === 'error' ? 'red' : 'purple',
      icon: SparklesOutline,
    })
  }

  const weak = dashboardData.value?.weak_knowledge_top?.[0]
  if (weak) {
    items.push({
      title: '薄弱知识点更新',
      desc: `「${weak.knowledge_label}」累计错题 ${weak.fail_count} 次`,
      time: '实时',
      tone: 'amber',
      icon: AnalyticsOutline,
    })
  }

  const alert = dashboardData.value?.alerts?.[0]
  if (alert) {
    items.push({
      title: alert.title,
      desc: alert.desc,
      time: alert.time || '实时',
      tone: (alert.tone === 'red' || alert.tone === 'amber' || alert.tone === 'green' ? alert.tone : 'red') as Tone,
      icon: AlertCircleOutline,
    })
  }

  const metrics = dashboardData.value?.metrics
  if (metrics && items.length < 4) {
    items.push({
      title: '平台运行摘要',
      desc: `活跃学生 ${metrics.active_students} · 运行试炼 ${metrics.running_trials} · 健康度 ${metrics.health_score}%`,
      time: '实时',
      tone: 'green',
      icon: ShieldCheckmarkOutline,
    })
  }

  if (!items.length) {
    return [
      { title: '暂无新动态', desc: '系统运行平稳，等待新的业务事件', time: '—', tone: 'purple', icon: SparklesOutline },
    ]
  }
  return items.slice(0, 6)
})

async function refreshAgentsStatus() {
  agentsStatusLoading.value = true
  try {
    const [status, orch] = await Promise.all([
      fetchAgentsStatus(),
      agentOrchestrationData.value
        ? Promise.resolve(agentOrchestrationData.value)
        : fetchAgentOrchestration().catch(() => null),
    ])
    agentsStatusRows.value = status.agents ?? []
    agentsStatusMeta.value = {
      backend: status.backend,
      checked_at: status.checked_at,
      service: status.service,
    }
    if (orch && !agentOrchestrationData.value) {
      agentOrchestrationData.value = orch
    }
  } catch {
    if (!agentsStatusRows.value.length && agentOrchestrationData.value?.runtime_status?.length) {
      agentsStatusRows.value = agentOrchestrationData.value.runtime_status.map((row) => ({
        id: row.id,
        name: row.name,
        role: row.role,
        status: (row.status as AgentStatusItem['status']) || 'idle',
        lastRunAt: row.lastRunAt ?? undefined,
        avgLatency: row.avgLatency ?? undefined,
      }))
    }
  } finally {
    agentsStatusLoading.value = false
  }
}

async function openAgentsDetail() {
  showAgentsDetail.value = true
  await refreshAgentsStatus()
}

async function openFeedDetail() {
  showFeedDetail.value = true
  await Promise.all([
    loadAdminNotifications(),
    loadDashboard(),
    refreshAgentsStatus(),
  ])
}

function openAlertsDetail() {
  showAlertsDetail.value = true
}

const alertItems = computed<AlertItem[]>(() => {
  const rows = dashboardData.value?.alerts
  if (!rows?.length) {
    return [
      { title: '系统运行平稳', desc: '暂无需要立即处理的告警', time: '实时', level: '低', tone: 'purple' },
    ]
  }
  return rows.map((item) => ({
    title: item.title,
    desc: item.desc,
    time: item.time,
    level: (item.level === '高' || item.level === '中' || item.level === '低' ? item.level : '低') as AlertItem['level'],
    tone: (item.tone === 'red' || item.tone === 'amber' || item.tone === 'purple' || item.tone === 'green'
      ? item.tone
      : 'purple') as Tone,
  }))
})

const liveTrendPoints = computed(() => {
  const submissions = dashboardData.value?.charts?.activity_trend?.submissions ?? []
  if (!submissions.length) return [8, 14, 11, 18, 16, 22, 19]
  const max = Math.max(...submissions, 1)
  return submissions.map((n) => Math.max(4, Math.round((n / max) * 42)))
})

const liveTrendAxis = computed(() => {
  const labels = dashboardData.value?.charts?.activity_trend?.x_data
  if (labels?.length) return labels
  return ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
})

const trendPolyline = computed(() =>
  liveTrendPoints.value
    .map((point, index) => {
      const step = liveTrendPoints.value.length > 1 ? 378 / (liveTrendPoints.value.length - 1) : 0
      return `${index * step},${128 - point * 2.2}`
    })
    .join(' '),
)

const storageInfo = computed(() => {
  const storage = dashboardData.value?.storage
  if (!storage) {
    return {
      total_tb: 0,
      used_tb: 0,
      free_tb: 0,
      used_ratio: 0,
      breakdown: [] as Array<{ label: string; value_tb: number; count: number }>,
      detail: null as AdminDashboardResult['storage'] extends infer S
        ? S extends { detail: infer D }
          ? D
          : null
        : null,
    }
  }
  return storage
})

const moduleCards = [
  { label: '学生端', icon: BookOutline, pulse: 'pulse-a' },
  { label: '教师端', icon: PersonCircleOutline, pulse: 'pulse-b' },
  { label: '管理端', icon: AppsOutline, pulse: 'pulse-c' },
  { label: 'Agent 链路', icon: PlanetOutline, pulse: 'pulse-d' },
]

function openRunningTrials() {
  showRunningTrialsDrill.value = true
}

function openPeopleDrill(mode: 'students' | 'teachers') {
  peopleDrillMode.value = mode
  showPeopleDrill.value = true
}

function isNexusMetricClickable(label: string) {
  return activeNav.value === 'nexus' && ['活跃学习者', '注册教师', '运行试炼'].includes(label)
}

function onMetricCardClick(label: string) {
  if (activeNav.value !== 'nexus') return
  if (label === '活跃学习者') {
    openPeopleDrill('students')
    return
  }
  if (label === '注册教师') {
    openPeopleDrill('teachers')
    return
  }
  if (label === '运行试炼') {
    openRunningTrials()
  }
}

const waveMetric = ref<'activity' | 'health'>('activity')
const waveMetricOptions: SelectOption[] = [
  { label: '活跃度', value: 'activity' },
  { label: '健康度', value: 'health' },
]

const waveChartPoints = computed(() => {
  const charts = dashboardData.value?.charts
  if (waveMetric.value === 'health') {
    const scores = charts?.health_trend?.scores
    if (scores?.length) return scores
    const passed = charts?.activity_trend?.passed ?? []
    const submissions = charts?.activity_trend?.submissions ?? []
    if (passed.length) {
      return passed.map((p, i) => {
        const total = submissions[i] ?? 0
        return total > 0 ? Math.round((p / total) * 100) : 95
      })
    }
    return [92, 94, 91, 96, 93, 97, 95]
  }
  const submissions = charts?.activity_trend?.submissions
  if (submissions?.length) return submissions
  return [48, 55, 66, 54, 49, 72, 86, 68, 51, 50, 74, 84, 72, 64, 70, 79]
})

const waveChartAxis = computed(() => {
  const xData = dashboardData.value?.charts?.activity_trend?.x_data
  if (xData?.length) return xData
  return ['05-14', '05-15', '05-16', '05-17', '05-18', '05-19', '05-20']
})

const wavePolyline = computed(() => {
  const points = waveChartPoints.value
  const max = Math.max(...points, 1)
  const step = points.length > 1 ? 390 / (points.length - 1) : 390
  return points.map((point, index) => `${index * step},${130 - (point / max) * 100}`).join(' ')
})

const waveChartCircles = computed(() => {
  const points = waveChartPoints.value
  const max = Math.max(...points, 1)
  const step = points.length > 1 ? 390 / (points.length - 1) : 390
  return points.map((point, index) => ({
    cx: index * step,
    cy: 130 - (point / max) * 100,
  }))
})

const currentNav = computed(() => navItems.find((item) => item.key === activeNav.value) ?? navItems[0])
const pageSubtitle = computed(() => {
  if (activeNav.value === 'observer') return '观测试炼数据、平台波动与各模块运行状态'
  if (activeNav.value === 'agents') return '配置检查智能体编排，协同完成学生做题自动校验'
  return '实时掌控 PLEX 平台的运行状态与关键指标'
})
const visibleMetrics = computed(() => {
  if (activeNav.value === 'observer') return observerMetricCards.value
  if (activeNav.value === 'agents') return agentsMetricCardsLive.value
  return liveMetricCards.value
})

interface AdminNotificationItem {
  id: string
  title: string
  body: string
  createdAt: string
  read: boolean
  navTarget?: NavKey
}

const adminNotifications = ref<AdminNotificationItem[]>([])
const showAdminNotifications = ref(false)
const adminNotificationsLoading = ref(false)

const adminUnreadCount = computed(() => adminNotifications.value.filter((item) => !item.read).length)

function classRequestActionLabel(action: ClassChangeRequest['action']) {
  if (action === 'create') return '新建班级'
  if (action === 'delete') return '删除班级'
  return '修改班级'
}

async function loadAdminNotifications() {
  adminNotificationsLoading.value = true
  try {
    const pending = await fetchClassRequests('pending')
    adminNotifications.value = pending.map((row) => ({
      id: `class-req-${row.id}`,
      title: '班级变更待审批',
      body: `${row.requester_name || `教师#${row.requester_id}`} 申请${classRequestActionLabel(row.action)}${row.class_name ? `「${row.class_name}」` : ''}`,
      createdAt: row.created_at ?? new Date().toISOString(),
      read: false,
      navTarget: 'governance',
    }))
  } catch {
    adminNotifications.value = []
  } finally {
    adminNotificationsLoading.value = false
  }
}

function markAdminNotificationsRead() {
  adminNotifications.value = adminNotifications.value.map((item) => ({ ...item, read: true }))
}

function onAdminNotificationClick(item: AdminNotificationItem) {
  adminNotifications.value = adminNotifications.value.map((row) =>
    row.id === item.id ? { ...row, read: true } : row,
  )
  if (item.navTarget) setActiveNav(item.navTarget)
  showAdminNotifications.value = false
}

function setActiveNav(key: NavKey) {
  activeNav.value = key
  if (key === 'governance') {
    void loadAnnouncements()
    void loadAdminNotifications()
  }
  if (key === 'nexus' || key === 'observer') {
    void loadDashboard()
  }
  if (key === 'agents') {
    void loadAgentOrchestrationMetrics()
  }
}

async function loadAgentOrchestrationMetrics() {
  try {
    agentOrchestrationData.value = await fetchAgentOrchestration()
  } catch {
    agentOrchestrationData.value = null
  }
}

async function loadAnnouncements() {
  try {
    recentAnnouncements.value = await fetchAdminAnnouncements()
  } catch (error) {
    recentAnnouncements.value = []
    message.error(error instanceof Error ? error.message : '公告列表加载失败')
  }
}

function announcementSuccessText(target: 'teacher' | 'student' | 'all') {
  if (target === 'student') return '公告已发布，学生端将收到通知'
  if (target === 'all') return '公告已发布，教师与学生端将收到通知'
  return '公告已发布，教师端将收到通知'
}

function openEditAnnouncement(item: SystemAnnouncement) {
  editingAnnouncement.value = item
  editAnnouncementTitle.value = item.title
  editAnnouncementBody.value = item.body
  editAnnouncementTarget.value = item.target_role as 'teacher' | 'student' | 'all'
  showEditAnnouncementModal.value = true
}

async function saveEditAnnouncement() {
  if (!editingAnnouncement.value) return
  if (!editAnnouncementTitle.value.trim() || !editAnnouncementBody.value.trim()) {
    message.warning('请填写公告标题与内容')
    return
  }
  savingAnnouncement.value = true
  try {
    await updateAdminAnnouncement(editingAnnouncement.value.id, {
      title: editAnnouncementTitle.value.trim(),
      body: editAnnouncementBody.value.trim(),
      target_role: editAnnouncementTarget.value,
    })
    message.success('公告已更新')
    showEditAnnouncementModal.value = false
    editingAnnouncement.value = null
    await loadAnnouncements()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '更新失败')
  } finally {
    savingAnnouncement.value = false
  }
}

async function removeAnnouncement(id: number) {
  deletingAnnouncementId.value = id
  try {
    await deleteAdminAnnouncement(id)
    message.success('公告已删除')
    await loadAnnouncements()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除失败')
  } finally {
    deletingAnnouncementId.value = null
  }
}

async function postAnnouncement() {
  if (!announcementTitle.value.trim() || !announcementBody.value.trim()) {
    message.warning('请填写公告标题与内容')
    return
  }
  postingAnnouncement.value = true
  try {
    await createAdminAnnouncement({
      title: announcementTitle.value.trim(),
      body: announcementBody.value.trim(),
      target_role: announcementTarget.value,
    })
    message.success(announcementSuccessText(announcementTarget.value))
    announcementTitle.value = ''
    announcementBody.value = ''
    await loadAnnouncements()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '发布失败')
  } finally {
    postingAnnouncement.value = false
  }
}

async function handleLogout() {
  await auth.logout()
  await router.replace({ name: 'login' })
}

async function handleUserMenuSelect(key: string) {
  if (key === 'restart-tour') {
    await restartAdminTour()
    return
  }
  if (key === 'logout') {
    await handleLogout()
  }
}

onMounted(() => {
  clockTimer = setInterval(() => {
    now.value = new Date()
  }, 1000)
  void loadDashboard()
  void loadAdminNotifications()
  void refreshAgentsStatus()
  void loadAgentOrchestrationMetrics()

  // Handle ?panel=xxx deep link navigation
  const valid: NavKey[] = ['nexus', 'agents', 'observer', 'governance']
  const initPanel = route.query.panel as string | undefined
  if (initPanel && valid.includes(initPanel as NavKey)) {
    setActiveNav(initPanel as NavKey)
  }
  watch(
    () => route.query.panel as string | undefined,
    (panel) => {
      if (panel && valid.includes(panel as NavKey)) {
        setActiveNav(panel as NavKey)
      }
    },
  )
})

onUnmounted(() => {
  if (clockTimer !== undefined) clearInterval(clockTimer)
})
</script>

<template>
  <div class="admin-shell">
    <PlexGuideTour role="admin" />
    <aside class="admin-sidebar" aria-label="管理员导航">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"><n-icon :component="SparklesOutline" /></span>
        <strong>PLEX</strong>
      </div>

      <nav class="admin-nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          class="nav-item"
          :class="{ active: activeNav === item.key }"
          @click="setActiveNav(item.key)"
        >
          <span class="nav-icon"><n-icon :component="item.icon" /></span>
          <span>
            <strong>{{ item.label }}</strong>
            <small>{{ item.sub }}</small>
          </span>
        </button>
      </nav>

      <section class="overseer-card">
        <span class="overseer-orbit" aria-hidden="true"><n-icon :component="SparklesOutline" /></span>
        <div>
          <strong>平台管理员</strong>
          <small>系统治理</small>
        </div>
        <em>管理员</em>
      </section>

      <footer class="sidebar-actions">
        <button type="button" aria-label="退出登录" @click="handleLogout"><n-icon :component="ExitOutline" /></button>
      </footer>
    </aside>

    <main class="admin-main">
      <header class="admin-topbar">
        <div class="title-block">
          <h1>{{ currentNav.label }} <span>{{ currentNav.sub }}</span><i /></h1>
          <p>{{ pageSubtitle }}</p>
        </div>

        <div class="topbar-tools">
          <plex-theme-switcher />
          <n-popover
            trigger="click"
            placement="bottom-end"
            :show="showAdminNotifications"
            class="admin-notif-popover"
            @update:show="(show) => { showAdminNotifications = show; if (show) void loadAdminNotifications() }"
          >
            <template #trigger>
              <n-badge :value="adminUnreadCount || undefined" :max="9" type="error" :offset="[-2, 4]">
                <button type="button" class="nexus-globe" aria-label="通知中心" data-tour="admin-notifications">
                  <n-icon :component="SparklesOutline" />
                </button>
              </n-badge>
            </template>
            <div class="admin-notif-panel">
              <header class="admin-notif-panel__head">
                <strong>通知中心</strong>
                <n-button
                  v-if="adminNotifications.length"
                  text
                  size="tiny"
                  type="primary"
                  @click="markAdminNotificationsRead"
                >
                  全部已读
                </n-button>
              </header>
              <div v-if="adminNotificationsLoading" class="admin-notif-panel__empty">加载中…</div>
              <ul v-else-if="adminNotifications.length" class="admin-notif-panel__list">
                <li
                  v-for="item in adminNotifications"
                  :key="item.id"
                  class="admin-notif-item"
                  :class="{ 'admin-notif-item--unread': !item.read }"
                  @click="onAdminNotificationClick(item)"
                >
                  <div class="admin-notif-item__title">{{ item.title }}</div>
                  <p class="admin-notif-item__body">{{ item.body }}</p>
                  <time class="admin-notif-item__time">{{ item.createdAt.slice(0, 16).replace('T', ' ') }}</time>
                </li>
              </ul>
              <n-empty v-else size="small" description="暂无待处理通知" class="admin-notif-panel__empty" />
            </div>
          </n-popover>
          <n-dropdown trigger="click" :options="userMenuOptions" @select="handleUserMenuSelect">
            <button type="button" class="profile-button" aria-label="打开用户菜单">
              <n-icon :component="PersonCircleOutline" />
              <span><strong>{{ adminDisplayName }}</strong><small>系统治理者</small></span>
              <n-icon :component="ChevronDownOutline" />
            </button>
          </n-dropdown>
        </div>

        <div class="current-time">{{ currentTimeText }}</div>
      </header>

      <section
        class="metric-row"
        :class="{ 'metric-row--observer': activeNav === 'observer' || activeNav === 'agents' }"
        aria-label="核心指标"
        data-tour="admin-nexus-metrics"
      >
        <article
          v-for="item in visibleMetrics"
          :key="item.label"
          class="metric-card"
          :class="[`tone-${item.tone}`, { 'metric-card--clickable': isNexusMetricClickable(item.label) }]"
          @click="onMetricCardClick(item.label)"
        >
          <span class="metric-icon"><n-icon :component="item.icon" /></span>
          <div>
            <small>{{ item.label }}</small>
            <strong>{{ item.value }}</strong>
            <em>{{ item.sub }}</em>
          </div>
        </article>
      </section>

      <section v-if="activeNav === 'nexus'" class="dashboard-grid" aria-label="中央总控面板">
        <article class="panel operations-panel">
          <header class="panel-head">
            <h2>平台运行概览</h2>
            <n-select v-model:value="period" :options="periodOptions" size="small" class="period-select" />
          </header>
          <div class="progress-list">
            <article v-for="item in liveProgressMetrics" :key="item.label">
              <span><n-icon :component="item.icon" /></span>
              <div>
                <div class="progress-copy">
                  <strong>{{ item.label }}</strong>
                  <em>{{ item.value }}%</em>
                  <small>{{ item.delta }}</small>
                </div>
                <i><b :style="{ width: `${item.value}%` }" /></i>
              </div>
            </article>
          </div>
          <div
            v-if="dashboardData?.weak_knowledge_top?.length"
            class="weak-knowledge-top"
          >
            <h3>全校高频薄弱知识点</h3>
            <ul>
              <li v-for="item in dashboardData.weak_knowledge_top" :key="item.knowledge_key">
                <span>{{ item.knowledge_label }}</span>
                <em>{{ item.fail_count }} 次错题</em>
              </li>
            </ul>
          </div>
        </article>

        <article class="panel agents-panel panel--clickable" role="button" tabindex="0" @click="openAgentsDetail" @keydown.enter="openAgentsDetail">
          <header class="panel-head">
            <h2>智能体运行状态</h2>
            <button type="button" @click.stop="openAgentsDetail">全部智能体 ›</button>
          </header>
          <div class="agent-layout">
            <div class="nexus-orbit" aria-hidden="true">
              <span v-for="ring in 5" :key="ring" :style="{ '--ring': ring }" />
              <i v-for="dot in 12" :key="dot" :style="{ '--dot': dot }" />
              <b><n-icon :component="SparklesOutline" /></b>
            </div>
            <div class="agent-list">
              <div v-for="agent in agentRows" :key="agent.name">
                <span>{{ agent.name }}</span>
                <em>{{ agent.status }}</em>
              </div>
              <button type="button" @click.stop="openAgentsDetail">更多智能体 ›</button>
            </div>
          </div>
        </article>

        <article class="panel feed-panel panel--clickable" role="button" tabindex="0" @click="openFeedDetail" @keydown.enter="openFeedDetail">
          <header class="panel-head">
            <h2>实时系统动态</h2>
            <button type="button" @click.stop="openFeedDetail">全部动态 ›</button>
          </header>
          <div class="feed-list">
            <article v-for="item in feedItems" :key="item.title" :class="`tone-${item.tone}`">
              <span><n-icon :component="item.icon" /></span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.desc }}</small>
              </div>
              <time>{{ item.time }}</time>
            </article>
          </div>
        </article>

        <article class="panel trend-panel">
          <header class="panel-head">
            <h2>用户活跃趋势</h2>
            <div class="segmented">
              <button type="button" :class="{ active: trendRange === '7' }" @click="trendRange = '7'; period = 'week'">7日</button>
              <button type="button" :class="{ active: trendRange === '30' }" @click="trendRange = '30'; period = 'month'">30日</button>
              <button type="button" :class="{ active: trendRange === '90' }" @click="trendRange = '90'; period = 'month'">90日</button>
            </div>
          </header>
          <svg class="trend-chart" viewBox="0 0 390 150" role="img" aria-label="用户活跃趋势">
            <defs>
              <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgba(139, 92, 246, .55)" />
                <stop offset="100%" stop-color="rgba(139, 92, 246, 0)" />
              </linearGradient>
            </defs>
            <path :d="`M0,150 L${trendPolyline} L378,150 Z`" fill="url(#trendFill)" opacity=".6" />
            <polyline :points="trendPolyline" />
            <circle
              v-for="(point, index) in liveTrendPoints"
              :key="`${index}-${point}`"
              :cx="liveTrendPoints.length > 1 ? index * (378 / (liveTrendPoints.length - 1)) : 0"
              :cy="128 - point * 2.2"
              r="4"
            />
          </svg>
          <div class="chart-axis">
            <span v-for="label in liveTrendAxis" :key="label">{{ label }}</span>
          </div>
        </article>

        <article class="panel storage-panel">
          <header class="panel-head">
            <h2>资源与存储</h2>
            <button type="button" @click="showStorageDetail = true">查看详情 ›</button>
          </header>
          <div class="storage-layout">
            <div class="storage-ring" :style="{ '--used': `${storageInfo.used_ratio || 0}%` }">
              <span><n-icon :component="SparklesOutline" /></span>
            </div>
            <dl>
              <div><dt>总存储空间</dt><dd>{{ storageInfo.total_tb }} TB</dd></div>
              <div><dt>已使用</dt><dd>{{ storageInfo.used_tb }} TB</dd></div>
              <div><dt>可用空间</dt><dd>{{ storageInfo.free_tb }} TB</dd></div>
            </dl>
            <ul>
              <li v-for="row in storageInfo.breakdown" :key="row.label">
                <span>{{ row.label }}</span>
                <strong>{{ row.value_tb }} TB</strong>
              </li>
            </ul>
          </div>
        </article>

        <article class="panel alerts-panel">
          <header class="panel-head">
            <h2>系统告警</h2>
            <button type="button" @click="openAlertsDetail">全部告警 ›</button>
          </header>
          <div class="alert-list">
            <article v-for="item in alertItems" :key="item.title" :class="`tone-${item.tone}`">
              <span><n-icon :component="AlertCircleOutline" /></span>
              <em>{{ item.level }}</em>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.desc }}</small>
              </div>
              <time>{{ item.time }}</time>
            </article>
          </div>
        </article>
      </section>

      <section v-else-if="activeNav === 'observer'" class="observer-grid" aria-label="系统观测面板">
        <AdminTrialObservatoryPanel class="panel observatory-trials-panel observatory-trials-panel--expanded" />

        <div class="observer-grid__footer" data-tour="admin-system-monitor">
        <article class="panel wave-panel">
          <header class="panel-head">
            <h2>近7日平台波动 <span class="info-dot">i</span></h2>
            <n-select v-model:value="waveMetric" :options="waveMetricOptions" size="small" class="observe-select" />
          </header>
          <svg class="wave-chart" viewBox="0 0 390 150" role="img" :aria-label="waveMetric === 'health' ? '近7日健康度' : '近7日活跃度'">
            <defs>
              <linearGradient id="waveFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgba(139, 92, 246, .62)" />
                <stop offset="100%" stop-color="rgba(139, 92, 246, 0)" />
              </linearGradient>
            </defs>
            <path :d="`M0,150 L${wavePolyline} L390,150 Z`" fill="url(#waveFill)" />
            <polyline :points="wavePolyline" />
            <circle v-for="(point, index) in waveChartCircles" :key="`${point.cx}-${index}`" :cx="point.cx" :cy="point.cy" r="3" />
          </svg>
          <div class="chart-axis">
            <span v-for="label in waveChartAxis" :key="label">{{ label }}</span>
          </div>
        </article>

        <article class="panel module-panel">
          <header class="panel-head">
            <h2>模块运行状态 <span class="info-dot">i</span></h2>
          </header>
          <div class="module-row module-row--four">
            <article v-for="item in moduleCards" :key="item.label" class="module-status-card" :class="item.pulse">
              <span class="module-status-card__pulse" aria-hidden="true" />
              <n-icon :component="item.icon" />
              <strong>{{ item.label }}</strong>
              <small><i class="module-status-card__dot" />正常</small>
            </article>
          </div>
        </article>
        </div>
      </section>

      <admin-agent-orchestration-panel
        v-else-if="activeNav === 'agents'"
        data-tour="admin-agent-flow"
        @orchestration-updated="loadAgentOrchestrationMetrics"
      />

      <section v-else-if="activeNav === 'governance'" class="dashboard-grid governance-grid" aria-label="权限与公告" data-tour="admin-permission-control">
        <article class="panel governance-announce-panel">
          <header class="panel-head">
            <h2>系统公告</h2>
          </header>
          <p class="governance-hint">向教师、学生或全体用户发布公告；教师/学生登录后将在顶栏通知中收到。</p>
          <label class="gov-field">
            <span>接收对象</span>
            <n-select v-model:value="announcementTarget" :options="announcementTargetOptions" />
          </label>
          <label class="gov-field">
            <span>公告标题</span>
            <n-input v-model:value="announcementTitle" placeholder="请输入公告标题" />
          </label>
          <label class="gov-field">
            <span>公告内容</span>
            <n-input
              v-model:value="announcementBody"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              placeholder="请输入公告正文"
            />
          </label>
          <n-button type="primary" class="gov-primary-btn" :loading="postingAnnouncement" @click="postAnnouncement">发布公告</n-button>
        </article>

        <article class="panel governance-list-panel">
          <header class="panel-head">
            <h2>近期公告</h2>
            <n-button quaternary size="small" class="gov-refresh-btn" @click="loadAnnouncements()">刷新</n-button>
          </header>
          <div v-if="!recentAnnouncements.length" class="governance-empty">暂无公告记录</div>
          <article v-for="item in recentAnnouncements" :key="item.id" class="gov-announce-item">
            <strong>{{ item.title }}</strong>
            <p>{{ item.body }}</p>
            <small>{{ item.target_role }} · {{ item.created_at?.slice(0, 16).replace('T', ' ') }}</small>
            <div class="gov-announce-actions">
              <n-button size="tiny" secondary @click="openEditAnnouncement(item)">编辑</n-button>
              <n-button
                size="tiny"
                quaternary
                type="error"
                :loading="deletingAnnouncementId === item.id"
                @click="removeAnnouncement(item.id)"
              >
                删除
              </n-button>
            </div>
          </article>
        </article>

        <n-modal
          v-model:show="showEditAnnouncementModal"
          preset="card"
          title="编辑公告"
          :style="{ maxWidth: '480px' }"
        >
          <label class="gov-field">
            <span>接收对象</span>
            <n-select v-model:value="editAnnouncementTarget" :options="announcementTargetOptions" />
          </label>
          <label class="gov-field">
            <span>公告标题</span>
            <n-input v-model:value="editAnnouncementTitle" />
          </label>
          <label class="gov-field">
            <span>公告内容</span>
            <n-input v-model:value="editAnnouncementBody" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
          </label>
          <template #footer>
            <n-button quaternary @click="showEditAnnouncementModal = false">取消</n-button>
            <n-button type="primary" class="gov-primary-btn" :loading="savingAnnouncement" @click="saveEditAnnouncement">保存</n-button>
          </template>
        </n-modal>

        <AdminGovernanceComboPanel class="governance-combo-span" @reviewed="loadAdminNotifications" />
      </section>

      <n-modal
        v-model:show="showStorageDetail"
        preset="card"
        title="资源与存储详情"
        style="width: min(560px, 92vw)"
      >
        <dl class="storage-detail-list">
          <div><dt>总容量</dt><dd>{{ storageInfo.total_tb }} TB</dd></div>
          <div><dt>已使用</dt><dd>{{ storageInfo.used_tb }} TB · {{ storageInfo.used_ratio }}%</dd></div>
          <div><dt>可用</dt><dd>{{ storageInfo.free_tb }} TB</dd></div>
        </dl>
        <ul class="storage-detail-breakdown">
          <li v-for="row in storageInfo.breakdown" :key="row.label">
            <span>{{ row.label }}</span>
            <em>{{ row.value_tb }} TB · {{ row.count }} 项</em>
          </li>
        </ul>
        <div v-if="storageInfo.detail" class="storage-detail-meta">
          <p>已批准资源 {{ storageInfo.detail.approved_resources }} · 待审 {{ storageInfo.detail.pending_review }}</p>
          <p>生成任务 {{ storageInfo.detail.resource_tasks }}（完成 {{ storageInfo.detail.completed_tasks }} / 失败 {{ storageInfo.detail.failed_tasks }}）</p>
          <p>试炼参与 {{ storageInfo.detail.participations }} · 作答记录 {{ storageInfo.detail.progress_answers }}</p>
        </div>
      </n-modal>

      <n-modal
        v-model:show="showAgentsDetail"
        preset="card"
        title="智能体运行详情"
        style="width: min(720px, 94vw)"
      >
        <div class="detail-modal-meta">
          <span>后端：{{ agentsStatusMeta.backend || agentOrchestrationData?.agent_backend || '—' }}</span>
          <span>成功率：{{ agentOrchestrationData?.runtime?.success_rate ?? '—' }}%</span>
          <span>平均延迟：{{ agentOrchestrationData?.runtime?.avg_latency_ms ?? '—' }} ms</span>
          <n-button quaternary size="tiny" :loading="agentsStatusLoading" @click="refreshAgentsStatus">刷新</n-button>
        </div>
        <div v-if="agentsStatusLoading && !liveAgentStatusSource.length" class="detail-modal-empty">加载中…</div>
        <ul v-else-if="liveAgentStatusSource.length" class="detail-agent-list">
          <li v-for="agent in liveAgentStatusSource" :key="agent.id">
            <div>
              <strong>{{ agent.name }}</strong>
              <small>{{ agent.role || agent.id }}</small>
            </div>
            <em :class="`status-${agent.status}`">{{ agentStatusLabel(agent.status) }}</em>
            <span>{{ formatAgentTime(agent.lastRunAt) }}</span>
            <span>{{ agent.avgLatency == null ? '—' : `${agent.avgLatency} ms` }}</span>
          </li>
        </ul>
        <div v-else class="detail-modal-empty">暂无智能体运行态数据</div>
      </n-modal>

      <n-modal
        v-model:show="showFeedDetail"
        preset="card"
        title="实时系统动态"
        style="width: min(640px, 94vw)"
      >
        <ul v-if="feedItems.length" class="detail-feed-list">
          <li v-for="item in feedItems" :key="`${item.title}-${item.time}`" :class="`tone-${item.tone}`">
            <span><n-icon :component="item.icon" /></span>
            <div>
              <strong>{{ item.title }}</strong>
              <small>{{ item.desc }}</small>
            </div>
            <time>{{ item.time }}</time>
          </li>
        </ul>
        <div v-else class="detail-modal-empty">暂无系统动态</div>
      </n-modal>

      <n-modal
        v-model:show="showAlertsDetail"
        preset="card"
        title="全部系统告警"
        style="width: min(640px, 94vw)"
      >
        <ul v-if="alertItems.length" class="detail-alert-list">
          <li v-for="item in alertItems" :key="`${item.title}-${item.time}`" :class="`tone-${item.tone}`">
            <em>{{ item.level }}</em>
            <div>
              <strong>{{ item.title }}</strong>
              <small>{{ item.desc }}</small>
            </div>
            <time>{{ item.time }}</time>
          </li>
        </ul>
        <div v-else class="detail-modal-empty">暂无告警</div>
      </n-modal>

      <AdminRunningTrialsDrilldown v-model:show="showRunningTrialsDrill" />
      <AdminPeopleDrilldown v-model:show="showPeopleDrill" :mode="peopleDrillMode" />

      <footer class="admin-footer">© {{ currentYear }} PLEX Universe. All rights reserved.</footer>
    </main>
  </div>
</template>

<style scoped>
.admin-shell {
  --violet: #8b5cf6;
  --violet-2: #a855f7;
  --green: #34d399;
  --amber: #f59e0b;
  --red: #ef4444;
  display: flex;
  min-height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  background: #050712;
  color: #eef2ff;
  font-family: 'Outfit', 'Noto Sans SC', 'Microsoft YaHei', system-ui, sans-serif;
}

.admin-sidebar {
  position: relative;
  z-index: 3;
  display: flex;
  width: 206px;
  flex-shrink: 0;
  flex-direction: column;
  border-right: 1px solid rgba(167, 139, 250, 0.16);
  background:
    radial-gradient(circle at 12% 5%, rgba(139, 92, 246, 0.2), transparent 24%),
    linear-gradient(180deg, rgba(7, 9, 22, 0.98), rgba(5, 7, 18, 0.99));
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  height: 108px;
  padding: 0 1.8rem;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: #a78bfa;
  font-size: 2rem;
  filter: drop-shadow(0 0 16px rgba(139, 92, 246, 0.8));
}

.brand strong {
  color: #ffffff;
  font-size: 1.62rem;
  letter-spacing: 0.04em;
}

.admin-nav {
  display: grid;
  gap: 1rem;
}

.nav-item {
  position: relative;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 0.9rem;
  align-items: center;
  min-height: 72px;
  border: 0;
  border-radius: 0 10px 10px 0;
  background: transparent;
  color: rgba(226, 232, 240, 0.62);
  cursor: pointer;
  font: inherit;
  padding: 0.8rem 1.25rem 0.8rem 1.65rem;
  text-align: left;
}

.nav-item.active {
  color: #fff;
  background: linear-gradient(90deg, rgba(139, 92, 246, 0.72), rgba(139, 92, 246, 0.16));
  box-shadow: inset 0 0 26px rgba(139, 92, 246, 0.28), 0 0 30px rgba(139, 92, 246, 0.22);
}

.nav-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: currentColor;
  font-size: 1.45rem;
}

.nav-item strong,
.nav-item small {
  display: block;
  white-space: nowrap;
}

.nav-item strong {
  font-size: 0.95rem;
  font-weight: 720;
}

.nav-item small {
  margin-top: 0.2rem;
  color: rgba(221, 214, 254, 0.62);
  font-size: 0.74rem;
}

.overseer-card {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 0.75rem;
  align-items: center;
  margin: auto 1.2rem 1.6rem;
  padding: 1rem;
  border: 1px solid rgba(167, 139, 250, 0.14);
  border-radius: 10px;
  background: rgba(24, 18, 48, 0.58);
}

.overseer-orbit {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  color: #c4b5fd;
  font-size: 1.8rem;
  border: 1px solid rgba(139, 92, 246, 0.65);
  background: radial-gradient(circle, rgba(139, 92, 246, 0.4), rgba(17, 14, 36, 0.9));
}

.overseer-card strong,
.overseer-card small,
.overseer-card em {
  display: block;
}

.overseer-card strong {
  color: white;
}

.overseer-card small {
  color: rgba(221, 214, 254, 0.6);
  font-size: 0.72rem;
}

.overseer-card em {
  grid-column: 1 / -1;
  justify-self: center;
  min-width: 120px;
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 999px;
  padding: 0.35rem 1rem;
  color: #d8b4fe;
  font-style: normal;
  text-align: center;
}

.sidebar-actions {
  display: flex;
  justify-content: space-around;
  padding: 0 1.5rem 1.6rem;
}

.sidebar-actions button,
.profile-button {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
}

.sidebar-actions button {
  color: #a78bfa;
  font-size: 1.2rem;
}

.admin-main {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 1.6rem 2rem 1rem;
  background:
    radial-gradient(circle at 77% 6%, rgba(139, 92, 246, 0.16), transparent 24%),
    radial-gradient(circle at 50% 48%, rgba(59, 130, 246, 0.06), transparent 35%),
    linear-gradient(180deg, #070917 0%, #040711 100%);
}

.admin-main::before {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.45;
  background-image:
    radial-gradient(1px 1px at 18% 24%, rgba(255, 255, 255, 0.36), transparent),
    radial-gradient(1px 1px at 76% 42%, rgba(167, 139, 250, 0.45), transparent),
    radial-gradient(1px 1px at 44% 72%, rgba(139, 92, 246, 0.34), transparent);
  background-size: 260px 260px;
  content: '';
}

.admin-topbar,
.metric-row,
.dashboard-grid,
.observer-grid,
.admin-footer {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
}

.dashboard-grid,
.observer-grid {
  flex: 1;
  min-height: 0;
  overflow: auto;
  align-content: start;
}

.admin-topbar {
  display: grid;
  grid-template-columns: minmax(300px, 1fr) minmax(280px, auto);
  gap: 1rem;
  align-items: start;
}

.title-block h1 {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin: 0;
  color: #ffffff;
  font-size: 1.85rem;
  line-height: 1;
}

.title-block h1 span {
  color: rgba(221, 214, 254, 0.74);
  font-size: 0.98rem;
  font-weight: 500;
}

.title-block h1 i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a855f7;
  box-shadow: 0 0 14px #a855f7;
}

.title-block p {
  margin: 0.75rem 0 0;
  color: rgba(226, 232, 240, 0.66);
}

.topbar-tools {
  display: flex;
  justify-content: flex-end;
  gap: 1.25rem;
  align-items: center;
}

.search-input {
  width: 376px;
}

.search-input :deep(.n-input) {
  --n-height: 44px !important;
  --n-color: rgba(8, 10, 24, 0.72) !important;
  --n-color-focus: rgba(11, 13, 30, 0.92) !important;
  --n-border: 1px solid rgba(167, 139, 250, 0.16) !important;
  --n-border-hover: 1px solid rgba(167, 139, 250, 0.34) !important;
  --n-text-color: #eef2ff !important;
  --n-placeholder-color: rgba(221, 214, 254, 0.45) !important;
}

.nexus-globe {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(139, 92, 246, 0.55);
  background: radial-gradient(circle, rgba(139, 92, 246, 0.48), rgba(14, 12, 32, 0.86));
  color: #c4b5fd;
  font-size: 1.6rem;
  cursor: pointer;
  padding: 0;
}

.admin-notif-panel {
  width: min(360px, 88vw);
}

.admin-notif-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
}

.admin-notif-panel__head strong {
  color: #1e1b4b;
  font-size: 0.95rem;
}

.admin-notif-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 320px;
  overflow-y: auto;
}

.admin-notif-item {
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  cursor: pointer;
}

.admin-notif-item--unread {
  background: rgba(139, 92, 246, 0.06);
}

.admin-notif-item__title {
  color: #1e293b;
  font-size: 0.86rem;
  font-weight: 600;
}

.admin-notif-item__body {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.8rem;
  line-height: 1.45;
}

.admin-notif-item__time {
  display: block;
  margin-top: 0.25rem;
  color: #94a3b8;
  font-size: 0.72rem;
}

.admin-notif-panel__empty {
  padding: 0.5rem 0;
  text-align: center;
  color: #64748b;
  font-size: 0.82rem;
}

.profile-button {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.35rem 0.7rem;
  border: 1px solid rgba(167, 139, 250, 0.18);
  border-radius: 999px;
  background: rgba(8, 10, 24, 0.62);
}

.profile-button > .n-icon:first-child {
  color: #ddd6fe;
  font-size: 1.8rem;
}

.profile-button strong,
.profile-button small {
  display: block;
  text-align: left;
}

.profile-button small,
.current-time {
  color: rgba(221, 214, 254, 0.62);
  font-size: 0.75rem;
}

.current-time {
  grid-column: 1 / -1;
  justify-self: end;
  margin-top: -0.2rem;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.metric-row--observer {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card,
.panel {
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background:
    radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.11), transparent 42%),
    linear-gradient(145deg, rgba(19, 20, 43, 0.88), rgba(8, 11, 26, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 18px 50px rgba(0, 0, 0, 0.22);
}

.metric-card {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: center;
  min-height: 96px;
  padding: 0.85rem 1rem;
  transition: none;
}

.metric-card:hover {
  transform: none;
}

.metric-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(139, 92, 246, 0.7);
  background: radial-gradient(circle, rgba(139, 92, 246, 0.36), rgba(8, 11, 26, 0.8));
  color: #c4b5fd;
  font-size: 1.6rem;
}

.tone-amber .metric-icon {
  border-color: rgba(245, 158, 11, 0.72);
  color: #fbbf24;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.32), rgba(8, 11, 26, 0.8));
}

.metric-card small,
.metric-card em {
  color: rgba(226, 232, 240, 0.68);
}

.metric-card strong {
  display: block;
  margin: 0.3rem 0;
  color: #ffffff;
  font-size: 1.45rem;
  font-weight: 600;
}

.metric-card em {
  font-style: normal;
}

.tone-green em,
.metric-card em {
  color: #34d399;
}

.dashboard-grid,
.observer-grid {
  --admin-panel-row-top: 334px;
  --admin-panel-row-bottom: 240px;
  --admin-panel-stack-h: calc(var(--admin-panel-row-top) + 1rem + var(--admin-panel-row-bottom));
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(390px, 1fr) minmax(390px, 1.02fr) minmax(390px, 1fr);
  grid-template-rows: var(--admin-panel-row-top) var(--admin-panel-row-bottom);
  gap: 1rem;
  margin-top: 1.05rem;
}

.panel {
  min-width: 0;
  overflow: hidden;
  padding: 1.15rem 1.25rem;
}

.panel--clickable {
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.panel--clickable:hover,
.panel--clickable:focus-visible {
  border-color: rgba(167, 139, 250, 0.42);
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.06), 0 18px 50px rgba(88, 60, 180, 0.22);
  outline: none;
}

.detail-modal-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem 1rem;
  margin-bottom: 0.9rem;
  color: rgba(196, 181, 253, 0.78);
  font-size: 0.84rem;
}

.detail-modal-empty {
  padding: 1.4rem 0;
  color: rgba(196, 181, 253, 0.7);
  text-align: center;
}

.detail-agent-list,
.detail-feed-list,
.detail-alert-list {
  display: grid;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: min(60vh, 520px);
  overflow: auto;
}

.detail-agent-list > li,
.detail-feed-list > li,
.detail-alert-list > li {
  display: grid;
  gap: 0.45rem 0.75rem;
  align-items: center;
  padding: 0.7rem 0.8rem;
  border: 1px solid rgba(167, 139, 250, 0.16);
  border-radius: 10px;
  background: rgba(12, 14, 32, 0.72);
}

.detail-agent-list > li {
  grid-template-columns: minmax(0, 1.4fr) auto auto auto;
}

.detail-feed-list > li,
.detail-alert-list > li {
  grid-template-columns: auto minmax(0, 1fr) auto;
}

.detail-agent-list strong,
.detail-feed-list strong,
.detail-alert-list strong {
  display: block;
  color: #f5f3ff;
}

.detail-agent-list small,
.detail-feed-list small,
.detail-alert-list small {
  display: block;
  margin-top: 0.2rem;
  color: rgba(226, 214, 255, 0.68);
  font-size: 0.8rem;
  line-height: 1.4;
}

.detail-agent-list em,
.detail-alert-list em {
  font-style: normal;
  color: #a78bfa;
  font-size: 0.82rem;
}

.detail-agent-list .status-running { color: #34d399; }
.detail-agent-list .status-success { color: #60a5fa; }
.detail-agent-list .status-error { color: #f87171; }
.detail-agent-list .status-idle { color: rgba(196, 181, 253, 0.72); }

.detail-agent-list span,
.detail-feed-list time,
.detail-alert-list time {
  color: rgba(196, 181, 253, 0.62);
  font-size: 0.78rem;
  white-space: nowrap;
}

.detail-feed-list span,
.detail-alert-list em {
  display: grid;
  place-items: center;
  min-width: 2rem;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel-head h2 {
  margin: 0;
  color: #fff;
  font-size: 1.08rem;
}

.panel-head button {
  border: 0;
  background: transparent;
  color: #a78bfa;
  cursor: pointer;
}

.period-select {
  width: 80px;
}

.period-select :deep(.n-base-selection) {
  --n-color: rgba(8, 10, 24, 0.62) !important;
  --n-border: 1px solid rgba(167, 139, 250, 0.14) !important;
  --n-text-color: #ddd6fe !important;
}

.progress-list {
  display: grid;
  gap: 1.25rem;
}

.weak-knowledge-top {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(167, 139, 250, 0.12);
}

.weak-knowledge-top h3 {
  margin: 0 0 0.65rem;
  font-size: 0.88rem;
  color: #ddd6fe;
}

.weak-knowledge-top ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.4rem;
}

.weak-knowledge-top li {
  display: flex;
  justify-content: space-between;
  font-size: 0.82rem;
  color: #a5b4fc;
}

.weak-knowledge-top em {
  font-style: normal;
  color: #c4b5fd;
}

.progress-list article {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 0.75rem;
  align-items: center;
}

.progress-list article > span,
.feed-list article > span,
.alert-list article > span {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 50%;
  color: #a78bfa;
  background: rgba(139, 92, 246, 0.16);
}

.progress-copy {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 1rem;
  align-items: center;
  color: rgba(226, 232, 240, 0.72);
}

.progress-copy em {
  color: #fff;
  font-style: normal;
}

.progress-copy small,
.agent-list em {
  color: #34d399;
}

.progress-list i {
  display: block;
  height: 7px;
  margin-top: 0.55rem;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(167, 139, 250, 0.13);
}

.progress-list b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7c3aed, #8b5cf6, #a855f7);
  box-shadow: 0 0 18px rgba(139, 92, 246, 0.65);
}

.agent-layout,
.storage-layout {
  display: grid;
  grid-template-columns: 205px minmax(0, 1fr);
  gap: 1.15rem;
  align-items: center;
}

.nexus-orbit {
  position: relative;
  display: grid;
  height: 230px;
  place-items: center;
}

.nexus-orbit span {
  position: absolute;
  width: calc(var(--ring) * 38px);
  height: calc(var(--ring) * 38px);
  border: 1px solid rgba(139, 92, 246, 0.22);
  border-radius: 50%;
}

.nexus-orbit i {
  position: absolute;
  left: calc(50% + cos(var(--dot) * 30deg) * 90px);
  top: calc(50% + sin(var(--dot) * 30deg) * 90px);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a78bfa;
  box-shadow: 0 0 14px rgba(167, 139, 250, 0.8);
}

.nexus-orbit b {
  display: grid;
  width: 82px;
  height: 82px;
  place-items: center;
  color: #ddd6fe;
  font-size: 2.9rem;
  filter: drop-shadow(0 0 22px rgba(139, 92, 246, 0.76));
}

.agent-list {
  display: grid;
  gap: 0.9rem;
}

.agent-list div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  color: rgba(226, 232, 240, 0.7);
}

.agent-list em::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 0.5rem;
  border-radius: 50%;
  background: currentColor;
}

.agent-list button {
  justify-self: start;
  border: 0;
  background: transparent;
  color: #a78bfa;
  cursor: pointer;
}

.feed-list,
.alert-list {
  display: grid;
  gap: 0.95rem;
}

.feed-list article,
.alert-list article {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
}

.feed-list strong,
.alert-list strong {
  display: block;
  color: rgba(255, 255, 255, 0.9);
}

.feed-list small,
.alert-list small,
.feed-list time,
.alert-list time {
  color: rgba(226, 232, 240, 0.52);
  font-size: 0.78rem;
}

.tone-red > span,
.tone-red .metric-icon {
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.42);
  background: rgba(239, 68, 68, 0.16);
}

.trend-panel,
.storage-panel,
.alerts-panel {
  min-height: 0;
}

.segmented {
  display: flex;
  gap: 0.35rem;
}

.segmented button {
  min-width: 42px;
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  color: rgba(221, 214, 254, 0.65);
}

.segmented button.active {
  background: rgba(139, 92, 246, 0.42);
  color: #fff;
}

.trend-chart {
  width: 100%;
  height: 145px;
}

.trend-chart polyline {
  fill: none;
  stroke: #8b5cf6;
  stroke-width: 3;
  filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.65));
}

.trend-chart circle {
  fill: #a78bfa;
  stroke: #ddd6fe;
  stroke-width: 1;
}

.chart-axis {
  display: flex;
  justify-content: space-between;
  color: rgba(226, 232, 240, 0.52);
  font-size: 0.78rem;
}

.storage-layout {
  grid-template-columns: 118px 94px minmax(0, 1fr);
}

.storage-ring {
  display: grid;
  width: 104px;
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #0a0d1f 54%, transparent 55%),
    conic-gradient(#a855f7 72%, #4f46e5 0 82%, rgba(167, 139, 250, 0.16) 0);
}

.storage-ring span {
  color: #ddd6fe;
  font-size: 2.5rem;
}

.storage-layout dl,
.storage-layout ul {
  margin: 0;
}

.storage-layout dl div,
.storage-layout li {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  color: rgba(226, 232, 240, 0.65);
}

.storage-layout dl div {
  display: block;
  margin-bottom: 0.55rem;
}

.storage-layout dd {
  margin: 0.1rem 0 0;
  color: #fff;
}

.storage-layout ul {
  display: grid;
  gap: 0.7rem;
  padding: 0;
  list-style: none;
}

.storage-layout strong {
  color: #fff;
  font-weight: 600;
}

.alert-list article {
  grid-template-columns: 34px 32px minmax(0, 1fr) auto;
}

.alert-list em {
  display: grid;
  width: 28px;
  height: 22px;
  place-items: center;
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.16);
  color: #c4b5fd;
  font-size: 0.72rem;
  font-style: normal;
}

.tone-amber em,
.tone-amber > span {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.16);
}

.tone-red em {
  color: #f87171;
  background: rgba(239, 68, 68, 0.16);
}

.admin-footer {
  margin-top: 0.85rem;
  color: rgba(226, 232, 240, 0.36);
  text-align: center;
}

.observer-grid {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: minmax(640px, 1fr) auto;
  gap: 1rem;
  margin-top: 1.05rem;
  align-items: stretch;
  align-content: start;
}

.observer-grid > .panel,
.observer-grid > .observatory-trials-panel,
.observer-grid > .observer-grid__footer {
  min-width: 0;
}

.observatory-trials-panel {
  grid-column: 1;
  grid-row: 1;
  display: flex;
  flex-direction: column;
  min-height: 640px;
}

.observatory-trials-panel--expanded {
  min-height: 640px;
}

.observer-grid__footer {
  grid-column: 1;
  grid-row: 2;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: stretch;
}

.observer-grid__footer > .panel {
  min-width: 0;
}

.anomaly-panel .anomaly-list {
  flex: 1;
  min-height: 0;
  align-content: start;
  overflow: auto;
}

.observatory-trials-panel :deep(.admin-trials) {
  flex: 1;
  min-height: 560px;
}

.observatory-trials-panel :deep(.admin-trials__body) {
  flex: 1;
  min-height: 520px;
}

.info-dot {
  display: inline-grid;
  width: 16px;
  height: 16px;
  margin-left: 0.35rem;
  place-items: center;
  border: 1px solid rgba(221, 214, 254, 0.32);
  border-radius: 50%;
  color: rgba(221, 214, 254, 0.72);
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 600;
}

.observe-select {
  width: 118px;
}

.observe-select :deep(.n-base-selection) {
  --n-color: rgba(8, 10, 24, 0.62) !important;
  --n-border: 1px solid rgba(167, 139, 250, 0.14) !important;
  --n-text-color: #ddd6fe !important;
}

.observatory-services {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.55rem;
  flex: 1;
  padding-top: 0.15rem;
  align-content: start;
}

.observatory-panel .observatory-service {
  grid-template-columns: 44px minmax(0, 1fr) auto;
  display: grid;
  align-items: center;
  justify-items: start;
  text-align: left;
  padding: 0.65rem 0.75rem;
  gap: 0.65rem;
}

.observatory-panel .observatory-service .n-icon {
  width: 40px;
  height: 40px;
  font-size: 1.1rem;
}

.observatory-panel .observatory-service small {
  justify-self: end;
}

.observatory-service {
  display: grid;
  justify-items: center;
  gap: 0.35rem;
  padding: 0.85rem 0.5rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 12px;
  background: rgba(12, 14, 32, 0.55);
  color: rgba(226, 232, 240, 0.82);
  font-size: 0.82rem;
  text-align: center;
}

.observatory-service .n-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border: 1px solid rgba(139, 92, 246, 0.45);
  border-radius: 50%;
  background: rgba(139, 92, 246, 0.12);
  color: #a78bfa;
  font-size: 1.25rem;
}

.observatory-service small {
  color: #34d399;
  font-size: 0.72rem;
}

.anomaly-list {
  display: grid;
  gap: 0.95rem;
}

.anomaly-list article {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 3.2rem;
  gap: 0.75rem;
  align-items: center;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid rgba(167, 139, 250, 0.08);
}

.anomaly-list article > span {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid rgba(139, 92, 246, 0.44);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.3), rgba(8, 11, 26, 0.8));
  color: #a78bfa;
  font-size: 1.35rem;
}

.anomaly-list strong {
  display: block;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.92rem;
}

.anomaly-list small {
  display: block;
  margin-top: 0.35rem;
  color: rgba(226, 232, 240, 0.52);
  font-size: 0.78rem;
}

.anomaly-list em {
  color: rgba(221, 214, 254, 0.8);
  font-size: 0.78rem;
  font-style: normal;
}

.anomaly-list i {
  grid-column: 2 / span 2;
  display: block;
  height: 5px;
  border-radius: 999px;
  background: rgba(167, 139, 250, 0.13);
}

.anomaly-list b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #8b5cf6, #a855f7);
}

.wave-chart {
  width: 100%;
  height: 130px;
}

.wave-chart polyline {
  fill: none;
  stroke: #8b5cf6;
  stroke-width: 3;
  filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.7));
}

.wave-chart circle {
  fill: #a78bfa;
  stroke: #ddd6fe;
  stroke-width: 1;
}

.module-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
}

.module-row--four article {
  min-height: 110px;
}

.module-row article {
  display: grid;
  min-height: 120px;
  place-items: center;
  gap: 0.55rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background: rgba(12, 14, 32, 0.66);
  text-align: center;
}

.module-row .n-icon {
  color: #a78bfa;
  font-size: 2rem;
}

.module-row strong {
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.86rem;
}

.module-row small {
  color: #34d399;
}

.module-row small::before {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 0.35rem;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.global-alert-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.global-alert-row article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 58px;
  align-items: center;
  min-height: 94px;
  padding: 0.9rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background: rgba(12, 14, 32, 0.66);
}

.global-alert-row small {
  color: rgba(226, 232, 240, 0.68);
}

.global-alert-row strong {
  display: block;
  margin-top: 0.35rem;
  color: #ffffff;
  font-size: 1.8rem;
  font-weight: 560;
}

.global-alert-row span {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 50%;
  color: #a78bfa;
  background: rgba(139, 92, 246, 0.16);
  font-size: 1.55rem;
}

.global-alert-row .tone-red span {
  color: #f472b6;
  background: rgba(236, 72, 153, 0.16);
}

.global-alert-row .tone-amber span {
  color: #f472b6;
  background: rgba(236, 72, 153, 0.14);
}

.alert-delta {
  margin: 0.8rem 0 0;
  color: #34d399;
}

@media (max-width: 1280px) {
  .admin-shell {
    max-height: none;
    overflow: auto;
  }

  .metric-row,
  .dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto;
  }

  .observer-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }

  .observatory-trials-panel {
    grid-column: 1;
    grid-row: 1;
  }

  .observer-grid__footer {
    grid-column: 1;
    grid-row: 2;
    grid-template-columns: 1fr;
  }

  .module-row,
  .module-row--four {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .admin-topbar {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .admin-shell {
    flex-direction: column;
  }

  .admin-sidebar {
    width: 100%;
  }

  .admin-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-row,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .observer-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .observatory-trials-panel,
  .observer-grid__footer {
    grid-column: 1;
    grid-row: auto;
  }

  .observer-grid__footer {
    grid-template-columns: 1fr;
  }

  .module-row,
  .module-row--four {
    grid-template-columns: 1fr;
  }

  .topbar-tools,
  .admin-topbar {
    align-items: stretch;
  }

  .topbar-tools {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}

.governance-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: auto minmax(0, 1fr);
  grid-auto-rows: auto;
  gap: 1rem;
  align-items: stretch;
  align-content: stretch;
  height: 100%;
  min-height: 0;
}

.governance-grid .panel:not(.governance-combo-span) {
  overflow: visible;
  height: auto;
  max-height: none;
}

.governance-announce-panel {
  grid-column: 1;
  grid-row: 1;
}

.governance-list-panel {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  flex-direction: column;
  align-self: stretch;
  min-height: 100%;
}

.governance-list-panel .governance-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 8rem;
}

.governance-settings-panel {
  grid-column: 1 / -1;
  grid-row: 2;
}

.governance-grid :deep(.gov-class-panel) {
  grid-column: 1 / -1;
  grid-row: 3;
}

@media (max-width: 1100px) {
  .governance-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto minmax(0, 1fr);
  }

  .governance-announce-panel,
  .governance-list-panel,
  .governance-settings-panel,
  .governance-grid :deep(.gov-class-panel),
  .governance-combo-span {
    grid-column: 1;
    grid-row: auto;
  }

  .governance-combo-span {
    min-height: calc(100dvh - 360px);
  }
}

.governance-hint {
  margin: 0 0 1rem;
  color: rgba(226, 232, 240, 0.68);
  font-size: 0.88rem;
  line-height: 1.5;
}

.gov-field {
  display: grid;
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}

.gov-field > span {
  color: rgba(226, 232, 240, 0.78);
  font-size: 0.82rem;
}

.governance-empty {
  padding: 1.5rem 0;
  color: rgba(226, 232, 240, 0.55);
  text-align: center;
}

.gov-announce-item {
  padding: 0.85rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.12);
}

.gov-announce-item:last-child {
  border-bottom: none;
}

.gov-announce-item strong {
  color: #fff;
  font-size: 0.95rem;
}

.gov-announce-item p {
  margin: 0.35rem 0;
  color: rgba(226, 232, 240, 0.72);
  font-size: 0.86rem;
  line-height: 1.45;
}

.gov-announce-item small {
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.78rem;
}

.gov-announce-actions {
  display: flex;
  gap: 0.45rem;
  margin-top: 0.45rem;
}

.gov-settings-section {
  margin-bottom: 1.2rem;
}

.gov-settings-section h3 {
  font-size: 0.85rem;
  color: rgba(167, 139, 250, 0.9);
  margin: 0 0 0.65rem;
  letter-spacing: 0.03em;
}

.gov-field--switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.3rem 0;
}

.gov-err {
  color: #ef4444;
}

.gov-field--inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  flex-wrap: wrap;
  padding: 0.3rem 0;
}

.gov-theme-options {
  display: flex;
  gap: 0.5rem;
}

.gov-theme-btn {
  padding: 0.35rem 0.85rem;
  border: 1px solid rgba(129, 140, 248, 0.25);
  border-radius: 8px;
  background: transparent;
  color: rgba(199, 210, 254, 0.75);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.15s;
}

.gov-theme-btn:hover {
  border-color: rgba(129, 140, 248, 0.55);
  color: #c7d2fe;
}

.gov-theme-btn--active {
  border-color: #818cf8;
  background: rgba(129, 140, 248, 0.15);
  color: #a5b4fc;
}

.metric-card--clickable {
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease;
}

.metric-card--clickable:hover {
  transform: translateY(-2px);
  border-color: rgba(196, 181, 253, 0.55);
}

.module-status-card {
  position: relative;
  overflow: hidden;
}

.module-status-card__pulse {
  position: absolute;
  inset: auto auto -18% -18%;
  width: 64px;
  height: 64px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(74, 222, 128, 0.35), transparent 70%);
  animation: module-pulse 2.4s ease-in-out infinite;
}

.module-status-card.pulse-b .module-status-card__pulse { animation-delay: 0.35s; }
.module-status-card.pulse-c .module-status-card__pulse { animation-delay: 0.7s; }
.module-status-card.pulse-d .module-status-card__pulse { animation-delay: 1.05s; }

.module-status-card__dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 0.35rem;
  border-radius: 999px;
  background: #4ade80;
  box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.55);
  animation: module-dot 1.8s ease-out infinite;
}

.governance-combo-span {
  grid-column: 1 / -1;
  grid-row: 2;
  align-self: stretch;
  min-height: calc(100dvh - 280px);
  height: 100%;
}

.storage-detail-list,
.storage-detail-breakdown {
  display: grid;
  gap: 0.45rem;
  margin: 0 0 0.85rem;
  padding: 0;
  list-style: none;
}

.storage-detail-list > div,
.storage-detail-breakdown li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  color: rgba(226, 214, 255, 0.86);
}

.storage-detail-meta p {
  margin: 0.35rem 0;
  color: rgba(196, 181, 253, 0.75);
  font-size: 0.84rem;
}

@keyframes module-pulse {
  0%, 100% { transform: scale(0.85); opacity: 0.45; }
  50% { transform: scale(1.25); opacity: 0.9; }
}

@keyframes module-dot {
  0% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.55); }
  70% { box-shadow: 0 0 0 8px rgba(74, 222, 128, 0); }
  100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }
}
</style>
