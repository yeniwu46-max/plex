export const MERMAID_ZOOM_MIN = 0.35
export const MERMAID_ZOOM_MAX = 4
export const MERMAID_ZOOM_STEP = 0.2

export function clampMermaidZoom(value: number) {
  return Math.min(MERMAID_ZOOM_MAX, Math.max(MERMAID_ZOOM_MIN, Math.round(value * 100) / 100))
}

export function readSvgSize(svg: SVGSVGElement) {
  const viewBox = svg.viewBox?.baseVal
  const width = Number(svg.getAttribute('width')) || viewBox?.width || svg.clientWidth || 640
  const height = Number(svg.getAttribute('height')) || viewBox?.height || svg.clientHeight || 360
  return {
    width: Math.max(1, width),
    height: Math.max(1, height),
  }
}

export function svgToPngBlob(svg: SVGSVGElement): Promise<Blob> {
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

export function computeMermaidFitScale(viewport: HTMLElement, width: number, height: number) {
  const pad = 20
  const vw = Math.max(80, viewport.clientWidth - pad)
  const vh = Math.max(80, viewport.clientHeight - pad)
  const fit = Math.min(vw / width, vh / height)
  return clampMermaidZoom(Math.min(MERMAID_ZOOM_MAX, Math.max(MERMAID_ZOOM_MIN, fit)))
}

export function downloadPngBlob(blob: Blob, filename = '知识图.png') {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

export type MermaidControlsOptions = {
  enablePan?: boolean
  fitOnMount?: boolean
}

/** 按钮/滚轮缩放、可选拖拽平移、初始适应视口、复制与下载图片。 */
export function attachMermaidControls(root: HTMLElement, options: MermaidControlsOptions = {}) {
  const { enablePan = false, fitOnMount = true } = options
  const viewport = root.querySelector<HTMLElement>('.mermaid-viewport')
  const canvas = root.querySelector<HTMLElement>('.mermaid-canvas')
  const label = root.querySelector<HTMLElement>('[data-zoom-label]')
  const btnIn = root.querySelector<HTMLButtonElement>('[data-zoom-in]')
  const btnOut = root.querySelector<HTMLButtonElement>('[data-zoom-out]')
  const btnReset = root.querySelector<HTMLButtonElement>('[data-zoom-reset]')
  const btnCopy = root.querySelector<HTMLButtonElement>('[data-copy-image]')
  const btnDownload = root.querySelector<HTMLButtonElement>('[data-download-image]')
  if (!viewport || !canvas) return () => {}

  let scale = 1
  let fitScale = 1
  const base = { width: 0, height: 0 }
  let panX = 0
  let panY = 0
  let dragging = false
  let dragStartX = 0
  let dragStartY = 0
  let panStartX = 0
  let panStartY = 0

  const measureBase = () => {
    const svg = canvas.querySelector('svg')
    if (!svg) return
    canvas.style.zoom = ''
    canvas.style.transform = ''
    canvas.style.width = ''
    canvas.style.height = ''
    const size = readSvgSize(svg)
    base.width = size.width
    base.height = size.height
    fitScale = computeMermaidFitScale(viewport, base.width, base.height)
  }

  const apply = () => {
    const style = canvas.style as CSSStyleDeclaration & { zoom?: string }
    const pan = enablePan && (panX !== 0 || panY !== 0) ? ` translate(${panX}px, ${panY}px)` : ''
    if ('zoom' in style || 'zoom' in document.documentElement.style) {
      style.zoom = String(scale)
      canvas.style.transform = pan ? pan.trim() : ''
      canvas.style.width = ''
      canvas.style.height = ''
    } else {
      canvas.style.removeProperty('zoom')
      canvas.style.transformOrigin = 'top left'
      canvas.style.transform = `scale(${scale})${pan}`
      if (base.width && base.height) {
        canvas.style.width = `${base.width * scale}px`
        canvas.style.height = `${base.height * scale}px`
      }
    }
    if (label) label.textContent = `${Math.round(scale * 100)}%`
    root.dataset.zoomed = scale === 1 ? '0' : '1'
  }

  const setScale = (next: number) => {
    scale = clampMermaidZoom(next)
    apply()
  }

  const onWheel = (event: WheelEvent) => {
    event.preventDefault()
    const delta = event.deltaY > 0 ? -MERMAID_ZOOM_STEP : MERMAID_ZOOM_STEP
    setScale(scale + delta)
  }

  btnIn?.addEventListener('click', () => setScale(scale + MERMAID_ZOOM_STEP))
  btnOut?.addEventListener('click', () => setScale(scale - MERMAID_ZOOM_STEP))
  btnReset?.addEventListener('click', () => {
    panX = 0
    panY = 0
    setScale(fitScale)
  })

  viewport.addEventListener('wheel', onWheel, { passive: false })

  const onPointerDown = (event: PointerEvent) => {
    if (!enablePan || event.button !== 0) return
    dragging = true
    dragStartX = event.clientX
    dragStartY = event.clientY
    panStartX = panX
    panStartY = panY
    viewport.setPointerCapture(event.pointerId)
    viewport.style.cursor = 'grabbing'
  }

  const onPointerMove = (event: PointerEvent) => {
    if (!dragging) return
    panX = panStartX + (event.clientX - dragStartX)
    panY = panStartY + (event.clientY - dragStartY)
    apply()
  }

  const onPointerUp = (event: PointerEvent) => {
    if (!dragging) return
    dragging = false
    viewport.style.cursor = enablePan ? 'grab' : ''
    try {
      viewport.releasePointerCapture(event.pointerId)
    } catch {
      /* ignore */
    }
  }

  if (enablePan) {
    viewport.style.cursor = 'grab'
    viewport.addEventListener('pointerdown', onPointerDown)
    viewport.addEventListener('pointermove', onPointerMove)
    viewport.addEventListener('pointerup', onPointerUp)
    viewport.addEventListener('pointercancel', onPointerUp)
  }

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
        downloadPngBlob(blob)
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

  btnDownload?.addEventListener('click', async () => {
    const svg = canvas.querySelector('svg')
    if (!svg || !btnDownload) return
    const original = btnDownload.textContent
    btnDownload.disabled = true
    try {
      const blob = await svgToPngBlob(svg)
      downloadPngBlob(blob)
      btnDownload.textContent = '已保存'
    } catch {
      btnDownload.textContent = '保存失败'
    } finally {
      window.setTimeout(() => {
        btnDownload.textContent = original
        btnDownload.disabled = false
      }, 1600)
    }
  })

  measureBase()
  if (fitOnMount) setScale(fitScale)
  else apply()

  return () => {
    viewport.removeEventListener('wheel', onWheel)
    if (enablePan) {
      viewport.removeEventListener('pointerdown', onPointerDown)
      viewport.removeEventListener('pointermove', onPointerMove)
      viewport.removeEventListener('pointerup', onPointerUp)
      viewport.removeEventListener('pointercancel', onPointerUp)
    }
  }
}

export function mermaidDiagramToolbarHtml(compact = false) {
  const hint = compact
    ? '点击打开全屏知识图'
    : '滚轮或按钮缩放，可拖动平移'
  return `
    <div class="mermaid-toolbar">
      <span class="mermaid-toolbar__hint">${hint}</span>
      <div class="mermaid-toolbar__actions">
        <button type="button" class="mermaid-zoom-btn" data-zoom-out aria-label="缩小">−</button>
        <span class="mermaid-zoom-label" data-zoom-label>100%</span>
        <button type="button" class="mermaid-zoom-btn" data-zoom-in aria-label="放大">+</button>
        <button type="button" class="mermaid-zoom-btn mermaid-zoom-btn--text" data-zoom-reset>适应</button>
        <button type="button" class="mermaid-zoom-btn mermaid-zoom-btn--text" data-copy-image>复制图片</button>
        <button type="button" class="mermaid-zoom-btn mermaid-zoom-btn--text" data-download-image>保存图片</button>
      </div>
    </div>
  `
}
