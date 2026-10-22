<script setup lang="ts">
import { NInputNumber, NSelect } from 'naive-ui'
import type { AuthoringForm } from '../../utils/counterexampleAuthoring'
defineProps<{ model: AuthoringForm['output']; output?: boolean; disabled: boolean; prefix: string }>()
const kinds = [{ label: '整数', value: 'integer' }, { label: '整数数组', value: 'integer_array' }]
</script>
<template>
  <div class="contract-fields">
    <div><label :for="`${prefix}-type`">{{ output ? '输出' : '输入' }}类型</label>
      <n-select filterable :input-props="{ id: `${prefix}-type` }" v-model:value="model.type" :disabled="disabled" :options="output ? [...kinds, { label: '布尔值', value: 'boolean' }] : kinds" /></div>
    <template v-if="model.type !== 'boolean'">
      <div><label :for="`${prefix}-minimum`">最小整数</label><n-input-number :input-props="{ id: `${prefix}-minimum` }" :value="model.minimum" :disabled="disabled" :precision="0" :min="output ? -1e12 : -1e6" :max="output ? 1e12 : 1e6" @update:value="value => model.minimum = value ?? 0" /></div>
      <div><label :for="`${prefix}-maximum`">最大整数</label><n-input-number :input-props="{ id: `${prefix}-maximum` }" :value="model.maximum" :disabled="disabled" :precision="0" :min="output ? -1e12 : -1e6" :max="output ? 1e12 : 1e6" @update:value="value => model.maximum = value ?? 0" /></div>
    </template>
    <template v-if="model.type === 'integer_array'">
      <div><label :for="`${prefix}-min-items`">最少元素</label><n-input-number :input-props="{ id: `${prefix}-min-items` }" :value="model.min_items" :disabled="disabled" :precision="0" :min="0" :max="128" @update:value="value => model.min_items = value ?? 0" /></div>
      <div><label :for="`${prefix}-max-items`">最多元素</label><n-input-number :input-props="{ id: `${prefix}-max-items` }" :value="model.max_items" :disabled="disabled" :precision="0" :min="0" :max="128" @update:value="value => model.max_items = value ?? 0" /></div>
    </template>
  </div>
</template>
<style scoped>
.contract-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(160px, 100%), 1fr)); gap: 12px; }
.contract-fields label { display: block; margin: 0 0 6px; font-size: 13px; }
</style>
