<script setup lang="ts">
/**
 * 洛谷风格标签 chips 展示（增强#3）。
 *
 * `concept`/`difficulty`/`source` 三类标签数量固定较少，始终展示；`topic`
 * （细粒度算法/知识点标签，规则匹配得出，0-N 个）数量不定，参照参考图里
 * "隐藏算法标签"的折叠交互单独收纳。点击任意标签会 emit `tag-click`，由
 * 父组件负责跳转到"按标签筛选"的题目列表视图。
 */
import { computed, ref } from 'vue'
import type { ProblemTag } from '../../api/problemBank'

const props = defineProps<{
  tags: ProblemTag[]
}>()

const emit = defineEmits<{
  (e: 'tag-click', code: string): void
}>()

const expanded = ref(false)

const alwaysVisible = computed(() => props.tags.filter((t) => t.tag_type !== 'topic'))
const collapsible = computed(() => props.tags.filter((t) => t.tag_type === 'topic'))

const TAG_COLOR_FALLBACK = '#2080f0'

function chipStyle(tag: ProblemTag) {
  const color = tag.color || TAG_COLOR_FALLBACK
  return {
    backgroundColor: `${color}26`,
    borderColor: `${color}66`,
    color,
  }
}
</script>

<template>
  <div v-if="tags.length" class="problem-tags">
    <span class="problem-tags__title">标签</span>
    <div class="problem-tags__chips">
      <button
        v-for="tag in alwaysVisible"
        :key="tag.code"
        type="button"
        class="problem-tags__chip"
        :style="chipStyle(tag)"
        @click="emit('tag-click', tag.code)"
      >
        {{ tag.label }}
      </button>
      <template v-if="expanded">
        <button
          v-for="tag in collapsible"
          :key="tag.code"
          type="button"
          class="problem-tags__chip"
          :style="chipStyle(tag)"
          @click="emit('tag-click', tag.code)"
        >
          {{ tag.label }}
        </button>
      </template>
    </div>
    <button v-if="collapsible.length" type="button" class="problem-tags__toggle" @click="expanded = !expanded">
      {{ expanded ? '︿ 隐藏算法标签' : `﹀ 展开算法标签 (${collapsible.length})` }}
    </button>
  </div>
</template>

<style scoped>
.problem-tags {
  display: flex;
  flex-direction: column;
  gap: 0.5em;
}

.problem-tags__title {
  font-size: 0.85em;
  color: rgba(217, 246, 255, 0.55);
}

.problem-tags__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5em;
}

.problem-tags__chip {
  border: 1px solid;
  border-radius: 999px;
  padding: 0.25em 0.85em;
  font-size: 0.8em;
  cursor: pointer;
  background: transparent;
  transition: filter 0.15s ease;
}

.problem-tags__chip:hover {
  filter: brightness(1.25);
}

.problem-tags__toggle {
  align-self: flex-start;
  border: none;
  background: transparent;
  color: rgba(217, 246, 255, 0.45);
  font-size: 0.78em;
  cursor: pointer;
  padding: 0;
}

.problem-tags__toggle:hover {
  color: #5ad9ff;
}
</style>
