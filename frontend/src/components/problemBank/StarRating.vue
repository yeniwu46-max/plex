<script setup lang="ts">
/**
 * 洛谷风格 1-5 星难度展示（5星最难）。映射规则见 REPORT.md 增强篇4：
 * 按 problems.difficulty（0-5，原始字段）夹取到 1-5，difficulty 缺失时退化用 level。
 */
const props = withDefaults(
  defineProps<{
    value: number | null
    compact?: boolean
  }>(),
  { compact: false },
)

const STAR_LABELS: Record<number, string> = {
  1: '入门',
  2: '简单',
  3: '中等',
  4: '较难',
  5: '困难',
}
</script>

<template>
  <span v-if="props.value" class="star-rating" :title="`难度：${STAR_LABELS[props.value] || ''} (${props.value}/5)`">
    <span
      v-for="i in 5"
      :key="i"
      class="star-rating__star"
      :class="{ 'star-rating__star--filled': i <= props.value }"
      >★</span
    >
    <span v-if="!compact" class="star-rating__label">{{ STAR_LABELS[props.value] }}</span>
  </span>
</template>

<style scoped>
.star-rating {
  display: inline-flex;
  align-items: center;
  gap: 0.05em;
  font-size: 0.95em;
}

.star-rating__star {
  color: rgba(217, 246, 255, 0.2);
}

.star-rating__star--filled {
  color: #f0c020;
}

.star-rating__label {
  margin-left: 0.4em;
  font-size: 0.8em;
  color: rgba(217, 246, 255, 0.6);
}
</style>
