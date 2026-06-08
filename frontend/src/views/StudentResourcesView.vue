<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NProgress, NSelect, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { createResourceTask, fetchPersonalizedResources, fetchResourceTask, type PersonalizedResource, type ResourceTask } from '../api/personalizedResources'

const message = useMessage()
const knowledgeKey = ref('loop')
const task = ref<ResourceTask | null>(null)
const resources = ref<PersonalizedResource[]>([])
const generating = ref(false)
const selected = ref<PersonalizedResource | null>(null)
const knowledgeOptions = [
  { label: 'Python入门', value: 'intro' }, { label: '变量与类型', value: 'var' },
  { label: '条件分支', value: 'cond' }, { label: '循环结构', value: 'loop' },
  { label: '列表', value: 'list' }, { label: '字典', value: 'dict' },
  { label: '字符串', value: 'str' }, { label: '函数', value: 'func' },
  { label: '文件读写', value: 'file' }, { label: '异常处理', value: 'except' },
]
const typeLabels: Record<string, string> = { lesson_document: '讲解文档', mind_map: '思维导图', exercise_set: '分层题库', extended_reading: '拓展阅读', coding_lab: '代码实操', audio_explanation: '语音讲解' }

async function load() { resources.value = (await fetchPersonalizedResources()).items }
async function poll(id: string) {
  for (let index = 0; index < 90; index += 1) {
    task.value = await fetchResourceTask(id)
    if (['completed', 'failed'].includes(task.value.status)) break
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
  }
}
async function generate() {
  generating.value = true
  try {
    task.value = await createResourceTask(knowledgeKey.value)
    if (task.value.status !== 'completed') await poll(task.value.task_id)
    if (task.value.status === 'failed') throw new Error(task.value.error || '生成任务失败')
    await load()
    message.success('五类个性化资源已生成')
  } catch (error) { message.error(error instanceof Error ? error.message : '生成失败') }
  finally { generating.value = false }
}
function contentText(item: PersonalizedResource) {
  return typeof item.content.markdown === 'string' ? item.content.markdown : JSON.stringify(item.content, null, 2)
}
onMounted(() => void load())
</script>

<template>
  <DashboardShell active-nav="resources" page-title="个性化资源中心" page-subtitle="画像驱动的五类课程资源" search-placeholder="" hide-search>
    <main class="resource-page">
      <section class="generator"><div><h2>生成学习资源包</h2><p>画像解释 → 知识检索 → 教学设计 → 资源生成 → 质量审核 → 路径更新</p></div><n-select v-model:value="knowledgeKey" :options="knowledgeOptions" class="knowledge-select" /><n-button type="primary" :loading="generating" @click="generate">生成五类资源</n-button></section>
      <section v-if="task" class="task-panel"><header><strong>{{ task.status }} · {{ task.backend }}</strong><span v-if="task.fallback_reason">已降级：{{ task.fallback_reason }}</span></header><n-progress :percentage="task.progress" color="#25f5ee" /><div class="steps"><n-tag v-for="step in task.steps" :key="step.agent" :type="step.status === 'completed' ? 'success' : step.status === 'running' ? 'warning' : 'default'">{{ step.agent }} · {{ step.status }}</n-tag></div></section>
      <section class="resource-grid"><article v-for="item in resources" :key="item.id" class="resource-card" @click="selected = item"><header><n-tag type="info">{{ typeLabels[item.resource_type] }}</n-tag><n-tag :type="item.backend === 'iflytek_spark' ? 'success' : 'warning'">{{ item.backend }}</n-tag></header><h3>{{ item.title }}</h3><p>{{ item.recommendation_reason }}</p><footer><span>置信度 {{ Math.round(item.confidence * 100) }}%</span><span>{{ item.estimated_minutes }} 分钟</span></footer></article></section>
      <section v-if="selected" class="resource-detail"><header><h2>{{ selected.title }}</h2><n-button quaternary @click="selected = null">关闭</n-button></header><pre>{{ contentText(selected) }}</pre><h4>知识库引用</h4><ul><li v-for="citation in selected.citations" :key="citation.document_id">{{ citation.title }} · {{ citation.section }}：{{ citation.snippet }}</li></ul></section>
    </main>
  </DashboardShell>
</template>

<style scoped>
.resource-page{width:100%;padding:0 var(--plex-page-gutter-x) 2rem;overflow-y:auto}.generator,.task-panel,.resource-card,.resource-detail{border:1px solid rgba(37,245,238,.15);background:rgba(3,16,28,.84);border-radius:16px}.generator{display:flex;align-items:center;gap:1rem;padding:1.2rem}.generator div{flex:1}.generator h2{margin:0;color:#f2fbff}.generator p{margin:.35rem 0 0;color:#7da5b6}.knowledge-select{width:180px}.task-panel{margin-top:1rem;padding:1rem}.task-panel header{display:flex;justify-content:space-between;color:#b9e9e6;margin-bottom:.7rem}.steps{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.8rem}.resource-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1rem}.resource-card{padding:1.1rem;cursor:pointer}.resource-card header,.resource-card footer{display:flex;justify-content:space-between;gap:.5rem}.resource-card h3{color:#f0faff}.resource-card p,.resource-card footer{color:#86a8b7;font-size:.85rem}.resource-detail{margin-top:1rem;padding:1.2rem}.resource-detail header{display:flex;justify-content:space-between}.resource-detail h2,.resource-detail h4{color:#eefbff}.resource-detail pre{white-space:pre-wrap;color:#cce6ef;line-height:1.6;overflow:auto}.resource-detail li{color:#8fb7c4;margin:.45rem 0}@media(max-width:850px){.generator{align-items:stretch;flex-direction:column}.knowledge-select{width:100%}.resource-grid{grid-template-columns:1fr}}
</style>
