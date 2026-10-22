import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { fetchRagSource, type RagSourceDetail } from '../api/rag'

/** A citation is re-read with current permissions; closed or superseded reads cannot repopulate it. */
export function useRagSourceDialog(scope: () => unknown) {
  const auth = useAuthStore()
  const open = ref(false), loading = ref(false), error = ref('')
  const detail = ref<RagSourceDetail | null>(null)
  let active = true, alive = true, version = 0
  let selected: { chunk_id: string; version?: number } | null = null

  function reset() {
    version++; selected = null
    open.value = false; loading.value = false; detail.value = null; error.value = ''
  }
  async function show(citation: { chunk_id: string; version?: number }) {
    if (!active || !alive || !auth.profile?.id) return
    selected = { chunk_id: citation.chunk_id, version: citation.version }
    open.value = true; loading.value = true; detail.value = null; error.value = ''
    const request = ++version
    try {
      const result = await fetchRagSource(selected.chunk_id, selected.version)
      if (request === version && active && alive && open.value) detail.value = result
    } catch (failure) {
      if (request === version && active && alive && open.value) {
        error.value = failure instanceof Error ? failure.message : '来源暂不可用，请重试'
      }
    } finally {
      if (request === version) loading.value = false
    }
  }
  function retry() { if (selected && !loading.value) void show(selected) }
  watch(open, visible => { if (!visible) reset() }, { flush: 'sync' })
  watch(scope, reset, { flush: 'sync' })
  watch(() => [auth.profile?.id, auth.profile?.role], reset, { flush: 'sync' })
  onDeactivated(() => { active = false; reset() })
  onActivated(() => { active = true })
  onBeforeUnmount(() => { alive = false; active = false; reset() })
  return { open, loading, error, detail, show, retry }
}
