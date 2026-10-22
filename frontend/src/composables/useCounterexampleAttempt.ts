import { createRequestId } from '../utils/browserCrypto'
import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { isAxiosError } from 'axios'
import { fetchCounterexample, fetchCounterexamples, fetchCounterexampleAttempt, fetchCounterexampleAttempts,
  submitCounterexample, parseCounterexampleValue, type CounterexampleChallenge, type CounterexampleAttempt,
  type CounterexampleRequest, type AttemptSummary } from '../api/counterexamples'

// Persist identifiers only. Answers are restored through the authenticated server.
export function useCounterexampleAttempt(userId: Ref<number | undefined>, challengeId: Ref<string>) {
  const items = ref<CounterexampleChallenge[]>([])
  const challenge = ref<CounterexampleChallenge | null>(null)
  const attempt = ref<CounterexampleAttempt | null>(null)
  const history = ref<AttemptSummary[]>([])
  const input = ref(''), expected = ref(''), explanation = ref('')
  const loading = ref(false), busy = ref(false), error = ref(''), historyError = ref('')
  const pending = ref<CounterexampleRequest | null>(null)
  const unresolvedId = ref<string | null>(null)
  let generation = 0
  let controller = new AbortController()
  const cacheKey = () => `plex:counterexample:${userId.value}:${challengeId.value}`
  const locked = computed(() => busy.value || !!pending.value || !!unresolvedId.value)
  const canRetry = computed(() => !!pending.value && (!attempt.value || attempt.value.retryable))
  const canStart = computed(() => !busy.value && !loading.value && !!challenge.value &&
    (!pending.value || attempt.value?.status === 'complete' || attempt.value?.status === 'stale'))
  function readCache() {
    try { return localStorage.getItem(cacheKey()) } catch { return null }
  }
  function remember(id: string | null) {
    try { if (id) localStorage.setItem(cacheKey(), id); else localStorage.removeItem(cacheKey()) } catch { /* Storage is optional. */ }
  }
  function isCurrent(mark: number) { return mark === generation && !!userId.value && !controller.signal.aborted }
  function message(cause: unknown, fallback: string) {
    if (isAxiosError(cause)) return cause.response?.data?.message || fallback
    return cause instanceof Error ? cause.message : fallback
  }
  function invalidRecord(cause: unknown) { return isAxiosError(cause) && [400, 404, 409].includes(cause.response?.status || 0) }
  function show(row: CounterexampleAttempt) {
    unresolvedId.value = null
    attempt.value = row
    input.value = JSON.stringify(row.input)
    expected.value = JSON.stringify(row.expected_output)
    explanation.value = row.explanation
    pending.value = { request_id: row.request_id, revision: row.revision, version: row.version,
      input: row.input, expected_output: row.expected_output, explanation: row.explanation }
    remember(row.request_id)
    if (row.status === 'material_issue' || row.status === 'stale') challenge.value = null
  }
  async function restore(id: string, mark: number) {
    const row = await fetchCounterexampleAttempt(id, controller.signal)
    if (!isCurrent(mark)) return
    if (row.challenge_id !== challengeId.value) throw new Error('这条记录不属于当前题目。')
    show(row)
  }
  async function load() {
    controller.abort(); controller = new AbortController()
    const mark = ++generation
    challenge.value = null; attempt.value = null; pending.value = null; unresolvedId.value = null
    items.value = []; history.value = []; error.value = ''; historyError.value = ''
    input.value = ''; expected.value = ''; explanation.value = ''; busy.value = false
    loading.value = true
    try {
      if (!userId.value) return
      if (!challengeId.value) {
        const list = await fetchCounterexamples(controller.signal)
        if (isCurrent(mark)) items.value = list
        return
      }
      const remembered = readCache()
      // Read saved results first: a material issue may have withdrawn the task.
      if (remembered) {
        unresolvedId.value = remembered
        try { await restore(remembered, mark) }
        catch (cause) {
          if (isCurrent(mark)) {
            if (invalidRecord(cause)) { unresolvedId.value = null; remember(null) }
            historyError.value = invalidRecord(cause) ? '上次记录已失效或当前不可访问。请返回挑战列表，选择可用题目后再查看历史记录。' : '上次记录暂无法恢复，请先重试读取，避免重复提交。'
          }
        }
      }
      const restoredAttempt = attempt.value as CounterexampleAttempt | null
      if (!isCurrent(mark) || restoredAttempt?.status === 'material_issue') return
      const task = await fetchCounterexample(challengeId.value, controller.signal)
      if (!isCurrent(mark)) return
      challenge.value = task
      const restoredRequest = pending.value as CounterexampleRequest | null
      if (restoredRequest && (restoredRequest.version !== task.version || restoredRequest.revision !== task.revision)) {
        pending.value = null; attempt.value = null; input.value = ''; expected.value = ''; explanation.value = ''
        remember(null)
      }
      try {
        const rows = await fetchCounterexampleAttempts(challengeId.value, controller.signal)
        if (isCurrent(mark)) history.value = rows
      } catch { if (isCurrent(mark)) historyError.value = '本题历史暂无法读取，可稍后刷新。' }
    } catch (cause) {
      if (isCurrent(mark)) error.value = message(cause, '题目暂不可用，请刷新重试。')
    } finally { if (isCurrent(mark)) loading.value = false }
  }
  async function readResult(id = pending.value?.request_id || unresolvedId.value || readCache()) {
    if (!id || busy.value) return
    const mark = generation
    busy.value = true; error.value = ''; historyError.value = ''
    try { await restore(id, mark) }
    catch (cause) { if (isCurrent(mark)) error.value = message(cause, '暂无法恢复结果，请重试。') }
    finally { if (isCurrent(mark)) busy.value = false }
  }
  async function submit() {
    if (busy.value || loading.value || unresolvedId.value || !challenge.value || !userId.value) return
    if (pending.value && !canRetry.value) { await readResult(); return }
    const mark = generation
    error.value = ''
    try {
      if (!pending.value) {
        if (!explanation.value.trim() || explanation.value.length > 2000) throw new Error('请用 1–2000 字说明输入为何能触发错误。')
        const value = parseCounterexampleValue(input.value, challenge.value.input_contract)
        const output = parseCounterexampleValue(expected.value, challenge.value.output_contract)
        pending.value = { request_id: createRequestId(), revision: challenge.value.revision, version: challenge.value.version,
          input: value, expected_output: output, explanation: explanation.value.trim() }
        remember(pending.value.request_id)
      }
      busy.value = true
      const row = await submitCounterexample(challenge.value.id, pending.value, controller.signal)
      if (isCurrent(mark)) {
        show(row)
        history.value = [{ request_id: row.request_id, status: row.status, created_at: row.created_at },
          ...history.value.filter(item => item.request_id !== row.request_id)].slice(0, 20)
      }
    } catch (cause) {
      if (!isCurrent(mark)) return
      error.value = message(cause, '暂未收到结果，请读取结果或重试原提交。')
      // A lost response or in-flight conflict must not allocate another request.
      if (pending.value) {
        try { await restore(pending.value.request_id, mark) } catch {
          if (isCurrent(mark) && isAxiosError(cause) && cause.response?.status === 400) {
            pending.value = null; remember(null) // A rejected request was never accepted for execution.
          }
        }
      }
    } finally { if (isCurrent(mark)) busy.value = false }
  }
  function startNew() {
    if (!canStart.value) return
    pending.value = null; attempt.value = null; error.value = ''; remember(null)
    // Keep the previous text available for revision, but use a fresh request only on submit.
  }
  watch([userId, challengeId], () => { void load() }, { immediate: true, flush: 'sync' })
  onBeforeUnmount(() => { generation++; controller.abort() })
  return { items, challenge, attempt, history, input, expected, explanation, loading, busy, error, historyError,
    locked, canRetry, canStart, pending, unresolvedId, load, readResult, submit, startNew }
}
