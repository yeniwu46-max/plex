<script setup lang="ts">
import type { StarPathGem } from '../../data/starPathTrail'

const props = defineProps<{
  slots: string[]
  activeIndex: number
  gems?: StarPathGem[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  select: [index: number]
}>()

function gemState(index: number): StarPathGem {
  return props.gems?.[index] ?? (index === props.activeIndex ? 'active' : 'pending')
}

function gemLabel(index: number) {
  const state = gemState(index)
  if (state === 'locked') return '未解锁'
  if (state === 'done') return '已完成'
  if (state === 'active') return '当前'
  return '待挑战'
}

function onSelect(index: number) {
  if (props.disabled || gemState(index) === 'locked') return
  emit('select', index)
}
</script>

<template>
  <nav class="slot-gems" aria-label="试炼小题切换">
    <button
      v-for="(slotId, index) in slots"
      :key="slotId"
      type="button"
      class="slot-gem"
      :class="[
        `slot-gem--${gemState(index)}`,
        { 'slot-gem--selected': index === activeIndex },
      ]"
      :disabled="disabled || gemState(index) === 'locked'"
      :aria-current="index === activeIndex ? 'step' : undefined"
      :aria-label="`第 ${index + 1} 题 ${gemLabel(index)}`"
      @click="onSelect(index)"
    >
      <span class="slot-gem__diamond" aria-hidden="true" />
      <span class="slot-gem__index">s{{ index }}</span>
    </button>
  </nav>
</template>

<style scoped>
.slot-gems {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: center;
  padding: 0.35rem 0;
}

.slot-gem {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-width: 3.4rem;
  min-height: 2.35rem;
  padding: 0.5rem 0.85rem 0.5rem 0.7rem;
  border: 1.5px solid rgba(130, 212, 255, 0.22);
  border-radius: 999px;
  background: rgba(5, 18, 30, 0.88);
  color: rgba(224, 237, 247, 0.88);
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 500;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease,
    background 0.2s ease;
}

.slot-gem:hover:not(:disabled) {
  border-color: rgba(35, 255, 222, 0.52);
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(35, 255, 222, 0.12);
}

.slot-gem--selected {
  border-color: rgba(35, 255, 222, 0.85);
  background: rgba(16, 240, 192, 0.18);
  box-shadow: 0 0 22px rgba(35, 255, 222, 0.32);
  color: #eaffff;
  transform: scale(1.04);
}

.slot-gem--done .slot-gem__diamond {
  background: linear-gradient(135deg, #23ffde, #0891b2);
  box-shadow: 0 0 10px rgba(35, 255, 222, 0.45);
}

.slot-gem--active .slot-gem__diamond,
.slot-gem--selected .slot-gem__diamond {
  background: linear-gradient(135deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 14px rgba(35, 255, 222, 0.55);
}

.slot-gem--locked {
  opacity: 0.42;
  cursor: not-allowed;
}

.slot-gem--locked .slot-gem__diamond {
  background: rgba(125, 135, 145, 0.55);
  box-shadow: none;
}

.slot-gem__diamond {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  transform: rotate(45deg);
  border-radius: 2px;
  background: rgba(130, 212, 255, 0.4);
}

.slot-gem__index {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.95rem;
  letter-spacing: 0.06em;
}
</style>
