import { storageKeys, type ApiEnvelope } from './http'

/** 后端 SSE 事件契约（与 llm_stream.sse_event 对应）。 */
export interface SseStreamEvent {
  type: 'delta' | 'stage' | 'done' | 'error' | 'illustration'
  text?: string
  stage?: string
  label?: string
  message?: string
  illustration?: { url: string; caption?: string }
  [key: string]: unknown
}

export interface SseStreamHandlers {
  onDelta?: (text: string) => void
  onStage?: (stage: string, label: string) => void
  onDone?: (event: SseStreamEvent) => void
  onIllustration?: (illustration: { url: string; caption?: string }) => void
  signal?: AbortSignal
  /**
   * 收到 done 后立刻结束 await（后台继续读 illustration）。
   * 避免生图等尾帧阻塞前端「对话完成」状态。
   */
  settleOnDone?: boolean
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api'

/**
 * 向后端 SSE 端点发起 POST 并逐帧回调。
 *
 * 401/400 等错误会在流式开始前以普通 JSON 返回，此时抛出携带后端
 * message 的 Error，调用方可复用现有错误气泡逻辑。
 */
export async function postSseStream(
  path: string,
  body: Record<string, unknown>,
  handlers: SseStreamHandlers,
): Promise<SseStreamEvent | null> {
  const token = localStorage.getItem(storageKeys.access)
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: handlers.signal,
  })

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('text/event-stream')) {
    // 流式开始前的失败（安全拦截、参数错误、鉴权失败）走普通 JSON。
    let message = `请求失败（${response.status}）`
    try {
      const payload = (await response.json()) as ApiEnvelope
      if (payload?.message) message = payload.message
    } catch {
      /* keep fallback message */
    }
    throw new Error(message)
  }
  if (!response.body) throw new Error('当前浏览器不支持流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let doneEvent: SseStreamEvent | null = null
  const settleRef: { current: ((event: SseStreamEvent | null) => void) | null } = { current: null }
  const earlyPromise =
    handlers.settleOnDone
      ? new Promise<SseStreamEvent | null>((resolve) => {
          settleRef.current = resolve
        })
      : null

  const dispatch = (frame: string) => {
    const data = frame
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('')
    if (!data) return
    let event: SseStreamEvent
    try {
      event = JSON.parse(data) as SseStreamEvent
    } catch {
      return
    }
    if (event.type === 'delta' && typeof event.text === 'string') {
      handlers.onDelta?.(event.text)
    } else if (event.type === 'stage') {
      handlers.onStage?.(String(event.stage ?? ''), String(event.label ?? ''))
    } else if (event.type === 'done') {
      doneEvent = event
      handlers.onDone?.(event)
      settleRef.current?.(event)
      settleRef.current = null
    } else if (event.type === 'illustration' && event.illustration?.url) {
      handlers.onIllustration?.(event.illustration)
    } else if (event.type === 'error') {
      throw new Error(event.message || '对话流中断')
    }
  }

  const pump = (async () => {
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let boundary = buffer.indexOf('\n\n')
        while (boundary >= 0) {
          dispatch(buffer.slice(0, boundary))
          buffer = buffer.slice(boundary + 2)
          boundary = buffer.indexOf('\n\n')
        }
      }
      if (buffer.trim()) dispatch(buffer)
    } finally {
      settleRef.current?.(doneEvent)
      settleRef.current = null
    }
    return doneEvent
  })()

  if (earlyPromise) {
    // 文字完成后立刻返回；illustration 回调仍会在后台触发
    void pump.catch(() => undefined)
    return earlyPromise
  }
  return pump
}
