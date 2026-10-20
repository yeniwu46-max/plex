<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchTutorSource } from '../../api/agentService'

const props = defineProps<{
  requestId: string
  citations: Array<{ label: string; title: string; chapter: string }>
}>()
const emit = defineEmits<{ invalid: [] }>()
const openLabel = ref('')
const excerpt = ref('')
const loading = ref(false)
const error = ref('')
let sequence = 0

function clear() {
  ++sequence
  openLabel.value = ''
  excerpt.value = ''
  error.value = ''
  loading.value = false
}

async function toggle(label: string) {
  const closing = openLabel.value === label
  clear()
  if (closing) return
  openLabel.value = label
  const current = sequence
  loading.value = true
  try {
    const source = await fetchTutorSource(props.requestId, label)
    if (sequence === current) excerpt.value = source.excerpt
  } catch {
    if (sequence === current) {
      error.value = '课程依据暂时无法核验，请重新提问。'
      emit('invalid')
    }
  } finally {
    if (sequence === current) loading.value = false
  }
}

onMounted(() => document.addEventListener('visibilitychange', clear))
onBeforeUnmount(() => {
  clear()
  document.removeEventListener('visibilitychange', clear)
})
</script>

<template>
  <section class="tutor-evidence" aria-label="课程依据">
    <strong>课程依据</strong>
    <div v-for="source in citations" :key="source.label">
      <button type="button" :aria-expanded="openLabel === source.label" @click="toggle(source.label)">
        [{{ source.label }}] {{ source.title }} · {{ source.chapter }}
      </button>
      <div v-if="openLabel === source.label" aria-live="polite">
        <p v-if="loading">正在核验课程依据…</p>
        <p v-else-if="error">{{ error }}</p>
        <p v-else class="tutor-evidence__excerpt">{{ excerpt }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tutor-evidence { margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px solid currentColor; font-size: 0.78rem; }
.tutor-evidence button { color: inherit; background: transparent; border: 0; text-align: left; cursor: pointer; padding: 0.4rem 0; overflow-wrap: anywhere; }
.tutor-evidence__excerpt { white-space: pre-wrap; line-height: 1.6; overflow-wrap: anywhere; }
</style>
