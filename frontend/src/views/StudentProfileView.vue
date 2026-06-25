<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NInput, NModal, NProgress, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import StudentSectionTabs from '../components/student/StudentSectionTabs.vue'
import {
  chatDynamicProfile,
  fetchDynamicProfile,
  fetchProfileSuggestions,
  resolveProfileSuggestion,
  updateDynamicProfile,
  type DynamicStudentProfile,
  type ProfileDimensionKey,
  type ProfileSuggestion,
} from '../api/personalizedProfile'

const message = useMessage()
const profile = ref<DynamicStudentProfile | null>(null)
const suggestions = ref<ProfileSuggestion[]>([])
const prompt = ref('')
const loading = ref(false)
const backend = ref('')
const editingKey = ref<ProfileDimensionKey | null>(null)
const editingValue = ref('')
const editModalVisible = computed({
  get: () => editingKey.value !== null,
  set: (value: boolean) => {
    if (!value) editingKey.value = null
  },
})
const labels: Record<ProfileDimensionKey, string> = {
  major_background: '专业背景',
  knowledge_foundation: '知识基础',
  learning_goal: '学习目标',
  explanation_preference: '讲解偏好',
  mistake_pattern: '易错模式',
  learning_pace: '学习节奏',
  interest_direction: '兴趣方向',
}
const entries = computed(() =>
  profile.value
    ? (Object.entries(profile.value.dimensions) as Array<
        [ProfileDimensionKey, DynamicStudentProfile['dimensions'][ProfileDimensionKey]]
      >)
    : [],
)

async function analyze() {
  loading.value = true
  try {
    const text = prompt.value.trim() || '请根据我的最近练习、错题和学习情况分析并更新学习画像'
    const result = await chatDynamicProfile(text, true)
    profile.value = result.profile
    backend.value = result.backend
    prompt.value = ''
    await loadSuggestions()
    message.success(result.assistant_reply)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '画像分析失败')
  } finally {
    loading.value = false
  }
}

function edit(key: ProfileDimensionKey) {
  editingKey.value = key
  editingValue.value = profile.value?.dimensions[key]?.value || ''
}

async function saveEdit() {
  if (!editingKey.value) return
  const value = editingValue.value.trim()
  if (!value) {
    message.warning('请先填写修正内容')
    return
  }
  try {
    profile.value = await updateDynamicProfile({ [editingKey.value]: value })
    editingKey.value = null
    editingValue.value = ''
    message.success('画像已按你的确认更新')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '画像更新失败')
  }
}

async function loadSuggestions() {
  suggestions.value = (await fetchProfileSuggestions()).items
}

async function resolveSuggestion(item: ProfileSuggestion, action: 'accepted' | 'rejected') {
  try {
    const result = await resolveProfileSuggestion(item.id, action)
    if (result.profile) profile.value = result.profile
    await loadSuggestions()
    message.success(action === 'accepted' ? '画像建议已接受' : '画像建议已忽略')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '画像建议处理失败')
  }
}

onMounted(async () => {
  await Promise.all([
    fetchDynamicProfile().then((value) => { profile.value = value }),
    loadSuggestions(),
  ])
})
</script>

<template>
  <DashboardShell active-nav="me" page-title="学习画像" page-subtitle="对话构建七维动态画像" search-placeholder="" hide-search>
    <template #toolbar><StudentSectionTabs area="me" /></template>
    <main class="profile-page">
      <section class="profile-hero">
        <div><p>PROFILE VERSION {{ profile?.version ?? 1 }}</p><h2>七维动态学习画像</h2><span>每个结论都保留置信度和证据，你可以随时修正。</span></div>
        <n-progress type="circle" :percentage="profile?.completion_rate ?? 0" color="#25f5ee" />
      </section>
      <section class="profile-dialog">
        <n-input v-model:value="prompt" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" placeholder="介绍你的专业、基础、目标、讲解偏好、易错点、学习节奏和兴趣方向。" @keydown.ctrl.enter.prevent="analyze" />
        <div class="dialog-actions"><span v-if="backend">本次后端：{{ backend }}</span><n-button type="primary" :loading="loading" @click="analyze">分析并更新画像</n-button></div>
      </section>
      <section v-if="suggestions.length" class="suggestion-list">
        <article v-for="item in suggestions" :key="item.id" class="suggestion-card">
          <div>
            <n-tag type="warning">学习行为建议</n-tag>
            <h3>{{ labels[item.dimension] }}</h3>
            <p>{{ item.proposed_value }}</p>
            <small>{{ item.evidence.join('；') }}</small>
          </div>
          <footer>
            <n-button secondary @click="resolveSuggestion(item, 'rejected')">忽略</n-button>
            <n-button type="primary" @click="resolveSuggestion(item, 'accepted')">接受并更新画像</n-button>
          </footer>
        </article>
      </section>
      <section class="dimension-grid">
        <article v-for="[key, item] in entries" :key="key" class="dimension-card">
          <header><h3>{{ labels[key] }}</h3><n-tag size="small" :type="item.source === 'confirmed' ? 'success' : 'info'">{{ item.source }}</n-tag></header>
          <p class="dimension-value">{{ item.value || '等待对话补充' }}</p>
          <n-progress :percentage="Math.round(item.confidence * 100)" :show-indicator="false" />
          <ul><li v-for="evidence in item.evidence" :key="evidence">{{ evidence }}</li></ul>
          <n-button size="small" secondary @click="edit(key)">人工修正</n-button>
        </article>
      </section>
      <n-modal v-model:show="editModalVisible" preset="card" class="profile-edit-modal" :title="editingKey ? `修正${labels[editingKey]}` : '修正画像'">
        <n-input
          v-model:value="editingValue"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 6 }"
          placeholder="写下你确认后的画像描述"
        />
        <template #footer>
          <div class="profile-edit-modal__actions">
            <n-button secondary @click="editingKey = null">取消</n-button>
            <n-button type="primary" @click="saveEdit">保存修正</n-button>
          </div>
        </template>
      </n-modal>
    </main>
  </DashboardShell>
</template>

<style scoped>
.profile-page{width:100%;padding:0 var(--plex-page-gutter-x) 2rem;overflow-y:auto}.profile-hero,.profile-dialog,.dimension-card,.suggestion-card{border:1px solid rgba(37,245,238,.16);background:rgba(3,16,28,.82);border-radius:18px}.profile-hero{display:flex;justify-content:space-between;align-items:center;padding:1.5rem;margin-bottom:1rem}.profile-hero p{color:#52fff1;letter-spacing:.12em;font-size:.72rem;margin:0}.profile-hero h2{margin:.35rem 0;color:#f3fbff}.profile-hero span{color:rgba(215,230,242,.68)}.profile-dialog{padding:1.25rem;margin-bottom:1rem}.dialog-actions{display:flex;justify-content:space-between;align-items:center;margin-top:.8rem;color:#8ddbd6;font-size:.82rem}.suggestion-list{display:grid;gap:.75rem;margin-bottom:1rem}.suggestion-card{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem 1.2rem}.suggestion-card h3{margin:.5rem 0;color:#effaff}.suggestion-card p{margin:.25rem 0;color:#cfe8f3}.suggestion-card small{color:rgba(205,222,235,.62)}.suggestion-card footer{display:flex;gap:.5rem;flex-shrink:0}.dimension-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.dimension-card{padding:1.2rem}.dimension-card header{display:flex;justify-content:space-between;align-items:center}.dimension-card h3{margin:0;color:#effaff}.dimension-value{min-height:2.8rem;color:#cfe8f3;line-height:1.55}.dimension-card ul{min-height:2rem;padding-left:1.1rem;color:rgba(205,222,235,.62);font-size:.82rem}@media(max-width:800px){.dimension-grid{grid-template-columns:1fr}.suggestion-card{align-items:stretch;flex-direction:column}.suggestion-card footer{justify-content:flex-end}}
.profile-edit-modal{max-width:min(520px,92vw)}.profile-edit-modal__actions{display:flex;justify-content:flex-end;gap:.65rem}
</style>
