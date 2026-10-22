<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NCard, NInput, NTag } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { useAuthStore } from '../stores/auth'
import { useCounterexampleAttempt } from '../composables/useCounterexampleAttempt'
import { describeValueContract, type CounterexampleOutcome, type CounterexampleAttempt } from '../api/counterexamples'

defineOptions({ name: 'StudentCounterexampleView' })
const auth = useAuthStore(), route = useRoute(), router = useRouter()
const challengeId = computed(() => String(route.params.challengeId || ''))
const userId = computed(() => auth.profile?.role === 'student' ? auth.profile.id : undefined)
const { items, challenge, attempt, history, input, expected, explanation, loading, busy, error, historyError,
  locked, canRetry, canStart, pending, unresolvedId, load, readResult, submit, startNew } = useCounterexampleAttempt(userId, challengeId)
const versionMismatch = computed(() => typeof route.query.version === 'string' && !!challenge.value && route.query.version !== challenge.value.version)
const statuses: Record<CounterexampleAttempt['status'], string> = {
  processing: '正在核对', complete: '已核对', material_issue: '题目待核对', unavailable: '可重试', stale: '版本已变化',
}
function output(result?: CounterexampleOutcome) {
  return result?.kind === 'exception' ? `发生 ${result.exception}` : result?.kind === 'value' ? JSON.stringify(result.value) : '尚无结果'
}
function date(value: string) { return new Date(value).toLocaleString('zh-CN', { hour12: false }) }
function open(id: string) { void router.push(`/student/trials/counterexamples/${encodeURIComponent(id)}`) }
</script>

<template>
  <DashboardShell active-nav="trial" page-title="反例挑战" page-subtitle="用一个测试输入，找出程序的边界问题" search-placeholder="" hide-search>
    <main class="counterexample-page" :aria-busy="loading || busy">
      <header class="counterexample-header">
        <div><span class="counterexample-kicker">PLEX · 反例实验室</span><h1>{{ challenge?.title || '让程序的漏洞现形' }}</h1>
          <p>读懂程序，设计输入，核对输出，再解释为什么。</p></div>
        <n-button @click="router.push(challengeId ? '/student/trials/counterexamples' : '/student/trials')">
          {{ challengeId ? '返回挑战列表' : '返回试炼场' }}
        </n-button>
      </header>
      <n-alert v-if="error" type="error" :show-icon="false" role="alert" class="counterexample-notice">{{ error }}
        <n-button size="small" :disabled="busy || loading" @click="load">重新加载</n-button>
      </n-alert>
      <n-alert v-if="historyError" type="warning" :show-icon="false" role="alert" class="counterexample-notice">
        {{ historyError }} <n-button size="small" :disabled="busy || loading" @click="load">重新读取</n-button>
      </n-alert>
      <p v-if="loading" role="status">正在读取题目与本人记录…</p>
      <template v-else-if="!challengeId">
        <n-card v-if="!items.length" class="counterexample-empty">
          <h2>{{ error ? '挑战暂未加载' : '本班还没有开放的反例挑战' }}</h2>
          <p>教师核对程序、测试与教学说明后，挑战会在这里出现。</p>
          <n-button @click="load">刷新列表</n-button>
        </n-card>
        <section v-else class="counterexample-list" aria-label="本班开放的反例挑战">
          <n-card v-for="item in items" :key="item.id" class="counterexample-panel">
            <n-tag size="small">Python · 版本 {{ item.revision }}</n-tag>
            <h2>{{ item.title }}</h2><p class="task-statement">{{ item.statement }}</p>
            <n-button type="primary" @click="open(item.id)">开始寻找反例</n-button>
          </n-card>
        </section>
      </template>
      <template v-else>
        <n-alert v-if="versionMismatch" type="warning" :show-icon="false" role="alert" class="counterexample-notice">推荐的题目版本已更新，请返回挑战列表后重新选择。原推荐不会自动替换为新题。</n-alert>
        <div v-if="challenge && !versionMismatch" class="counterexample-workspace">
          <n-card class="counterexample-panel" title="01 · 阅读任务">
            <div class="counterexample-meta"><n-tag size="small">Python</n-tag><span>题目版本 {{ challenge.revision }}</span></div>
            <p class="task-statement">{{ challenge.statement }}</p>
            <dl class="counterexample-contract"><dt>输入范围</dt><dd>{{ describeValueContract(challenge.input_contract) }}</dd>
              <dt>输出格式</dt><dd>{{ describeValueContract(challenge.output_contract) }}</dd></dl>
            <p>下面的程序含有错误。请设计一个合法输入，让它暴露问题。</p>
            <pre class="counterexample-code" tabindex="0" aria-label="待检查的 Python 程序"><code>{{ challenge.buggy_code }}</code></pre>
            <p v-if="challenge.allowed_bug_exceptions.length" class="counterexample-note">本题允许用 {{ challenge.allowed_bug_exceptions.join('、') }} 异常作为错误表现。</p>
          </n-card>
          <n-card class="counterexample-panel" title="02 · 提交你的证据">
            <form class="counterexample-form" @submit.prevent="submit">
              <label for="counter-input">测试输入（JSON）</label>
              <n-input id="counter-input" v-model:value="input" type="textarea" :disabled="locked" :maxlength="10000"
                :autosize="{ minRows: 2, maxRows: 5 }" :input-props="{ 'aria-label': '测试输入 JSON', spellcheck: false }"
                :placeholder="challenge.input_contract.type === 'integer_array' ? '例如 [1, 2]，请自行设计能触发错误的数据' : '填写一个符合范围的整数'" />
              <label for="counter-expected">你认为正确的输出（JSON）</label>
              <n-input id="counter-expected" v-model:value="expected" type="textarea" :disabled="locked" :maxlength="10000"
                :autosize="{ minRows: 1, maxRows: 4 }" :input-props="{ 'aria-label': '预期正确输出 JSON', spellcheck: false }" placeholder="根据题意推算，不要照抄错误程序的输出" />
              <label for="counter-explanation">为什么这个输入能暴露错误？</label>
              <n-input id="counter-explanation" v-model:value="explanation" type="textarea" :disabled="locked" :maxlength="2000" show-count
                :autosize="{ minRows: 4, maxRows: 9 }" :input-props="{ 'aria-label': '反例原因说明' }" placeholder="指出有问题的条件或操作，说明它如何影响你的这组输入。" />
              <div class="counterexample-actions">
                <n-button v-if="!pending && !unresolvedId" type="primary" attr-type="submit" :loading="busy">验证这个反例</n-button>
                <n-button v-else-if="canRetry" type="primary" attr-type="submit" :loading="busy">重试原提交</n-button>
                <n-button v-if="pending || unresolvedId" :disabled="busy" @click="readResult()">读取最新结果</n-button>
                <n-button v-if="pending && canStart" :disabled="busy" @click="startNew">修改并尝试新输入</n-button>
              </div>
              <p class="counterexample-note">仅记录本次反例实践，不计入班级成绩。执行环境故障时可以重试，重复请求不会重复记录。</p>
              <p v-if="busy" role="status">正在核对输入和解释，请稍候。离开后可恢复已保存的结果。</p>
            </form>
          </n-card>
        </div>
        <n-card v-if="attempt && !versionMismatch" class="counterexample-panel counterexample-result" title="03 · 核对结果" aria-live="polite">
          <n-tag>{{ statuses[attempt.status] }}</n-tag>
          <template v-if="attempt.status === 'complete'">
            <div class="counterexample-facts">
              <article><h3>程序结果</h3><p>{{ attempt.counterexample_found ? '找到差异：这个输入触发了错误。' : '这个输入的结果相同，还没有暴露错误。' }}</p></article>
              <article><h3>预期输出</h3><p>{{ attempt.expected_output_correct ? '你的预期与核对结果一致。' : '你的预期与核对结果不同，请再按题意推算。' }}</p></article>
            </div>
            <div class="counterexample-facts">
              <div><h3>错误程序的实际输出</h3><pre class="counterexample-code">{{ output(attempt.buggy_result) }}</pre></div>
              <div><h3>参考与修正版一致的输出</h3><pre class="counterexample-code">{{ output(attempt.correct_result) }}</pre></div>
            </div>
            <section v-if="attempt.explanation_review" class="counterexample-explanation" aria-label="原因说明核对">
              <h3>{{ attempt.explanation_review.source === 'teacher' ? '教师核对' : '小 E 的解释建议' }}</h3>
              <p>{{ attempt.explanation_review.feedback }}</p><small>{{ attempt.explanation_review.notice }}</small>
            </section>
            <p class="counterexample-note">{{ attempt.notice }} · 证据 #{{ attempt.evidence_event_id }}</p>
          </template>
          <p v-else role="status">{{ attempt.message }}</p>
          <small>提交时间：{{ date(attempt.created_at) }}</small>
        </n-card>
        <n-card v-if="history.length && challenge && !versionMismatch" class="counterexample-panel counterexample-history" title="本版本最近的提交">
          <ul><li v-for="row in history" :key="row.request_id">
            <span>{{ date(row.created_at) }} · {{ statuses[row.status] }}</span>
            <n-button size="small" :disabled="busy" @click="readResult(row.request_id)">查看记录</n-button>
          </li></ul>
        </n-card>
        <n-button v-if="!challenge && !loading" :disabled="busy" @click="load">重新加载题目</n-button>
      </template>
    </main>
  </DashboardShell>
</template>

<style scoped>
.counterexample-page { max-width: 1440px; margin: 0 auto; padding: clamp(16px, 3vw, 36px); min-width: 0; }
.counterexample-header { display: flex; gap: 20px; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.counterexample-header h1 { font-size: clamp(24px, 3vw, 34px); margin: 8px 0; }
.counterexample-header p { margin: 0; opacity: .8; }
.counterexample-kicker { font-weight: 700; letter-spacing: .12em; font-size: 12px; }
.counterexample-list, .counterexample-workspace { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; }
.counterexample-panel { min-width: 0; }
.counterexample-panel p { line-height: 1.8; overflow-wrap: anywhere; }
.counterexample-panel h2 { font-size: 20px; }
.counterexample-panel h3 { font-size: 15px; margin: 16px 0 8px; }
.counterexample-notice, .counterexample-result, .counterexample-history { margin-bottom: 20px; }
.counterexample-result { margin-top: 22px; }
.counterexample-meta, .counterexample-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.counterexample-contract { padding: 14px; border: 1px solid color-mix(in srgb, currentColor 18%, transparent); border-radius: 8px; }
.counterexample-contract dt { font-weight: 700; margin-top: 8px; }
.counterexample-contract dt:first-child { margin-top: 0; }
.counterexample-contract dd { margin: 4px 0 0; overflow-wrap: anywhere; }
.task-statement { white-space: pre-wrap; }
.counterexample-code { max-width: 100%; overflow: auto; padding: 16px; border: 1px solid color-mix(in srgb, currentColor 18%, transparent); border-radius: 8px; background: color-mix(in srgb, currentColor 5%, transparent); font: 14px/1.8 Consolas, monospace; tab-size: 4; }
.counterexample-code:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
.counterexample-form { display: grid; gap: 12px; }
.counterexample-form label { font-weight: 600; }
.counterexample-form label:not(:first-child) { margin-top: 8px; }
.counterexample-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.counterexample-facts > * { min-width: 0; }
.counterexample-explanation { border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent); padding-top: 8px; }
.counterexample-note, .counterexample-panel small { font-size: 12px; line-height: 1.8; opacity: .75; }
.counterexample-history ul { list-style: none; margin: 0; padding: 0; }
.counterexample-history li { display: flex; gap: 12px; align-items: center; justify-content: space-between; padding: 10px 0; flex-wrap: wrap; }
:global(html[data-plex-style="comic"] .counterexample-page .counterexample-panel) { border: 2px solid color-mix(in srgb, currentColor 38%, transparent); border-radius: 5px 16px 5px 16px; box-shadow: 4px 4px 0 color-mix(in srgb, currentColor 20%, transparent); }
:global(html[data-plex-style="comic"] .counterexample-page .counterexample-kicker) { display: inline-block; padding: 5px 10px; border: 2px solid currentColor; border-radius: 5px; }
@media (max-width: 900px) { .counterexample-workspace { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 600px) { .counterexample-list, .counterexample-facts { grid-template-columns: minmax(0, 1fr); } .counterexample-header { align-items: flex-start; flex-direction: column; } }
</style>
