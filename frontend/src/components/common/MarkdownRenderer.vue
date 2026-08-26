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

const ZOOM_MIN = 0.75
const ZOOM_MAX = 2.5
const ZOOM_STEP = 0.25

function clampZoom(value: number) {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(value * 100) / 100))
}

function readSvgSize(svg: SVGSVGElement) {
  const viewBox = svg.viewBox?.baseVal
  const width = Number(svg.getAttribute('width')) || viewBox?.width || svg.clientWidth || 640
  const height = Number(svg.getAttribute('height')) || viewBox?.height || svg.clientHeight || 360
  return {
    width: Math.max(1, width),
    height: Math.max(1, height),
  }
}

/** 将 Mermaid SVG 栅格化为 PNG，供剪贴板复制。 */
function svgToPngBlob(svg: SVGSVGElement): Promise<Blob> {
  const { width, height } = readSvgSize(svg)
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  if (!clone.getAttribute('width')) clone.setAttribute('width', String(width))
  if (!clone.getAttribute('height')) clone.setAttribute('height', String(height))
  const xml = new XMLSerializer().serializeToString(clone)
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(xml)}`
  const pixelRatio = Math.min(2, window.devicePixelRatio || 1)

  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = Math.ceil(width * pixelRatio)
      canvas.height = Math.ceil(height * pixelRatio)
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('canvas_unavailable'))
        return
      }
      ctx.fillStyle = '#04141e'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
      ctx.drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('png_encode_failed'))),
        'image/png',
      )
    }
    img.onerror = () => reject(new Error('svg_rasterize_failed'))
    img.src = url
  })
}

/** 按钮整体缩放 + 复制图片（不用滚轮）。 */
function attachMermaidControls(root: HTMLElement) {
  const viewport = root.querySelector<HTMLElement>('.mermaid-viewport')
  const canvas = root.querySelector<HTMLElement>('.mermaid-canvas')
  const label = root.querySelector<HTMLElement>('[data-zoom-label]')
  const btnIn = root.querySelector<HTMLButtonElement>('[data-zoom-in]')
  const btnOut = root.querySelector<HTMLButtonElement>('[data-zoom-out]')
  const btnReset = root.querySelector<HTMLButtonElement>('[data-zoom-reset]')
  const btnCopy = root.querySelector<HTMLButtonElement>('[data-copy-image]')
  if (!viewport || !canvas) return

  let scale = 1
  const base = { width: 0, height: 0 }

  const measureBase = () => {
    const svg = canvas.querySelector('svg')
    if (!svg) return
    // 先清缩放再量原始尺寸，避免叠加误差
    canvas.style.zoom = ''
    canvas.style.transform = ''
    canvas.style.width = ''
    canvas.style.height = ''
    const size = readSvgSize(svg)
    base.width = size.width
    base.height = size.height
  }

  const apply = () => {
    // CSS zoom：整图等比放大，布局占位同步变大，视口内滚动查看
    const style = canvas.style as CSSStyleDeclaration & { zoom?: string }
    if ('zoom' in style || 'zoom' in document.documentElement.style) {
      style.zoom = String(scale)
      canvas.style.transform = ''
      canvas.style.width = ''
      canvas.style.height = ''
    } else {
      canvas.style.removeProperty('zoom')
      canvas.style.transformOrigin = 'top left'
      canvas.style.transform = `scale(${scale})`
      if (base.width && base.height) {
        canvas.style.width = `${base.width * scale}px`
        canvas.style.height = `${base.height * scale}px`
      }
    }
    if (label) label.textContent = `${Math.round(scale * 100)}%`
    root.dataset.zoomed = scale === 1 ? '0' : '1'
  }

  const setScale = (next: number) => {
    scale = clampZoom(next)
    apply()
  }

  measureBase()
  btnIn?.addEventListener('click', () => setScale(scale + ZOOM_STEP))
  btnOut?.addEventListener('click', () => setScale(scale - ZOOM_STEP))
  btnReset?.addEventListener('click', () => setScale(1))

  btnCopy?.addEventListener('click', async () => {
    const svg = canvas.querySelector('svg')
    if (!svg || !btnCopy) return
    const original = btnCopy.textContent
    btnCopy.disabled = true
    try {
      const blob = await svgToPngBlob(svg)
      if (navigator.clipboard && 'ClipboardItem' in window) {
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
      } else {
        // 不支持剪贴板图片时降级为下载
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = '知识图.png'
        link.click()
        URL.revokeObjectURL(link.href)
      }
      btnCopy.textContent = '已复制'
    } catch {
      btnCopy.textContent = '复制失败'
    } finally {
      window.setTimeout(() => {
        btnCopy.textContent = original
        btnCopy.disabled = false
      }, 1600)
    }
  })

  apply()
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
      wrapper.className = 'mermaid-diagram'
      wrapper.setAttribute('role', 'group')
      wrapper.setAttribute('aria-label', '知识图，可整体缩放')
      wrapper.innerHTML = `
        <div class="mermaid-toolbar">
          <span class="mermaid-toolbar__hint">使用按钮整体放大缩小</span>
          <div class="mermaid-toolbar__actions">
            <button type="button" class="mermaid-zoom-btn" data-zoom-out aria-label="缩小">−</button>
            <span class="mermaid-zoom-label" data-zoom-label>100%</span>
            <button type="button" class="mermaid-zoom-btn" data-zoom-in aria-label="放大">+</button>
            <button type="button" class="mermaid-zoom-btn mermaid-zoom-btn--text" data-zoom-reset>重置</button>
            <button type="button" class="mermaid-zoom-btn mermaid-zoom-btn--text" data-copy-image>复制图片</button>
          </div>
        </div>
        <div class="mermaid-viewport" tabindex="0">
          <div class="mermaid-canvas">${svg}</div>
        </div>
      `
      block.replaceWith(wrapper)
      attachMermaidControls(wrapper)
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

.markdown-body :deep(.mermaid-viewport) {
  position: relative;
  max-height: min(70vh, 560px);
  min-height: 180px;
  overflow: auto;
  border-radius: 8px;
  background: rgba(2, 12, 20, 0.45);
  outline: none;
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
