<script setup lang="ts">
import { computed } from 'vue'
import type { KnowledgeDomainDef } from '../../data/teacherKnowledgeCatalog'

const props = defineProps<{
  domains: KnowledgeDomainDef[]
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [keys: string[]]
}>()

const selectedSet = computed(() => new Set(props.modelValue))

function toggle(key: string) {
  const next = new Set(props.modelValue)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  emit('update:modelValue', [...next])
}

function isSelected(key: string) {
  return selectedSet.value.has(key)
}
</script>

<template>
  <div class="kp-picker" aria-label="知识宇宙知识点勾选">
    <p class="kp-picker__intro">从六大学域中勾选知识点，用于创建作业模板或试炼。</p>
    <p v-if="!domains.length" class="kp-picker__empty">知识点目录加载中或暂不可用，请刷新页面重试。</p>
    <section v-for="domain in domains" :key="domain.key" class="kp-domain">
      <header class="kp-domain__head">{{ domain.label }}</header>
      <div class="kp-domain__grid">
        <label
          v-for="point in domain.points"
          :key="point.key"
          class="kp-point"
          :class="{ 'kp-point--active': isSelected(point.key) }"
        >
          <input
            type="checkbox"
            :checked="isSelected(point.key)"
            @change="toggle(point.key)"
          />
          <span>{{ point.label }}</span>
        </label>
      </div>
    </section>
  </div>
</template>

<style scoped>
.kp-picker__intro {
  margin: 0 0 0.35rem;
  color: rgba(255, 237, 213, 0.62);
  font-size: 0.78rem;
}

.kp-picker__empty {
  margin: 0;
  padding: 0.75rem;
  border: 1px dashed rgba(251, 146, 60, 0.35);
  border-radius: 0.5rem;
  color: rgba(252, 211, 77, 0.9);
  font-size: 0.8rem;
}

.kp-picker {
  display: grid;
  gap: 0.85rem;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.kp-domain__head {
  margin: 0 0 0.45rem;
  color: rgba(255, 237, 213, 0.9);
  font-size: 0.82rem;
  font-weight: 680;
}

.kp-domain__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.45rem;
}

.kp-point {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.55rem;
  border: 1px solid rgba(251, 146, 60, 0.18);
  border-radius: 0.4rem;
  background: rgba(15, 23, 42, 0.55);
  color: rgba(255, 247, 237, 0.88);
  font-size: 0.78rem;
  cursor: pointer;
}

.kp-point--active {
  border-color: rgba(251, 191, 36, 0.55);
  background: rgba(251, 146, 60, 0.12);
}

.kp-point input {
  accent-color: #fbbf24;
}
</style>
