<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NCheckbox, NIcon, useMessage } from 'naive-ui'
import {
  CheckmarkCircleOutline,
  CodeSlashOutline,
  GitNetworkOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
  WarningOutline,
} from '@vicons/ionicons5'
import {
  GRADING_AGENT_CATEGORY_LABELS,
  TEACHER_GRADING_AGENTS,
  type GradingAgentCategory,
} from '../../data/gradingAgents'
import {
  canSelectGradingAgent,
  validateGradingAgentSelection,
  type GradingAgentValidationResult,
} from '../../utils/gradingAgentValidation'
import PlexAgentFlow from './PlexAgentFlow.vue'

const STORAGE_KEY = 'plex.teacher-grading-agents'

const message = useMessage()
const selectedAgentIds = ref<string[]>([])
const validation = ref<GradingAgentValidationResult>({
  valid: true,
  selectedCount: 0,
  duplicates: [],
  warnings: [],
})

const categoryOrder: GradingAgentCategory[] = [
  'correctness',
  'code',
  'logic',
  'feedback',
  'integrity',
]

const categoryIcon: Record<GradingAgentCategory, typeof CodeSlashOutline> = {
  correctness: CheckmarkCircleOutline,
  code: CodeSlashOutline,
  logic: GitNetworkOutline,
  feedback: SparklesOutline,
  integrity: ShieldCheckmarkOutline,
}

const groupedAgents = computed(() =>
  categoryOrder.map((category) => ({
    category,
    label: GRADING_AGENT_CATEGORY_LABELS[category],
    agents: TEACHER_GRADING_AGENTS.filter((agent) => agent.category === category),
  })),
)

function refreshValidation() {
  validation.value = validateGradingAgentSelection(selectedAgentIds.value)
}

function loadSavedSelection() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw) as string[]
    if (Array.isArray(parsed)) {
      selectedAgentIds.value = parsed.filter((id) => TEACHER_GRADING_AGENTS.some((agent) => agent.id === id))
    }
  } catch {
    selectedAgentIds.value = []
  }
  refreshValidation()
}

function toggleAgent(agentId: string, checked: boolean) {
  if (checked) {
    const gate = canSelectGradingAgent(selectedAgentIds.value, agentId)
    if (!gate.allowed) {
      message.warning(gate.reason ?? '与已选智能体检查维度重复')
      return
    }
    selectedAgentIds.value = [...selectedAgentIds.value, agentId]
  } else {
    selectedAgentIds.value = selectedAgentIds.value.filter((id) => id !== agentId)
  }
  refreshValidation()
}

function saveSelection() {
  refreshValidation()
  if (selectedAgentIds.value.length === 0) {
    message.warning('请至少勾选一个检查智能体')
    return
  }
  if (!validation.value.valid) {
    message.error('存在重复检查维度，请调整勾选后再保存')
    return
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedAgentIds.value))
  message.success(`已保存 ${validation.value.selectedCount} 个检查智能体编排`)
}

function resetSelection() {
  selectedAgentIds.value = []
  refreshValidation()
  localStorage.removeItem(STORAGE_KEY)
  message.info('已清空教师检查智能体勾选')
}

watch(selectedAgentIds, refreshValidation, { deep: true })

loadSavedSelection()
</script>

<template>
  <section class="agents-layout" aria-label="智能体编排面板">
    <article class="panel grading-panel">
      <header class="panel-head panel-head--stack">
        <div>
          <h2>教师检查智能体</h2>
          <p>勾选参与学生做题自动检查；各智能体检查维度互不重叠</p>
        </div>
        <div class="grading-actions">
          <n-button type="primary" :disabled="!validation.valid || validation.selectedCount === 0" @click="saveSelection">
            保存编排
          </n-button>
          <n-button secondary @click="resetSelection">清空</n-button>
        </div>
      </header>

      <div
        class="validation-banner"
        :class="{
          'validation-banner--ok': validation.valid && validation.selectedCount > 0,
          'validation-banner--warn': !validation.valid,
          'validation-banner--idle': validation.selectedCount === 0,
        }"
      >
        <n-icon :component="validation.valid ? CheckmarkCircleOutline : WarningOutline" />
        <span v-if="validation.selectedCount === 0">尚未勾选检查智能体</span>
        <span v-else-if="validation.valid">已选 {{ validation.selectedCount }} 个，重复校验通过</span>
        <span v-else>检测到 {{ validation.duplicates.length }} 处重复检查维度</span>
      </div>

      <div class="grading-groups">
        <section v-for="group in groupedAgents" :key="group.category" class="grading-group">
          <header class="grading-group-head">
            <n-icon :component="categoryIcon[group.category]" />
            <strong>{{ group.label }}</strong>
          </header>
          <div class="grading-agent-grid">
            <label
              v-for="agent in group.agents"
              :key="agent.id"
              class="grading-agent-card"
              :class="{ selected: selectedAgentIds.includes(agent.id) }"
            >
              <n-checkbox
                :checked="selectedAgentIds.includes(agent.id)"
                @update:checked="(checked) => toggleAgent(agent.id, checked)"
              />
              <div class="grading-agent-body">
                <div class="grading-agent-title">
                  <strong>{{ agent.name }}</strong>
                  <span v-if="agent.status === 'beta'" class="beta-tag">Beta</span>
                </div>
                <em>{{ agent.nameEn }}</em>
                <small>{{ agent.description }}</small>
              </div>
            </label>
          </div>
        </section>
      </div>
    </article>

    <article class="panel flow-panel">
      <header class="panel-head">
        <h2>多智能体协同流程</h2>
        <span class="core-badge">Vue Flow · 可视化编排</span>
      </header>
      <plex-agent-flow />
    </article>
  </section>
</template>

<style scoped>
.agents-layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.05rem;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.panel {
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background:
    radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.11), transparent 42%),
    linear-gradient(145deg, rgba(19, 20, 43, 0.88), rgba(8, 11, 26, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 18px 50px rgba(0, 0, 0, 0.22);
  min-width: 0;
  padding: 1.15rem 1.25rem;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel-head--stack {
  align-items: flex-start;
}

.panel-head h2 {
  margin: 0;
  color: #fff;
  font-size: 1.08rem;
}

.panel-head p {
  margin: 0.35rem 0 0;
  color: rgba(226, 232, 240, 0.58);
  font-size: 0.78rem;
}

.grading-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0.55rem;
}

.validation-banner {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 1rem;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  border: 1px solid rgba(167, 139, 250, 0.16);
  background: rgba(12, 14, 32, 0.62);
  font-size: 0.82rem;
  color: rgba(226, 232, 240, 0.72);
}

.validation-banner--ok {
  border-color: rgba(52, 211, 153, 0.35);
  color: #6ee7b7;
}

.validation-banner--warn {
  border-color: rgba(245, 158, 11, 0.45);
  color: #fcd34d;
}

.grading-groups {
  display: grid;
  gap: 1.1rem;
}

.grading-group-head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.65rem;
  color: #c4b5fd;
  font-size: 0.84rem;
}

.grading-agent-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.grading-agent-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.65rem;
  align-items: start;
  min-height: 96px;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 8px;
  background: rgba(8, 10, 24, 0.45);
  cursor: pointer;
}

.grading-agent-card.selected {
  border-color: rgba(139, 92, 246, 0.55);
  background: rgba(139, 92, 246, 0.12);
}

.grading-agent-body {
  display: grid;
  gap: 0.25rem;
  min-width: 0;
}

.grading-agent-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.grading-agent-title strong {
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.86rem;
  line-height: 1.35;
}

.grading-agent-body em {
  color: rgba(167, 139, 250, 0.7);
  font-size: 0.7rem;
  font-style: normal;
}

.grading-agent-body small {
  color: rgba(226, 232, 240, 0.6);
  font-size: 0.76rem;
  line-height: 1.45;
}

.beta-tag {
  flex-shrink: 0;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
  font-size: 0.65rem;
}

.flow-panel {
  overflow: visible;
}

.core-badge {
  flex-shrink: 0;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid rgba(167, 139, 250, 0.28);
  color: #d8b4fe;
  font-size: 0.68rem;
  white-space: nowrap;
}

.topology-list,
.schedule-log {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.55rem;
}

.topology-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.08);
  color: rgba(226, 232, 240, 0.72);
  font-size: 0.82rem;
}

.topology-list li:last-child {
  border-bottom: none;
}

.topology-list em {
  flex-shrink: 0;
  color: #34d399;
  font-style: normal;
  font-size: 0.74rem;
}

.topology-list em::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 0.35rem;
  border-radius: 50%;
  background: currentColor;
}

.chain-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.45rem;
}

.chain-list li {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 0.55rem;
  align-items: center;
  color: rgba(226, 232, 240, 0.78);
  font-size: 0.82rem;
}

.chain-list i {
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 50%;
  background: rgba(139, 92, 246, 0.22);
  color: #c4b5fd;
  font-style: normal;
  font-size: 0.72rem;
}

.chain-loop {
  margin: auto 0 0;
  padding-top: 0.75rem;
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.76rem;
}

.schedule-log li {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 0.55rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.08);
  color: rgba(226, 232, 240, 0.68);
  font-size: 0.78rem;
  line-height: 1.4;
}

.schedule-log li:last-child {
  border-bottom: none;
}

.schedule-log time {
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.72rem;
}

@media (max-width: 1280px) {
  .grading-agent-grid {
    grid-template-columns: 1fr;
  }

  .agents-bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .panel-head--stack {
    flex-direction: column;
  }

  .grading-actions {
    width: 100%;
  }
}
</style>
