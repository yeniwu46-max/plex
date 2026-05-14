<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { json } from '@codemirror/lang-json'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from '@codemirror/view'
import { Graph, type GraphData } from '@antv/g6'
import DashboardShell from '../components/layout/DashboardShell.vue'

const graphRef = ref<HTMLElement | null>(null)
let graph: Graph | null = null

const graphJson = ref(
  JSON.stringify(
    {
      nodes: [
        { id: 'n1', data: { label: '入口' } },
        { id: 'n2', data: { label: '循环' } },
        { id: 'n3', data: { label: '决策' } },
      ],
      edges: [
        { id: 'e1', source: 'n1', target: 'n2' },
        { id: 'e2', source: 'n2', target: 'n3' },
      ],
    },
    null,
    2,
  ),
)

const cmExtensions = [json(), oneDark, EditorView.lineWrapping]

onMounted(async () => {
  if (!graphRef.value) return
  try {
    const data = JSON.parse(graphJson.value) as GraphData
    graph = new Graph({
      container: graphRef.value,
      data,
      layout: { type: 'dagre', rankdir: 'LR' },
      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    })
    await graph.render()
  } catch (e) {
    console.error('G6 render failed', e)
  }
})

onUnmounted(() => {
  graph?.destroy()
  graph = null
})
</script>

<template>
  <DashboardShell
    active-nav="track"
    page-title="星轨路径"
    search-placeholder="搜索节点、路径…"
  >
    <div class="lab">
      <p class="lab__hint">
        本页演示已安装的 <strong>@antv/g6</strong> 与 <strong>vue-codemirror</strong>（JSON 语法）。图谱数据为静态示例。
      </p>
      <div class="lab__grid">
        <div class="lab__panel">
          <h3 class="lab__title">知识路径（G6）</h3>
          <div ref="graphRef" class="lab__graph" />
        </div>
        <div class="lab__panel">
          <h3 class="lab__title">图谱数据（CodeMirror）</h3>
          <Codemirror
            v-model="graphJson"
            class="lab__cm"
            :extensions="cmExtensions"
            :tab-size="2"
          />
        </div>
      </div>
    </div>
  </DashboardShell>
</template>

<style scoped>
.lab {
  position: relative;
  z-index: 1;
  padding: 1rem 1.25rem 2rem;
}
.lab__hint {
  margin: 0 0 1rem;
  font-size: 0.85rem;
  color: rgba(148, 163, 184, 0.95);
  line-height: 1.5;
}
.lab__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
@media (max-width: 900px) {
  .lab__grid {
    grid-template-columns: 1fr;
  }
}
.lab__panel {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.75rem;
  background: rgba(15, 23, 42, 0.35);
  padding: 0.75rem;
  min-width: 0;
}
.lab__title {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #e2e8f0;
}
.lab__graph {
  height: 280px;
  width: 100%;
  border-radius: 0.5rem;
  background: rgba(2, 6, 23, 0.5);
}
.lab__cm {
  height: 280px;
  overflow: hidden;
  border-radius: 0.5rem;
}
.lab__cm :deep(.cm-editor) {
  height: 100%;
}
</style>
