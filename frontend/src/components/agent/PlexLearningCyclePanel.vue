<script setup lang="ts">
import type { LearningCycleResult } from '../../api/agentService'

defineProps<{
  result: LearningCycleResult
}>()
</script>

<template>
  <section class="cycle-panel" aria-label="小E 学习闭环">
    <header class="cycle-panel__head">
      <div>
        <p>小E 的学习闭环</p>
        <h3>{{ result.learningReport.headline }}</h3>
      </div>
      <span :class="result.execution.all_passed ? 'is-pass' : 'is-fix'">
        {{ result.execution.all_passed ? '测试已通过' : '需要修复' }}
      </span>
    </header>

    <div class="cycle-panel__grid">
      <article>
        <h4>学习画像与路径</h4>
        <p>讲解方式：{{ result.learningProfile.interventionPresentation }}</p>
        <p>循环掌握度：{{ result.learningProfile.loopMastery }}</p>
        <strong>下一步：{{ result.learningPath.nextKnowledgePoint }}</strong>
        <small>{{ result.learningPath.reason }}</small>
      </article>

      <article>
        <h4>{{ result.resources.executionDiagram.title }}</h4>
        <p>{{ result.resources.executionDiagram.description }}</p>
        <ol class="cycle-panel__diagram">
          <li v-for="step in result.resources.executionDiagram.steps" :key="step.round">
            <b>第 {{ step.round }} 轮</b><span>i = {{ step.i }}</span><span>{{ step.action }}</span>
          </li>
        </ol>
      </article>

      <article>
        <h4>{{ result.resources.microFix.title }}</h4>
        <p>{{ result.resources.microFix.prompt }}</p>
        <code>{{ result.resources.microFix.starterCode }}</code>
        <small>{{ result.resources.microFix.expectedOutcome }}</small>
      </article>

      <article class="cycle-panel__tutor">
        <h4>启发式追问</h4>
        <p>{{ result.tutor.question }}</p>
        <small>{{ result.tutor.nextAction }}</small>
      </article>
    </div>

    <footer>
      <span>知识图谱 · {{ result.knowledgeGraphUpdate.nodeLabel }}：{{ result.knowledgeGraphUpdate.evidence }}</span>
      <ol>
        <li v-for="action in result.learningReport.nextActions" :key="action">{{ action }}</li>
      </ol>
    </footer>
  </section>
</template>

<style scoped>
.cycle-panel { display: grid; gap: .8rem; padding: 1rem; border: 1px solid rgba(96, 165, 250, .24); border-radius: 14px; background: linear-gradient(135deg, rgba(15, 23, 42, .8), rgba(8, 47, 73, .52)); }
.cycle-panel__head { display: flex; justify-content: space-between; align-items: start; gap: .75rem; }
.cycle-panel__head p, .cycle-panel__head h3, .cycle-panel h4, .cycle-panel p, .cycle-panel small { margin: 0; }
.cycle-panel__head p { color: #7dd3fc; font-size: .74rem; letter-spacing: .08em; }
.cycle-panel__head h3 { margin-top: .18rem; color: #f8fafc; font-size: 1rem; }
.cycle-panel__head > span { padding: .2rem .55rem; border-radius: 999px; font-size: .75rem; font-weight: 700; white-space: nowrap; }
.is-pass { color: #6ee7b7; background: rgba(16, 185, 129, .14); }.is-fix { color: #fcd34d; background: rgba(245, 158, 11, .14); }
.cycle-panel__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
.cycle-panel article { display: grid; gap: .4rem; padding: .75rem; border-radius: 10px; background: rgba(15, 23, 42, .52); }
.cycle-panel h4 { color: #bae6fd; font-size: .86rem; }.cycle-panel p, .cycle-panel small, .cycle-panel footer { color: rgba(226, 232, 240, .78); font-size: .8rem; line-height: 1.5; }
.cycle-panel strong { color: #a7f3d0; font-size: .85rem; }.cycle-panel code { overflow: auto; padding: .5rem; border-radius: 7px; background: rgba(2, 6, 23, .72); color: #c4b5fd; font-size: .74rem; white-space: pre; }
.cycle-panel__diagram { display: grid; gap: .3rem; margin: 0; padding: 0; list-style: none; }.cycle-panel__diagram li { display: grid; grid-template-columns: 3.3rem 2.8rem 1fr; gap: .35rem; font-size: .74rem; color: #dbeafe; }.cycle-panel__diagram b { color: #93c5fd; }
.cycle-panel__tutor { border-color: rgba(196, 181, 253, .18); }.cycle-panel footer { display: grid; gap: .35rem; padding-top: .7rem; border-top: 1px solid rgba(148, 163, 184, .16); }.cycle-panel footer ol { margin: 0; padding-left: 1.05rem; }
@media (max-width: 680px) { .cycle-panel__grid { grid-template-columns: 1fr; } }
</style>
