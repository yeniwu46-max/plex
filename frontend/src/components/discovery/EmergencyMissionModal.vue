<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NModal, NTag, useMessage } from 'naive-ui'
import {
  startEmergencyMission,
  submitEmergencyMission,
  type EmergencyMissionSession,
  type EmergencyQuestion,
} from '../../api/emergencyMission'
import { showIncentiveFeedback } from '../../utils/incentiveFeedback'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  completed: []
}>()

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const session = ref<EmergencyMissionSession | null>(null)
const selections = ref<Record<number, number | null>>({})
const phase = ref<'quiz' | 'result'>('quiz')

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

const canSubmit = computed(() => {
  if (!session.value || phase.value !== 'quiz') return false
  return session.value.questions.every((q) => selections.value[q.id] !== null && selections.value[q.id] !== undefined)
})

function resetState() {
  session.value = null
  selections.value = {}
  phase.value = 'quiz'
}

function initSelections(questions: EmergencyQuestion[]) {
  for (const q of questions) {
    if (selections.value[q.id] === undefined) {
      selections.value[q.id] = q.selected_index ?? null
    }
  }
}

async function loadMission() {
  loading.value = true
  try {
    session.value = await startEmergencyMission()
    initSelections(session.value.questions)
    phase.value = session.value.status === 'submitted' ? 'result' : 'quiz'
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载失败')
    visible.value = false
  } finally {
    loading.value = false
  }
}

function selectOption(questionId: number, index: number) {
  if (phase.value !== 'quiz' || submitting.value) return
  selections.value[questionId] = index
}

async function handleSubmit() {
  if (!session.value || !canSubmit.value) return
  submitting.value = true
  try {
    const answers = session.value.questions.map((q) => ({
      question_id: q.id,
      selected_index: selections.value[q.id] as number,
    }))
    const result = await submitEmergencyMission(session.value.id, answers)
    session.value = result.session
    phase.value = 'result'
    showIncentiveFeedback(message, result.incentive)
    if (result.session.all_correct) {
      message.success(`全对！已获得 +${result.session.reward_points} XP`)
    } else {
      message.warning(`答对 ${result.session.correct_count}/3，未获得奖励，可在探索档案查看解析`)
    }
    emit('completed')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

function closeModal() {
  visible.value = false
}

watch(
  () => props.show,
  (open) => {
    if (open) {
      resetState()
      void loadMission()
    }
  },
)
</script>

<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    class="emergency-modal"
    :style="{ width: 'min(520px, 92vw)' }"
    :title="phase === 'quiz' ? '紧急任务' : '作答结果'"
    :mask-closable="phase === 'result'"
    @after-leave="resetState"
  >
    <div v-if="loading" class="emergency-modal__loading">正在根据你的知识点掌握情况生成题目…</div>

    <template v-else-if="session">
      <header class="emergency-modal__meta">
        <p class="emergency-modal__subtitle">边界条件补给站</p>
        <n-tag size="small" :bordered="false" type="info">薄弱强化 · {{ session.focus_label }}</n-tag>
      </header>

      <p v-if="phase === 'quiz'" class="emergency-modal__hint">共 3 题，全部答对可获得补给奖励（+55 XP）</p>
      <p v-else class="emergency-modal__hint" :class="{ 'emergency-modal__hint--ok': session.all_correct }">
        {{
          session.all_correct
            ? `恭喜全对！奖励 +${session.reward_points} XP 已发放`
            : `本次答对 ${session.correct_count}/3，未达全对，暂无奖励`
        }}
      </p>

      <article v-for="q in session.questions" :key="q.id" class="emergency-q">
        <h4>{{ q.sort_order }}. {{ q.stem }}</h4>
        <ul class="emergency-q__options">
          <li v-for="(opt, idx) in q.options" :key="idx">
            <button
              type="button"
              class="emergency-opt"
              :class="{
                'emergency-opt--picked': selections[q.id] === idx,
                'emergency-opt--right': phase === 'result' && q.correct_index === idx,
                'emergency-opt--wrong':
                  phase === 'result' && selections[q.id] === idx && q.correct_index !== idx,
              }"
              :disabled="phase === 'result' || submitting"
              @click="selectOption(q.id, idx)"
            >
              <span>{{ String.fromCharCode(65 + idx) }}</span>
              {{ opt }}
            </button>
          </li>
        </ul>
        <p v-if="phase === 'result'" class="emergency-q__verdict">
          {{ q.is_correct ? '✓ 回答正确' : `✗ 正确答案：${String.fromCharCode(65 + (q.correct_index ?? 0))}` }}
        </p>
      </article>

      <footer class="emergency-modal__foot">
        <n-button v-if="phase === 'quiz'" quaternary @click="closeModal">稍后再做</n-button>
        <n-button
          v-if="phase === 'quiz'"
          type="primary"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          提交并查看答案
        </n-button>
        <n-button v-else type="primary" @click="closeModal">完成</n-button>
      </footer>
    </template>
  </n-modal>
</template>

<style scoped>
.emergency-modal__loading {
  padding: 2rem 0;
  text-align: center;
  color: rgba(142, 163, 184, 0.95);
  font-size: 0.9rem;
}

.emergency-modal__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.emergency-modal__subtitle {
  margin: 0;
  font-size: 0.78rem;
  color: rgba(16, 240, 192, 0.85);
  letter-spacing: 0.06em;
}

.emergency-modal__hint {
  margin: 0 0 1rem;
  font-size: 0.82rem;
  color: rgba(142, 163, 184, 0.95);
}

.emergency-modal__hint--ok {
  color: rgba(16, 240, 192, 0.95);
}

.emergency-q {
  margin-bottom: 1rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.emergency-q h4 {
  margin: 0 0 0.55rem;
  font-size: 0.92rem;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 600;
}

.emergency-q__options {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.emergency-opt {
  width: 100%;
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  text-align: left;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(8, 14, 28, 0.6);
  color: rgba(255, 255, 255, 0.88);
  cursor: pointer;
  font-size: 0.84rem;
}

.emergency-opt span:first-child {
  flex-shrink: 0;
  font-weight: 700;
  color: rgba(16, 240, 192, 0.9);
}

.emergency-opt--picked {
  border-color: rgba(16, 240, 192, 0.55);
  background: rgba(16, 240, 192, 0.08);
}

.emergency-opt--right {
  border-color: rgba(16, 240, 192, 0.85);
  background: rgba(16, 240, 192, 0.14);
}

.emergency-opt--wrong {
  border-color: rgba(232, 128, 128, 0.75);
  background: rgba(232, 128, 128, 0.1);
}

.emergency-q__verdict {
  margin: 0.45rem 0 0;
  font-size: 0.8rem;
  color: rgba(142, 163, 184, 0.95);
}

.emergency-modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>

<style>
.emergency-modal.n-modal {
  --n-color: #0b1628;
  --n-text-color: #e8fff8;
  --n-title-text-color: #e8fff8;
  --n-border-color: rgba(16, 240, 192, 0.25);
}
</style>
