<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NSelect, NSwitch } from 'naive-ui'
import { fetchKnowledgePublicationClasses, updateKnowledgeAccess, type KnowledgeDocument } from '../../api/knowledge'

const props = defineProps<{ document: KnowledgeDocument }>()
const emit = defineEmits<{ saved: [document: KnowledgeDocument] }>()
const visibility = ref<KnowledgeDocument['visibility']>('private')
const classId = ref<number | null>(null)
const published = ref(false)
const busy = ref(false)
const error = ref('')
const classes = ref<Array<{ label: string; value: number }>>([])
const classLoading = ref(false)
const options = computed(() => [
  { label: '私有 · 仅本人及管理员', value: 'private' },
  { label: '指定班级', value: 'class' },
  ...(props.document.may_publish_public ? [{ label: '全课程公开', value: 'public' }] : []),
])
watch(() => props.document, (doc) => {
  visibility.value = doc.visibility
  classId.value = doc.class_id
  published.value = doc.published
}, { immediate: true })
watch(visibility, (value) => {
  if (value !== 'class') classId.value = null
  if (value === 'private') published.value = false
  if (value === 'class') void loadClasses()
})
async function loadClasses() {
  if (classLoading.value || classes.value.length) return
  classLoading.value = true
  error.value = ''
  try {
    classes.value = (await fetchKnowledgePublicationClasses()).items.map((c) => ({ label: c.name, value: c.id }))
  } catch (err) { error.value = (err as Error).message }
  finally { classLoading.value = false }
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    emit('saved', await updateKnowledgeAccess(props.document.id, {
      visibility: visibility.value, class_id: classId.value, published: published.value,
    }))
  } catch (err) { error.value = (err as Error).message }
  finally { busy.value = false }
}
onMounted(() => { if (visibility.value === 'class') void loadClasses() })
</script>

<template>
  <div class="doc-access" :aria-label="`${document.title}的发布范围`">
    <p v-if="!document.can_manage">{{ document.published ? '已发布' : '未发布' }} · {{ document.visibility === 'public' ? '全课程' : document.visibility === 'class' ? '指定班级' : '私有' }}</p>
    <template v-else>
      <n-select v-model:value="visibility" :options="options" aria-label="文档可见范围" size="small" :disabled="busy" />
      <n-select v-if="visibility === 'class'" v-model:value="classId" :options="classes" :loading="classLoading" placeholder="选择班级" aria-label="发布班级" size="small" :disabled="busy" @focus="loadClasses" />
      <label class="doc-access__toggle">向学生发布 <n-switch v-model:value="published" aria-label="向学生发布" :disabled="busy || visibility === 'private'" /></label>
      <n-button size="small" :loading="busy" :disabled="visibility === 'class' && !classId" @click="save">保存范围</n-button>
      <small>保存后生效；学生引用还需索引就绪。教师笔记与答案片段不会提供给学生。</small>
    </template>
    <p v-if="error" role="alert">{{ error }} <button v-if="visibility === 'class'" type="button" @click="loadClasses">重试班级加载</button></p>
  </div>
</template>

<style scoped>
.doc-access { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; width: 100%; box-sizing: border-box; color: var(--plex-text); background: var(--plex-bg-card); padding: 12px; border-radius: 10px; }
.doc-access :deep(.n-select) { flex: 1 1 180px; min-width: 0; }
.doc-access__toggle { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.doc-access small, .doc-access p { flex-basis: 100%; margin: 0; line-height: 1.6; }
.doc-access small { opacity: .72; }
.doc-access [role='alert'] { color: #d48339; }
.doc-access button { color: inherit; cursor: pointer; }
</style>
