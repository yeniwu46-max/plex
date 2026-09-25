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
import katexPluginImport from '@vscode/markdown-it-katex'
import hljs from 'highlight.js'
import mermaid from 'mermaid'
import MermaidDiagramModal from './MermaidDiagramModal.vue'
import { attachMermaidControls, mermaidDiagramToolbarHtml } from '../../utils/mermaidDiagramControls'
import 'highlight.js/styles/github-dark.css'
import 'katex/dist/katex.min.css'

const props = withDefaults(
  defineProps<{
    content: string
    streaming?: boolean
  }>(),
  { streaming: false },
)

/**
 * `@vscode/markdown-it-katex` is CommonJS and marks its export as `__esModule`.
 * Vite's development dependency optimizer can therefore expose it as
 * `{ default: { default: plugin } }`, while production builds expose the
 * function directly. Normalize both shapes before passing it to markdown-it.
 */
function unwrapDefaultExport<T>(moduleValue: T): T {
  let value: unknown = moduleValue
  const visited = new Set<unknown>()

  while (
    value
    && typeof value === 'object'
    && 'default' in value
    && !visited.has(value)
  ) {
    visited.add(value)
    value = (value as { default: unknown }).default
  }

  if (typeof value !== 'function') {
    throw new TypeError('KaTeX Markdown 插件加载失败')
  }
  return value as T
}

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
md.use(unwrapDefaultExport(katexPluginImport))

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

const mermaidModalOpen = ref(false)
const mermaidModalSvg = ref('')

function openMermaidModal(svgHtml: string) {
  mermaidModalSvg.value = svgHtml
  mermaidModalOpen.value = true
}

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
      wrapper.className = 'mermaid-diagram mermaid-diagram--compact'
      wrapper.setAttribute('role', 'group')
      wrapper.setAttribute('aria-label', '知识图，点击查看全屏')
      wrapper.innerHTML = `
        ${mermaidDiagramToolbarHtml(true)}
        <button type="button" class="mermaid-open-full" data-open-full aria-label="全屏查看知识图">
          <div class="mermaid-viewport" tabindex="-1">
            <div class="mermaid-canvas">${svg}</div>
          </div>
          <span class="mermaid-open-full__badge">点击查看全图</span>
        </button>
      `
      block.replaceWith(wrapper)
      attachMermaidControls(wrapper, { enablePan: false, fitOnMount: true })
      const openBtn = wrapper.querySelector<HTMLButtonElement>('[data-open-full]')
      const openFull = (event: Event) => {
        event.preventDefault()
        event.stopPropagation()
        openMermaidModal(svg)
      }
      openBtn?.addEventListener('click', openFull)
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
  <MermaidDiagramModal v-model:show="mermaidModalOpen" :svg-html="mermaidModalSvg" />
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
  padding: 0.55em 0.65em 0.65em;
  border-radius: 10px;
  background: rgba(4, 20, 30, 0.72);
  border: 1px solid rgba(110, 228, 255, 0.14);
  overflow: hidden;
}

.markdown-body :deep(.mermaid-toolbar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
  flex-wrap: wrap;
}

.markdown-body :deep(.mermaid-toolbar__hint) {
  font-size: 0.75rem;
  color: rgba(180, 220, 235, 0.62);
}

.markdown-body :deep(.mermaid-toolbar__actions) {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.markdown-body :deep(.mermaid-zoom-btn) {
  min-width: 1.85rem;
  height: 1.85rem;
  padding: 0 0.4rem;
  border-radius: 6px;
  border: 1px solid rgba(110, 228, 255, 0.28);
  background: rgba(8, 36, 48, 0.9);
  color: #d9f6ff;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}

.markdown-body :deep(.mermaid-zoom-btn:hover) {
  border-color: rgba(37, 245, 238, 0.55);
  background: rgba(14, 56, 72, 0.95);
}

.markdown-body :deep(.mermaid-zoom-btn--text) {
  font-size: 0.78rem;
  min-width: auto;
  padding: 0 0.55rem;
}

.markdown-body :deep(.mermaid-zoom-label) {
  min-width: 2.6rem;
  text-align: center;
  font-size: 0.78rem;
  color: rgba(210, 240, 250, 0.85);
  font-variant-numeric: tabular-nums;
}

.markdown-body :deep(.mermaid-diagram--compact .mermaid-toolbar__actions) {
  display: none;
}

.markdown-body :deep(.mermaid-open-full) {
  position: relative;
  display: block;
  width: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
  text-align: inherit;
}

.markdown-body :deep(.mermaid-open-full__badge) {
  position: absolute;
  right: 0.55rem;
  bottom: 0.45rem;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  font-size: 0.72rem;
  color: rgba(210, 240, 250, 0.92);
  background: rgba(4, 18, 28, 0.82);
  border: 1px solid rgba(110, 228, 255, 0.22);
  pointer-events: none;
}

.markdown-body :deep(.mermaid-viewport) {
  position: relative;
  max-height: min(75vh, 640px);
  min-height: 240px;
  overflow: auto;
  border-radius: 8px;
  background: rgba(2, 12, 20, 0.45);
  outline: none;
  cursor: inherit;
}

.markdown-body :deep(.mermaid-diagram--compact .mermaid-viewport) {
  max-height: 200px;
  min-height: 140px;
  overflow: hidden;
  pointer-events: none;
}

.markdown-body :deep(.mermaid-canvas) {
  display: inline-block;
  min-width: 100%;
  transform-origin: top left;
}

.markdown-body :deep(.mermaid-diagram svg) {
  max-width: none;
  width: auto;
  height: auto;
  display: block;
  margin: 0 auto;
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
