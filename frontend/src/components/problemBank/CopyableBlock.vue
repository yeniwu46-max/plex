<script setup lang="ts">
/**
 * 通用「带复制按钮的纯文本/代码块」组件。
 * 用于题目样例输入输出、提交代码等需要一键复制的纯文本场景。
 */
import { ref } from 'vue'
import { NButton, NIcon, useMessage } from 'naive-ui'
import { CopyOutline } from '@vicons/ionicons5'

const props = withDefaults(
  defineProps<{
    content: string
    label?: string
    mono?: boolean
    maxHeight?: string
  }>(),
  { mono: true, maxHeight: '260px' },
)

const message = useMessage()
const copied = ref(false)

async function copy() {
  if (!props.content) return
  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    message.success('已复制到剪贴板')
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    message.error('复制失败，请手动选中文本复制')
  }
}
</script>

<template>
  <div class="copyable-block">
    <div v-if="label" class="copyable-block__label">
      <span>{{ label }}</span>
      <n-button size="tiny" quaternary type="primary" @click="copy">
        <template #icon><n-icon :component="CopyOutline" /></template>
        {{ copied ? '已复制' : '复制' }}
      </n-button>
    </div>
    <pre class="copyable-block__body" :class="{ 'copyable-block__body--mono': mono }" :style="{ maxHeight }"><code>{{ content }}</code></pre>
    <n-button v-if="!label" size="tiny" quaternary type="primary" class="copyable-block__floating-btn" @click="copy">
      <template #icon><n-icon :component="CopyOutline" /></template>
      {{ copied ? '已复制' : '复制' }}
    </n-button>
  </div>
</template>

<style scoped>
.copyable-block {
  position: relative;
  border-radius: 10px;
  border: 1px solid rgba(110, 228, 255, 0.16);
  background: rgba(4, 20, 30, 0.55);
  overflow: hidden;
}

.copyable-block__label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.35em 0.75em;
  font-size: 0.82em;
  color: rgba(217, 246, 255, 0.7);
  border-bottom: 1px solid rgba(110, 228, 255, 0.12);
  background: rgba(37, 245, 238, 0.05);
}

.copyable-block__body {
  margin: 0;
  padding: 0.75em 1em;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.88em;
  line-height: 1.6;
}

.copyable-block__body--mono code {
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.copyable-block__floating-btn {
  position: absolute;
  top: 6px;
  right: 8px;
}
</style>
