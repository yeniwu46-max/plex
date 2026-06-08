<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  accept?: string[]
  multiple?: boolean
  disabled?: boolean
  dropText?: string
}>()

const emit = defineEmits<{
  filesSelected: [files: File[]]
}>()

const isDragOver = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)

function onDragEnter(e: DragEvent) {
  e.preventDefault()
  if (!props.disabled) isDragOver.value = true
}

function onDragLeave(e: DragEvent) {
  e.preventDefault()
  const rel = e.relatedTarget as Node | null
  if (!(e.currentTarget as HTMLElement).contains(rel)) {
    isDragOver.value = false
  }
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  if (props.disabled) return
  const dt = e.dataTransfer
  if (!dt) return
  const files = Array.from(dt.files)
  if (files.length) emit('filesSelected', files)
}

function onInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (files.length) emit('filesSelected', files)
  input.value = ''
}

function triggerInput() {
  if (!props.disabled) inputRef.value?.click()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    triggerInput()
  }
}

const acceptAttr = computed(() => props.accept?.join(',') ?? undefined)

import { computed } from 'vue'
</script>

<template>
  <div
    class="plex-dropzone"
    :class="{
      'plex-dropzone--over': isDragOver,
      'plex-dropzone--disabled': disabled,
    }"
    tabindex="0"
    role="button"
    :aria-label="dropText ?? '点击或拖拽文件到此处上传'"
    @dragenter="onDragEnter"
    @dragleave="onDragLeave"
    @dragover="onDragOver"
    @drop="onDrop"
    @click="triggerInput"
    @keydown="onKeydown"
  >
    <input
      ref="inputRef"
      type="file"
      class="plex-dropzone__input"
      :accept="acceptAttr"
      :multiple="multiple ?? true"
      tabindex="-1"
      @change="onInputChange"
    />

    <span class="plex-dropzone__icon" aria-hidden="true">
      <slot name="icon">⬆</slot>
    </span>

    <p class="plex-dropzone__text">
      {{ isDragOver ? '松开鼠标即可上传' : (dropText ?? '拖拽文件到这里，或点击选择') }}
    </p>

    <p v-if="accept && accept.length" class="plex-dropzone__hint">
      支持 {{ accept.join('、') }}
    </p>

    <button type="button" class="plex-dropzone__btn" :disabled="disabled" @click.stop="triggerInput">
      选择文件
    </button>
  </div>
</template>
