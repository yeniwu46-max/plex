<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NCheckbox, NInput, NSelect, useMessage } from 'naive-ui'
import KnowledgePointPicker from './KnowledgePointPicker.vue'
import {
  createTeacherTemplate,
  deleteTeacherTemplate,
  fetchTeacherTemplates,
  publishTeacherTemplate,
  type TeacherTrialTemplate,
} from '../../api/teacherTemplates'
import { labelForKnowledgeKey } from '../../data/teacherKnowledgeCatalog'
import { useKnowledgeCatalog } from '../../composables/useKnowledgeCatalog'
import { useTeacherOverviewInjected } from '../../composables/useTeacherOverview'
import { useAuthStore } from '../../stores/auth'
import { useTeacherNotificationStore } from '../../stores/teacherNotifications'

const props = defineProps<{
  trialTypeOptions: Array<{ label: string; value: string | number }>
}>()

const emit = defineEmits<{
  published: []
}>()

const message = useMessage()
const auth = useAuthStore()
const teacherNotifications = useTeacherNotificationStore()
const { selectedClassId, hasSelectedClass } = useTeacherOverviewInjected()

const { domains, loadCatalog } = useKnowledgeCatalog()
const templates = ref<TeacherTrialTemplate[]>([])
const loading = ref(false)
const saving = ref(false)
const publishingId = ref<number | null>(null)

const templateTitle = ref('')
const trialType = ref('solo')
const selectedKeys = ref<string[]>([])
const notifyStudents = ref(true)

const selectedLabels = computed(() => selectedKeys.value.map((k) => labelForKnowledgeKey(k)))

async function load() {
  if (!hasSelectedClass.value) return
  loading.value = true
  try {
    if (!domains.value.length) {
      await loadCatalog()
    }
    const list = await fetchTeacherTemplates(selectedClassId.value ?? undefined)
    templates.value = list
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载失败')
  } finally {
    loading.value = false
  }
}

async function saveTemplate() {
  if (!selectedClassId.value) {
    message.warning('请先选择班级')
    return
  }
  if (!selectedKeys.value.length) {
    message.warning('请至少勾选一个知识点')
    return
  }
  const title =
    templateTitle.value.trim() ||
    `${selectedLabels.value.slice(0, 2).join('、')}${selectedKeys.value.length > 2 ? ' 等' : ''}作业`
  saving.value = true
  try {
    await createTeacherTemplate({
      title,
      trial_type: trialType.value,
      knowledge_keys: selectedKeys.value,
      class_id: selectedClassId.value,
    })
    message.success('模板已保存')
    templateTitle.value = ''
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeTemplate(id: number) {
  try {
    await deleteTeacherTemplate(id)
    message.success('已删除模板')
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除失败')
  }
}

async function publishTemplate(row: TeacherTrialTemplate) {
  if (!selectedClassId.value) {
    message.warning('请先选择班级')
    return
  }
  publishingId.value = row.id
  try {
    const result = await publishTeacherTemplate(row.id, selectedClassId.value, notifyStudents.value)
    const uid = auth.profile?.id
    if (uid && notifyStudents.value) {
      teacherNotifications.notifyAssignmentPublished(
        uid,
        row.title,
        result.student_count ?? 0,
      )
    } else if (uid) {
      teacherNotifications.notifyAssignmentPublished(uid, row.title, 0)
    }
    message.success(
      notifyStudents.value && result.student_count
        ? `已发布并通知 ${result.student_count} 名学生`
        : '作业已发布',
    )
    emit('published')
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '发布失败')
  } finally {
    publishingId.value = null
  }
}

onMounted(() => {
  void loadCatalog()
  void load()
})

watch(selectedClassId, () => {
  void load()
})
</script>

<template>
  <div class="templates-panel">
    <div v-if="!hasSelectedClass" class="teacher-state-panel">请先在顶部选择班级。</div>
    <template v-else>
      <div class="templates-panel__editor">
        <h3>新建作业模板</h3>
        <p class="templates-panel__hint">勾选若干知识点后保存为模板，可一键发布并通知全班学生。</p>
        <label class="field">
          <span>模板名称</span>
          <n-input v-model:value="templateTitle" placeholder="留空则根据知识点自动生成" />
        </label>
        <label class="field">
          <span>试炼类型</span>
          <n-select v-model:value="trialType" :options="props.trialTypeOptions" />
        </label>
        <KnowledgePointPicker v-model="selectedKeys" :domains="domains" />
        <div class="templates-panel__selected" v-if="selectedKeys.length">
          已选 {{ selectedKeys.length }} 个：{{ selectedLabels.join('、') }}
        </div>
        <n-checkbox v-model:checked="notifyStudents">发布时通知全班学生</n-checkbox>
        <n-button type="primary" :loading="saving" @click="saveTemplate">保存为模板</n-button>
      </div>

      <div class="templates-panel__list">
        <h3>已保存模板</h3>
        <div v-if="loading" class="teacher-state-panel">加载中…</div>
        <div v-else-if="!templates.length" class="teacher-state-panel">暂无模板，请在上方勾选知识点并保存。</div>
        <article v-for="row in templates" :key="row.id" class="template-row">
          <div>
            <strong>{{ row.title }}</strong>
            <p>
              {{ row.knowledge_keys.map((k) => labelForKnowledgeKey(k)).join(' · ') }}
            </p>
            <small>{{ row.trial_type }} · {{ row.duration_minutes }} 分钟 · {{ row.reward_points }} XP</small>
          </div>
          <div class="template-row__actions">
            <n-button
              type="primary"
              size="small"
              :loading="publishingId === row.id"
              @click="publishTemplate(row)"
            >
              发布作业
            </n-button>
            <n-button size="small" quaternary @click="removeTemplate(row.id)">删除</n-button>
          </div>
        </article>
      </div>
    </template>
  </div>
</template>

<style scoped>
.templates-panel {
  display: grid;
  gap: 1.25rem;
}

.templates-panel__editor,
.templates-panel__list {
  padding: 1rem 1.1rem;
  border: 1px solid rgba(251, 146, 60, 0.15);
  border-radius: 0.65rem;
  background: rgba(15, 23, 42, 0.45);
}

.templates-panel h3 {
  margin: 0 0 0.5rem;
  color: #fff7ed;
  font-size: 1rem;
}

.templates-panel__hint {
  margin: 0 0 0.85rem;
  color: rgba(255, 237, 213, 0.65);
  font-size: 0.82rem;
}

.field {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.field span {
  color: rgba(255, 237, 213, 0.75);
  font-size: 0.8rem;
}

.templates-panel__selected {
  margin: 0.65rem 0;
  color: rgba(255, 237, 213, 0.8);
  font-size: 0.8rem;
  line-height: 1.5;
}

.template-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0;
  border-top: 1px solid rgba(251, 146, 60, 0.1);
}

.template-row:first-of-type {
  border-top: 0;
}

.template-row strong {
  color: #fff7ed;
}

.template-row p {
  margin: 0.25rem 0;
  color: rgba(255, 237, 213, 0.75);
  font-size: 0.82rem;
}

.template-row small {
  color: rgba(255, 237, 213, 0.5);
  font-size: 0.72rem;
}

.template-row__actions {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex-shrink: 0;
}
</style>
