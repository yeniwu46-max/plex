<script setup lang="ts">
import { RouterLink } from 'vue-router'
import PythonTraceView from './PythonTraceView.vue'
import { NModal, NSpin } from 'naive-ui'
import { useRagSourceDialog } from '../../composables/useRagSourceDialog'
import { tutorModes, type TutorResponse } from '../../api/tutoring'

const props = defineProps<{ response: TutorResponse }>()
const autoLabels = {concept_explain:'概念解释',algorithm_validation:'算法验证',algorithm_trace:'过程推演',learning_overview:'学习记录',clarify:'继续交流'}
const { open: sourceOpen, loading: sourceLoading, detail: source, error: sourceError, show: openSource, retry: retrySource } = useRagSourceDialog(() => props.response)
</script>

<template>
  <section class="tutor-answer" aria-label="小 E 辅导回答">
    <small class="tutor-answer__mode">{{ tutorModes.find(item => item.mode === response.mode)?.label || autoLabels[response.mode as keyof typeof autoLabels] }}</small>
    <p>{{ response.summary }}</p>
    <small v-if="response.records_at">记录截至 {{ new Date(response.records_at).toLocaleString() }}</small>
    <ul v-if="response.annotations?.length" class="tutor-answer__annotations">
      <li v-for="item in response.annotations" :key="item.line"><strong>第 {{ item.line }} 行</strong> · {{ item.message }}</li>
    </ul>
    <div v-if="response.pseudocode_lines?.length" class="tutor-answer__steps">
      <small>局部伪代码 · 核心决策由你补全</small>
      <ol><li v-for="(item, index) in response.pseudocode_lines" :key="index"><code>{{ item.step }}</code><p>{{ item.explanation }}</p></li></ol>
    </div>
    <div v-if="response.example" class="tutor-answer__steps">
      <small>概念示例 · 尚未执行</small>
      <pre class="tutor-answer__source-body">{{ response.example.code }}</pre><p>{{ response.example.explanation }}</p>
    </div>
    <div v-if="response.trace_steps?.length" class="tutor-answer__steps">
      <small>{{ response.trace_notice }}</small><p>示例输入：{{ response.trace_input }}</p>
      <ol><li v-for="(step, index) in response.trace_steps" :key="index">{{ step }}</li></ol>
    </div>
    <python-trace-view v-if="response.execution_trace" :trace="response.execution_trace" />
    <div v-if="response.next_step" class="tutor-answer__next"><strong>下一步</strong><p>{{ response.next_step }}</p></div>
    <p v-if="response.follow_up">{{ response.follow_up }}</p>
    <small class="tutor-answer__evidence">{{ response.evidence_notice }}</small>
    <ul v-if="response.citations.length" class="tutor-answer__sources">
      <li v-for="citation in response.citations" :key="citation.chunk_id">
        <button type="button" @click="openSource(citation)">{{ citation.title || citation.document_title }} · v{{ citation.version }}</button>
        <small>{{ citation.supports }}</small>
      </li>
    </ul>
    <aside v-if="response.counterexample_pick" class="tutor-answer__practice" aria-label="推荐反例挑战">
      <strong>可选练习 · {{ response.counterexample_pick.title }}</strong>
      <p>{{ response.counterexample_pick.reason }}</p>
      <small>依据学习状态 v{{ response.counterexample_pick.state_version }} · 证据 {{ response.counterexample_pick.evidence_ids.map(id => `#${id}`).join('、') }}</small>
      <RouterLink :to="{ name: 'student-counterexamples', params: { challengeId: response.counterexample_pick.id }, query: { version: response.counterexample_pick.version } }">开始反例挑战</RouterLink>
      <small>用合法输入核对边界；反例实践单独记录，不计入正式成绩。</small>
    </aside>
    <p v-if="response.recommendation_notice" role="status">{{ response.recommendation_notice }}</p>
    <n-modal v-model:show="sourceOpen" preset="card" class="plex-reading-modal tutor-source-modal" :title="source?.title || '课程来源'" style="width: min(720px, 92vw)">
      <p v-if="sourceError" role="alert">{{ sourceError }} <button type="button" @click="retrySource">重试来源</button></p>
      <n-spin :show="sourceLoading"><pre v-if="source" class="tutor-answer__source-body">{{ source.content }}</pre></n-spin>
    </n-modal>
  </section>
</template>

<style scoped>
.tutor-answer { min-width: 0; line-height: 1.7; overflow-wrap: anywhere; color: inherit; }
.tutor-answer p { margin: 8px 0; white-space: pre-wrap; }
.tutor-answer__mode { display: inline-block; padding: 2px 8px; border: 1px solid currentColor; border-radius: 6px; }
.tutor-answer__next { margin: 12px 0; padding: 8px 12px; border-inline-start: 3px solid #22afa9; background: rgb(34 175 169 / 8%); }
.tutor-answer__annotations, .tutor-answer__steps ol { padding-inline-start: 22px; }
.tutor-answer__steps { padding: 10px; border: 1px solid rgb(128 150 160 / 40%); border-radius: 8px; }
.tutor-answer__steps code { font-family: inherit; white-space: pre-wrap; }
.tutor-answer__sources { list-style: none; padding: 0; }
.tutor-answer__sources li { margin: 8px 0; }
.tutor-answer__sources small { display: block; }
.tutor-answer__sources button { color: inherit; font: inherit; text-align: left; background: transparent; border: 0; padding: 0; text-decoration: underline; cursor: pointer; }
.tutor-answer__sources button:focus-visible { outline: 2px solid #22afa9; outline-offset: 3px; }
.tutor-answer__evidence { display: block; opacity: .85; }
.tutor-answer__practice { display: grid; gap: 8px; margin-top: 16px; padding: 12px; border: 1px solid currentColor; border-radius: 8px; }
.tutor-answer__practice a { justify-self: start; padding: 6px 12px; border: 1px solid currentColor; border-radius: 6px; color: inherit; font-weight: 600; }
.tutor-answer__practice a:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
:global(html[data-plex-style="comic"] .tutor-answer__practice) { border-width: 2px; border-radius: 4px 12px 4px 12px; box-shadow: 3px 3px 0 rgb(34 175 169 / 20%); }
.tutor-answer__source-body { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14px; line-height: 1.7; }
:global(html[data-plex-style="comic"] .tutor-answer__next) { border: 2px solid currentColor; border-radius: 4px 12px 4px 12px; box-shadow: 3px 3px 0 rgb(34 175 169 / 20%); }
</style>
