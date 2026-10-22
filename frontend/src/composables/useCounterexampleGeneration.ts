import { createRequestId } from '../utils/browserCrypto'
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { isAxiosError } from 'axios'
import * as api from '../api/teacherCounterexamples'

/** A separate queue view: closing a page does not cancel server work. */
export function useCounterexampleGeneration(userId: Ref<number | undefined>, classId: Ref<number | null>) {
  const tasks = ref<api.Page<api.CounterexampleGenerationTask>>({ items: [], total: 0, page: 1, page_size: 20 })
  const selected = ref<api.CounterexampleGenerationTask | null>(null)
  const busy = ref(false), error = ref('')
  type Pointer = { taskId: string; specId: string; bugKind: api.CounterexampleCandidate['bug_kind'] }
  const pending = ref<Pointer | null>(null)
  let snapshot: api.CounterexampleSpecification | null = null
  let epoch = 0, controller = new AbortController(), timer: ReturnType<typeof setTimeout> | undefined
  const key = () => `plex:counterexample-generation:${userId.value}:${classId.value}`
  function cache(value: Pointer | null) {
    pending.value = value
    try { if (value) localStorage.setItem(key(), JSON.stringify(value)); else localStorage.removeItem(key()) } catch { /* cache optional */ }
  }
  function valid(mark: number) { return mark === epoch && !!userId.value && !!classId.value && !controller.signal.aborted }
  function schedule() {
    clearTimeout(timer)
    if (tasks.value.items.some(task => ['queued','running'].includes(task.status)) || selected.value && ['queued','running'].includes(selected.value.status))
      timer = setTimeout(() => { void refresh() }, 5000)
  }
  async function run(work: (mark: number, signal: AbortSignal) => Promise<void>) {
    if (busy.value || !userId.value || !classId.value) return false
    const mark = epoch; busy.value = true; error.value = ''; clearTimeout(timer)
    try { await work(mark, controller.signal); return valid(mark) }
    catch (cause) {
      if (valid(mark)) error.value = isAxiosError(cause) ? cause.response?.data?.message || '读取或提交暂未完成，请重试原任务。'
        : cause instanceof Error ? cause.message : '任务暂不可用，请重试。'
      return false
    } finally { if (valid(mark)) { busy.value = false; schedule() } }
  }
  function accept(task: api.CounterexampleGenerationTask) {
    if (task.class_id !== classId.value) throw new Error('任务不属于当前班级。')
    selected.value = task
    const index = tasks.value.items.findIndex(item => item.id === task.id)
    if (index >= 0) tasks.value.items[index] = task
  }
  async function load(mark: number, signal: AbortSignal, page = tasks.value.page) {
    const rows = await api.listCounterexampleGenerationTasks(classId.value!, page, signal)
    if (valid(mark)) tasks.value = rows
  }
  async function refresh(page = tasks.value.page) {
    return run(async (mark, signal) => {
      await load(mark, signal, page)
      if (!valid(mark)) return
      const id = pending.value?.taskId || selected.value?.id
      if (!id) return
      try {
        const task = await api.getCounterexampleGenerationTask(id, signal)
        if (valid(mark)) { accept(task); if (pending.value?.taskId === task.id) { cache(null); snapshot = null } }
      } catch (cause) {
        if (valid(mark) && isAxiosError(cause) && cause.response?.status === 404 && pending.value?.taskId === id)
          error.value = '任务尚未找到。可恢复原请求；已保存的独立基准不会重新生成。'
        else throw cause
      }
    })
  }
  async function select(id: string) {
    return run(async (mark, signal) => { const task = await api.getCounterexampleGenerationTask(id, signal); if (valid(mark)) accept(task) })
  }
  async function queue(specification?: api.CounterexampleSpecification, bugKind?: api.CounterexampleCandidate['bug_kind']) {
    return run(async (mark, signal) => {
      try {
        if (!pending.value) {
          if (!specification || !bugKind) throw new Error('请先确认独立基准和错误类型。')
          snapshot = JSON.parse(JSON.stringify(specification))
          cache({ taskId: createRequestId(), specId: createRequestId(), bugKind })
        }
        const request = { ...pending.value! }
        if (snapshot) await api.saveCounterexampleSpecification({ request_id: request.specId, class_id: classId.value!, specification: snapshot }, signal)
        else {
          const basis = await api.getCounterexampleSpecification(request.specId, signal)
          if (basis.class_id !== classId.value) throw new Error('基准不属于当前班级。')
        }
        if (!valid(mark)) return
        const task = await api.createCounterexampleGenerationTask({ request_id: request.taskId, spec_id: request.specId, bug_kind: request.bugKind }, signal)
        if (!valid(mark)) return
        accept(task); cache(null); snapshot = null
        try { await load(mark, signal, 1) }
        catch { if (valid(mark)) error.value = '任务已保存，列表刷新失败，可稍后刷新。' }
      } catch (cause) {
        // A definite contract rejection did not enqueue work. Let the teacher fix it.
        if (valid(mark) && isAxiosError(cause) && cause.response?.status === 400) { cache(null); snapshot = null }
        throw cause
      }
    })
  }
  async function action(kind: 'cancel' | 'retry') {
    if (!selected.value) return false
    return run(async (mark, signal) => {
      const task = selected.value!
      const result = kind === 'cancel' ? await api.cancelCounterexampleGenerationTask(task.id, signal)
        : await api.retryCounterexampleGenerationTask(task.id, task.attempts, signal)
      if (!valid(mark)) return
      accept(result); await load(mark, signal)
    })
  }
  function abandonPending() {
    // Only forgets an unsent/uncertain pointer. Server tasks are cancelled explicitly.
    if (!busy.value) { cache(null); snapshot = null; error.value = '' }
  }
  watch([userId, classId], () => {
    epoch++; controller.abort(); controller = new AbortController(); clearTimeout(timer)
    selected.value = null; busy.value = false; error.value = ''; snapshot = null; pending.value = null
    tasks.value = { items: [], total: 0, page: 1, page_size: 20 }
    if (!userId.value || !classId.value) return
    try {
      const value = JSON.parse(localStorage.getItem(key()) || 'null')
      if (value && typeof value.taskId === 'string' && typeof value.specId === 'string' && ['loop_boundary','empty_input','duplicate_elements'].includes(value.bugKind)) pending.value = value
    } catch { /* optional pointer */ }
    void refresh(1)
  }, { immediate: true })
  onBeforeUnmount(() => { epoch++; controller.abort(); clearTimeout(timer) })
  return { tasks, selected, busy, error, pending, queue, refresh, select, action, abandonPending }
}
