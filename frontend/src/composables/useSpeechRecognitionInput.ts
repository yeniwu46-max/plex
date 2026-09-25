import { ref } from 'vue'
import type { MessageApi } from 'naive-ui/es/message'

type SpeechResultItem = {
  isFinal: boolean
  0: { transcript: string }
}

type SpeechRecognitionInstance = {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: { resultIndex: number; results: SpeechResultItem[] }) => void) | null
  onerror: ((event: { error?: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance

function normalizeSpeechText(text: string) {
  return text.replace(/\s+/g, ' ').trim()
}

/** 去掉连续重复的短片段，缓解浏览器重复上报 interim 时的口吃感 */
function dedupeStutter(text: string) {
  const normalized = normalizeSpeechText(text)
  if (!normalized) return ''
  const parts = normalized.split(/\s+/)
  const out: string[] = []
  for (const part of parts) {
    if (out.length && out[out.length - 1] === part) continue
    out.push(part)
  }
  return out.join(' ')
}

function joinBaseAndSpeech(base: string, speech: string) {
  const left = normalizeSpeechText(base)
  const right = normalizeSpeechText(speech)
  if (!left) return right
  if (!right) return left
  return `${left} ${right}`
}

export function useSpeechRecognitionInput(options: {
  getText: () => string
  setText: (value: string) => void
  message?: MessageApi
  lang?: string
}) {
  const listening = ref(false)
  let recognition: SpeechRecognitionInstance | null = null
  let sessionBase = ''

  function resolveCtor(): SpeechRecognitionCtor | null {
    const win = window as Window & {
      SpeechRecognition?: SpeechRecognitionCtor
      webkitSpeechRecognition?: SpeechRecognitionCtor
    }
    return win.SpeechRecognition || win.webkitSpeechRecognition || null
  }

  function applyTranscriptFromResults(results: SpeechResultItem[]) {
    let finals = ''
    let interim = ''
    for (let i = 0; i < results.length; i += 1) {
      const piece = results[i]?.[0]?.transcript ?? ''
      if (!piece) continue
      if (results[i]?.isFinal) finals += piece
      else interim = piece
    }
    const spoken = finals + interim
    options.setText(joinBaseAndSpeech(sessionBase, spoken))
  }

  function finalizeOnStop() {
    const merged = dedupeStutter(options.getText())
    options.setText(merged)
    sessionBase = merged
  }

  function stop() {
    listening.value = false
    try {
      recognition?.stop()
    } catch {
      /* ignore */
    }
    finalizeOnStop()
    recognition = null
  }

  function toggle() {
    if (listening.value) {
      stop()
      return
    }
    const SpeechRecognition = resolveCtor()
    if (!SpeechRecognition) {
      options.message?.warning('当前浏览器不支持语音输入，请改用文字提问')
      return
    }
    sessionBase = normalizeSpeechText(options.getText())
    recognition = new SpeechRecognition()
    recognition.lang = options.lang ?? 'zh-CN'
    recognition.interimResults = true
    recognition.continuous = true
    listening.value = true

    recognition.onresult = (event) => {
      const list = Array.from(event.results) as SpeechResultItem[]
      applyTranscriptFromResults(list)
    }
    recognition.onerror = () => {
      options.message?.error('语音识别失败，请检查麦克风权限')
      listening.value = false
      finalizeOnStop()
      recognition = null
    }
    recognition.onend = () => {
      listening.value = false
      finalizeOnStop()
      recognition = null
    }
    recognition.start()
  }

  return { listening, toggle, stop }
}
