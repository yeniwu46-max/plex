<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NInput, NSelect, useMessage, type SelectOption } from 'naive-ui'
import {
  AlertCircleOutline,
  AnalyticsOutline,
  AppsOutline,
  BookOutline,
  ChevronDownOutline,
  ExitOutline,
  GitNetworkOutline,
  HardwareChipOutline,
  HelpCircleOutline,
  NotificationsOutline,
  PeopleOutline,
  PersonCircleOutline,
  PlanetOutline,
  SearchOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import { createAdminAnnouncement, fetchAdminAnnouncements } from '../api/adminAnnouncements'
import AdminAgentOrchestrationPanel from '../components/admin/AdminAgentOrchestrationPanel.vue'
import AdminClassRequestPanel from '../components/admin/AdminClassRequestPanel.vue'
import AdminKnowledgeNexusPanel from '../components/admin/AdminKnowledgeNexusPanel.vue'
import AdminTrialObservatoryPanel from '../components/admin/AdminTrialObservatoryPanel.vue'
import type { SystemAnnouncement } from '../api/teacherAnnouncements'

type NavKey = 'nexus' | 'agents' | 'knowledge' | 'observer' | 'governance'
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

const searchText = ref('')
const now = ref(new Date())
let clockTimer: ReturnType<typeof setInterval> | undefined

function formatDateTime(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const currentTimeText = computed(() => `当前时间 ${formatDateTime(now.value)}`)
const currentYear = computed(() => now.value.getFullYear())

const activeNav = ref<NavKey>('nexus')
const period = ref('today')
const auth = useAuthStore()
const router = useRouter()
const message = useMessage()

const announcementTitle = ref('')
const announcementBody = ref('')
const announcementTarget = ref<'teacher' | 'student' | 'all'>('teacher')
const postingAnnouncement = ref(false)
const recentAnnouncements = ref<SystemAnnouncement[]>([])

const announcementTargetOptions: SelectOption[] = [
  { label: '全体教师', value: 'teacher' },
  { label: '全体学生', value: 'student' },
  { label: '全体用户', value: 'all' },
]

const navItems = [
  { key: 'nexus' as const, label: '中央总控', sub: 'Central Nexus', icon: SettingsOutline },
  { key: 'agents' as const, label: '智能体编排', sub: 'Agent Orchestration', icon: PeopleOutline },
  { key: 'knowledge' as const, label: '知识图谱', sub: 'Knowledge Nexus', icon: GitNetworkOutline },
  { key: 'observer' as const, label: '系统观测', sub: 'System Observatory', icon: AppsOutline },
  { key: 'governance' as const, label: '权限与控制', sub: 'Governance Center', icon: ShieldCheckmarkOutline },
]

const periodOptions: SelectOption[] = [
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
]

const metricCards: MetricCard[] = [
  { label: '活跃学习者', value: '32,681', sub: '较昨日 ↑ 12.4%', icon: PeopleOutline, tone: 'purple' },
  { label: '活跃教师', value: '2,153', sub: '较昨日 ↑ 8.7%', icon: BookOutline, tone: 'amber' },
  { label: '运行智能体', value: '24', sub: '全部正常运行', icon: HardwareChipOutline, tone: 'purple' },
  { label: '知识节点总数', value: '156,782', sub: '较昨日 ↑ 3.6%', icon: PlanetOutline, tone: 'purple' },
  { label: '系统健康度', value: '98.7%', sub: '状态良好', icon: ShieldCheckmarkOutline, tone: 'purple' },
]

const observerMetricCards: MetricCard[] = [
  { label: '平台活跃度', value: '78.6%', sub: '较昨日 ↑ 8.6%', icon: AnalyticsOutline, tone: 'purple' },
  { label: '系统健康度', value: '96.2%', sub: '较昨日 ↑ 1.3%', icon: ShieldCheckmarkOutline, tone: 'purple' },
  { label: '实时风险信号', value: '7', sub: '较昨日 ↓ 1', icon: AlertCircleOutline, tone: 'purple' },
  { label: '在线智能体数量', value: '2,456', sub: '较昨日 ↑ 128', icon: HardwareChipOutline, tone: 'purple' },
]

const agentsMetricCards: MetricCard[] = [
  { label: '运行智能体', value: '24', sub: '较昨日 ↑ 9.1%', icon: HardwareChipOutline, tone: 'purple' },
  { label: '当前编排任务', value: '128', sub: '较昨日 ↑ 15.6%', icon: GitNetworkOutline, tone: 'purple' },
  { label: '平均响应延迟', value: '0.8s', sub: '较昨日 ↓ 8.7%', icon: AnalyticsOutline, tone: 'purple' },
  { label: '协同成功率', value: '98.6%', sub: '较昨日 ↑ 1.2%', icon: ShieldCheckmarkOutline, tone: 'purple' },
]

const knowledgeMetricCards: MetricCard[] = [
  { label: '知识节点总数', value: '48', sub: '试炼 24 + 星轨 24', icon: PlanetOutline, tone: 'purple' },
  { label: '学域数量', value: '12', sub: '6 试炼域 + 6 星轨域', icon: GitNetworkOutline, tone: 'purple' },
  { label: '关联边数', value: '14', sub: '前置与扩展关系', icon: BookOutline, tone: 'purple' },
  { label: '同步状态', value: '正常', sub: '最近一次 14:32', icon: ShieldCheckmarkOutline, tone: 'purple' },
]

const progressMetrics: ProgressMetric[] = [
  { label: '学习任务完成率', value: 78.6, delta: '↑ 6.2%', icon: SettingsOutline },
  { label: '试炼参与率', value: 65.3, delta: '↑ 4.8%', icon: BookOutline },
  { label: '知识掌握率', value: 72.1, delta: '↑ 5.3%', icon: ShieldCheckmarkOutline },
  { label: '学习活跃度', value: 83.7, delta: '↑ 7.1%', icon: SparklesOutline },
]

const agentRows: AgentRow[] = [
  { name: '学习画像智能体', status: '运行中' },
  { name: '知识图谱智能体', status: '运行中' },
  { name: '路径规划智能体', status: '运行中' },
  { name: '认知诊断智能体', status: '运行中' },
  { name: '试炼生成智能体', status: '运行中' },
  { name: '反馈评估智能体', status: '运行中' },
]

const feedItems: FeedItem[] = [
  { title: '知识图谱新增节点', desc: '新增节点「递归算法优化」已完成人图', time: '14:32', tone: 'purple', icon: GitNetworkOutline },
  { title: '学习路径生成完成', desc: '为用户「星航者-0421」生成个性化路径', time: '14:32', tone: 'purple', icon: BookOutline },
  { title: '智能体任务调度', desc: '路径规划智能体已完成任务调度', time: '14:32', tone: 'purple', icon: SparklesOutline },
  { title: '异常行为预警', desc: '检测到 3 起异常刷题行为', time: '14:32', tone: 'red', icon: AlertCircleOutline },
]

const alertItems: AlertItem[] = [
  { title: '数据库负载过高', desc: '主数据库负载已超过 85%', time: '14:28', level: '高', tone: 'red' },
  { title: '知识图谱更新延迟', desc: '部分领域知识更新延迟 15 分钟', time: '14:15', level: '中', tone: 'amber' },
  { title: '存储空间预警', desc: '试炼资源存储使用率超过 80%', time: '13:42', level: '低', tone: 'purple' },
]

const trendPoints = [12, 31, 22, 36, 28, 42, 35, 39]
const trendPolyline = computed(() => trendPoints.map((point, index) => `${index * 54},${128 - point * 2.2}`).join(' '))
const wavePoints = [48, 55, 66, 54, 49, 72, 86, 68, 51, 50, 74, 84, 72, 64, 70, 79]
const wavePolyline = computed(() => wavePoints.map((point, index) => `${index * 26},${130 - point}`).join(' '))

const currentNav = computed(() => navItems.find((item) => item.key === activeNav.value) ?? navItems[0])
const pageSubtitle = computed(() => {
  if (activeNav.value === 'observer') return '监测平台运行态势、活跃波动与全域风险信号'
  if (activeNav.value === 'agents') return '配置教师检查智能体编排，协同完成学生做题自动校验'
  if (activeNav.value === 'knowledge') return '浏览试炼与星轨知识节点、关联关系及题库绑定'
  return '实时掌控 PLEX 宇宙的运行状态与关键指标'
})
const visibleMetrics = computed(() => {
  if (activeNav.value === 'observer') return observerMetricCards
  if (activeNav.value === 'agents') return agentsMetricCards
  if (activeNav.value === 'knowledge') return knowledgeMetricCards
  return metricCards
})

const anomalyItems = [
  { title: '某星域活跃度下降', desc: '「北极星域」活跃度较昨日下降 12.4%', level: '中等', progress: 42, icon: GitNetworkOutline },
  { title: '某智能体响应延迟升高', desc: '路径规划智能体平均延迟升至 0.82s', level: '偏高', progress: 48, icon: NotificationsOutline },
  { title: '晚间访问峰值增强', desc: '20:00–22:00 访问量较昨日增长 18.7%', level: '提示', progress: 44, icon: AnalyticsOutline },
  { title: '某模块同步状态正常', desc: '知识图谱同步任务运行正常', level: '正常', progress: 92, icon: ShieldCheckmarkOutline },
]

const moduleCards = [
  { label: '学生端', icon: BookOutline },
  { label: '教师端', icon: PersonCircleOutline },
  { label: '管理端', icon: AppsOutline },
  { label: '知识图谱', icon: GitNetworkOutline },
  { label: 'Agent 链路', icon: PlanetOutline },
]

const observerAlerts = [
  { label: '紧急', value: 2, tone: 'red', icon: AlertCircleOutline },
  { label: '重要', value: 7, tone: 'amber', icon: AlertCircleOutline },
  { label: '提示', value: 23, tone: 'purple', icon: NotificationsOutline },
]

function setActiveNav(key: NavKey) {
  activeNav.value = key
  if (key === 'governance') {
    void loadAnnouncements()
  }
}

async function loadAnnouncements() {
  try {
    recentAnnouncements.value = await fetchAdminAnnouncements()
  } catch {
    recentAnnouncements.value = []
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
    message.success('公告已发布，教师端将收到通知')
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

onMounted(() => {
  clockTimer = setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (clockTimer !== undefined) clearInterval(clockTimer)
})
</script>

<template>
  <div class="admin-shell">
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
          <strong>Overseer</strong>
          <small>系统治理者</small>
        </div>
        <em>Lv.99</em>
      </section>

      <footer class="sidebar-actions">
        <button type="button" aria-label="设置"><n-icon :component="SettingsOutline" /></button>
        <button type="button" aria-label="帮助"><n-icon :component="HelpCircleOutline" /></button>
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
          <n-input v-model:value="searchText" round clearable placeholder="搜索用户、智能体、资源或事件..." class="search-input">
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <button type="button" class="icon-button" aria-label="通知"><n-icon :component="NotificationsOutline" /><i /></button>
          <span class="nexus-globe" aria-hidden="true"><n-icon :component="SparklesOutline" /></span>
          <button type="button" class="profile-button">
            <n-icon :component="PersonCircleOutline" />
            <span><strong>Overseer</strong><small>系统治理者</small></span>
            <n-icon :component="ChevronDownOutline" />
          </button>
        </div>

        <div class="current-time">{{ currentTimeText }}</div>
      </header>

      <section
        class="metric-row"
        :class="{ 'metric-row--observer': activeNav === 'observer' || activeNav === 'agents' || activeNav === 'knowledge' }"
        aria-label="核心指标"
      >
        <article v-for="item in visibleMetrics" :key="item.label" class="metric-card" :class="`tone-${item.tone}`">
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
            <article v-for="item in progressMetrics" :key="item.label">
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
        </article>

        <article class="panel agents-panel">
          <header class="panel-head">
            <h2>智能体运行状态</h2>
            <button type="button">全部智能体 ›</button>
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
              <button type="button">更多智能体 ›</button>
            </div>
          </div>
        </article>

        <article class="panel feed-panel">
          <header class="panel-head">
            <h2>实时系统动态</h2>
            <button type="button">全部动态 ›</button>
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
            <div class="segmented"><button class="active">7日</button><button>30日</button><button>90日</button></div>
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
            <circle v-for="point in trendPoints" :key="point" :cx="trendPoints.indexOf(point) * 54" :cy="128 - point * 2.2" r="4" />
          </svg>
          <div class="chart-axis"><span>05-14</span><span>05-15</span><span>05-16</span><span>05-17</span><span>05-18</span><span>05-19</span><span>05-20</span></div>
        </article>

        <article class="panel storage-panel">
          <header class="panel-head">
            <h2>资源与存储</h2>
            <button type="button">查看详情 ›</button>
          </header>
          <div class="storage-layout">
            <div class="storage-ring"><span><n-icon :component="SparklesOutline" /></span></div>
            <dl>
              <div><dt>总存储空间</dt><dd>100 TB</dd></div>
              <div><dt>已使用</dt><dd>72 TB</dd></div>
              <div><dt>可用空间</dt><dd>28 TB</dd></div>
            </dl>
            <ul>
              <li><span>知识资源</span><strong>48.2 TB</strong></li>
              <li><span>试炼资源</span><strong>14.6 TB</strong></li>
              <li><span>用户数据</span><strong>7.8 TB</strong></li>
              <li><span>系统日志</span><strong>1.4 TB</strong></li>
            </ul>
          </div>
        </article>

        <article class="panel alerts-panel">
          <header class="panel-head">
            <h2>系统告警</h2>
            <button type="button">全部告警 ›</button>
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
        <AdminTrialObservatoryPanel class="panel observatory-trials-panel" />

        <article class="panel observatory-panel">
          <header class="panel-head">
            <h2>平台运行态势 <span class="info-dot">i</span></h2>
            <n-select :value="'realtime'" :options="[{ label: '实时监测', value: 'realtime' }, { label: '近 1 小时', value: 'hour' }]" size="small" class="observe-select" />
          </header>
          <div class="observatory-map">
            <div class="pulse-field" aria-hidden="true">
              <span v-for="ring in 9" :key="ring" :style="{ '--ring': ring }" />
              <i v-for="bar in 34" :key="bar" :style="{ '--bar': bar }" />
              <b><n-icon :component="SparklesOutline" /></b>
            </div>
            <div class="map-node map-node--user"><n-icon :component="PersonCircleOutline" /><span>用户交互</span></div>
            <div class="map-node map-node--agent"><n-icon :component="HardwareChipOutline" /><span>智能体响应</span></div>
            <div class="map-node map-node--resource"><n-icon :component="AppsOutline" /><span>资源调度</span></div>
            <div class="map-node map-node--knowledge"><n-icon :component="BookOutline" /><span>知识服务</span></div>
            <div class="map-node map-node--task"><n-icon :component="AppsOutline" /><span>任务处理</span></div>
          </div>
        </article>

        <article class="panel anomaly-panel">
          <header class="panel-head">
            <h2>异常洞察</h2>
            <button type="button">查看全部 ›</button>
          </header>
          <div class="anomaly-list">
            <article v-for="item in anomalyItems" :key="item.title">
              <span><n-icon :component="item.icon" /></span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.desc }}</small>
              </div>
              <em>{{ item.level }}</em>
              <i><b :style="{ width: `${item.progress}%` }" /></i>
            </article>
          </div>
        </article>

        <article class="panel wave-panel">
          <header class="panel-head">
            <h2>近7日平台波动 <span class="info-dot">i</span></h2>
            <n-select :value="'activity'" :options="[{ label: '活跃度', value: 'activity' }, { label: '健康度', value: 'health' }]" size="small" class="observe-select" />
          </header>
          <svg class="wave-chart" viewBox="0 0 390 150" role="img" aria-label="近7日平台波动">
            <defs>
              <linearGradient id="waveFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgba(139, 92, 246, .62)" />
                <stop offset="100%" stop-color="rgba(139, 92, 246, 0)" />
              </linearGradient>
            </defs>
            <path :d="`M0,150 L${wavePolyline} L390,150 Z`" fill="url(#waveFill)" />
            <polyline :points="wavePolyline" />
            <circle v-for="(point, index) in wavePoints" :key="`${point}-${index}`" :cx="index * 26" :cy="130 - point" r="3" />
          </svg>
          <div class="chart-axis"><span>05-14</span><span>05-15</span><span>05-16</span><span>05-17</span><span>05-18</span><span>05-19</span><span>05-20</span></div>
        </article>

        <article class="panel module-panel">
          <header class="panel-head">
            <h2>模块运行状态 <span class="info-dot">i</span></h2>
          </header>
          <div class="module-row">
            <article v-for="item in moduleCards" :key="item.label">
              <n-icon :component="item.icon" />
              <strong>{{ item.label }}</strong>
              <small>正常</small>
            </article>
          </div>
        </article>

        <article class="panel global-alert-panel">
          <header class="panel-head">
            <h2>全域告警 <span class="info-dot">i</span></h2>
            <button type="button">查看全部 ›</button>
          </header>
          <div class="global-alert-row">
            <article v-for="item in observerAlerts" :key="item.label" :class="`tone-${item.tone}`">
              <div>
                <small>{{ item.label }}</small>
                <strong>{{ item.value }}</strong>
              </div>
              <span><n-icon :component="item.icon" /></span>
            </article>
          </div>
          <p class="alert-delta">较昨日 ↓ 2</p>
        </article>
      </section>

      <admin-agent-orchestration-panel v-else-if="activeNav === 'agents'" />

      <admin-knowledge-nexus-panel v-else-if="activeNav === 'knowledge'" />

      <section v-else-if="activeNav === 'governance'" class="dashboard-grid governance-grid" aria-label="权限与公告">
        <article class="panel governance-announce-panel">
          <header class="panel-head">
            <h2>向教师发布公告</h2>
          </header>
          <p class="governance-hint">教师登录后将在顶栏通知中收到管理员公告；发布作业请由教师在试炼中枢操作。</p>
          <label class="gov-field">
            <span>接收对象</span>
            <n-select v-model:value="announcementTarget" :options="announcementTargetOptions" />
          </label>
          <label class="gov-field">
            <span>公告标题</span>
            <n-input v-model:value="announcementTitle" placeholder="例如：本周教研安排" />
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
          <n-button type="primary" :loading="postingAnnouncement" @click="postAnnouncement">发布公告</n-button>
        </article>

        <article class="panel governance-list-panel">
          <header class="panel-head">
            <h2>近期公告</h2>
            <button type="button" @click="loadAnnouncements()">刷新</button>
          </header>
          <div v-if="!recentAnnouncements.length" class="governance-empty">暂无公告记录</div>
          <article v-for="item in recentAnnouncements" :key="item.id" class="gov-announce-item">
            <strong>{{ item.title }}</strong>
            <p>{{ item.body }}</p>
            <small>{{ item.target_role }} · {{ item.created_at?.slice(0, 16).replace('T', ' ') }}</small>
          </article>
        </article>

        <admin-class-request-panel />
      </section>

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
.icon-button,
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
  grid-template-columns: minmax(300px, 1fr) minmax(620px, auto);
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

.icon-button {
  position: relative;
  color: #ddd6fe;
  font-size: 1.4rem;
}

.icon-button i {
  position: absolute;
  right: -2px;
  top: -4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a855f7;
  box-shadow: 0 0 10px #a855f7;
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
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1rem;
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
  grid-template-columns: 86px minmax(0, 1fr);
  align-items: center;
  min-height: 128px;
  padding: 1.2rem 1.45rem;
}

.metric-icon {
  display: grid;
  width: 80px;
  height: 80px;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(139, 92, 246, 0.7);
  background: radial-gradient(circle, rgba(139, 92, 246, 0.36), rgba(8, 11, 26, 0.8));
  color: #c4b5fd;
  font-size: 2.4rem;
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
  margin: 0.45rem 0;
  color: #ffffff;
  font-size: 1.9rem;
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
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  grid-template-rows: minmax(300px, auto) minmax(220px, auto);
  gap: 1rem;
  margin-top: 1.05rem;
  align-items: stretch;
}

.observatory-trials-panel {
  grid-column: 1 / -1;
  grid-row: 1;
}

.observatory-panel,
.anomaly-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.observatory-panel {
  grid-column: 1 / 3;
  grid-row: 2;
}

.anomaly-panel {
  grid-column: 3;
  grid-row: 2;
}

.anomaly-panel .anomaly-list {
  flex: 1;
  min-height: 0;
  max-height: 280px;
  align-content: start;
  overflow: auto;
}

.wave-panel {
  grid-column: 1;
  grid-row: 2;
}

.module-panel {
  grid-column: 2;
  grid-row: 2;
}

.global-alert-panel {
  grid-column: 3;
  grid-row: 2;
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

.observatory-map {
  position: relative;
  flex: 1;
  min-height: 240px;
  max-height: 280px;
  overflow: hidden;
  border-top: 1px solid rgba(167, 139, 250, 0.08);
}

.pulse-field {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.pulse-field span {
  position: absolute;
  width: calc(var(--ring) * 88px);
  height: calc(var(--ring) * 28px);
  transform: rotate(-5deg);
  border: 1px solid rgba(139, 92, 246, 0.24);
  border-radius: 50%;
}

.pulse-field i {
  position: absolute;
  left: calc(50% + (var(--bar) - 17) * 10px);
  top: calc(50% - ((var(--bar) % 9) * 8px));
  width: 3px;
  height: calc(22px + (var(--bar) % 7) * 9px);
  transform-origin: bottom;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(167, 139, 250, 0.9), rgba(139, 92, 246, 0.05));
  box-shadow: 0 0 12px rgba(139, 92, 246, 0.75);
}

.pulse-field b {
  position: relative;
  display: grid;
  width: 92px;
  height: 92px;
  place-items: center;
  color: #ddd6fe;
  font-size: 3.2rem;
  filter: drop-shadow(0 0 24px rgba(139, 92, 246, 0.9));
}

.map-node {
  position: absolute;
  display: grid;
  place-items: center;
  gap: 0.35rem;
  color: rgba(226, 232, 240, 0.76);
  font-size: 0.86rem;
}

.map-node .n-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid rgba(139, 92, 246, 0.55);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.36), rgba(8, 11, 26, 0.78));
  color: #a78bfa;
  font-size: 1.45rem;
  box-shadow: 0 0 18px rgba(139, 92, 246, 0.35);
}

.map-node--user {
  left: 18%;
  top: 10%;
}

.map-node--agent {
  right: 16%;
  top: 10%;
}

.map-node--resource {
  right: 12%;
  bottom: 14%;
}

.map-node--knowledge {
  left: 50%;
  bottom: 10%;
  transform: translateX(-50%);
}

.map-node--task {
  left: 14%;
  bottom: 14%;
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
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.6rem;
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
  .dashboard-grid,
  .observer-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto;
  }

  .observatory-panel {
    grid-column: 1 / -1;
  }

  .observatory-panel,
  .anomaly-panel,
  .wave-panel,
  .module-panel,
  .global-alert-panel {
    grid-row: auto;
  }

  .anomaly-panel .anomaly-list {
    max-height: none;
  }

  .observatory-map {
    max-height: none;
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
  .dashboard-grid,
  .observer-grid {
    grid-template-columns: 1fr;
  }

  .topbar-tools,
  .admin-topbar {
    align-items: stretch;
  }

  .topbar-tools {
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }
}

.governance-grid {
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 1rem;
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
</style>
