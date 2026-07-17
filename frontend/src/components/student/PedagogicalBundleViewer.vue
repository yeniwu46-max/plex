<script setup lang="ts">
import { computed } from 'vue'
import { NCollapse, NCollapseItem } from 'naive-ui'
import { stripMarkdownAsterisks } from '../../utils/questionStemSanitizer'

export interface PedagogicalBundleContent {
  format?: string
  title?: string
  node?: string
  objective?: string[]
  analysis?: {
    positioning?: string
    learning_objectives?: string[]
    competency_objectives?: string[]
    bloom_level?: string
    recommended_styles?: string[]
    learning_stage?: string
  }
  explain?: string
  diagrams?: Array<{ caption?: string; flow_hint?: string; sketch?: string; mermaid?: string }>
  cases?: Array<{ title?: string; scenario?: string; why_real?: string; key_idea?: string }>
  code?: Array<{ title?: string; source?: string; complexity?: string; pep8_note?: string }>
  exercises?: Array<{
    type?: string
    stem?: string
    options?: string[]
    answer?: string
    explanation?: string
    tags?: string[]
  }>
  summary?: { one_liner?: string; keywords?: string[]; mindmap_markdown?: string }
  markdown?: string
}

const props = defineProps<{ content: PedagogicalBundleContent }>()

function clean(value?: string) {
  return stripMarkdownAsterisks(value ?? '')
}

const sections = computed(() => {
  const items: Array<{ name: string; title: string; count?: number }> = []
  if (props.content.explain) items.push({ name: 'explain', title: '讲解文档' })
  if (props.content.diagrams?.length) {
    items.push({ name: 'diagrams', title: '思维导图 / 图示', count: props.content.diagrams.length })
  }
  if (props.content.cases?.length) {
    items.push({ name: 'cases', title: '案例', count: props.content.cases.length })
  }
  if (props.content.code?.length) {
    items.push({ name: 'code', title: '代码实操', count: props.content.code.length })
  }
  if (props.content.exercises?.length) {
    items.push({ name: 'exercises', title: '分层题库', count: props.content.exercises.length })
  }
  if (props.content.summary) items.push({ name: 'summary', title: '总结' })
  return items
})

const exerciseTypeLabel: Record<string, string> = {
  choice: '选择题',
  fill: '填空题',
  coding: '编程题',
}
</script>

<template>
  <div class="bundle-viewer">
    <section v-if="content.analysis" class="bundle-viewer__analysis">
      <h3>教学分析</h3>
      <p>{{ clean(content.analysis.positioning) }}</p>
      <ul>
        <li>Bloom 层级：{{ clean(content.analysis.bloom_level) }}</li>
        <li>推荐方式：{{ (content.analysis.recommended_styles ?? []).join('、') }}</li>
      </ul>
      <ul v-if="content.analysis.learning_objectives?.length">
        <li v-for="item in content.analysis.learning_objectives" :key="item">{{ clean(item) }}</li>
      </ul>
    </section>

    <n-collapse class="bundle-viewer__accordion" :default-expanded-names="sections[0]?.name ? [sections[0].name] : []">
      <n-collapse-item v-if="content.explain" name="explain" title="讲解文档">
        <pre class="bundle-section__text">{{ clean(content.explain) }}</pre>
      </n-collapse-item>

      <n-collapse-item
        v-if="content.diagrams?.length"
        name="diagrams"
        :title="`思维导图 / 图示（${content.diagrams.length}）`"
      >
        <article v-for="(diagram, index) in content.diagrams" :key="index" class="bundle-section">
          <h4>{{ clean(diagram.caption) }}</h4>
          <p>{{ clean(diagram.sketch) }}</p>
          <p class="bundle-section__hint">{{ clean(diagram.flow_hint) }}</p>
          <pre v-if="diagram.mermaid" class="bundle-section__code">{{ clean(diagram.mermaid) }}</pre>
        </article>
      </n-collapse-item>

      <n-collapse-item
        v-if="content.cases?.length"
        name="cases"
        :title="`案例（${content.cases.length}）`"
      >
        <article v-for="item in content.cases" :key="item.title" class="bundle-section">
          <h4>{{ clean(item.title) }}</h4>
          <p>{{ clean(item.scenario) }}</p>
          <p class="bundle-section__hint">为何真实：{{ clean(item.why_real) }}</p>
          <p>要点：{{ clean(item.key_idea) }}</p>
        </article>
      </n-collapse-item>

      <n-collapse-item
        v-if="content.code?.length"
        name="code"
        :title="`代码实操（${content.code.length}）`"
      >
        <article v-for="block in content.code" :key="block.title" class="bundle-section">
          <h4>{{ clean(block.title) }}（{{ clean(block.complexity) }}）</h4>
          <p class="bundle-section__hint">{{ clean(block.pep8_note) }}</p>
          <pre class="bundle-section__code">{{ clean(block.source) }}</pre>
        </article>
      </n-collapse-item>

      <n-collapse-item
        v-if="content.exercises?.length"
        name="exercises"
        :title="`分层题库（${content.exercises.length}）`"
      >
        <article v-for="(ex, index) in content.exercises" :key="index" class="bundle-section">
          <h4>第 {{ index + 1 }} 题 · {{ exerciseTypeLabel[ex.type ?? ''] ?? ex.type }}</h4>
          <p>{{ clean(ex.stem) }}</p>
          <ul v-if="ex.options?.length">
            <li v-for="opt in ex.options" :key="String(opt)">{{ clean(String(opt)) }}</li>
          </ul>
          <n-collapse>
            <n-collapse-item title="参考答案与解析" :name="`ex-${index}`">
              <pre v-if="ex.answer" class="bundle-section__answer">{{ clean(ex.answer) }}</pre>
              <p>{{ clean(ex.explanation) }}</p>
            </n-collapse-item>
          </n-collapse>
        </article>
      </n-collapse-item>

      <n-collapse-item v-if="content.summary" name="summary" title="总结">
        <p>{{ clean(content.summary?.one_liner) }}</p>
        <p>关键词：{{ (content.summary?.keywords ?? []).join(' · ') }}</p>
        <pre class="bundle-section__text">{{ clean(content.summary?.mindmap_markdown) }}</pre>
      </n-collapse-item>
    </n-collapse>
  </div>
</template>

<style scoped>
.bundle-viewer {
  display: grid;
  gap: 1rem;
}

.bundle-viewer__analysis {
  padding: 0.85rem 1rem;
  border: 1px solid rgba(37, 245, 238, 0.14);
  border-radius: 0.55rem;
  background: rgba(2, 10, 18, 0.55);
  color: #cce6ef;
}

.bundle-viewer__analysis h3,
.bundle-section h4 {
  margin: 0 0 0.5rem;
  color: #f0faff;
}

.bundle-viewer__analysis ul {
  margin: 0.35rem 0 0;
  padding-left: 1.1rem;
}

.bundle-section {
  padding: 0.75rem 0;
}

.bundle-section__text,
.bundle-section__code,
.bundle-section__answer {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #cce6ef;
  margin: 0;
}

.bundle-section__code,
.bundle-section__answer {
  padding: 0.75rem;
  border-radius: 0.45rem;
  background: rgba(0, 0, 0, 0.35);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.86rem;
}

.bundle-section__hint {
  color: #7da5b6;
  font-size: 0.84rem;
}
</style>
