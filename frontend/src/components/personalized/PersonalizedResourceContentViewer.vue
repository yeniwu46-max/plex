<script setup lang="ts">
import { computed, ref } from 'vue'
import { NCollapse, NCollapseItem, NTag } from 'naive-ui'
import PedagogicalBundleViewer, {
  type PedagogicalBundleContent,
} from '../student/PedagogicalBundleViewer.vue'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import type { PersonalizedResource } from '../../api/personalizedResources'

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
  const content = props.item.content as Record<string, unknown> | string | null | undefined
  if (content && typeof content === 'object') {
    if (typeof content.markdown === 'string' && content.markdown.trim()) return content.markdown
    if (typeof content.body === 'string' && content.body.trim()) return content.body
    if (typeof content.text === 'string' && content.text.trim()) return content.text
  }
  if (typeof content === 'string' && content.trim()) return content
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
  const format = props.item.content?.format
  if (format !== 'audio_fallback' && format !== 'audio') return ''
  return String(props.item.content.transcript || '')
})

const audioUrl = computed(() =>
  props.item.resource_type === 'audio_explanation' ? props.item.content_url || '' : '',
)

const videoScript = computed(() => {
  const format = props.item.content?.format
  if (format !== 'video' && format !== 'video_script') return ''
  return String(props.item.content.script || '')
})

const videoUrl = computed(() =>
  props.item.resource_type === 'video_lesson' ? props.item.content_url || '' : '',
)

const fallbackMarkdown = computed(() => {
  if (markdownText.value || codingLab.value || mindMap.value || exerciseQuestions.value.length) return ''
  if (audioTranscript.value || videoScript.value || isBundle.value) return ''
  const reason = String(props.item.recommendation_reason || '').trim()
  const title = String(props.item.title || '学习资料').trim()
  return [
    `# ${title}`,
    '',
    reason || '本资源正文暂未完整入库，可先阅读下方说明，或使用下载按钮获取文件。',
    '',
    `- 知识点：${props.item.knowledge_label || props.item.knowledge_key || '未标注'}`,
    `- 类型：${props.item.resource_type}`,
  ].join('\n')
})

const showBundleToggle = computed(
  () => !isBundle.value && bundleContent.value && props.bundleItem,
)

function cleanText(value?: string) {
  return (value ?? '').trim()
}

/** 将 tree JSON 转成 mermaid mindmap 源码，交给 MarkdownRenderer 可视化。 */
const mindMapMermaid = computed(() => {
  const map = mindMap.value
  if (!map) return ''
  const sanitize = (text?: string) =>
    (text ?? '').replace(/[()[\]{}"`]/g, ' ').replace(/\s+/g, ' ').trim() || '节点'
  const lines = ['mindmap', `  root((${sanitize(map.root || '思维导图')}))`]
  for (const child of map.children ?? []) {
    lines.push(`    ${sanitize(child.label)}`)
    if (child.note) lines.push(`      ${sanitize(child.note)}`)
  }
  return '```mermaid\n' + lines.join('\n') + '\n```'
})

function fencedCode(code?: string, lang = 'python') {
  return '```' + lang + '\n' + (code ?? '').trim() + '\n```'
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
        当前资源 · {{ item.resource_type }}
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
          <div class="content-rendered">
            <MarkdownRenderer :content="markdownText" />
          </div>
        </n-collapse-item>

        <n-collapse-item
          v-else-if="exerciseQuestions.length"
          name="main"
          :title="`分层题库 · ${exerciseQuestions.length} 题`"
        >
          <article v-for="(q, index) in exerciseQuestions" :key="index" class="exercise-row">
            <header>
              <n-tag size="small">{{ q.type || q.level || '题目' }}</n-tag>
              <strong>第 {{ index + 1 }} 题</strong>
            </header>
            <MarkdownRenderer :content="cleanText(String(q.question || q.stem || ''))" />
            <ul v-if="q.options?.length">
              <li v-for="opt in q.options" :key="String(opt)">{{ cleanText(String(opt)) }}</li>
            </ul>
            <n-collapse>
              <n-collapse-item title="参考答案与解析" :name="`q-${index}`">
                <MarkdownRenderer
                  v-if="q.answer"
                  :content="fencedCode(String(q.answer))"
                />
                <MarkdownRenderer :content="cleanText(String(q.explanation || ''))" />
              </n-collapse-item>
            </n-collapse>
          </article>
        </n-collapse-item>

        <n-collapse-item v-else-if="mindMap" name="main" title="思维导图">
          <MarkdownRenderer v-if="mindMapMermaid" :content="mindMapMermaid" />
          <details class="content-outline">
            <summary>大纲视图</summary>
            <h4>{{ cleanText(mindMap.root || '思维导图') }}</h4>
            <ul>
              <li v-for="child in mindMap.children ?? []" :key="child.label">
                <strong>{{ cleanText(child.label) }}</strong>
                <span v-if="child.note"> — {{ cleanText(child.note) }}</span>
              </li>
            </ul>
          </details>
        </n-collapse-item>

        <n-collapse-item v-else-if="codingLab" name="main" title="代码实操">
          <MarkdownRenderer :content="cleanText(codingLab.scenario)" />
          <h4>Starter Code</h4>
          <MarkdownRenderer :content="fencedCode(codingLab.starter_code)" />
          <ul v-if="codingLab.checks?.length">
            <li v-for="check in codingLab.checks" :key="check">{{ cleanText(check) }}</li>
          </ul>
        </n-collapse-item>

        <n-collapse-item v-else-if="audioTranscript" name="main" title="语音讲解">
          <div v-if="audioUrl" class="audio-player">
            <audio controls preload="metadata" :src="audioUrl">
              当前浏览器不支持音频播放，可查看下方文稿。
            </audio>
            <small>由语音合成生成 · 可拖动进度条跟读</small>
          </div>
          <p v-else class="content-hint">语音文件生成中或暂不可用，先阅读文稿：</p>
          <div class="content-rendered">
            <MarkdownRenderer :content="audioTranscript" />
          </div>
        </n-collapse-item>

        <n-collapse-item v-else-if="videoScript || videoUrl" name="main" title="教学短视频">
          <div v-if="videoUrl" class="video-player">
            <video controls preload="metadata" :src="videoUrl">
              当前浏览器不支持视频播放。
            </video>
            <small>由多模态生成模型制作 · 约 15–30 秒</small>
          </div>
          <p v-else class="content-hint">视频仍在生成或暂不可用，先看分镜脚本：</p>
          <div class="content-rendered">
            <MarkdownRenderer :content="videoScript" />
          </div>
        </n-collapse-item>

        <n-collapse-item v-else-if="fallbackMarkdown" name="main" title="资料概要">
          <div class="content-rendered">
            <MarkdownRenderer :content="fallbackMarkdown" />
          </div>
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

.content-rendered {
  max-height: min(60vh, 520px);
  overflow: auto;
  padding-right: 0.35rem;
}

.audio-player {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.audio-player audio {
  width: 100%;
  border-radius: 10px;
}

.audio-player small {
  color: rgba(150, 185, 200, 0.75);
  font-size: 0.75rem;
}

.video-player {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.video-player video {
  width: 100%;
  max-height: 360px;
  border-radius: 12px;
  background: #000;
}

.video-player small {
  color: rgba(150, 185, 200, 0.75);
  font-size: 0.75rem;
}

.content-outline {
  margin-top: 0.6rem;
  font-size: 0.88rem;
}

.content-outline summary {
  cursor: pointer;
  color: rgba(204, 230, 239, 0.7);
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
