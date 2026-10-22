import { createRequestId } from '../utils/browserCrypto'
import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { isAxiosError } from 'axios'
import * as api from '../api/teacherCounterexamples'
import { blankCounterexampleForm, buildCounterexampleDraft, formFromCounterexample } from '../utils/counterexampleAuthoring'

export function useCounterexampleWorkbench(userId: Ref<number | undefined>, classId: Ref<number | null>) {
  const list = ref<api.Page<api.CounterexampleSummary>>({ items: [], total: 0, page: 1, page_size: 20 })
  const detail = ref<api.TeacherCounterexample | null>(null)
  const versions = ref<api.Page<api.VersionSummary>>({ items: [], total: 0, page: 1, page_size: 20 })
  const attempts = ref<api.Page<api.TeacherAttemptSummary>>({ items: [], total: 0, page: 1, page_size: 20 })
  const selectedAttempt = ref<api.TeacherCounterexampleAttempt | null>(null)
  const templates = ref<api.CounterexampleCatalog | null>(null)
  const sourceTemplate = ref<api.TemplateReference | null>(null)
  const form = ref(blankCounterexampleForm())
  const editing = ref(false), busy = ref(false), error = ref(''), notice = ref('')
  const approvedBasis = ref(false), reviewNote = ref(''), explanationNote = ref('')
  const freshChecks = (): api.PublicationChecks => ({ single_clear_bug: false, statement_consistent: false, explanation_correct: false, difficulty_appropriate: false })
  const checks = ref(freshChecks())
  let generation = 0, controller = new AbortController()
  type Pointer = { challengeId: string; specId?: string; validationId?: string; validationHash?: string; sourceTemplate?: api.TemplateReference }
  let pointer: Pointer | null = null
  type PendingSave = { id: string; class_id: number; specification: api.CounterexampleSpecification; candidate: api.CounterexampleCandidate;
    spec_id: string; version_id: string; existing: boolean; expected_revision: number; source_template?: api.TemplateReference }
  const pendingSave = ref<PendingSave | null>(null)
  let pendingReview: { attemptId: string; body: Parameters<typeof api.reviewCounterexampleExplanation>[1] } | null = null
  const currentVersion = computed(() => !!detail.value && detail.value.revision === detail.value.current_revision)
  const canPublish = computed(() => currentVersion.value && !editing.value && !detail.value?.blocked_reason &&
    (detail.value?.origin !== 'model_generated' || (detail.value.generation?.status === 'ready' &&
      detail.value.generation.pedagogy_review?.verdict === 'pass' &&
      detail.value.generation.pedagogy_review?.manifest_hash === detail.value.manifest_hash &&
      detail.value.generation.pedagogy_review?.validation_id === detail.value.validation?.id)) &&
    detail.value?.validation?.status === 'passed' && detail.value.validation.report?.passed === true &&
    detail.value.validation.manifest_hash === detail.value.manifest_hash &&
    Object.values(checks.value).every(Boolean) && !!reviewNote.value.trim())
  const savedKey = () => `plex:counterexample-author:${userId.value}:${classId.value}`
  function remember(next: Pointer | null) {
    pointer = next
    try { if (next) localStorage.setItem(savedKey(), JSON.stringify(next)); else localStorage.removeItem(savedKey()) } catch { /* optional cache */ }
  }
  function readPointer(): Pointer | null {
    try {
      const value = JSON.parse(localStorage.getItem(savedKey()) || 'null')
      return value && typeof value.challengeId === 'string' ? value : null
    } catch { return null }
  }
  function valid(mark: number) { return generation === mark && !!userId.value && !!classId.value && !controller.signal.aborted }
  function message(cause: unknown) {
    return isAxiosError(cause) ? cause.response?.data?.message || '请求暂未完成，可读取最新状态或重试原操作。'
      : cause instanceof Error ? cause.message : '请求未完成，请重试。'
  }
  async function run(work: (mark: number, signal: AbortSignal) => Promise<void>) {
    if (busy.value || !userId.value || !classId.value) return
    const mark = generation
    busy.value = true; error.value = ''; notice.value = ''
    try { await work(mark, controller.signal) }
    catch (cause) { if (valid(mark)) error.value = message(cause) }
    finally { if (valid(mark)) busy.value = false }
  }
  function show(row: api.TeacherCounterexample) {
    if (row.class_id !== classId.value) throw new Error('题目不属于当前班级，请重新选择。')
    detail.value = row; form.value = formFromCounterexample(row.specification, row.candidate)
    sourceTemplate.value = row.source_template ? { id: row.source_template.id, content_hash: row.source_template.content_hash } : null
    editing.value = false; approvedBasis.value = false; pendingSave.value = null
    checks.value = freshChecks(); reviewNote.value = ''
    remember({ challengeId: row.id, specId: row.spec_id, ...(sourceTemplate.value ? { sourceTemplate: { ...sourceTemplate.value } } : {}),
      ...(pointer?.challengeId === row.id && pointer.validationHash === row.manifest_hash
        ? { validationId: pointer.validationId, validationHash: pointer.validationHash } : {}) })
  }
  async function related(id: string, mark: number, signal: AbortSignal) {
    // These rows belong to the detail being loaded, never the previous task.
    versions.value = { ...versions.value, items: [], total: 0, page: 1 }
    attempts.value = { ...attempts.value, items: [], total: 0, page: 1 }
    selectedAttempt.value = null; explanationNote.value = ''; pendingReview = null
    const [history, submissions] = await Promise.all([api.getCounterexampleVersions(id, 1, signal), api.listTeacherCounterexampleAttempts(id, 1, signal)])
    if (valid(mark)) { versions.value = history; attempts.value = submissions }
  }
  async function listPage(page = 1) {
    await run(async (mark, signal) => {
      const data = await api.listTeacherCounterexamples(classId.value!, page, signal)
      if (valid(mark)) list.value = data
    })
  }
  async function loadTemplates() {
    await run(async (mark, signal) => {
      const data = await api.listCounterexampleTemplates(classId.value!, signal)
      if (valid(mark)) templates.value = data
    })
  }
  async function loadTemplate(source: api.TemplateReference) {
    if (editing.value || pendingSave.value) return
    await run(async (mark, signal) => {
      const data = await api.getCounterexampleTemplate(classId.value!, source, signal)
      if (!valid(mark)) return
      detail.value = null; selectedAttempt.value = null; pendingReview = null
      form.value = formFromCounterexample(data.specification, data.candidate)
      sourceTemplate.value = { id: data.id, content_hash: data.content_hash }
      editing.value = true; approvedBasis.value = false; checks.value = freshChecks(); reviewNote.value = ''
      versions.value = { ...versions.value, items: [], total: 0 }; attempts.value = { ...attempts.value, items: [], total: 0 }
      remember(null)
      notice.value = `已载入待审草稿 ${data.id}。请先核对题意与独立预期，保存后在当前环境重新验证；开发报告不会自动发布题目。`
    })
  }
  async function select(id: string, revision?: number) {
    await run(async (mark, signal) => {
      const row = await api.getTeacherCounterexample(id, signal, revision)
      if (!valid(mark)) return
      show(row); selectedAttempt.value = null; pendingReview = null
      await related(id, mark, signal)
    })
  }
  async function reload() {
    // An explicit reload discards only the in-memory edit, never a saved version.
    await run(async (mark, signal) => {
      const data = await api.listTeacherCounterexamples(classId.value!, list.value.page, signal)
      if (!valid(mark)) return
      list.value = data
      const saved = pointer || readPointer()
      if (!saved) return
      try {
        const row = await api.getTeacherCounterexample(saved.challengeId, signal)
        if (!valid(mark)) return
        show(row); await related(row.id, mark, signal)
      } catch (cause) {
        if (!valid(mark)) return
        if (!(isAxiosError(cause) && cause.response?.status === 404 && saved.specId)) throw cause
        const spec = await api.getCounterexampleSpecification(saved.specId, signal)
        if (!valid(mark)) return
        if (spec.class_id !== classId.value) throw new Error('基准不属于当前班级。')
        detail.value = null; form.value = formFromCounterexample(spec.specification); editing.value = true
        sourceTemplate.value = saved.sourceTemplate ? { ...saved.sourceTemplate } : null
        pendingSave.value = null; approvedBasis.value = false; remember(saved)
        notice.value = '题意与独立测试已保存，候选尚未找到。请补齐程序并保存；不会自动发布。'
      }
    })
  }
  function newDraft() {
    if (busy.value || pendingSave.value || !classId.value) return
    detail.value = null; form.value = blankCounterexampleForm(); selectedAttempt.value = null
    sourceTemplate.value = null
    versions.value = { ...versions.value, items: [], total: 0 }; attempts.value = { ...attempts.value, items: [], total: 0 }
    editing.value = true; approvedBasis.value = false; checks.value = freshChecks(); error.value = ''; notice.value = ''; remember(null)
  }
  function edit() {
    if (busy.value || !currentVersion.value || !detail.value) return
    form.value = formFromCounterexample(detail.value.specification, detail.value.candidate)
    editing.value = true; approvedBasis.value = false; checks.value = freshChecks()
  }
  function discardEdit() {
    if (busy.value || pendingSave.value) return
    editing.value = false; approvedBasis.value = false; error.value = ''; notice.value = ''
    sourceTemplate.value = detail.value?.source_template ? { id: detail.value.source_template.id, content_hash: detail.value.source_template.content_hash } : null
    form.value = detail.value ? formFromCounterexample(detail.value.specification, detail.value.candidate) : blankCounterexampleForm()
  }
  async function save() {
    await run(async (mark, signal) => {
      try {
      if (!pendingSave.value) {
        if (!approvedBasis.value) throw new Error('请先核对题意、输入范围、参考实现与独立预期测试。')
        const draft = buildCounterexampleDraft(form.value)
        pendingSave.value = { ...draft, class_id: classId.value!, spec_id: createRequestId(), version_id: createRequestId(),
          id: detail.value?.id || pointer?.challengeId || createRequestId(), existing: !!detail.value,
          expected_revision: detail.value?.current_revision || 0,
          ...(sourceTemplate.value ? { source_template: { ...sourceTemplate.value } } : {}) }
      }
      const snapshot = JSON.parse(JSON.stringify(pendingSave.value)) as PendingSave
      remember({ challengeId: snapshot.id, specId: snapshot.spec_id, ...(snapshot.source_template ? { sourceTemplate: snapshot.source_template } : {}) })
      const spec = await api.saveCounterexampleSpecification({ request_id: snapshot.spec_id,
        class_id: snapshot.class_id, specification: snapshot.specification }, signal)
      if (!valid(mark)) return
      const row = snapshot.existing ? await api.reviseCounterexample(snapshot.id, { request_id: snapshot.version_id,
        expected_revision: snapshot.expected_revision, spec_id: spec.id, candidate: snapshot.candidate, source_template: snapshot.source_template }, signal)
        : await api.createCounterexample({ request_id: snapshot.id, spec_id: spec.id, candidate: snapshot.candidate, source_template: snapshot.source_template }, signal)
      if (!valid(mark)) return
      show(row); notice.value = '新版本已保存，尚未发布。请先执行验证，再完成教学审核。'
      await related(row.id, mark, signal)
      const data = await api.listTeacherCounterexamples(classId.value!, 1, signal)
      if (valid(mark)) list.value = data
      } catch (cause) {
        if (valid(mark) && isAxiosError(cause) && cause.response?.status === 400) {
          pendingSave.value = null
          remember(detail.value ? { challengeId: detail.value.id, specId: detail.value.spec_id } : null)
        }
        throw cause
      }
    })
  }
  async function validate() {
    if (!currentVersion.value || editing.value || detail.value?.blocked_reason) return
    await run(async (mark, signal) => {
      const row = detail.value!
      const reusable = row.validation && ['processing', 'unavailable'].includes(row.validation.status) ? row.validation.id
        : pointer?.validationHash === row.manifest_hash && pointer.validationId !== row.validation?.id ? pointer.validationId : undefined
      const id = reusable || createRequestId()
      remember({ challengeId: row.id, specId: row.spec_id, validationId: id, validationHash: row.manifest_hash })
      await api.validateCounterexample(row.id, { request_id: id, manifest_hash: row.manifest_hash }, signal)
      if (!valid(mark)) return
      const refreshed = await api.getTeacherCounterexample(row.id, signal)
      if (!valid(mark)) return
      show(refreshed)
      // A finished validation can be deliberately rerun; retries during uncertainty retain the ID.
      remember({ challengeId: row.id, specId: row.spec_id })
    })
  }
  async function publish(action: 'publish' | 'withdraw') {
    if (!detail.value || !currentVersion.value || editing.value || (action === 'publish' && !canPublish.value)) return
    await run(async (mark, signal) => {
      const row = detail.value!
      const updated = await api.publishCounterexample(row.id, { action, manifest_hash: row.manifest_hash,
        ...(action === 'publish' ? { validation_id: row.validation!.id, note: reviewNote.value, checks: { ...checks.value } } : {}) }, signal)
      if (!valid(mark)) return
      show(updated); notice.value = action === 'publish' ? '已向本班学生开放。' : '已撤回，学生不能再提交此题。'
      const data = await api.listTeacherCounterexamples(classId.value!, list.value.page, signal)
      if (valid(mark)) list.value = data
    })
  }
  async function historyPage(kind: 'versions' | 'attempts', page: number) {
    if (!detail.value) return
    await run(async (mark, signal) => {
      if (kind === 'versions') { const data = await api.getCounterexampleVersions(detail.value!.id, page, signal); if (valid(mark)) versions.value = data }
      else { const data = await api.listTeacherCounterexampleAttempts(detail.value!.id, page, signal); if (valid(mark)) attempts.value = data }
    })
  }
  async function readAttempt(id: string) {
    await run(async (mark, signal) => {
      selectedAttempt.value = null; explanationNote.value = ''; pendingReview = null
      const row = await api.getTeacherCounterexampleAttempt(id, signal)
      if (!valid(mark)) return
      if (row.challenge_id !== detail.value?.id) throw new Error('作答记录不属于当前题目。')
      selectedAttempt.value = row; explanationNote.value = ''; pendingReview = null
    })
  }
  async function reviewExplanation(verdict: 'supported' | 'needs_revision') {
    if (!selectedAttempt.value || selectedAttempt.value.status !== 'complete') return
    await run(async (mark, signal) => {
      const row = selectedAttempt.value!
      if (!explanationNote.value.trim() || explanationNote.value.length > 500) throw new Error('请填写 1–500 字核对说明。')
      const body = { expected_revision: row.explanation_review?.revision || 0, verdict, note: explanationNote.value.trim() }
      if (!pendingReview || pendingReview.attemptId !== row.request_id || Object.entries(body).some(([key, value]) => pendingReview!.body[key as keyof typeof body] !== value))
        pendingReview = { attemptId: row.request_id, body: { ...body, request_id: createRequestId() } }
      const updated = await api.reviewCounterexampleExplanation(row.request_id, pendingReview.body, signal)
      if (!valid(mark)) return
      selectedAttempt.value = updated; pendingReview = null; explanationNote.value = ''; notice.value = '解释意见已保存，执行结果保持原记录。'
      const data = await api.listTeacherCounterexampleAttempts(detail.value!.id, attempts.value.page, signal)
      if (valid(mark)) attempts.value = data
    })
  }
  watch([userId, classId], () => {
    generation++; controller.abort(); controller = new AbortController(); busy.value = false
    detail.value = null; selectedAttempt.value = null; pendingSave.value = null; pendingReview = null
    templates.value = null; sourceTemplate.value = null
    list.value = { items: [], total: 0, page: 1, page_size: 20 }; versions.value = { ...versions.value, items: [], total: 0 }; attempts.value = { ...attempts.value, items: [], total: 0 }
    form.value = blankCounterexampleForm(); editing.value = false; approvedBasis.value = false; checks.value = freshChecks()
    error.value = ''; notice.value = ''; reviewNote.value = ''; explanationNote.value = ''; pointer = readPointer()
    void reload()
  }, { immediate: true, flush: 'sync' })
  onBeforeUnmount(() => { generation++; controller.abort() })
  return { list, detail, versions, attempts, selectedAttempt, form, editing, busy, error, notice, approvedBasis, reviewNote,
    explanationNote, checks, pendingSave, currentVersion, canPublish, listPage, select, reload, newDraft, edit, discardEdit, save,
    validate, publish, historyPage, readAttempt, reviewExplanation, templates, sourceTemplate, loadTemplates, loadTemplate }
}
