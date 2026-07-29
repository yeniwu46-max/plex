<script setup lang="ts">
/**
 * 统一 Markdown 渲染组件：代码高亮（highlight.js）、数学公式（KaTeX）、
 * 思维导图/流程图（mermaid）。全站 AI 输出均经此组件渲染。
 *
 * - `streaming` 为 true 时跳过 mermaid 异步渲染，避免流式期间闪烁；
 * - markdown-it 关闭原始 HTML，防止注入。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import katexPlugin from '@vscode/markdown-it-katex'
import hljs from 'highlight.js'
import mermaid from 'mermaid'
import 'highlight.js/styles/github-dark.css'
import 'katex/dist/katex.min.css'

const props = withDefaults(
  defineProps<{
    content: string
    streaming?: boolean
  }>(),
  { streaming: false },
)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(code: string, lang: string): string {
    if (lang === 'mermaid') {
      return `<pre class="mermaid-source" data-mermaid>${md.utils.escapeHtml(code)}</pre>`
    }
    const language = lang && hljs.getLanguage(lang) ? lang : ''
    try {
      const value = language
        ? hljs.highlight(code, { language }).value
        : hljs.highlightAuto(code).value
      return `<pre class="hljs"><code>${value}</code></pre>`
    } catch {
      return `<pre class="hljs"><code>${md.utils.escapeHtml(code)}</code></pre>`
    }
  },
})
md.use(katexPlugin)

let mermaidReady = false
function ensureMermaid() {
  if (mermaidReady) return
  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'strict',
    themeVariables: {
      primaryColor: '#0b2a38',
      primaryTextColor: '#d9f6ff',
      primaryBorderColor: '#25f5ee',
      lineColor: '#5ad9ff',
      fontSize: '14px',
    },
  })
  mermaidReady = true
}

const container = ref<HTMLElement | null>(null)
const rendered = computed(() => md.render(props.content || ''))
let mermaidSeq = 0

async function renderMermaidBlocks() {
  if (props.streaming || !container.value) return
  const blocks = container.value.querySelectorAll<HTMLElement>('[data-mermaid]')
  if (!blocks.length) return
  ensureMermaid()
  for (const block of Array.from(blocks)) {
    const source = block.textContent ?? ''
    if (!source.trim()) continue
    try {
      const { svg } = await mermaid.render(`md-mermaid-${Date.now()}-${mermaidSeq++}`, source)
      const wrapper = document.createElement('div')
      wrapper.className = 'mermaid-diagram'
      wrapper.innerHTML = svg
      block.replaceWith(wrapper)
    } catch {
      // 图源语法错误时保留源码展示，不阻塞其余内容。
      block.classList.add('mermaid-source--failed')
    }
  }
}

onMounted(() => {
  void nextTick(renderMermaidBlocks)
})

watch(
  () => [props.content, props.streaming] as const,
  async () => {
    await nextTick()
    await renderMermaidBlocks()
  },
)
</script>

<template>
  <div ref="container" class="markdown-body" v-html="rendered" />
</template>

<style scoped>
.markdown-body {
  line-height: 1.7;
  word-break: break-word;
  font-size: 0.95em;
}

.markdown-body :deep(p) {
  margin: 0.35em 0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 0.8em 0 0.4em;
  line-height: 1.35;
  color: inherit;
}

.markdown-body :deep(h1) { font-size: 1.25em; }
.markdown-body :deep(h2) { font-size: 1.15em; }
.markdown-body :deep(h3) { font-size: 1.05em; }

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.4em;
}

.markdown-body :deep(li) {
  margin: 0.2em 0;
}

.markdown-body :deep(code):not(pre code) {
  padding: 0.12em 0.4em;
  border-radius: 4px;
  background: rgba(90, 217, 255, 0.12);
  border: 1px solid rgba(90, 217, 255, 0.18);
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 0.9em;
}

.markdown-body :deep(pre.hljs) {
  margin: 0.6em 0;
  padding: 0.85em 1em;
  border-radius: 10px;
  background: #0d1117;
  border: 1px solid rgba(110, 228, 255, 0.14);
  overflow-x: auto;
  font-size: 0.88em;
  line-height: 1.55;
}

.markdown-body :deep(pre.hljs code) {
  font-family: 'JetBrains Mono', Consolas, monospace;
  background: transparent;
}

.markdown-body :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.3em 0.9em;
  border-left: 3px solid rgba(37, 245, 238, 0.5);
  background: rgba(37, 245, 238, 0.06);
  border-radius: 0 8px 8px 0;
}

.markdown-body :deep(table) {
  margin: 0.6em 0;
  border-collapse: collapse;
  width: 100%;
  font-size: 0.9em;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 0.4em 0.7em;
  border: 1px solid rgba(110, 228, 255, 0.18);
  text-align: left;
}

.markdown-body :deep(th) {
  background: rgba(37, 245, 238, 0.08);
}

.markdown-body :deep(a) {
  color: #5ad9ff;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.markdown-body :deep(hr) {
  margin: 0.8em 0;
  border: none;
  border-top: 1px solid rgba(110, 228, 255, 0.16);
}

.markdown-body :deep(.mermaid-diagram) {
  margin: 0.6em 0;
  padding: 0.75em;
  border-radius: 10px;
  background: rgba(4, 20, 30, 0.72);
  border: 1px solid rgba(110, 228, 255, 0.14);
  overflow-x: auto;
}

.markdown-body :deep(.mermaid-diagram svg) {
  max-width: 100%;
  height: auto;
}

.markdown-body :deep(.mermaid-source) {
  margin: 0.6em 0;
  padding: 0.85em 1em;
  border-radius: 10px;
  background: #0d1117;
  border: 1px dashed rgba(110, 228, 255, 0.25);
  font-size: 0.85em;
  overflow-x: auto;
  white-space: pre-wrap;
}

.markdown-body :deep(.katex-display) {
  margin: 0.6em 0;
  overflow-x: auto;
}
</style>
