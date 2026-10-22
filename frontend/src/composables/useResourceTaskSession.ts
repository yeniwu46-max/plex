import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { formatHttpError } from '../api/http'
import {
  createResourceTask, fetchPersonalizedResources, fetchResourceTask, fetchResourceTasks,
  retryResourceTask, type PersonalizedResource, type ResourceTask,
} from '../api/personalizedResources'

/** Page lifetime controls observation only; leaving never cancels a durable server task. */
export function useResourceTaskSession() {
  const auth = useAuthStore()
  const resources = ref<PersonalizedResource[]>([])
  const taskHistory = ref<ResourceTask[]>([])
  const task = ref<ResourceTask | null>(null)
  const generating = ref(false)
  const loading = ref(true)
  const loadError = ref('')
  const taskError = ref('')
  const pollingTimedOut = ref(false)
  let active = false, alive = true, epoch = 0, readVersion = 0, operation = 0
  let releaseDelay: (() => void) | null = null

  const identity = () => ({ epoch, owner: auth.profile?.id })
  const current = (key: ReturnType<typeof identity>) => alive && active && key.epoch === epoch
    && !!key.owner && key.owner === auth.profile?.id && auth.profile?.role === 'student'

  function clear() {
    epoch++; readVersion++; operation++; releaseDelay?.()
    resources.value = []; taskHistory.value = []; task.value = null
    generating.value = false; loading.value = false
    loadError.value = ''; taskError.value = ''; pollingTimedOut.value = false
  }

  async function load(preferredTaskId?: string) {
    const key = identity(), request = ++readVersion
    if (!current(key)) return false
    const selectedId = preferredTaskId ?? task.value?.task_id
    // Until permissions are rechecked, do not leave cached source material or a modal readable.
    resources.value = []; taskHistory.value = []; task.value = null
    loading.value = true; loadError.value = ''
    try {
      const [resourceResult, history] = await Promise.all([fetchPersonalizedResources(), fetchResourceTasks()])
      if (!current(key) || request !== readVersion) return false
      resources.value = resourceResult.items
      taskHistory.value = history.items
      task.value = history.items.find(item => item.task_id === selectedId) ?? history.items[0] ?? null
      return true
    } catch (failure) {
      if (current(key) && request === readVersion) loadError.value = formatHttpError(failure, '资源加载失败')
      return false
    } finally {
      if (current(key) && request === readVersion) loading.value = false
    }
  }

  function delay() {
    return new Promise<void>(resolve => {
      const timer = window.setTimeout(finish, 1000)
      function finish() {
        window.clearTimeout(timer)
        if (releaseDelay === finish) releaseDelay = null
        resolve()
      }
      releaseDelay = finish
    })
  }

  async function follow(start: () => Promise<ResourceTask>) {
    const key = identity()
    if (!current(key) || generating.value) return null
    const request = ++operation
    readVersion++; loading.value = false
    generating.value = true; taskError.value = ''; pollingTimedOut.value = false
    const valid = () => current(key) && request === operation
    try {
      let result = await start()
      if (!valid()) return null
      const show = () => {
        task.value = result
        taskHistory.value = [result, ...taskHistory.value.filter(item => item.task_id !== result.task_id)]
      }
      show()
      for (let index = 0; index < 120 && !['completed', 'failed'].includes(result.status); index++) {
        await delay()
        if (!valid()) return null
        result = await fetchResourceTask(result.task_id)
        if (!valid()) return null
        show()
      }
      if (!['completed', 'failed'].includes(result.status)) pollingTimedOut.value = true
      else if (result.status === 'failed') taskError.value = result.error || '生成任务失败'
      else {
        // Use a fresh authorized list, not resource bodies cached in an earlier task response.
        await load(result.task_id)
        if (!valid()) return null
      }
      return result
    } catch (failure) {
      if (!valid()) return null
      taskError.value = formatHttpError(failure, '暂时无法确认任务状态，请查看最近生成记录后重试')
      // A lost creation response may still have created a task; refresh history without resubmitting.
      await load(task.value?.task_id)
      return null
    } finally {
      if (valid()) generating.value = false
    }
  }

  function generate(...args: Parameters<typeof createResourceTask>) { return follow(() => createResourceTask(...args)) }
  function retry(id: string) { return follow(() => retryResourceTask(id)) }
  function inspect(id: string) { return follow(() => fetchResourceTask(id)) }

  function restore() {
    void load().then(loaded => {
      const restored = task.value
      if (loaded && restored && ['pending', 'running'].includes(restored.status)) void inspect(restored.task_id)
    })
  }

  function activate() {
    if (!alive || active) return
    active = true
    restore()
  }
  function deactivate() { active = false; clear() }
  watch(() => [auth.profile?.id, auth.profile?.role], () => {
    clear()
    if (active) restore()
  }, { flush: 'sync' })
  onMounted(activate)
  onActivated(activate)
  onDeactivated(deactivate)
  onBeforeUnmount(() => { alive = false; deactivate() })

  return { resources, taskHistory, task, generating, loading, loadError, taskError, pollingTimedOut,
    load, generate, retry, inspect }
}
