<script setup lang="ts">
/**
 * 管理员 · 检索测试 / RAG Debug。
 * 展示：识别知识点 → Graph 节点 → Vector/Lexical Top-K → Rerank Score → Context → Answer，以及 RAG 请求日志。
 */
import { computed, ref } from 'vue'
import { NButton, NEmpty, NIcon, NInput, NInputNumber, NSelect, NSpin, NSwitch, NTag, useMessage, type SelectOption } from 'naive-ui'
import { RefreshOutline, SearchOutline, SparklesOutline, TerminalOutline } from '@vicons/ionicons5'
import { KNOWLEDGE_TYPE_LABELS, type KnowledgeType } from '../../api/knowledge'
import {
  fetchRagLog,
  fetchRagLogs,
  ragQuery,
  ragRetrieve,
  type RagAnswer,
  type RagDebugChunk,
  type RagGraphContext,
  type RagQueryLog,
  type RagRerankExplain,
  type RagRetrieveResult,
  type RagScene,
  type RagUnderstanding,
} from '../../api/rag'

const message = useMessage()

const query = ref('')
const scene = ref<RagScene>('chat')
const hintLevel = ref(0)
const topK = ref(6)
const asUserId = ref<number | null>(null)
const requireVerified = ref(false)
const knowledgeTypes = ref<KnowledgeType[]>([])
const useLlm = ref(true)
const mode = ref<'retrieve' | 'answer'>('answer')
const running = ref(false)

const retrieveResult = ref<RagRetrieveResult | null>(null)
const answerResult = ref<RagAnswer | null>(null)
const activeSection = ref<'graph' | 'candidates' | 'rerank' | 'context' | 'answer'>('answer')

const sceneOptions: SelectOption[] = [
  { label: 'chat · 小E 答疑', value: 'chat' },
  { label: 'trial · 试炼（练习禁泄题）', value: 'trial' },
  { label: 'practice · 练习', value: 'practice' },
  { label: 'diagnosis · 诊断', value: 'diagnosis' },
  { label: 'path · 路径推荐', value: 'path' },
  { label: 'resource · 资源生成', value: 'resource' },
]
const hintOptions: SelectOption[] = [
  { label: '不设置', value: 0 },
  { label: 'Level 1 · 思路引导', value: 1 },
  { label: 'Level 2 · 知识点定位', value: 2 },
  { label: 'Level 3 · 关键代码片段', value: 3 },
  { label: 'Level 4 · 完整解析', value: 4 },
]
const knowledgeTypeOptions: SelectOption[] = (Object.keys(KNOWLEDGE_TYPE_LABELS) as KnowledgeType[]).map((k) => ({
  label: KNOWLEDGE_TYPE_LABELS[k],
  value: k,
}))

const understanding = computed<RagUnderstanding | null>(() => answerResult.value?.debug?.understanding ?? retrieveResult.value?.understanding ?? null)
const graph = computed<RagGraphContext | null>(() => answerResult.value?.debug?.graph ?? retrieveResult.value?.graph ?? null)
const candidates = computed<RagDebugChunk[]>(() => answerResult.value?.debug?.candidates ?? retrieveResult.value?.candidates ?? [])
const reranked = computed<RagDebugChunk[]>(() => answerResult.value?.debug?.reranked ?? retrieveResult.value?.reranked ?? [])
const rerankExplain = computed<RagRerankExplain[]>(() => answerResult.value?.debug?.rerank_explain ?? retrieveResult.value?.rerank_explain ?? [])
const strategy = computed(() => answerResult.value?.debug?.strategy ?? retrieveResult.value?.strategy ?? null)
const channelStats = computed(() => answerResult.value?.debug?.channel_stats ?? retrieveResult.value?.channel_stats ?? null)
const confidence = computed(() => answerResult.value ?? retrieveResult.value)
const contextDebug = computed(() => answerResult.value?.debug?.context ?? null)

const conceptNames = computed(() => Object.fromEntries((graph.value?.nodes ?? []).map((n) => [n.concept_id, n.name])))

function conceptName(id: string) {
  return conceptNames.value[id] ?? id
}

async function run() {
  const q = query.value.trim()
  if (!q) {
    message.warning('请输入测试问题')
    return
  }
  running.value = true
  answerResult.value = null
  retrieveResult.value = null
  try {
    const context = hintLevel.value ? { hint_level: hintLevel.value, task_type: scene.value === 'trial' ? 'trial' : undefined } : undefined
    if (mode.value === 'retrieve') {
      retrieveResult.value = await ragRetrieve({
        query: q,
        top_k: topK.value,
        knowledge_types: knowledgeTypes.value.length ? knowledgeTypes.value : undefined,
        require_verified: requireVerified.value,
        as_user_id: asUserId.value ?? undefined,
        context,
      })
      activeSection.value = 'rerank'
    } else {
      answerResult.value = await ragQuery({
        query: q,
        scene: scene.value,
        debug: true,
        use_llm: useLlm.value,
        hint_level: hintLevel.value || undefined,
        context,
      })
      activeSection.value = 'answer'
    }
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    running.value = false
  }
}

function pct(v: number | undefined | null) {
  if (v === undefined || v === null) return '—'
  return (v * 100).toFixed(1)
}

function fixed(v: number | undefined | null, digits = 3) {
  if (v === undefined || v === null) return '—'
  return v.toFixed(digits)
}

function levelTone(level: string | undefined) {
  if (level === 'HIGH') return 'success'
  if (level === 'MEDIUM') return 'warning'
  return 'error'
}

const sections: Array<{ key: typeof activeSection.value; label: string }> = [
  { key: 'graph', label: '识别知识点 & Graph' },
  { key: 'candidates', label: '召回候选（Vector / Lexical）' },
  { key: 'rerank', label: 'Rerank Top-K' },
  { key: 'context', label: 'Context / Prompt' },
  { key: 'answer', label: 'Answer' },
]

// ------------------------------------------------------------------ 日志
const logs = ref<RagQueryLog[]>([])
const logTotal = ref(0)
const logPage = ref(1)
const logLoading = ref(false)
const logDetail = ref<RagQueryLog | null>(null)
const logSceneFilter = ref('')
const logStatusFilter = ref('')

async function loadLogs() {
  logLoading.value = true
  try {
    const result = await fetchRagLogs({ page: logPage.value, per_page: 12, scene: logSceneFilter.value || undefined, status: logStatusFilter.value || undefined })
    logs.value = result.items
    logTotal.value = result.total
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    logLoading.value = false
  }
}

async function openLog(row: RagQueryLog) {
  try {
    logDetail.value = await fetchRagLog(row.id)
  } catch (error) {
    message.error((error as Error).message)
  }
}

const logPages = computed(() => Math.max(1, Math.ceil(logTotal.value / 12)))
const showLogs = ref(false)

function toggleLogs() {
  showLogs.value = !showLogs.value
  if (showLogs.value && !logs.value.length) void loadLogs()
}

function fmtTime(value: string | null | undefined) {
  if (!value) return '—'
  return value.slice(0, 19).replace('T', ' ')
}
</script>

<template>
  <div class="rag-inspect">
    <article class="panel">
      <header class="section-head section-head--row">
        <n-icon :component="SearchOutline" />
        <div>
          <h2>检索测试与诊断</h2>
          <p>Hybrid Retrieval：Query Understanding → Learner Context → Graph 1-hop → Vector Top-K → Metadata Filter → Rerank。分值仅管理员可见。</p>
        </div>
        <div class="mode-switch">
          <button type="button" :class="{ active: mode === 'answer' }" @click="mode = 'answer'">完整问答</button>
          <button type="button" :class="{ active: mode === 'retrieve' }" @click="mode = 'retrieve'">仅检索</button>
        </div>
      </header>

      <div class="query-form">
        <n-input
          v-model:value="query"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 5 }"
          placeholder="请输入学生问题"
          @keydown.ctrl.enter.prevent="run"
        />
        <div class="query-options">
          <label><span>场景</span><n-select v-model:value="scene" :options="sceneOptions" size="small" /></label>
          <label><span>Hint Level</span><n-select v-model:value="hintLevel" :options="hintOptions" size="small" /></label>
          <label><span>Top-K</span><n-input-number v-model:value="topK" size="small" :min="1" :max="20" /></label>
          <label><span>以学生视角 · 学号</span><n-input-number v-model:value="asUserId" size="small" :min="1" placeholder="留空表示当前账号" clearable /></label>
          <label v-if="mode === 'retrieve'"><span>知识类型</span><n-select v-model:value="knowledgeTypes" :options="knowledgeTypeOptions" multiple size="small" max-tag-count="responsive" /></label>
          <label class="switch" v-if="mode === 'retrieve'"><span>仅教师审核</span><n-switch v-model:value="requireVerified" size="small" /></label>
          <label class="switch" v-else><span>调用 LLM</span><n-switch v-model:value="useLlm" size="small" /></label>
        </div>
        <n-button type="primary" :loading="running" @click="run"><template #icon><n-icon :component="SparklesOutline" /></template>运行（Ctrl+Enter）</n-button>
      </div>
    </article>

    <article v-if="confidence" class="panel">
      <div class="summary-strip">
        <n-tag :type="levelTone(confidence.confidence_level)" :bordered="false">{{ confidence.confidence_level }}</n-tag>
        <span>confidence <strong>{{ fixed(confidence.confidence) }}</strong></span>
        <span>grounded <strong>{{ confidence.knowledge_grounded ? 'true' : 'false' }}</strong></span>
        <span v-if="answerResult">mode <strong>{{ answerResult.generation_mode }}</strong></span>
        <span v-if="answerResult?.model">model <strong>{{ answerResult.provider }}/{{ answerResult.model }}</strong></span>
        <span>latency <strong>{{ confidence.latency_ms }} ms</strong></span>
        <span v-if="answerResult?.log_id">log #{{ answerResult.log_id }}</span>
        <span v-if="channelStats" class="dim">channels {{ JSON.stringify(channelStats) }}</span>
      </div>

      <nav class="sub-tabs">
        <button v-for="s in sections" :key="s.key" type="button" :class="{ active: activeSection === s.key }" :disabled="s.key === 'answer' && !answerResult" @click="activeSection = s.key">{{ s.label }}</button>
      </nav>

      <!-- Graph -->
      <section v-if="activeSection === 'graph'" class="inspect-section">
        <div class="two-col">
          <div>
            <h3>Query Understanding</h3>
            <dl v-if="understanding" class="kv">
              <dt>normalized</dt><dd>{{ understanding.normalized_query }}</dd>
              <dt>intent</dt><dd>{{ understanding.intent }} <span class="dim">({{ understanding.method }})</span></dd>
              <dt>keywords</dt><dd>{{ understanding.keywords.join('、') || '—' }}</dd>
              <dt>error_type</dt><dd>{{ understanding.error_type ?? '—' }}</dd>
              <dt>concepts</dt>
              <dd>
                <span v-for="cid in understanding.concept_ids" :key="cid" class="chip">{{ conceptName(cid) }} <em>{{ fixed(understanding.concept_scores[cid], 2) }}</em></span>
                <span v-if="!understanding.concept_ids.length" class="dim">未识别</span>
              </dd>
            </dl>
            <h3>Teaching Strategy</h3>
            <dl v-if="strategy" class="kv">
              <dt>strategies</dt><dd><span v-for="s in strategy.strategies" :key="s" class="chip chip--strategy">{{ s }}</span></dd>
              <dt>mastery</dt><dd>{{ strategy.mastery_band }} <span class="dim">{{ strategy.focus_mastery !== null ? fixed(strategy.focus_mastery, 2) : '' }}</span></dd>
              <dt>hint</dt><dd>{{ strategy.hint_level ?? '—' }} / max {{ strategy.hint_max_level ?? '—' }} <span class="dim">{{ strategy.practice_mode ? 'practice_mode' : '' }}</span></dd>
              <dt>rationale</dt><dd><p v-for="(r, i) in strategy.rationale" :key="i" class="rationale">{{ r }}</p></dd>
            </dl>
          </div>
          <div>
            <h3>Graph Context（{{ graph?.nodes.length ?? 0 }} 节点）</h3>
            <ul v-if="graph" class="node-list">
              <li v-for="n in graph.nodes" :key="n.concept_id" :class="`role-${n.role}`">
                <span class="role">{{ n.role }}</span>
                <strong>{{ n.name }}</strong>
                <em>hop {{ n.hop }} · w {{ fixed(n.weight, 2) }}<template v-if="n.mastery !== null"> · 掌握 {{ fixed(n.mastery, 2) }}</template></em>
              </li>
            </ul>
            <p v-if="graph?.unmet_prerequisites.length" class="note">未满足前置：{{ graph.unmet_prerequisites.map(conceptName).join('、') }}</p>
            <p v-if="graph?.misconceptions.length" class="note">关联误区：{{ graph.misconceptions.map(conceptName).join('、') }}</p>
            <p v-if="graph?.next_recommended.length" class="note">推荐后续：{{ graph.next_recommended.map(conceptName).join('、') }}</p>
          </div>
        </div>
      </section>

      <!-- Candidates -->
      <section v-else-if="activeSection === 'candidates'" class="inspect-section">
        <n-empty v-if="!candidates.length" description="无召回候选" />
        <table v-else class="score-table">
          <thead>
            <tr><th>#</th><th>Chunk</th><th>类型</th><th>知识点</th><th>channels</th><th>vector</th><th>lexical</th><th>hybrid</th></tr>
          </thead>
          <tbody>
            <tr v-for="(c, i) in candidates" :key="c.chunk_id">
              <td>{{ i + 1 }}</td>
              <td class="title-cell"><strong :title="c.content">{{ c.title || c.document_title }}</strong><small>{{ c.document_title }}<template v-if="c.teacher_verified"> · 教师审核</template></small></td>
              <td>{{ KNOWLEDGE_TYPE_LABELS[c.knowledge_type] ?? c.knowledge_type }}</td>
              <td class="dim">{{ c.concept_ids.map(conceptName).join('、') }}</td>
              <td>{{ c.retrieval_channels.join('+') }}</td>
              <td class="num">{{ pct(c.vector_score) }}</td>
              <td class="num">{{ pct(c.lexical_score) }}</td>
              <td class="num">{{ pct(c.hybrid_score) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Rerank -->
      <section v-else-if="activeSection === 'rerank'" class="inspect-section">
        <n-empty v-if="!reranked.length" description="Rerank 后无结果" />
        <div v-else class="rerank-list">
          <article v-for="(c, i) in reranked" :key="c.chunk_id" class="rerank-item">
            <header>
              <span class="rank">{{ i + 1 }}</span>
              <strong>{{ c.title || c.document_title }}</strong>
              <n-tag size="tiny" :bordered="false">{{ KNOWLEDGE_TYPE_LABELS[c.knowledge_type] ?? c.knowledge_type }}</n-tag>
              <n-tag v-if="c.teacher_verified" size="tiny" type="success" :bordered="false">教师审核</n-tag>
              <em>final {{ fixed(c.final_score) }}</em>
            </header>
            <div class="breakdown">
              <span v-for="(v, k) in (rerankExplain[i]?.breakdown ?? c.score_breakdown)" :key="k"><i>{{ k }}</i>{{ fixed(v) }}</span>
            </div>
            <pre class="chunk-text">{{ c.content }}</pre>
          </article>
        </div>
      </section>

      <!-- Context -->
      <section v-else-if="activeSection === 'context'" class="inspect-section">
        <n-empty v-if="!contextDebug" description="仅「完整问答」模式包含 Context / Prompt" />
        <div v-else class="context-grid">
          <div><h3>Learner Context</h3><pre>{{ contextDebug.learner_context || '—' }}</pre></div>
          <div><h3>Knowledge Context</h3><pre>{{ contextDebug.knowledge_context || '—' }}</pre></div>
          <div><h3>Teaching Strategy / Hint</h3><pre>{{ [contextDebug.teaching_strategy, contextDebug.hint_instruction].filter(Boolean).join('\n\n') || '—' }}</pre></div>
          <div><h3>Retrieved Context</h3><pre>{{ contextDebug.retrieved_context || '—' }}</pre></div>
          <div class="span-2"><h3>System Prompt</h3><pre>{{ contextDebug.system_prompt }}</pre></div>
          <div class="span-2"><h3>User Prompt</h3><pre>{{ contextDebug.user_prompt }}</pre></div>
        </div>
      </section>

      <!-- Answer -->
      <section v-else class="inspect-section">
        <template v-if="answerResult">
          <pre class="answer-text">{{ answerResult.answer }}</pre>
          <div class="two-col">
            <div>
              <h3>concepts</h3>
              <span v-for="c in answerResult.concepts" :key="c.concept_id" class="chip">{{ c.name }} <em>{{ c.role }}</em></span>
              <h3>recommended_next</h3>
              <ul class="plain">
                <li v-for="r in answerResult.recommended_next" :key="`${r.type}-${r.concept_id}`"><strong>{{ r.name }}</strong> <span class="dim">{{ r.type }}</span><br /><small>{{ r.reason }}</small></li>
                <li v-if="!answerResult.recommended_next.length" class="dim">—</li>
              </ul>
            </div>
            <div>
              <h3>sources（学生安全视图）</h3>
              <ul class="plain">
                <li v-for="s in answerResult.sources" :key="s.chunk_id"><strong>{{ s.title }}</strong> <small class="dim">{{ s.document_title }}<template v-if="s.teacher_verified"> · 教师审核</template></small><br /><small>{{ s.preview }}</small></li>
              </ul>
              <h3>token_usage</h3>
              <pre class="mini">{{ JSON.stringify(answerResult.token_usage ?? {}, null, 1) }}</pre>
            </div>
          </div>
        </template>
      </section>
    </article>

    <article class="panel">
      <header class="section-head section-head--row">
        <n-icon :component="TerminalOutline" />
        <div>
          <h2>RAG 请求日志</h2>
          <p>每次请求记录 detected_concepts / graph_nodes / retrieved_chunks / scores / strategy / model / latency / token_usage / confidence。query 仅存摘要与哈希。</p>
        </div>
        <div class="log-tools">
          <n-select v-model:value="logSceneFilter" size="small" class="w120" :options="[{ label: '全部场景', value: '' }, ...sceneOptions, { label: 'retrieve', value: 'retrieve' }]" @update:value="logPage = 1; loadLogs()" />
          <n-select v-model:value="logStatusFilter" size="small" class="w120" :options="[{ label: '全部状态', value: '' }, { label: 'ok', value: 'ok' }, { label: 'refused', value: 'refused' }, { label: 'low_confidence', value: 'low_confidence' }, { label: 'error', value: 'error' }]" @update:value="logPage = 1; loadLogs()" />
          <n-button quaternary size="small" :loading="logLoading" @click="loadLogs"><n-icon :component="RefreshOutline" /></n-button>
          <n-button size="small" secondary @click="toggleLogs">{{ showLogs ? '收起' : '展开日志' }}</n-button>
        </div>
      </header>
      <n-spin v-if="showLogs" :show="logLoading">
        <n-empty v-if="!logs.length && !logLoading" description="暂无日志" />
        <table v-else class="score-table log-table">
          <thead><tr><th>时间</th><th>用户</th><th>场景</th><th>摘要</th><th>意图</th><th>策略</th><th>置信</th><th>模式</th><th>耗时</th></tr></thead>
          <tbody>
            <tr v-for="row in logs" :key="row.id" @click="openLog(row)">
              <td class="dim">{{ fmtTime(row.created_at) }}</td>
              <td>{{ row.user_id ?? '—' }}<small class="dim"> {{ row.role }}</small></td>
              <td>{{ row.scene }}</td>
              <td class="title-cell"><strong>{{ row.query_preview }}</strong></td>
              <td>{{ row.intent }}</td>
              <td class="dim">{{ row.teaching_strategy.join(', ') }}</td>
              <td><n-tag size="tiny" :type="levelTone(row.confidence_level)" :bordered="false">{{ fixed(row.confidence, 2) }}</n-tag></td>
              <td>{{ row.generation_mode }}<small v-if="row.model" class="dim"> {{ row.model }}</small></td>
              <td class="num">{{ row.latency_ms }}ms</td>
            </tr>
          </tbody>
        </table>
        <footer v-if="logPages > 1" class="pager">
          <n-button size="tiny" quaternary :disabled="logPage <= 1" @click="logPage--; loadLogs()">上一页</n-button>
          <span>{{ logPage }} / {{ logPages }}</span>
          <n-button size="tiny" quaternary :disabled="logPage >= logPages" @click="logPage++; loadLogs()">下一页</n-button>
        </footer>
        <pre v-if="logDetail" class="log-detail">{{ JSON.stringify(logDetail, null, 2) }}</pre>
      </n-spin>
    </article>
  </div>
</template>

<style scoped>
.rag-inspect { display: grid; gap: 1rem; min-width: 0; --ki-body: 0.82rem; --ki-meta: 0.72rem; }

.panel {
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background:
    radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.11), transparent 42%),
    linear-gradient(145deg, rgba(19, 20, 43, 0.88), rgba(8, 11, 26, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 18px 50px rgba(0, 0, 0, 0.22);
  min-width: 0;
  padding: 1.15rem 1.25rem;
}
.section-head { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 0.65rem; align-items: start; margin-bottom: 1rem; color: #c4b5fd; }
.section-head--row { grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; }
.section-head > .n-icon { font-size: 1.25rem; }
.section-head h2 { margin: 0; color: #fff; font-size: 1.02rem; }
.section-head p { margin: 0.3rem 0 0; color: rgba(226, 232, 240, 0.58); font-size: 0.76rem; line-height: 1.45; }

.mode-switch { display: inline-flex; gap: 0.25rem; padding: 0.2rem; border-radius: 8px; background: rgba(129, 140, 248, 0.1); }
.mode-switch button, .sub-tabs button {
  border: 0; border-radius: 6px; padding: 0.35rem 0.75rem; background: transparent;
  color: rgba(226, 232, 240, 0.7); font-size: var(--ki-meta); cursor: pointer;
}
.mode-switch button.active, .sub-tabs button.active { background: rgba(139, 92, 246, 0.35); color: #fff; }
.sub-tabs button:disabled { opacity: 0.4; cursor: not-allowed; }
.sub-tabs { display: flex; gap: 0.3rem; margin: 0.8rem 0; flex-wrap: wrap; }

.query-form { display: grid; gap: 0.7rem; }
.query-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.6rem; align-items: end; }
.query-options label { display: grid; gap: 0.25rem; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.6); }
.query-options label.switch { grid-template-columns: auto auto; align-items: center; justify-content: start; gap: 0.5rem; }
.query-form > .n-button { justify-self: start; }

.summary-strip { display: flex; flex-wrap: wrap; gap: 0.9rem; align-items: center; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.65); }
.summary-strip strong { color: #fff; margin-left: 0.2rem; }
.dim { color: rgba(226, 232, 240, 0.45); }

.inspect-section h3 { margin: 0.6rem 0 0.4rem; font-size: 0.78rem; color: #c4b5fd; font-weight: 600; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.kv { display: grid; grid-template-columns: 90px 1fr; gap: 0.3rem 0.6rem; margin: 0; font-size: var(--ki-meta); }
.kv dt { color: rgba(226, 232, 240, 0.5); }
.kv dd { margin: 0; color: rgba(226, 232, 240, 0.85); display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }
.rationale { margin: 0; }
.chip { display: inline-flex; gap: 0.3rem; align-items: center; border-radius: 999px; padding: 0.15rem 0.55rem; background: rgba(129, 140, 248, 0.14); border: 1px solid rgba(129, 140, 248, 0.28); color: #c7d2fe; font-size: var(--ki-meta); margin: 0.1rem 0.15rem 0.1rem 0; }
.chip em { color: rgba(226, 232, 240, 0.5); font-style: normal; }
.chip--strategy { background: rgba(56, 189, 248, 0.14); border-color: rgba(56, 189, 248, 0.3); color: #bae6fd; }
.node-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; max-height: 320px; overflow: auto; }
.node-list li { display: grid; grid-template-columns: 90px minmax(0, 1fr) auto; gap: 0.5rem; align-items: center; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.8); }
.node-list .role { color: #a5b4fc; text-transform: uppercase; font-size: 0.66rem; letter-spacing: 0.04em; }
.node-list li.role-focus .role { color: #fff; }
.node-list li.role-misconception .role { color: #fda4af; }
.node-list em { color: rgba(226, 232, 240, 0.5); font-style: normal; }
.note { margin: 0.4rem 0 0; font-size: var(--ki-meta); color: #fcd34d; }

.score-table { width: 100%; border-collapse: collapse; font-size: var(--ki-meta); }
.score-table th { text-align: left; color: #c4b5fd; padding: 0.4rem 0.5rem; border-bottom: 1px solid rgba(167, 139, 250, 0.2); font-weight: 600; }
.score-table td { padding: 0.45rem 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); color: rgba(226, 232, 240, 0.8); vertical-align: top; }
.score-table .num { text-align: right; font-family: Consolas, monospace; }
.title-cell strong { display: block; color: #fff; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.title-cell small { color: rgba(226, 232, 240, 0.5); }
.log-table tbody tr { cursor: pointer; }
.log-table tbody tr:hover td { background: rgba(139, 92, 246, 0.08); }

.rerank-list { display: grid; gap: 0.6rem; }
.rerank-item { border: 1px solid rgba(129, 140, 248, 0.16); border-radius: 8px; padding: 0.6rem 0.75rem; background: rgba(129, 140, 248, 0.06); }
.rerank-item header { display: flex; gap: 0.5rem; align-items: center; font-size: var(--ki-body); }
.rerank-item header strong { flex: 1; min-width: 0; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rerank-item header em { color: #a5b4fc; font-style: normal; font-family: Consolas, monospace; font-size: var(--ki-meta); }
.rank { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; background: rgba(139, 92, 246, 0.25); color: #e9d5ff; font-size: var(--ki-meta); }
.breakdown { display: flex; flex-wrap: wrap; gap: 0.6rem; margin: 0.4rem 0; font-size: var(--ki-meta); font-family: Consolas, monospace; color: rgba(226, 232, 240, 0.8); }
.breakdown i { color: rgba(226, 232, 240, 0.45); font-style: normal; margin-right: 0.25rem; }
.chunk-text, .answer-text, .context-grid pre, .log-detail, .mini {
  margin: 0; padding: 0.6rem; border-radius: 6px; background: rgba(5, 14, 26, 0.6);
  color: rgba(226, 232, 240, 0.85); font-size: 0.76rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word;
}
.chunk-text { max-height: 200px; overflow: auto; }
.answer-text { margin-bottom: 0.8rem; font-size: 0.84rem; }
.context-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.context-grid pre { max-height: 320px; overflow: auto; }
.span-2 { grid-column: 1 / -1; }
.plain { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.35rem; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.8); }
.plain strong { color: #fff; }
.log-tools { display: flex; gap: 0.4rem; align-items: center; }
.w120 { width: 130px; }
.pager { display: flex; justify-content: center; align-items: center; gap: 0.75rem; margin-top: 0.75rem; color: rgba(226, 232, 240, 0.6); font-size: var(--ki-meta); }
.log-detail { margin-top: 0.75rem; max-height: 420px; overflow: auto; }

@media (max-width: 1100px) {
  .two-col, .context-grid { grid-template-columns: 1fr; }
}
</style>
