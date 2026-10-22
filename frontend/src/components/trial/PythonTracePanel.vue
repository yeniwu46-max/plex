<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fetchTraceCapabilities, tracePython, type PythonTraceResult, type TraceCapabilities } from '../../api/pythonTrace'
import PythonTraceView from '../student/PythonTraceView.vue'

const props = defineProps<{ code: string; questionRef: string; formalQuestionId?: number; accountId?: number; disabled?: boolean }>()
const emit = defineEmits<{ recorded: [record: { id: string; code: string; version?: string }] }>()
const caps = ref<TraceCapabilities | null>(null)
const loading = ref(false)
const capabilityError = ref(false)
const pending = ref(false)
const error = ref('')
const stdin = ref('')
const result = ref<PythonTraceResult | null>(null)
const available = computed(() => caps.value?.enabled && caps.value.backend_supported)
let revision = 0, capabilityRevision = 0, alive = true

async function loadCapabilities() {
  const request = ++capabilityRevision
  loading.value = true; capabilityError.value = false
  try {
    const value = await fetchTraceCapabilities()
    if (alive && request === capabilityRevision) caps.value = value
  } catch { if (alive && request === capabilityRevision) capabilityError.value = true }
  finally { if (alive && request === capabilityRevision) loading.value = false }
}
function clear() { ++revision; pending.value = false; result.value = null; error.value = '' }
watch([() => props.accountId, () => props.questionRef, () => props.formalQuestionId], () => {
  clear(); stdin.value = ''; caps.value = null; void loadCapabilities()
}, { flush: 'sync' })
watch([() => props.code, stdin], clear, { flush: 'sync' })
onMounted(loadCapabilities)
onBeforeUnmount(() => { alive = false; ++revision; ++capabilityRevision })

async function runTrace() {
  if (!alive || pending.value || props.disabled || !available.value || !props.accountId || !props.code.trim()) return
  if (new TextEncoder().encode(stdin.value).length > 4096) { error.value = '输入最多为 4 KiB 文本'; return }
  const request = ++revision, source = props.code
  pending.value = true; error.value = ''; result.value = null
  try {
    const value = await tracePython({ code: source, stdin: stdin.value,
      question_ref: props.questionRef, formal_question_id: props.formalQuestionId })
    if (!alive || request !== revision) return
    result.value = value
    if (value.trace_status === 'recorded' && value.trace) emit('recorded', { id: value.run_id, code: source, version: value.question_version })
    else error.value = '执行达到隔离环境限制，本次未获得逐行记录。请缩小示例后重试。'
  } catch (failure) {
    if (alive && request === revision) error.value = failure instanceof Error ? failure.message : '本次轨迹未完成，请稍后重试'
  } finally { if (alive && request === revision) pending.value = false }
}
</script>

<template>
  <section v-if="available || capabilityError" class="python-trace-panel" aria-label="代码逐行轨迹">
    <template v-if="capabilityError"><p role="status">逐行轨迹状态暂不可用。</p><button type="button" :disabled="loading" @click="loadCapabilities">重试读取</button></template>
    <template v-else>
      <details><summary>逐行轨迹的输入与范围</summary>
        <p>支持赋值、条件、循环和基础集合，最多 80 步。函数定义、导入及属性访问请使用普通运行。只执行当前代码与下方输入。</p>
        <label>本次标准输入 · 可留空<textarea v-model="stdin" rows="2" maxlength="4096" placeholder="例如：3" /></label>
      </details>
      <button type="button" :disabled="pending || disabled || !code.trim()" @click="runTrace">{{ pending ? '正在获取轨迹…' : '查看逐行轨迹' }}</button>
      <p v-if="error" role="alert">{{ error }}</p>
      <python-trace-view v-if="result?.trace" :trace="result.trace" />
    </template>
  </section>
</template>

<style scoped>
.python-trace-panel { padding: 12px; min-width: 0; border-top: 1px solid rgb(128 150 160 / 30%); color: var(--plex-text); background: var(--plex-bg-card); font-size: 13px; }
.python-trace-panel p { margin: 8px 0; overflow-wrap: anywhere; }
.python-trace-panel summary { cursor: pointer; }
.python-trace-panel label { display: grid; gap: 6px; margin: 8px 0; }
.python-trace-panel textarea { width: 100%; box-sizing: border-box; resize: vertical; color: inherit; background: transparent; border: 1px solid currentColor; padding: 8px; border-radius: 6px; font: inherit; }
.python-trace-panel button { margin: 10px 0; padding: 6px 12px; font: inherit; color: inherit; background: transparent; border: 1px solid currentColor; border-radius: 6px; cursor: pointer; }
.python-trace-panel button:disabled { opacity: .55; cursor: default; }
.python-trace-panel :focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
</style>
