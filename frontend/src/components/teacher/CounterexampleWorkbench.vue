<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { NAlert, NButton, NCard, NCheckbox, NInput, NPagination, NPopconfirm, NSelect, NTag } from 'naive-ui'
import { useAuthStore } from '../../stores/auth'
import { useTeacherOverviewInjected } from '../../composables/useTeacherOverview'
import { useCounterexampleWorkbench } from '../../composables/useCounterexampleWorkbench'
import { useCounterexampleGeneration } from '../../composables/useCounterexampleGeneration'
import { buildCounterexampleSpecification } from '../../utils/counterexampleAuthoring'
import { TEACHER_KNOWLEDGE_UNIVERSE } from '../../data/teacherKnowledgeCatalog'
import { describeValueContract, type CounterexampleOutcome } from '../../api/counterexamples'
import type { PublicationChecks } from '../../api/teacherCounterexamples'
import CounterexampleContractFields from './CounterexampleContractFields.vue'

const auth = useAuthStore()
const { selectedClassId } = useTeacherOverviewInjected()
const userId = computed(() => ['teacher', 'admin'].includes(auth.profile?.role || '') ? auth.profile?.id : undefined)
const { list, detail, versions, attempts, selectedAttempt, form, editing, busy, error, notice, approvedBasis, reviewNote,
  explanationNote, checks, pendingSave, currentVersion, canPublish, listPage, select, reload, newDraft, edit, discardEdit, save,
  validate, publish, historyPage, readAttempt, reviewExplanation, templates, sourceTemplate, loadTemplates, loadTemplate } = useCounterexampleWorkbench(userId, selectedClassId)
const { tasks: generationTasks, selected: generationTask, busy: generationBusy, error: generationError,
  pending: generationPending, queue: queueGeneration, refresh: refreshGeneration, select: selectGeneration,
  action: generationAction, abandonPending } = useCounterexampleGeneration(userId, selectedClassId)
const formLocked = computed(() => busy.value || generationBusy.value || !!pendingSave.value || !!generationPending.value)
const generationStatuses: Record<string, string> = { queued: '等待处理', running: '后台处理中', ready: '待教师最终审核',
  rejected: '候选未通过，需修订', failed: '处理未完成', cancelled: '已取消' }
const generationStages: Record<string, string> = { generation: '程序生成', validation: '隔离执行验证', pedagogy: '教学审核' }
const generationErrors: Record<string, string> = { model_unavailable: '模型暂不可用，可重试原任务', candidate_contract_rejected: '候选不符合程序与字段约定',
  execution_rejected: '候选未通过执行验证', execution_unavailable: '隔离执行环境暂不可用', pedagogy_rejected: '教学审核要求进一步修订',
  review_contract_rejected: '审核回复不符合约定，未采纳为通过意见', context_changed: '任务依据或题目版本已变化',
  permission_changed: '任务所属账号或班级权限已变化', retry_limit: '已达恢复次数上限', worker_error: '后台处理异常', model_output_too_large: '模型回复超出长度限制' }
async function generateCandidate() {
  if (busy.value || generationBusy.value || pendingSave.value) return
  if (!generationPending.value && !approvedBasis.value) { generationError.value = '请先核对独立基准。'; return }
  try {
    const spec = generationPending.value ? undefined : buildCounterexampleSpecification(form.value)
    if (await queueGeneration(spec, form.value.candidate.bug_kind)) discardEdit()
  } catch (cause) { generationError.value = cause instanceof Error ? cause.message : '请检查基准内容。' }
}
function saveManual() { if (!generationBusy.value && !generationPending.value) void save() }
const newDraftButton = ref<InstanceType<typeof NButton> | null>(null)
const editDraftButton = ref<InstanceType<typeof NButton> | null>(null)
async function discardDraft() {
  discardEdit()
  if (editing.value) return
  await nextTick()
  const button = detail.value ? editDraftButton.value : newDraftButton.value
  ;(button?.$el as HTMLButtonElement | undefined)?.focus()
}
const concepts = TEACHER_KNOWLEDGE_UNIVERSE.flatMap(domain => domain.points.map(point => ({ label: `${domain.label} · ${point.label}`, value: point.key })))
const bugKinds = [{ label: '循环边界', value: 'loop_boundary' }, { label: '空输入', value: 'empty_input' }, { label: '重复元素', value: 'duplicate_elements' }]
const templateKind = ref('loop_boundary')
const visibleTemplates = computed(() => templates.value?.items.filter(item => item.bug_kind === templateKind.value) || [])
const exceptionOptions = ['IndexError', 'ValueError', 'ZeroDivisionError'].map(value => ({ label: value, value }))
const propertyOptions = [
  { value: 'permutation_invariant', label: '重排不变 · 反转或循环移位后，结果相同' },
  { value: 'duplicate_invariant', label: '重复不变 · 加入已有元素后，结果相同' },
  { value: 'append_zero_invariant', label: '追加零不变 · 末尾加 0 后，结果相同' },
  { value: 'concatenation_additive', label: '重复拼接可加 · 数组重复一遍，结果为原来的两倍' },
  { value: 'result_is_member', label: '结果来自输入 · 非空输入时，整数结果是其中一个元素' },
]
function propertyLabel(key: string) { return propertyOptions.find(item => item.value === key)?.label || key }
const programLabels: Record<string, string> = { reference: '参考程序', fixed: '修正程序', buggy: '错误程序' }
const inputOrigins: Record<string, string> = { teacher_test: '独立测试', boundary: '补充边界', metamorphic: '性质变形' }
const checkLabels: { key: keyof PublicationChecks; label: string }[] = [
  { key: 'single_clear_bug', label: '错误单一且清楚，能对应学习目标' }, { key: 'statement_consistent', label: '题意、输入范围与正确行为一致' },
  { key: 'explanation_correct', label: '错误原因说明准确，见证输入有说服力' }, { key: 'difficulty_appropriate', label: '难度适合本班学生，题面不直接泄露答案' },
]
const statuses: Record<string, string> = { processing: '核对中', passed: '执行通过', failed: '执行未通过', unavailable: '环境暂不可用',
  superseded: '版本已失效', complete: '已核对', material_issue: '材料待修正', stale: '版本已变化',
  needs_teacher: '待教师核对', needs_revision: '需要修改解释', supported: '解释获支持', not_evaluated: '先核对输入' }
const reasons: Record<string, string> = { reference_test_mismatch: '参考实现与独立测试预期不一致', fixed_test_mismatch: '修正程序与独立测试预期不一致',
  no_counterexample: '当前测试没有暴露错误版差异', execution_timeout: '程序超时', memory_limit: '超出内存限制', output_limit: '输出超过限制',
  non_deterministic: '重复执行结果不一致', reference_fixed_disagreement: '参考实现与修正程序不一致', runtime_changed: '运行环境已变化',
  fixed_reference_mismatch: '补充输入上，参考程序与修正程序不一致', reference_property_mismatch: '参考程序不满足所声明的性质',
  fixed_property_mismatch: '修正程序不满足所声明的性质', invalid_program_or_contract: '程序、契约或补充验证设置无效',
  reference_output_contract: '参考程序输出超出约定范围', fixed_output_contract: '修正程序输出超出约定范围', buggy_output_contract: '错误程序输出超出约定范围' }
function outcome(value: CounterexampleOutcome) { return value.kind === 'value' ? JSON.stringify(value.value) : `发生 ${value.exception}` }
function date(value: string) { return new Date(value).toLocaleString('zh-CN', { hour12: false }) }
</script>

<template>
  <section class="counterexample-workbench" aria-label="教师反例工作台" :aria-busy="busy">
    <header class="workbench-head"><div><h1>反例挑战工作台</h1><p>先确定正确行为，再验证错误程序，最后向本班开放。</p></div>
      <div class="workbench-actions"><n-button :disabled="busy || generationBusy || !!generationPending" @click="reload">读取最新状态</n-button>
        <n-button ref="newDraftButton" type="primary" :disabled="busy || generationBusy || editing || !!generationPending || !!pendingSave || !selectedClassId" @click="newDraft">新建反例题</n-button></div></header>
    <n-alert v-if="!selectedClassId" type="info" :show-icon="false">请先在顶部选择班级。</n-alert>
    <n-alert v-if="error" type="error" :show-icon="false" role="alert">{{ error }}</n-alert>
    <n-alert v-if="notice" type="info" :show-icon="false" role="status">{{ notice }}</n-alert>
    <n-card v-if="selectedClassId" title="待审草稿库 · 30 道" class="workbench-panel">
      <p class="workbench-note">循环边界、空输入、重复元素各 10 道 AI 辅助草稿。开发执行记录仅供核对，尚未经过真实教师审核；载入不会创建或发布题目。</p>
      <div class="workbench-actions"><n-button :disabled="formLocked" @click="loadTemplates">{{ templates ? '刷新草稿库' : '浏览待审草稿' }}</n-button></div>
      <template v-if="templates">
        <label for="ce-template-kind">查看错误类型</label><n-select :input-props="{ id: 'ce-template-kind' }" v-model:value="templateKind" :options="bugKinds" />
        <ul class="workbench-list"><li v-for="item in visibleTemplates" :key="item.id">
          <div><strong>{{ item.id }} · {{ item.title }}</strong><p>{{ item.difficulty }} · 待教师审核 · {{ item.development_validation?.passed ? '开发执行已通过' : '开发验证记录不可用或未通过' }}</p>
            <p v-if="item.development_validation">记录时间：{{ date(item.development_validation.verified_at) }}</p></div>
          <n-button :disabled="formLocked || editing" @click="loadTemplate(item)">载入待审草稿</n-button>
        </li></ul>
      </template>
    </n-card>
    <n-card v-if="selectedClassId" title="本班题目" class="workbench-panel">
      <p v-if="!list.items.length">{{ busy ? '正在读取题目…' : '还没有反例题，先建立题意和独立测试基准。' }}</p>
      <ul class="workbench-list"><li v-for="item in list.items" :key="item.id">
        <div><strong>{{ item.title }}</strong><p>版本 {{ item.revision }} · {{ item.blocked_reason ? '已暂停，材料待修正' : item.published_revision ? '已向学生开放' : '未发布' }} · {{ statuses[item.validation_status || ''] || '尚未验证' }}</p></div>
        <n-button :disabled="busy || editing || !!pendingSave" @click="select(item.id)">查看与审核</n-button>
      </li></ul>
      <n-pagination v-if="list.total > 20" :page="list.page" :item-count="list.total" :page-size="20" :disabled="busy" simple @update:page="listPage" />
    </n-card>

    <n-card v-if="selectedClassId" title="后台候选生成" class="workbench-panel">
      <p class="workbench-note">先在新建题目中确认独立基准，再让小 E 生成候选。后台会依次检查程序、执行结果和教学说明；通过后仍需你最终审核。关闭页面不影响处理。</p>
      <n-alert v-if="generationError" type="warning" :show-icon="false" role="alert">{{ generationError }}</n-alert>
      <div class="workbench-actions"><n-button :loading="generationBusy" @click="refreshGeneration()">刷新生成任务</n-button>
        <template v-if="generationPending"><n-button :disabled="busy || generationBusy" @click="generateCandidate">恢复原生成请求</n-button>
          <n-popconfirm @positive-click="abandonPending"><template #trigger><n-button :disabled="generationBusy">重新编辑基准</n-button></template>请先刷新任务列表确认提交结果。这里只解除本地恢复锁定，已经创建的后台任务仍会保留。</n-popconfirm></template></div>
      <p v-if="!generationTasks.items.length && !generationBusy">当前没有候选生成任务。</p>
      <ul class="workbench-list"><li v-for="task in generationTasks.items" :key="task.id"><div><strong>{{ bugKinds.find(kind => kind.value === task.bug_kind)?.label }}候选</strong>
        <p>{{ date(task.created_at) }} · {{ generationStatuses[task.status] }} · {{ generationStages[task.stage] }}</p></div>
        <n-button :disabled="generationBusy" @click="selectGeneration(task.id)">查看任务</n-button></li></ul>
      <n-pagination v-if="generationTasks.total > 20" :page="generationTasks.page" :item-count="generationTasks.total" :page-size="20" :disabled="generationBusy" simple @update:page="refreshGeneration" />
      <article v-if="generationTask" aria-live="polite">
        <h3>{{ generationStatuses[generationTask.status] }} · {{ generationStages[generationTask.stage] }}</h3>
        <p v-if="generationTask.error_code">{{ generationErrors[generationTask.error_code] || '请检查任务记录。' }}</p>
        <p v-if="generationTask.pedagogy_review?.note" class="preserve-text">小 E 审核意见：{{ generationTask.pedagogy_review.note }}</p>
        <div class="workbench-actions">
          <n-button v-if="['queued','running'].includes(generationTask.status)" :disabled="generationBusy" @click="generationAction('cancel')">取消后续处理</n-button>
          <n-button v-if="generationTask.retryable" :disabled="generationBusy" @click="generationAction('retry')">恢复原任务</n-button>
          <n-button v-if="generationTask.version_id" type="primary" :disabled="busy || editing || !!pendingSave" @click="select(generationTask.challenge_id)">打开候选与审核</n-button>
        </div>
        <p v-if="generationTask.status === 'cancelled'" class="workbench-note">后续阶段已停止。取消前已发出的请求可能仍产生用量，返回后会保留记录。</p>
        <details v-if="generationTask.calls?.length"><summary>调用与耗时记录</summary>
          <ul><li v-for="record in generationTask.calls" :key="record.id">第 {{ record.attempt }} 次处理 · {{ generationStages[record.stage] }} ·
            {{ record.audit?.provider || '供应商未返回' }} / {{ record.audit?.model || '型号未返回' }} ·
            {{ record.completed_at ? `${record.audit?.elapsed_ms ?? 0} ms` : '未取得完成记录，用量未知' }} ·
            Token {{ record.audit?.token_usage.total_tokens ?? '未知' }}</li></ul></details>
      </article>
    </n-card>

    <form v-if="editing" class="authoring-form" @submit.prevent="saveManual">
      <n-alert v-if="sourceTemplate" type="info" :show-icon="false">来源：待审草稿 {{ sourceTemplate.id }}。可按本班情况修改；请逐项核对题意、参考程序和预期结果，再保存并执行验证。</n-alert>
      <n-card class="workbench-panel" title="01 · 题意与独立基准">
        <p class="workbench-note">参考程序和预期结果需要独立核对。请保存后再离开页面或切换班级。保存修订版会撤下旧版；学生暂时不能作答，直到新版本重新审核发布。</p>
        <div class="field-grid">
          <div><label for="ce-title">题目名称</label><n-input :input-props="{ id: 'ce-title' }" v-model:value="form.title" :maxlength="120" :disabled="formLocked" placeholder="用一句话描述任务" /></div>
          <div><label for="ce-concept">知识点</label><n-select :input-props="{ id: 'ce-concept' }" v-model:value="form.concept_id" :options="concepts" filterable :disabled="formLocked" placeholder="选择课程知识点" /></div>
        </div>
        <label for="ce-statement">正确程序应完成什么？</label><n-input :input-props="{ id: 'ce-statement' }" v-model:value="form.statement" type="textarea" :maxlength="4000" :autosize="{ minRows: 3, maxRows: 10 }" :disabled="formLocked" placeholder="写清输入含义、输出定义，以及空输入和重复元素的约定。" />
        <fieldset :disabled="formLocked"><legend>合法输入与输出</legend>
          <CounterexampleContractFields :model="form.input" prefix="ce-input" :disabled="formLocked" />
          <CounterexampleContractFields :model="form.output" prefix="ce-output" output :disabled="formLocked" />
        </fieldset>
        <label for="ce-exceptions">错误版允许用作反例的异常 · 选填</label><n-select filterable :input-props="{ id: 'ce-exceptions' }" v-model:value="form.allowed_bug_exceptions" :options="exceptionOptions" multiple :disabled="formLocked" placeholder="不选择时，异常会阻止发布" />
        <label for="ce-reference">独立参考实现 · def solve(data)</label><n-input v-model:value="form.reference_code" type="textarea" :maxlength="16000" :autosize="{ minRows: 5, maxRows: 16 }" :disabled="formLocked" :input-props="{ id: 'ce-reference', spellcheck: false }" placeholder="填写已核对的 Python 函数；不要读取终端输入或访问网络。" />
        <fieldset :disabled="formLocked"><legend>独立预期测试 · 3–24 组</legend><p class="workbench-note">预期结果应按题意独立推算，不直接采信候选程序输出。每个输入使用 JSON 格式。</p>
          <div v-for="(test, index) in form.tests" :key="index" class="test-row">
            <div><label :for="`ce-test-input-${index}`">测试 {{ index + 1 }} · 输入</label><n-input :input-props="{ id: `ce-test-input-${index}` }" v-model:value="test.input" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" :disabled="formLocked" :maxlength="10000" /></div>
            <div><label :for="`ce-test-expected-${index}`">预期输出</label><n-input :input-props="{ id: `ce-test-expected-${index}` }" v-model:value="test.expected" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" :disabled="formLocked" :maxlength="10000" /></div>
            <n-button :disabled="formLocked || form.tests.length <= 3" :aria-label="`删除测试 ${index + 1}`" @click="form.tests.splice(index, 1)">删除</n-button>
          </div><n-button :disabled="formLocked || form.tests.length >= 24" @click="form.tests.push({ input: '', expected: '' })">增加独立测试</n-button>
        </fieldset>
        <label for="ce-reference-note">基准来源与核对说明</label><n-input :input-props="{ id: 'ce-reference-note' }" v-model:value="form.reference_note" type="textarea" :maxlength="1500" :disabled="formLocked" :autosize="{ minRows: 2, maxRows: 6 }" placeholder="说明参考实现的来源，如何核对预期结果，以及测试覆盖了哪些边界。" />
        <fieldset :disabled="formLocked"><legend>补充验证</legend>
          <n-checkbox v-model:checked="form.supplementary" :disabled="formLocked">启用边界与性质检查</n-checkbox>
          <template v-if="form.supplementary">
            <p class="workbench-note">自动生成合法的边界输入，检查参考与修正程序是否一致。只有题意确实要求的性质才应选择；例如，普通求和不满足“重复不变”。这些有限检查不能证明所有输入都正确。</p>
            <n-checkbox v-model:checked="form.verification.boundary_checks" :disabled="formLocked">检查空输入、极值、短数组、长数组和重复值</n-checkbox>
            <p class="workbench-note">允许空数组时，须在独立测试中先填写 [] 的正确输出。生成的其他边界输入只做两份正确程序的一致性核对。</p>
            <label for="ce-properties">题意要求的性质 · 选填</label><n-select filterable multiple :input-props="{ id: 'ce-properties' }" v-model:value="form.verification.properties" :options="propertyOptions" :disabled="formLocked" placeholder="没有适用关系时保持不选" />
            <label for="ce-property-note">补充验证依据</label><n-input type="textarea" :input-props="{ id: 'ce-property-note' }" v-model:value="form.verification.rationale" :maxlength="1000" :disabled="formLocked" :autosize="{ minRows: 2, maxRows: 6 }" placeholder="说明合法边界和所选性质为什么符合题意。只检查边界时，也请核对输入输出范围。" />
          </template>
        </fieldset>
      </n-card>
      <n-card class="workbench-panel" title="02 · 待验证的程序候选">
        <label for="ce-bug-kind">错误类型</label><n-select filterable :input-props="{ id: 'ce-bug-kind' }" v-model:value="form.candidate.bug_kind" :options="bugKinds" :disabled="formLocked" />
        <div class="field-grid">
          <div><label for="ce-buggy">给学生看的错误程序</label><n-input v-model:value="form.candidate.buggy_code" type="textarea" :maxlength="16000" :autosize="{ minRows: 7, maxRows: 18 }" :disabled="formLocked" :input-props="{ id: 'ce-buggy', spellcheck: false }" /></div>
          <div><label for="ce-fixed">修正程序 · 仅教师可见</label><n-input v-model:value="form.candidate.fixed_code" type="textarea" :maxlength="16000" :autosize="{ minRows: 7, maxRows: 18 }" :disabled="formLocked" :input-props="{ id: 'ce-fixed', spellcheck: false }" /></div>
        </div>
        <label for="ce-bug-note">错误原因与教学说明 · 仅教师可见</label><n-input :input-props="{ id: 'ce-bug-note' }" v-model:value="form.candidate.explanation" type="textarea" :maxlength="3000" :autosize="{ minRows: 3, maxRows: 8 }" :disabled="formLocked" />
        <div class="basis-check"><n-checkbox v-model:checked="approvedBasis" :disabled="formLocked">我已核对题意、输入约束、参考实现与独立预期测试。</n-checkbox></div>
        <div class="workbench-actions"><n-button v-if="!detail && !sourceTemplate" type="primary" :loading="generationBusy" :disabled="busy || !!pendingSave || (!approvedBasis && !generationPending)" @click="generateCandidate">{{ generationPending ? '恢复原生成请求' : '确认基准，让小 E 生成候选' }}</n-button>
          <n-button attr-type="submit" :loading="busy" :disabled="generationBusy || !!generationPending || (!approvedBasis && !pendingSave)">{{ pendingSave ? '重试原保存' : detail ? '保存为新版本' : '保存手工填写的候选' }}</n-button>
          <n-button v-if="pendingSave" :disabled="busy" @click="reload">读取保存结果</n-button>
          <n-popconfirm v-else @positive-click="discardDraft"><template #trigger><n-button :disabled="busy || generationBusy || !!generationPending">放弃未保存的编辑</n-button></template>放弃本次编辑并保留已保存的版本？</n-popconfirm></div>
      </n-card>
    </form>

    <template v-else-if="detail">
      <n-card class="workbench-panel" :title="`${detail.specification.title} · 版本 ${detail.revision}`">
        <p v-if="detail.source_template" class="workbench-note">来源：{{ detail.source_template.id }} · {{ detail.origin === 'catalog_draft' ? '固定草稿' : '基于草稿修改' }}。来源记录不代表已通过本班发布审核。</p>
        <div class="workbench-actions"><n-tag>{{ currentVersion ? '当前版本' : '历史版本，只读' }}</n-tag>
          <n-tag :type="detail.published_revision === detail.revision ? 'success' : 'default'">{{ detail.published_revision === detail.revision ? '已开放' : '未开放' }}</n-tag>
          <n-button v-if="currentVersion" ref="editDraftButton" :disabled="busy" @click="edit">修订为新版本</n-button>
          <n-button v-else :disabled="busy" @click="select(detail.id)">回到当前版本</n-button></div>
        <p class="preserve-text">{{ detail.specification.statement }}</p>
        <p>输入：{{ describeValueContract(detail.specification.input_contract) }}<br />输出：{{ describeValueContract(detail.specification.output_contract) }}</p>
        <div class="field-grid"><div><h3>错误程序</h3><pre tabindex="0">{{ detail.candidate.buggy_code }}</pre></div><div><h3>修正程序</h3><pre tabindex="0">{{ detail.candidate.fixed_code }}</pre></div></div>
        <p class="preserve-text">{{ detail.candidate.explanation }}</p>
        <details><summary>查看独立参考与测试</summary><pre tabindex="0">{{ detail.specification.reference_code }}</pre>
          <p>{{ detail.specification.reference_note }}</p><pre tabindex="0">{{ JSON.stringify(detail.specification.tests, null, 2) }}</pre></details>
        <details v-if="detail.specification.verification"><summary>本版本的补充验证约定</summary>
          <p>{{ detail.specification.verification.rationale }}</p><p>边界输入：{{ detail.specification.verification.boundary_checks ? '已启用' : '未启用' }}</p>
          <ul><li v-for="key in detail.specification.verification.properties" :key="key">{{ propertyLabel(key) }}</li></ul></details>
        <n-alert v-if="detail.blocked_reason" type="warning" :show-icon="false">题目已暂停：{{ reasons[detail.blocked_reason] || detail.blocked_reason }}。请创建修订版，并将仍合法的问题输入加入独立测试。</n-alert>
        <ul v-if="detail.material_issues.length"><li v-for="issue in detail.material_issues" :key="issue.attempt_id">问题输入 {{ JSON.stringify(issue.input) }} · {{ reasons[issue.reason] || issue.reason }}</li></ul>
      </n-card>
      <n-card class="workbench-panel" title="03 · 隔离执行验证与教学审核">
        <n-alert v-if="detail.origin === 'model_generated'" type="info" :show-icon="false">后台候选：{{ generationStatuses[detail.generation?.status || ''] || '生成状态不可用' }}。如需调整程序或重新验证，请修订为新版本。<p v-if="detail.generation?.pedagogy_review?.note">{{ detail.generation.pedagogy_review.note }}</p></n-alert>
        <p>执行检查：<strong>{{ statuses[detail.validation?.status || ''] || '尚未运行' }}</strong></p>
        <p v-if="detail.validation?.report?.reason">{{ reasons[detail.validation.report.reason] || detail.validation.report.reason }}</p>
        <div v-if="detail.validation?.report?.failure_detail"><h3>未通过的输入</h3>
          <p>{{ programLabels[detail.validation.report.failure_detail.program] }} · {{ JSON.stringify(detail.validation.report.failure_detail.input) }}</p>
          <p>实际结果：{{ outcome(detail.validation.report.failure_detail.observed) }}<template v-if="detail.validation.report.failure_detail.expected"> · 对照结果：{{ outcome(detail.validation.report.failure_detail.expected) }}</template></p></div>
        <div v-if="detail.validation?.report?.coverage"><h3>计划检查范围</h3>
          <p>{{ detail.validation.report.coverage.declared_inputs }} 个独立测试，加上 {{ detail.validation.report.coverage.boundary_inputs }} 个边界输入、{{ detail.validation.report.coverage.metamorphic_inputs }} 个变形输入，共 {{ detail.validation.report.coverage.total_inputs }} 个不同输入。</p>
          <p class="workbench-note">遇到失败会提前停止。未列出的程序性质不代表已经通过。</p>
          <ul><li v-for="item in detail.validation.report.coverage.properties" :key="`${item.program}-${item.property}`">{{ programLabels[item.program] }} · {{ propertyLabel(item.property) }}：检查 {{ item.checked }} 组，未通过 {{ item.failed }} 组</li></ul>
          <article v-for="(failure, index) in detail.validation.report.coverage.failures" :key="index"><strong>{{ programLabels[failure.program] }} · {{ propertyLabel(failure.property) }}</strong>
            <p>原输入 {{ JSON.stringify(failure.base_input) }} → 输出 {{ JSON.stringify(failure.base_output) }}</p>
            <p v-if="failure.derived_input !== null">变换后 {{ JSON.stringify(failure.derived_input) }} → 输出 {{ JSON.stringify(failure.derived_output) }}</p></article>
          <details><summary>复现标识</summary><pre tabindex="0">{{ detail.validation.report.coverage.policy_version }}
{{ detail.validation.report.coverage.plan_hash }}</pre></details>
        </div>
        <div class="workbench-actions"><n-button v-if="detail.origin !== 'model_generated'" :loading="busy" :disabled="!currentVersion || !!detail.blocked_reason" @click="validate">{{ detail.validation ? '验证或恢复验证' : '开始隔离验证' }}</n-button>
          <n-button v-if="currentVersion && detail.published_revision" :disabled="busy" @click="publish('withdraw')">撤回开放</n-button></div>
        <p class="workbench-note">重新验证会撤下当前发布。通过检查只代表这些测试已验证，不保证全部合法输入都正确。</p>
        <div v-if="detail.validation?.report?.witnesses?.length" class="witnesses"><h3>验证器发现的反例</h3>
          <article v-for="witness in detail.validation.report.witnesses" :key="witness.test_index"><strong>输入 {{ JSON.stringify(witness.input) }}</strong><span v-if="witness.input_origin"> · {{ inputOrigins[witness.input_origin] }}</span><p>错误程序：{{ outcome(witness.buggy) }} · 参考结果：{{ outcome(witness.reference) }}</p></article>
          <p v-if="(detail.validation.report.witness_count || 0) > detail.validation.report.witnesses.length">共发现 {{ detail.validation.report.witness_count }} 个差异输入，此处展示前 {{ detail.validation.report.witnesses.length }} 个。</p></div>
        <details v-if="detail.validation?.report"><summary>查看复现依据与运行环境</summary><pre tabindex="0">{{ JSON.stringify({ runtimes: detail.validation.report.runtimes, hashes: detail.validation.report.artifact_hashes, elapsed_ms: detail.validation.report.elapsed_ms }, null, 2) }}</pre></details>
        <fieldset v-if="currentVersion" :disabled="busy || detail.validation?.status !== 'passed' || !!detail.blocked_reason"><legend>逐项教学核对</legend>
          <div v-for="item in checkLabels" :key="item.key" class="basis-check"><n-checkbox v-model:checked="checks[item.key]" :disabled="busy || detail.validation?.status !== 'passed' || !!detail.blocked_reason">{{ item.label }}</n-checkbox></div>
          <label for="ce-publication-note">审核说明</label><n-input :input-props="{ id: 'ce-publication-note' }" v-model:value="reviewNote" type="textarea" :maxlength="1500" :autosize="{ minRows: 2, maxRows: 6 }" :disabled="busy || detail.validation?.status !== 'passed' || !!detail.blocked_reason" />
          <n-button type="primary" class="publish-button" :disabled="busy || !canPublish" @click="publish('publish')">审核完成，向本班开放</n-button>
        </fieldset>
        <p v-if="detail.review_note">本版本最近审核：{{ detail.review_note }}</p>
      </n-card>
      <n-card class="workbench-panel" title="题目版本">
        <ul class="workbench-list"><li v-for="version in versions.items" :key="version.revision"><span>版本 {{ version.revision }} · {{ date(version.created_at) }}</span><n-button :disabled="busy" @click="select(detail.id, version.revision)">查看版本</n-button></li></ul>
        <n-pagination v-if="versions.total > 20" :page="versions.page" :item-count="versions.total" :page-size="20" :disabled="busy" simple @update:page="page => historyPage('versions', page)" />
      </n-card>
      <n-card class="workbench-panel" title="学生反例提交 · 包含历史版本">
        <p v-if="!attempts.items.length">本班当前学生还没有提交记录。</p>
        <ul class="workbench-list"><li v-for="item in attempts.items" :key="item.request_id"><div><strong>{{ item.student_name }}</strong><p>版本 {{ item.revision }} · {{ date(item.created_at) }} · {{ statuses[item.status] }} · {{ statuses[item.explanation_status || ''] || '暂无解释评价' }}{{ item.explanation_source === 'teacher' ? ' · 教师意见' : '' }}</p></div><n-button :disabled="busy" @click="readAttempt(item.request_id)">核对解释</n-button></li></ul>
        <n-pagination v-if="attempts.total > 20" :page="attempts.page" :item-count="attempts.total" :page-size="20" :disabled="busy" simple @update:page="page => historyPage('attempts', page)" />
      </n-card>
      <n-card v-if="selectedAttempt" class="workbench-panel" :title="`${selectedAttempt.student_name} · 提交时的版本 ${selectedAttempt.revision}`">
        <p class="preserve-text">{{ selectedAttempt.task_snapshot.statement }}</p><pre tabindex="0">{{ selectedAttempt.task_snapshot.buggy_code }}</pre>
        <p>学生输入：{{ JSON.stringify(selectedAttempt.input) }} · 预期输出：{{ JSON.stringify(selectedAttempt.expected_output) }}</p>
        <blockquote class="preserve-text">{{ selectedAttempt.explanation }}</blockquote>
        <template v-if="selectedAttempt.status === 'complete'">
          <p>执行事实：{{ selectedAttempt.counterexample_found ? '已发现差异' : '未发现差异' }}；{{ selectedAttempt.expected_output_correct ? '预期一致' : '预期不符' }}。</p>
          <p v-if="selectedAttempt.buggy_result && selectedAttempt.correct_result">错误输出：{{ outcome(selectedAttempt.buggy_result) }} · 核对输出：{{ outcome(selectedAttempt.correct_result) }}</p>
          <p>当前解释意见：{{ selectedAttempt.explanation_review?.feedback }}</p>
          <label for="ce-review-explanation">教师核对说明</label><n-input :input-props="{ id: 'ce-review-explanation' }" v-model:value="explanationNote" type="textarea" :maxlength="500" :autosize="{ minRows: 2, maxRows: 6 }" :disabled="busy" placeholder="说明学生解释已抓住原因，或明确还需补充什么。" />
          <div class="workbench-actions explanation-actions"><n-button :disabled="busy || !explanationNote.trim()" @click="reviewExplanation('supported')">支持这段解释</n-button><n-button :disabled="busy || !explanationNote.trim()" @click="reviewExplanation('needs_revision')">请学生补充解释</n-button><n-button :disabled="busy" @click="readAttempt(selectedAttempt.request_id)">读取最新意见</n-button></div>
          <p class="workbench-note">解释意见不会改变已确认的执行结果，也不会重算成绩。</p>
        </template><p v-else>{{ selectedAttempt.message }}</p>
        <details v-if="selectedAttempt.execution_report"><summary>查看这次执行记录</summary><pre tabindex="0">{{ JSON.stringify(selectedAttempt.execution_report, null, 2) }}</pre></details>
        <h3 v-if="selectedAttempt.review_history.length">最近的教师核对记录</h3><ol><li v-for="record in selectedAttempt.review_history" :key="record.revision">{{ date(record.created_at) }} · {{ statuses[record.verdict] }}：{{ record.note }}</li></ol>
      </n-card>
    </template>
  </section>
</template>

<style scoped>
.counterexample-workbench { width: 100%; box-sizing: border-box; padding: clamp(16px, 3vw, 32px); max-width: 1440px; margin: auto; min-width: 0; }
.workbench-head, .workbench-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.workbench-head { justify-content: space-between; margin-bottom: 20px; }
.workbench-head h1 { margin: 0; font-size: clamp(22px, 3vw, 30px); }
.workbench-head p, .workbench-list p { margin: 8px 0 0; opacity: .75; }
.workbench-panel { margin-top: 20px; min-width: 0; }
.workbench-list { list-style: none; margin: 0; padding: 0; }
.workbench-list li { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; border-bottom: 1px solid color-mix(in srgb, currentColor 15%, transparent); }
.workbench-list li > div { min-width: 0; flex: 1 1 220px; }
.workbench-list strong, p, blockquote, li { overflow-wrap: anywhere; }
.workbench-panel label { display: block; margin: 16px 0 7px; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.field-grid > div { min-width: 0; }
fieldset { border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 8px; margin: 22px 0 12px; padding: 16px; min-width: 0; }
legend { font-weight: 700; padding: 0 6px; }
.contract-fields + .contract-fields { margin-top: 18px; }
.test-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; gap: 12px; align-items: end; margin-bottom: 12px; }
.workbench-note { opacity: .75; font-size: 13px; line-height: 1.8; }
.basis-check { margin: 15px 0; }
.publish-button, .explanation-actions { margin-top: 16px; }
.preserve-text { white-space: pre-wrap; line-height: 1.8; }
pre { max-width: 100%; overflow: auto; padding: 16px; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 8px; background: color-mix(in srgb, currentColor 5%, transparent); font: 13px/1.8 Consolas, monospace; tab-size: 4; }
pre:focus-visible, summary:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
details { margin: 18px 0; } summary { cursor: pointer; font-weight: 600; }
blockquote { margin: 16px 0; padding: 12px 16px; border-left: 3px solid currentColor; }
.witnesses article { padding: 12px 0; border-bottom: 1px solid color-mix(in srgb, currentColor 15%, transparent); }
.n-pagination { margin-top: 14px; }
@media (max-width: 900px) { .field-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 600px) { .test-row { grid-template-columns: minmax(0, 1fr); } .test-row .n-button { justify-self: start; } }
</style>
