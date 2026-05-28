import { ref } from 'vue'
import { fetchKnowledgeCatalog } from '../api/teacherTemplates'
import { TEACHER_KNOWLEDGE_UNIVERSE, type KnowledgeDomainDef } from '../data/teacherKnowledgeCatalog'

/** 加载知识宇宙目录：优先 API，失败时使用本地静态目录，避免教师端无法勾选知识点。 */
function normalizeDomains(raw: unknown): KnowledgeDomainDef[] {
  if (!Array.isArray(raw)) return []
  return raw.filter(
    (d): d is KnowledgeDomainDef =>
      Boolean(d && typeof d === 'object' && Array.isArray((d as KnowledgeDomainDef).points)),
  )
}

export function useKnowledgeCatalog() {
  /** 先展示本地目录，避免 API 慢/失败时教师端无法勾选知识点 */
  const domains = ref<KnowledgeDomainDef[]>([...TEACHER_KNOWLEDGE_UNIVERSE])
  const loading = ref(false)
  const fromRemote = ref(false)

  async function loadCatalog() {
    loading.value = true
    try {
      const remote = normalizeDomains(await fetchKnowledgeCatalog())
      if (remote.length) {
        domains.value = remote
        fromRemote.value = true
        return
      }
    } catch {
      /* 使用本地兜底 */
    } finally {
      loading.value = false
    }
    if (!domains.value.length) {
      domains.value = [...TEACHER_KNOWLEDGE_UNIVERSE]
    }
    fromRemote.value = false
  }

  return { domains, loading, fromRemote, loadCatalog }
}
