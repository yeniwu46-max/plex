import { computed, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

export const MESSENGER_SESSION_LIMIT = 5

export type PersistedChatMessage = {
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
  stageLabel?: string
  illustration?: { url: string; caption?: string }
  knowledge?: import('../api/rag').MessengerKnowledge | null
  questionPick?: import('../api/agentService').MessengerQuickActionResult['question_pick']
  artifact?: 'document' | 'graph'
  downloadName?: string
}

export type MessengerChatSession = {
  id: string
  name: string
  createdAt: number
  updatedAt: number
  lastActiveAt: number
  messages: PersistedChatMessage[]
}

function defaultSessionName(index: number) {
  return index <= 1 ? '对话 1' : `对话 ${index}`
}

function storageKey(userId: number | undefined) {
  return `a3_messenger_sessions_${userId ?? 'guest'}`
}

function newSession(index: number): MessengerChatSession {
  const now = Date.now()
  return {
    id: `ms-${now}-${Math.random().toString(36).slice(2, 8)}`,
    name: defaultSessionName(index),
    createdAt: now,
    updatedAt: now,
    lastActiveAt: now,
    messages: [],
  }
}

export function useMessengerChatSessions() {
  const auth = useAuthStore()
  const sessions = ref<MessengerChatSession[]>([])
  const activeSessionId = ref('')
  const hydrated = ref(false)

  function load() {
    hydrated.value = false
    try {
      const raw = localStorage.getItem(storageKey(auth.profile?.id))
      if (raw) {
        const parsed = JSON.parse(raw) as MessengerChatSession[]
        if (Array.isArray(parsed) && parsed.length) {
          sessions.value = parsed.slice(0, MESSENGER_SESSION_LIMIT)
          activeSessionId.value = sessions.value[0]?.id ?? ''
          hydrated.value = true
          return
        }
      }
    } catch {
      /* ignore corrupt cache */
    }
    const first = newSession(1)
    sessions.value = [first]
    activeSessionId.value = first.id
    hydrated.value = true
    persist()
  }

  function persist() {
    if (!hydrated.value) return
    localStorage.setItem(storageKey(auth.profile?.id), JSON.stringify(sessions.value))
  }

  const activeSession = computed(() => sessions.value.find((s) => s.id === activeSessionId.value) ?? null)

  const canCreateSession = computed(() => sessions.value.length < MESSENGER_SESSION_LIMIT)

  function touchSession(id: string) {
    const session = sessions.value.find((s) => s.id === id)
    if (!session) return
    session.lastActiveAt = Date.now()
    session.updatedAt = Date.now()
  }

  function switchSession(id: string) {
    if (!sessions.value.some((s) => s.id === id)) return
    activeSessionId.value = id
    touchSession(id)
    persist()
  }

  function createSession() {
    if (!canCreateSession.value) return null
    const session = newSession(sessions.value.length + 1)
    sessions.value = [...sessions.value, session]
    activeSessionId.value = session.id
    persist()
    return session
  }

  function renameSession(id: string, name: string) {
    const trimmed = name.trim()
    if (!trimmed) return false
    const session = sessions.value.find((s) => s.id === id)
    if (!session) return false
    session.name = trimmed.slice(0, 40)
    session.updatedAt = Date.now()
    persist()
    return true
  }

  function setSessionMessages(id: string, messages: PersistedChatMessage[]) {
    const session = sessions.value.find((s) => s.id === id)
    if (!session) return
    session.messages = messages.map((m) => ({
      ...m,
      streaming: false,
      stageLabel: undefined,
    }))
    session.updatedAt = Date.now()
    session.lastActiveAt = Date.now()
    persist()
  }

  watch(
    () => auth.profile?.id,
    () => load(),
    { immediate: true },
  )

  return {
    sessions,
    activeSessionId,
    activeSession,
    canCreateSession,
    hydrated,
    load,
    persist,
    switchSession,
    createSession,
    renameSession,
    setSessionMessages,
    touchSession,
  }
}
