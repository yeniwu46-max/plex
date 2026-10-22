<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NRadioGroup, NRadio, NAlert } from 'naive-ui'
import { useRouter } from 'vue-router'
import type { PracticeQuestionPayload } from '../../api/practiceQuestions'
import { practiceRequest, type Attempt } from '../../api/studentPractice'
import { createRequestId } from '../../utils/browserCrypto'
const props = defineProps<{ question: PracticeQuestionPayload }>()
const router = useRouter(), choice = ref<number | null>(null), busy = ref(false), error = ref(''), attempt = ref<Attempt | null>(null)
let request: { id: string; choice: number } | null = null
async function submit() {
  if (choice.value === null || busy.value) return
  busy.value = true; error.value = ''
  if (!request || request.choice !== choice.value) request = { id: createRequestId(), choice: choice.value }
  try {
    attempt.value = await practiceRequest<Attempt>('post', `/practice-submissions/${encodeURIComponent(props.question.id)}`, { request_id: request.id, selected_index: choice.value, code: '' })
    request = null
  } catch (e) { error.value = e instanceof Error ? e.message : '提交失败，请重试' }
  finally { busy.value = false }
}
</script>
<template>
  <section class="choice-practice">
    <h2>{{ question.title }}</h2><p>{{ question.description }}</p>
    <n-radio-group v-model:value="choice" name="practice-answer" aria-label="选择答案" :disabled="busy"><n-radio v-for="(option,i) in question.options" :key="i" :value="i">{{ String.fromCharCode(65+i) }}. {{ option }}</n-radio></n-radio-group>
    <n-alert v-if="error" type="warning">{{ error }}</n-alert>
    <n-alert v-if="attempt" :type="attempt.result.all_passed?'success':'info'">{{ attempt.result.all_passed?'回答正确，已记录正式作答':'本次未答对，已记录正式作答，可以继续思考或请小E帮助' }}</n-alert>
    <div><n-button type="primary" :disabled="choice===null" :loading="busy" @click="submit">正式提交</n-button><n-button v-if="attempt" @click="router.push({path:'/student/messenger',query:{submission:attempt.id}})">关联这次作答问小E</n-button></div>
  </section>
</template>
<style scoped>
.choice-practice{padding:24px;background:var(--plex-bg-card);color:var(--plex-text);border:1px solid var(--plex-border);border-radius:18px;display:grid;gap:24px}.choice-practice p{white-space:pre-wrap;line-height:1.8}.n-radio-group{display:grid;gap:18px}.choice-practice>div:last-child{display:flex;flex-wrap:wrap;gap:12px}:global(html[data-plex-style="comic"]) .choice-practice{border-width:2px;box-shadow:4px 4px 0 #07131f}
</style>
