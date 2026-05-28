<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { VueMonacoEditor, useMonaco } from '@guolao/vue-monaco-editor'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: string
    readonly?: boolean
    theme?: 'plex-dark' | 'vs-dark' | 'light'
    height?: string
    filename?: string
  }>(),
  {
    language: 'python',
    readonly: false,
    theme: 'plex-dark',
    height: '100%',
    filename: 'main.py',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  ready: []
}>()

const { monacoRef } = useMonaco()
const editorRef = ref()
const isReady = ref(false)

const editorTheme = computed(() => {
  if (props.theme === 'plex-dark') return 'plex-dark'
  return props.theme
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function defineTheme(monaco: any) {
  monaco.editor.defineTheme('plex-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '5a7a6a', fontStyle: 'italic' },
      { token: 'keyword', foreground: '7dd3fc', fontStyle: 'bold' },
      { token: 'string', foreground: '86efac' },
      { token: 'number', foreground: 'fbbf24' },
      { token: 'type', foreground: '34d399' },
      { token: 'function', foreground: '93c5fd' },
    ],
    colors: {
      'editor.background': '#050e1a',
      'editor.foreground': '#e2e8f0',
      'editor.lineHighlightBackground': '#0a1e30',
      'editorLineNumber.foreground': '#2d4a5f',
      'editorLineNumber.activeForeground': '#4ade80',
      'editor.selectionBackground': '#1e4a3a',
      'editor.inactiveSelectionBackground': '#162e24',
      'editorCursor.foreground': '#4ade80',
      'editorIndentGuide.background': '#0f2032',
      'editorIndentGuide.activeBackground': '#1a3548',
      'scrollbarSlider.background': '#1a3040',
      'scrollbarSlider.hoverBackground': '#22c55e33',
      'scrollbarSlider.activeBackground': '#22c55e55',
    },
  })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function handleMount(editor: any) {
  editorRef.value = editor
  isReady.value = true
  emit('ready')
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function handleBeforeMount(monaco: any) {
  defineTheme(monaco)
}

function handleChange(value: string | undefined) {
  emit('update:modelValue', value ?? '')
}

watch(
  () => monacoRef.value,
  (monaco: unknown) => {
    if (monaco) defineTheme(monaco)
  },
)

onBeforeUnmount(() => {
  editorRef.value?.dispose()
})
</script>

<template>
  <div class="plex-code-editor">
    <div class="plex-code-editor__topbar">
      <span class="plex-code-editor__dot plex-code-editor__dot--red" />
      <span class="plex-code-editor__dot plex-code-editor__dot--yellow" />
      <span class="plex-code-editor__dot plex-code-editor__dot--green" />
      <span class="plex-code-editor__filename">{{ filename }}</span>
      <span class="plex-code-editor__lang">{{ language.toUpperCase() }}</span>
    </div>
    <div class="plex-code-editor__body" :style="{ height }">
      <vue-monaco-editor
        :value="modelValue"
        :language="language"
        :theme="editorTheme"
        :read-only="readonly"
        :options="{
          fontSize: 14,
          fontFamily: '\'Consolas\', \'Fira Code\', \'Microsoft YaHei\', monospace',
          lineNumbers: 'on',
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          tabSize: 4,
          insertSpaces: true,
          renderWhitespace: 'boundary',
          bracketPairColorization: { enabled: true },
          smoothScrolling: true,
          cursorSmoothCaretAnimation: 'on',
          padding: { top: 12, bottom: 12 },
          automaticLayout: true,
          fixedOverflowWidgets: true,
        }"
        @mount="handleMount"
        @before-mount="handleBeforeMount"
        @change="handleChange"
      />
    </div>
  </div>
</template>

<style scoped>
.plex-code-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(74, 222, 128, 0.15);
  background: #050e1a;
}

.plex-code-editor__topbar {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 0.85rem;
  background: #060f1c;
  border-bottom: 1px solid rgba(74, 222, 128, 0.1);
  flex-shrink: 0;
}

.plex-code-editor__dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  flex-shrink: 0;
}

.plex-code-editor__dot--red { background: #f87171; }
.plex-code-editor__dot--yellow { background: #fbbf24; }
.plex-code-editor__dot--green { background: #4ade80; }

.plex-code-editor__filename {
  margin-left: 0.35rem;
  color: rgba(226, 232, 240, 0.6);
  font-family: 'Consolas', monospace;
  font-size: 0.78rem;
}

.plex-code-editor__lang {
  margin-left: auto;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
  background: rgba(74, 222, 128, 0.1);
  color: #4ade80;
  font-size: 0.68rem;
  font-family: monospace;
  letter-spacing: 0.04em;
}

.plex-code-editor__body {
  flex: 1;
  min-height: 0;
}
</style>
