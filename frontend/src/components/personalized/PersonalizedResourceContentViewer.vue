<script setup lang="ts">
import { computed, ref } from 'vue'
import { NCollapse, NCollapseItem, NTag } from 'naive-ui'
import PedagogicalBundleViewer, {
  type PedagogicalBundleContent,
} from '../student/PedagogicalBundleViewer.vue'
import type { PersonalizedResource } from '../../api/personalizedResources'
import { stripMarkdownAsterisks } from '../../utils/questionStemSanitizer'

const props = withDefaults(
  defineProps<{
    item: PersonalizedResource
    bundleItem?: PersonalizedResource | null
    theme?: 'student' | 'teacher'
  }>(),
  { theme: 'student' },
)

const viewMode = ref<'current' | 'bundle'>('current')

const isBundle = computed(
  () =>
    props.item.resource_type === 'learning_bundle' &&
    props.item.content?.format === 'pedagogical_v2',
)

const bundleContent = computed((): PedagogicalBundleContent | null => {
  const source =
    props.item.resource_type === 'learning_bundle'
      ? props.item
      : props.bundleItem
  if (!source || source.content?.format !== 'pedagogical_v2') return null
  return source.content as PedagogicalBundleContent
})

const markdownText = computed(() => {
  const content = props.item.content
  if (typeof content.markdown === 'string') return content.markdown
  return ''
})

const exerciseQuestions = computed(() => {
  const questions = props.item.content?.questions
  return Array.isArray(questions) ? questions : []
})

const mindMap = computed(() => {
  if (props.item.content?.format !== 'tree') return null
  return props.item.content as {
    root?: string
    children?: Array<{ label?: string; note?: string }>
  }
})

const codingLab = computed(() => {
  if (props.item.content?.format !== 'coding_lab') return null
  return props.item.content as {
    scenario?: string
    starter_code?: string
    checks?: string[]
  }
})

const audioTranscript = computed(() => {
  if (props.item.content?.format !== 'audio_fallback') return ''
  return String(props.item.content.transcript || '')
})

const showBundleToggle = computed(
  () => !isBundle.value && bundleContent.value && props.bundleItem,
)

function cleanText(value?: string) {
  return stripMarkdownAsterisks(value ?? '')
}
</script>

<template>
  <div class="content-viewer" :class="`content-viewer--${theme}`">
    <div v-if="showBundleToggle" class="content-viewer__toggle">
      <button
        type="button"
        class="toggle-btn"
        :class="{ 'toggle-btn--active': viewMode === 'current' }"
        @click="viewMode = 'current'"
      >
        当前资源（{{ item.resource_type }}）
      </button>
      <button
        type="button"
        class="toggle-btn"
        :class="{ 'toggle-btn--active': viewMode === 'bundle' }"
        @click="viewMode = 'bundle'"
      >
        完整资源包
      </button>
    </div>

    <PedagogicalBundleViewer
      v-if="(isBundle || viewMode === 'bundle') && bundleContent"
      :content="bundleContent"
    />

    <template v-else-if="viewMode === 'current'">
      <n-collapse class="content-accordion" :default-expanded-names="['main']">
        <n-collapse-item v-if="markdownText" name="main" title="讲解文档">
          <pre class="content-markdown">{{ cleanText(markdownText) }}</pre>
        </n-collapse-item>

        <n-collapse-item
          v-else-if="exerciseQuestions.length"
          name="main"
          :title="`分层题库（${exerciseQuestions.length}）`"
        >
          <article v-for="(q, index) in exerciseQuestions" :key="index" class="exercise-row">
            <header>
              <n-tag size="small">{{ q.type || q.level || '题目' }}</n-tag>
              <strong>第 {{ index + 1 }} 题</strong>
            </header>
            <p>{{ cleanText(String(q.question || q.stem || '')) }}</p>
            <ul v-if="q.options?.length">
              <li v-for="opt in q.options" :key="String(opt)">{{ cleanText(String(opt)) }}</li>
            </ul>
            <n-collapse>
              <n-collapse-item title="参考答案与解析" :name="`q-${index}`">
                <pre v-if="q.answer" class="content-code">{{ cleanText(String(q.answer)) }}</pre>
                <p>{{ cleanText(String(q.explanation || '')) }}</p>
              </n-collapse-item>
            </n-collapse>
          </article>
        </n-collapse-item>

        <n-collapse-item v-else-if="mindMap" name="main" title="思维导图">
          <h4>{{ cleanText(mindMap.root || '思维导图') }}</h4>
          <ul>
            <li v-for="child in mindMap.children ?? []" :key="child.label">
              <strong>{{ cleanText(child.label) }}</strong>
              <span v-if="child.note"> — {{ cleanText(child.note) }}</span>
            </li>
          </ul>
        </n-collapse-item>

        <n-collapse-item v-else-if="codingLab" name="main" title="代码实操">
          <p>{{ cleanText(codingLab.scenario) }}</p>
          <h4>Starter Code</h4>
          <pre class="content-code">{{ cleanText(codingLab.starter_code) }}</pre>
          <ul v-if="codingLab.checks?.length">
            <li v-for="check in codingLab.checks" :key="check">{{ cleanText(check) }}</li>
          </ul>
        </n-collapse-item>

        <n-collapse-item v-else-if="audioTranscript" name="main" title="语音讲解文稿">
          <pre class="content-markdown">{{ cleanText(audioTranscript) }}</pre>
        </n-collapse-item>

        <n-collapse-item v-else name="main" title="原始数据">
          <pre class="content-raw">{{ cleanText(JSON.stringify(item.content, null, 2)) }}</pre>
        </n-collapse-item>
      </n-collapse>
    </template>
  </div>
</template>

<style scoped>
.content-viewer {
  display: grid;
  gap: 0.85rem;
}

.content-viewer__toggle {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.toggle-btn {
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
}

.content-viewer--student .toggle-btn {
  border: 1px solid rgba(37, 245, 238, 0.25);
  color: rgba(204, 230, 239, 0.78);
}

.content-viewer--student .toggle-btn--active {
  border-color: rgba(37, 245, 238, 0.55);
  color: #f0faff;
  background: rgba(37, 245, 238, 0.1);
}

.content-viewer--teacher .toggle-btn {
  border: 1px solid rgba(255, 173, 76, 0.25);
  color: rgba(235, 215, 194, 0.75);
}

.content-viewer--teacher .toggle-btn--active {
  border-color: rgba(255, 173, 76, 0.55);
  color: #fff7ec;
  background: rgba(255, 173, 76, 0.12);
}

.content-block {
  padding: 0.75rem 0;
}

.content-markdown,
.content-code,
.content-raw {
  white-space: pre-wrap;
  line-height: 1.6;
  margin: 0;
  padding: 0.85rem;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.22);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.86rem;
  max-height: min(60vh, 520px);
  overflow: auto;
}

.content-viewer--student .content-markdown,
.content-viewer--student .content-code,
.content-viewer--student .content-raw {
  color: #cce6ef;
}

.content-viewer--teacher .content-markdown,
.content-viewer--teacher .content-code,
.content-viewer--teacher .content-raw {
  color: #e7d4bf;
}

.content-hint {
  font-size: 0.88rem;
  margin-bottom: 0.5rem;
}

.content-viewer--student .content-hint {
  color: rgba(125, 165, 182, 0.9);
}

.content-viewer--teacher .content-hint {
  color: rgba(235, 215, 194, 0.6);
}

.exercise-row {
  padding: 0.65rem 0;
  border-bottom: 1px solid rgba(120, 150, 170, 0.12);
}

.exercise-row header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.exercise-row p,
.exercise-row li {
  color: rgba(204, 230, 239, 0.82);
}

.exercise-row ul {
  padding-left: 1.2rem;
}
</style>
