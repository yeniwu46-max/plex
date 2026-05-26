<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NIcon, NSelect, NSlider, NSwitch, useMessage, type SelectOption } from 'naive-ui'
import {
  AlarmOutline,
  ArchiveOutline,
  CloudUploadOutline,
  DownloadOutline,
  FingerPrintOutline,
  LockClosedOutline,
  NotificationsOutline,
  PeopleOutline,
  PersonOutline,
  RefreshOutline,
  SchoolOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'

interface SideItem {
  key: string
  label: string
  icon: typeof PeopleOutline
}

interface StrategyItem {
  key: string
  title: string
  desc: string
  icon: typeof SettingsOutline
  enabled: boolean
}

interface NoticeItem {
  key: string
  title: string
  desc: string
  icon: typeof NotificationsOutline
  enabled: boolean
}

const message = useMessage()
const systemTab = ref('class')
const ruleTab = ref('trial')
const openTime = ref('08-22')
const dailyLimit = ref('3')
const punish = ref('none')
const dataScope = ref('teacher')
const difficulty = ref(48)

const timeOptions: SelectOption[] = [
  { label: '每日 08:00 - 22:00', value: '08-22' },
  { label: '每日 09:00 - 21:00', value: '09-21' },
  { label: '全天开放', value: 'all-day' },
]

const limitOptions: SelectOption[] = [
  { label: '1 次', value: '1' },
  { label: '3 次', value: '3' },
  { label: '5 次', value: '5' },
  { label: '不限', value: 'unlimited' },
]

const punishOptions: SelectOption[] = [
  { label: '无惩罚', value: 'none' },
  { label: '扣除少量积分', value: 'points' },
  { label: '冷却 30 分钟', value: 'cooldown' },
]

const dataScopeOptions: SelectOption[] = [
  { label: '仅教师可见', value: 'teacher' },
  { label: '班级成员可见', value: 'class' },
  { label: '管理员可见', value: 'admin' },
]

const systemItems: SideItem[] = [
  { key: 'class', label: '班级信息', icon: PeopleOutline },
  { key: 'members', label: '成员管理', icon: PersonOutline },
  { key: 'roles', label: '角色权限', icon: LockClosedOutline },
  { key: 'notice', label: '通知设置', icon: NotificationsOutline },
  { key: 'preference', label: '系统偏好', icon: SettingsOutline },
]

const ruleItems: SideItem[] = [
  { key: 'trial', label: '试炼规则', icon: PeopleOutline },
  { key: 'reward', label: '奖励规则', icon: SettingsOutline },
  { key: 'abyss', label: '深渊规则', icon: FingerPrintOutline },
  { key: 'quest', label: '委托规则', icon: SparklesOutline },
]

const strategies = ref<StrategyItem[]>([
  { key: 'recommend', title: '个性化推荐', desc: '根据 Explorer 表现智能推荐任务', icon: SettingsOutline, enabled: true },
  { key: 'difficulty', title: '动态难度调整', desc: '根据整体表现动态调整试炼难度', icon: ShieldCheckmarkOutline, enabled: true },
  { key: 'risk', title: '知识断层检测', desc: '识别知识薄弱点与潜在风险', icon: FingerPrintOutline, enabled: true },
  { key: 'rhythm', title: '学习节奏分析', desc: '分析班级整体学习节奏与疲劳度', icon: RefreshOutline, enabled: true },
])

const notices = ref<NoticeItem[]>([
  { key: 'done', title: '试炼完成通知', desc: '当 Explorer 完成试炼时通知', icon: SettingsOutline, enabled: true },
  { key: 'abyss', title: '深渊挑战预警', desc: '当深渊试炼风险升高时通知', icon: FingerPrintOutline, enabled: true },
  { key: 'ai', title: 'AI 洞察推送', desc: 'AI 发现重要洞察时推送', icon: ShieldCheckmarkOutline, enabled: true },
  { key: 'system', title: '系统公告', desc: '接收系统更新与重要公告', icon: ArchiveOutline, enabled: false },
])

const channels = [
  { label: '站内信', icon: ArchiveOutline, active: true },
  { label: '邮箱', icon: NotificationsOutline, active: false },
  { label: '微信', icon: PeopleOutline, active: false },
  { label: '短信', icon: AlarmOutline, active: false },
]

function saveClassInfo() {
  message.success('班级设置已保存')
}

function clearCache() {
  message.success('缓存已清理')
}
</script>

<template>
  <TeacherDashboardShell
    active-nav="admin"
    page-title="控制中枢"
    page-subtitle="管理班级系统设置，配置教学参数与 AI 策略"
    search-placeholder="搜索系统设置"
    hide-search
    toolbar-label="控制中枢筛选与状态"
  >
    <template #toolbar-trailing>
      <button type="button" class="teacher-toolbar__notify" aria-label="通知"><span /></button>
    </template>

    <section class="control-center" aria-label="控制中枢">
      <section class="control-panel system-panel">
        <h2>系统设置</h2>
        <div class="system-layout">
          <nav class="settings-nav" aria-label="系统设置分类">
            <button
              v-for="item in systemItems"
              :key="item.key"
              type="button"
              :class="{ active: systemTab === item.key }"
              @click="systemTab = item.key"
            >
              <n-icon :component="item.icon" />
              <span>{{ item.label }}</span>
            </button>
          </nav>

          <div class="class-orbit" aria-hidden="true">
            <span v-for="ring in 7" :key="ring" :style="{ '--ring': ring }" />
            <i />
            <n-icon :component="SchoolOutline" />
          </div>

          <div class="class-info">
            <header>
              <h3>计算机科学 2025</h3>
              <button type="button" aria-label="编辑班级信息">✎</button>
            </header>
            <dl>
              <div><dt>班级 ID:</dt><dd>CS2025-NAV-01</dd></div>
              <div><dt>创建时间:</dt><dd>2025.02.18</dd></div>
              <div><dt>班级人数:</dt><dd>40</dd></div>
              <div><dt>年级:</dt><dd>大二</dd></div>
              <div><dt>学期:</dt><dd>2024-2025 春季学期</dd></div>
            </dl>
            <n-button secondary class="outline-orange" @click="saveClassInfo">编辑班级信息</n-button>
          </div>
        </div>
      </section>

      <section class="control-panel ai-panel">
        <header class="panel-head">
          <h2>AI 教学策略</h2>
          <span class="enabled-pill">已启用</span>
        </header>
        <div class="ai-layout">
          <div class="bot-orbit" aria-hidden="true">
            <span v-for="ring in 6" :key="ring" :style="{ '--ring': ring }" />
            <i />
            <b><span /></b>
          </div>
          <div class="strategy-list">
            <article v-for="item in strategies" :key="item.key">
              <span><n-icon :component="item.icon" /></span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.desc }}</small>
              </div>
              <n-switch v-model:value="item.enabled" class="orange-switch" />
            </article>
            <label class="select-line">
              <span>数据更新频率</span>
              <n-select :value="'2h'" :options="[{ label: '每 2 小时', value: '2h' }, { label: '每 6 小时', value: '6h' }]" class="field-select" />
            </label>
          </div>
        </div>
      </section>

      <section class="control-panel notice-panel">
        <h2>通知设置</h2>
        <div class="notice-layout">
          <div class="bell-orbit" aria-hidden="true">
            <span v-for="ring in 5" :key="ring" :style="{ '--ring': ring }" />
            <n-icon :component="NotificationsOutline" />
          </div>
          <div class="notice-list">
            <article v-for="item in notices" :key="item.key">
              <span><n-icon :component="item.icon" /></span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.desc }}</small>
              </div>
              <n-switch v-model:value="item.enabled" class="orange-switch" />
            </article>
          </div>
        </div>
        <footer class="channel-row">
          <span>通知接收渠道</span>
          <button v-for="item in channels" :key="item.label" type="button" :class="{ active: item.active }">
            <n-icon :component="item.icon" />
            {{ item.label }}
          </button>
        </footer>
      </section>

      <section class="control-panel rules-panel">
        <h2>探索规则配置</h2>
        <div class="rules-layout">
          <nav class="settings-nav settings-nav--compact" aria-label="探索规则分类">
            <button
              v-for="item in ruleItems"
              :key="item.key"
              type="button"
              :class="{ active: ruleTab === item.key }"
              @click="ruleTab = item.key"
            >
              <n-icon :component="item.icon" />
              <span>{{ item.label }}</span>
            </button>
          </nav>
          <div class="rules-form">
            <label>
              <span>试炼开放时间</span>
              <n-select v-model:value="openTime" :options="timeOptions" class="field-select" />
            </label>
            <label>
              <span>每日可挑战次数</span>
              <n-select v-model:value="dailyLimit" :options="limitOptions" class="field-select" />
            </label>
            <div class="difficulty-field">
              <span>试炼难度范围</span>
              <n-slider v-model:value="difficulty" :min="0" :max="100" class="orange-slider" />
              <div><small>简单</small><small>中等</small><small>困难</small><small>噩梦</small></div>
            </div>
            <label>
              <span>失败惩罚设置</span>
              <n-select v-model:value="punish" :options="punishOptions" class="field-select" />
            </label>
          </div>
        </div>
      </section>

      <section class="control-panel security-panel">
        <h2>数据与安全</h2>
        <div class="security-layout">
          <div class="shield-orbit" aria-hidden="true">
            <span v-for="ring in 5" :key="ring" :style="{ '--ring': ring }" />
            <n-icon :component="LockClosedOutline" />
          </div>
          <div class="security-list">
            <label>
              <span>数据可见范围</span>
              <n-select v-model:value="dataScope" :options="dataScopeOptions" class="field-select small-select" />
            </label>
            <button type="button">
              <div><strong>数据导出</strong><small>导出班级数据报告</small></div>
              <n-icon :component="DownloadOutline" />
            </button>
            <button type="button">
              <div><strong>数据备份</strong><small>上次备份：2025.05.18 10:30</small></div>
              <n-icon :component="CloudUploadOutline" />
            </button>
            <button type="button">
              <div><strong>账户安全</strong><small>修改密码与安全设置</small></div>
              <span>›</span>
            </button>
          </div>
        </div>
        <footer class="security-footer">
          <n-button secondary class="outline-orange" @click="clearCache">清除缓存</n-button>
          <span>已使用 120MB / 2GB</span>
        </footer>
      </section>
    </section>
  </TeacherDashboardShell>
</template>

<style scoped>
.control-toolbar {
  position: relative;
  z-index: 4;
  display: flex;
  width: fit-content;
  align-items: center;
  gap: 1.35rem;
  margin: -3.95rem var(--plex-page-gutter-x) 1.8rem auto;
  color: rgba(255, 247, 237, 0.84);
}

.class-select {
  width: 210px;
}

.class-select :deep(.n-base-selection),
.field-select :deep(.n-base-selection) {
  --n-color: rgba(5, 18, 30, 0.72) !important;
  --n-color-active: rgba(5, 18, 30, 0.92) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.13) !important;
  --n-border-active: 1px solid rgba(251, 146, 60, 0.46) !important;
  --n-border-hover: 1px solid rgba(251, 146, 60, 0.34) !important;
  --n-text-color: #fff7ed !important;
  --n-placeholder-color: rgba(221, 230, 239, 0.5) !important;
}

.keeper-chip {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 220px;
  padding-left: 1.35rem;
  border-left: 1px solid rgba(219, 235, 249, 0.1);
}

.keeper-avatar {
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 30%, rgba(251, 146, 60, 0.22), transparent 54%), #061827;
  border: 1px solid rgba(255, 237, 213, 0.24);
  box-shadow: 0 0 0 5px rgba(251, 146, 60, 0.06);
}

.keeper-avatar span {
  width: 29px;
  height: 21px;
  border-radius: 9px;
  background: #e9f3fb;
  box-shadow: inset 0 -8px #111926;
}

.keeper-chip strong {
  display: block;
  color: rgba(255, 247, 237, 0.92);
  font-size: 0.9rem;
}

.keeper-chip small {
  color: #34d399;
}

.notify-btn {
  position: relative;
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 1px solid rgba(219, 235, 249, 0.1);
  border-radius: 13px;
  background: rgba(5, 18, 30, 0.62);
  cursor: pointer;
}

.notify-btn span {
  width: 14px;
  height: 16px;
  border: 2px solid rgba(255, 247, 237, 0.8);
  border-radius: 8px 8px 5px 5px;
}

.notify-btn::after {
  position: absolute;
  top: 13px;
  right: 14px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fb923c;
  content: '';
}

:deep(.plex-topbar__heading h1)::after {
  content: 'CONTROL CENTER';
  color: rgba(221, 230, 239, 0.62);
  font-size: 1rem;
  font-weight: 500;
}

:deep(.plex-topbar__heading h1 span) {
  background: #fb923c;
  box-shadow: 0 0 12px rgba(251, 146, 60, 0.85);
}

:deep(.plex-nav--active) {
  color: #fb923c !important;
  background: linear-gradient(90deg, rgba(251, 146, 60, 0.23), rgba(251, 146, 60, 0.08) 72%, transparent) !important;
  box-shadow: inset 0 0 24px rgba(251, 146, 60, 0.12), 0 0 22px rgba(251, 146, 60, 0.12) !important;
}

:deep(.plex-nav--active .plex-nav__bar) {
  background: linear-gradient(180deg, #fb923c, #f59e0b);
  box-shadow: 0 0 12px rgba(251, 146, 60, 0.65);
}

:deep(.plex-nav--active .plex-nav__label),
:deep(.plex-nav--active .plex-nav__sub),
:deep(.plex-nav--active .plex-nav__icon) {
  color: #fb923c !important;
  text-shadow: 0 0 14px rgba(251, 146, 60, 0.46);
}

.control-center {
  --orange: #fb923c;
  --gold: #fbbf24;
  --teal: #34d399;
  display: grid;
  grid-template-columns: minmax(430px, 1fr) minmax(320px, 0.72fr) minmax(420px, 0.88fr);
  grid-template-rows: 356px 374px;
  gap: 1rem;
  min-height: 0;
  overflow: auto;
  padding: 0 var(--plex-page-gutter-x) 2rem;
}

.system-panel {
  grid-column: 1 / span 2;
  grid-row: 1;
}

.ai-panel {
  grid-column: 3;
  grid-row: 1;
  padding: 1.15rem 1.3rem;
}

.notice-panel {
  grid-column: 1;
  grid-row: 2;
}

.rules-panel {
  grid-column: 2;
  grid-row: 2;
}

.security-panel {
  grid-column: 3;
  grid-row: 2;
}

.control-panel {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 16px;
  background: radial-gradient(circle at 48% 0%, rgba(251, 146, 60, 0.08), transparent 34%),
    linear-gradient(145deg, rgba(5, 18, 30, 0.91), rgba(3, 12, 20, 0.78));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 22px 70px rgba(0, 0, 0, 0.2);
  padding: 1.4rem;
}

.control-panel h2 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.18rem;
  font-weight: 740;
}

.system-layout {
  display: grid;
  grid-template-columns: 180px minmax(220px, 1fr) 230px;
  gap: 1.25rem;
  height: calc(100% - 1.8rem);
  align-items: center;
  margin-top: 0.55rem;
}

.settings-nav {
  display: grid;
  gap: 0.62rem;
  align-content: center;
  height: 100%;
  padding-right: 1rem;
  border-right: 1px solid rgba(219, 235, 249, 0.08);
}

.settings-nav button {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  min-height: 48px;
  padding: 0 0.85rem;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: rgba(221, 230, 239, 0.64);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.settings-nav button.active {
  border-color: rgba(251, 146, 60, 0.48);
  background: rgba(251, 146, 60, 0.13);
  color: var(--orange);
  box-shadow: 0 0 22px rgba(251, 146, 60, 0.15);
}

.settings-nav .n-icon {
  font-size: 1.35rem;
}

.class-orbit,
.bot-orbit,
.bell-orbit,
.shield-orbit {
  position: relative;
  display: grid;
  place-items: center;
}

.class-orbit {
  height: 250px;
}

.class-orbit span,
.bot-orbit span,
.bell-orbit span,
.shield-orbit span {
  position: absolute;
  width: calc(var(--ring) * 31px);
  height: calc(var(--ring) * 31px);
  border: 1px solid rgba(251, 146, 60, 0.16);
  border-radius: 50%;
}

.class-orbit i {
  position: absolute;
  width: 78px;
  height: 78px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 247, 237, 0.92), rgba(251, 146, 60, 0.82) 28%, transparent 64%);
  box-shadow: 0 0 38px rgba(251, 146, 60, 0.7);
}

.class-orbit > .n-icon {
  position: relative;
  z-index: 1;
  color: #fff7ed;
  font-size: 2.4rem;
}

.class-info header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.class-info h3 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.08rem;
}

.class-info header button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid rgba(221, 230, 239, 0.16);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(221, 230, 239, 0.7);
  cursor: pointer;
}

.class-info dl {
  display: grid;
  gap: 0.75rem;
  margin: 1.2rem 0 1.6rem;
}

.class-info dl div {
  display: flex;
  gap: 0.75rem;
  color: rgba(221, 230, 239, 0.66);
  font-size: 0.88rem;
}

.class-info dt,
.class-info dd {
  margin: 0;
}

.class-info dd {
  color: rgba(255, 247, 237, 0.72);
}

.outline-orange {
  --n-color: rgba(251, 146, 60, 0.08) !important;
  --n-color-hover: rgba(251, 146, 60, 0.14) !important;
  --n-border: 1px solid rgba(251, 146, 60, 0.58) !important;
  --n-border-hover: 1px solid rgba(251, 146, 60, 0.8) !important;
  --n-text-color: #fb923c !important;
  --n-text-color-hover: #fdba74 !important;
  font-weight: 760 !important;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.enabled-pill {
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(52, 211, 153, 0.34);
  border-radius: 999px;
  padding: 0.15rem 0.52rem;
  color: #34d399;
  background: rgba(52, 211, 153, 0.08);
  font-size: 0.76rem;
  font-weight: 800;
}

.ai-layout {
  display: grid;
  grid-template-columns: 136px minmax(0, 1fr);
  gap: 0.8rem;
  height: calc(100% - 1.55rem);
  align-items: center;
}

.bot-orbit {
  height: 184px;
  border-right: 1px solid rgba(219, 235, 249, 0.08);
}

.bot-orbit i {
  position: absolute;
  width: 114px;
  height: 114px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(251, 146, 60, 0.26), transparent 66%);
}

.bot-orbit b {
  position: relative;
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  border-radius: 50%;
  background: #e9f3fb;
  box-shadow: inset 0 -20px #111926, 0 0 26px rgba(251, 146, 60, 0.38);
}

.bot-orbit b span {
  width: 42px;
  height: 24px;
  border-radius: 12px;
  background: #07111d;
  box-shadow: inset 13px 10px #111926;
}

.strategy-list,
.notice-list {
  display: grid;
}

.strategy-list article,
.notice-list article {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 0.8rem;
  align-items: center;
  padding: 0.42rem 0;
  border-bottom: 1px solid rgba(219, 235, 249, 0.08);
}

.ai-panel .strategy-list article {
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 0.55rem;
}

.ai-panel .strategy-list small {
  line-height: 1.35;
}

.strategy-list article > span,
.notice-list article > span {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 1px solid rgba(221, 230, 239, 0.16);
  border-radius: 8px;
  color: rgba(221, 230, 239, 0.74);
}

.strategy-list strong,
.notice-list strong,
.security-list strong {
  display: block;
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.86rem;
}

.strategy-list small,
.notice-list small,
.security-list small {
  display: block;
  margin-top: 0.18rem;
  color: rgba(221, 230, 239, 0.5);
  font-size: 0.7rem;
}

.orange-switch :deep(.n-switch__rail) {
  background-color: rgba(255, 255, 255, 0.18) !important;
}

.orange-switch :deep(.n-switch--active .n-switch__rail),
.orange-switch :deep(.n-switch__rail[aria-checked='true']) {
  background-color: #fb923c !important;
}

.select-line {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  gap: 1rem;
  align-items: center;
  margin-top: 0.35rem;
  color: rgba(221, 230, 239, 0.58);
  font-size: 0.84rem;
}

.notice-layout,
.rules-layout,
.security-layout {
  display: grid;
  gap: 1.1rem;
  align-items: center;
}

.notice-layout {
  grid-template-columns: 170px minmax(0, 1fr);
  margin-top: 1rem;
}

.bell-orbit,
.shield-orbit {
  height: 170px;
}

.bell-orbit .n-icon,
.shield-orbit .n-icon {
  position: relative;
  z-index: 1;
  color: #fff7ed;
  font-size: 3rem;
  filter: drop-shadow(0 0 20px rgba(251, 146, 60, 0.8));
}

.channel-row {
  display: flex;
  align-items: center;
  gap: 1.35rem;
  margin-top: 1.05rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(219, 235, 249, 0.08);
  color: rgba(221, 230, 239, 0.58);
  font-size: 0.84rem;
}

.channel-row button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 0;
  background: transparent;
  color: rgba(221, 230, 239, 0.66);
  cursor: pointer;
}

.channel-row button.active {
  color: var(--orange);
}

.rules-layout {
  grid-template-columns: 150px minmax(0, 1fr);
  height: calc(100% - 2rem);
}

.settings-nav--compact {
  gap: 0.55rem;
  padding-right: 0.85rem;
}

.rules-form {
  display: grid;
  gap: 0.85rem;
}

.rules-form label,
.difficulty-field {
  display: grid;
  gap: 0.45rem;
}

.rules-form label > span,
.difficulty-field > span,
.security-list label > span {
  color: rgba(255, 237, 213, 0.72);
  font-size: 0.84rem;
}

.orange-slider :deep(.n-slider-rail__fill) {
  background: var(--orange) !important;
}

.orange-slider :deep(.n-slider-handle) {
  background: var(--orange) !important;
  border-color: var(--orange) !important;
}

.difficulty-field div {
  display: flex;
  justify-content: space-between;
  color: rgba(221, 230, 239, 0.48);
}

.security-layout {
  grid-template-columns: 180px minmax(0, 1fr);
  margin-top: 0.8rem;
}

.shield-orbit .n-icon {
  padding: 1rem;
  border: 2px solid rgba(251, 146, 60, 0.55);
  border-radius: 30% 30% 46% 46%;
}

.security-list {
  display: grid;
  gap: 0.72rem;
}

.security-list label,
.security-list button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.8rem;
  align-items: center;
}

.security-list label {
  grid-template-columns: 5.5rem minmax(0, 1fr);
}

.security-list button {
  width: 100%;
  border: 0;
  background: transparent;
  color: rgba(221, 230, 239, 0.74);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.security-list button > .n-icon,
.security-list button > span {
  color: rgba(221, 230, 239, 0.72);
  font-size: 1.2rem;
}

.small-select {
  width: 150px;
}

.security-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(219, 235, 249, 0.08);
  color: rgba(221, 230, 239, 0.58);
}

@media (max-width: 1280px) {
  .control-toolbar {
    margin: 1rem var(--plex-page-gutter-x);
  }

  .control-center {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .system-panel,
  .ai-panel,
  .notice-panel,
  .rules-panel,
  .security-panel {
    min-height: 340px;
  }
}

@media (max-width: 760px) {
  .control-toolbar {
    flex-direction: column;
    align-items: stretch;
    margin-inline: 1rem;
  }

  .class-select {
    width: 100%;
  }

  .keeper-chip {
    min-width: 0;
    padding-left: 0;
    border-left: 0;
  }

  .control-center {
    padding-inline: 1rem;
  }

  .system-layout,
  .ai-layout,
  .notice-layout,
  .rules-layout,
  .security-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .settings-nav,
  .bot-orbit {
    border-right: 0;
  }
}
</style>
