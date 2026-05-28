<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ScriptStep } from '../types/defense'
import { useScriptProgress } from '../composables/useScriptProgress'
import DemoLink from './DemoLink.vue'

const props = defineProps<{
  steps: ScriptStep[]
  sectionId: string
}>()

const { load, toggle, reset } = useScriptProgress()
const checked = ref<Record<string, boolean>>({})

function key(index: number) {
  return `${props.sectionId}-${index}`
}

onMounted(() => {
  checked.value = load()
})

function onToggle(index: number) {
  checked.value = toggle(key(index))
}
</script>

<template>
  <div class="script-block">
    <div class="script-toolbar">
      <button type="button" class="btn btn--ghost" @click="reset(); checked = {}">重置勾选</button>
    </div>
    <div
      v-for="(step, index) in steps"
      :key="index"
      class="script-step"
    >
      <input
        :id="key(index)"
        type="checkbox"
        :checked="!!checked[key(index)]"
        @change="onToggle(index)"
      />
      <label :for="key(index)">
        <strong>{{ index + 1 }}. {{ step.label }}</strong>
        <span v-if="step.account" class="script-meta">（{{ step.account }}）</span>
        <DemoLink v-if="step.path" :path="step.path" label="演示" />
      </label>
    </div>
  </div>
</template>

<style scoped>
.script-block {
  margin-top: 0.75rem;
}

.script-toolbar {
  margin-bottom: 0.5rem;
}

.script-step label {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.script-meta {
  color: var(--plex-muted);
  font-size: 0.85rem;
}
</style>
