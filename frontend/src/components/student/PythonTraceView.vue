<script setup lang="ts">
import type { PythonTrace } from '../../api/pythonTrace'
defineProps<{ trace: PythonTrace }>()
const outcomes = { completed: '本次执行结束', runtime_error: '在报错处停止', step_limit: '达到 80 步上限', output_limit: '达到输出上限' }
</script>

<template>
  <details class="python-trace-view" open>
    <summary>逐行执行记录 · {{ outcomes[trace.outcome] }}</summary>
    <p>变量快照记录在对应行执行前；长内容及部分变量会省略。本次自测不代表正式判题通过。</p>
    <p v-if="trace.code_normalized">本次执行已将全角代码符号规范为半角。</p>
    <div class="python-trace-view__scroll" tabindex="0" aria-label="逐行变量快照，可滚动">
      <table>
        <caption>{{ trace.steps.length }} 条快照 · Python {{ trace.python_version }}</caption>
        <thead><tr><th scope="col">步</th><th scope="col">行</th><th scope="col">执行前的变量预览</th></tr></thead>
        <tbody><tr v-for="(step, index) in trace.steps" :key="index">
          <td>{{ index + 1 }}</td><td>{{ step.line }}</td>
          <td><div v-for="(value, name) in step.variables.values" :key="name"><code>{{ name }} = {{ value }}</code></div>
            <span v-if="!Object.keys(step.variables.values).length">尚无可显示变量</span>
            <small v-if="step.variables.omitted">另有 {{ step.variables.omitted }} 个变量未显示</small>
          </td>
        </tr></tbody>
      </table>
    </div>
    <p><strong>{{ trace.completed ? '结束时' : '停止时' }}的变量预览</strong></p>
    <div v-for="(value, name) in trace.final_variables.values" :key="name"><code>{{ name }} = {{ value }}</code></div>
    <small v-if="trace.final_variables.omitted">另有 {{ trace.final_variables.omitted }} 个变量未显示</small>
    <p v-if="trace.error_type" role="status">第 {{ trace.last_line }} 行：{{ trace.error_type }} · {{ trace.error_message }}</p>
    <details><summary>本次标准输入</summary><pre>{{ trace.stdin || '未提供输入' }}</pre></details>
    <details v-if="trace.stdout"><summary>本次输出</summary><pre>{{ trace.stdout }}</pre></details>
  </details>
</template>

<style scoped>
.python-trace-view { min-width: 0; border: 1px solid rgb(128 150 160 / 45%); border-radius: 8px; padding: 12px; line-height: 1.6; color: inherit; overflow-wrap: anywhere; }
.python-trace-view summary { cursor: pointer; font-weight: 600; }
.python-trace-view p { margin: 8px 0; font-size: 13px; }
.python-trace-view__scroll { max-height: 320px; overflow: auto; margin: 8px 0; }
.python-trace-view table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
.python-trace-view caption { text-align: left; margin-bottom: 6px; }
.python-trace-view th, .python-trace-view td { padding: 6px; text-align: left; vertical-align: top; border-bottom: 1px solid rgb(128 150 160 / 30%); }
.python-trace-view th:nth-child(-n+2) { width: 2.5em; }
.python-trace-view small { display: block; opacity: .85; }
.python-trace-view code, .python-trace-view pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; }
.python-trace-view :focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
:global(html[data-plex-style="comic"] .python-trace-view) { border-width: 2px; border-radius: 4px 12px 4px 12px; }
</style>
