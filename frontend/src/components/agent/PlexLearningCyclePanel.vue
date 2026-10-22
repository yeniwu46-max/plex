<script setup lang="ts">
import type { LearningCycleResult } from '../../api/agentService'
import TutorResponseCard from '../student/TutorResponseCard.vue'

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
        {{ result.execution.all_passed ? '本次自测通过' : '本次自测未通过' }}
      </span>
    </header>

    <div class="cycle-panel__grid">
      <article>
        <h4>本次自测</h4>
        <strong>{{ result.execution.passed_count }} / {{ result.execution.total }} 个用例通过</strong>
        <p>有限自测通过不等于所有输入正确，不会据此修改正式成绩或掌握度。</p>
        <small>{{ result.learningPath.reason }}</small>
      </article>

      <article>
        <h4>运行结果</h4>
        <ol class="cycle-panel__results">
          <li v-for="(item, index) in result.execution.results" :key="index">
            <strong>{{ item.label || `用例 ${index + 1}` }} · {{ item.passed ? '通过' : '未通过' }}</strong>
            <p>预期输出</p><pre>{{ item.expected || '空输出' }}</pre>
            <p>实际输出</p><pre>{{ item.actual || '空输出' }}</pre>
            <pre v-if="item.error">{{ item.error }}</pre>
            <small v-if="item.truncated">较长的输出已截取显示。</small>
          </li>
        </ol>
      </article>

      <article class="cycle-panel__tutor">
        <TutorResponseCard :response="result.tutorResponse" />
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
.cycle-panel { --cycle-text: var(--plex-text); --cycle-muted: var(--plex-text-muted); --cycle-panel: var(--plex-bg-card); --cycle-raised: var(--plex-bg-elevated); --cycle-line: var(--plex-border); --cycle-accent: var(--plex-accent); display: grid; gap: .8rem; padding: 1rem; border: 1px solid var(--cycle-line); border-radius: 14px; background: var(--cycle-panel); color: var(--cycle-text); }
.cycle-panel__head { display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: .75rem; }
.cycle-panel__head p, .cycle-panel__head h3, .cycle-panel h4, .cycle-panel p, .cycle-panel small { margin: 0; }
.cycle-panel__head p { color: var(--cycle-accent); font-size: .74rem; letter-spacing: .08em; }
.cycle-panel__head h3 { margin-top: .18rem; font-size: 1rem; }
.cycle-panel__head > span { padding: .2rem .55rem; border: 1px solid currentColor; border-radius: 999px; font-size: .75rem; font-weight: 700; white-space: nowrap; }
.is-pass { color: var(--cycle-accent); }.is-fix { color: var(--cycle-text); }
.cycle-panel__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
.cycle-panel article { display: grid; gap: .4rem; min-width: 0; overflow-wrap: anywhere; padding: .75rem; border: 1px solid var(--cycle-line); border-radius: 10px; background: var(--cycle-raised); }
.cycle-panel h4 { font-size: .86rem; }.cycle-panel p, .cycle-panel small, .cycle-panel footer { color: var(--cycle-muted); font-size: .8rem; line-height: 1.5; }
.cycle-panel strong { font-size: .85rem; }
.cycle-panel__results { display: grid; gap: .75rem; padding-inline-start: 1.2rem; margin: 0; }
.cycle-panel__results pre { margin: .3rem 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: .8rem; }
.cycle-panel__tutor { grid-column: 1 / -1; }.cycle-panel footer { display: grid; gap: .35rem; padding-top: .7rem; border-top: 1px solid var(--cycle-line); }.cycle-panel footer ol { margin: 0; padding-left: 1.05rem; }
:global(html[data-plex-style='comic'][data-plex-persona='student'] .cycle-panel) { --cycle-text: var(--comic-text); --cycle-muted: var(--comic-muted); --cycle-panel: var(--comic-panel); --cycle-raised: var(--comic-raised); --cycle-line: var(--comic-line); --cycle-accent: var(--comic-accent); border-width: 2px; border-radius: 5px 16px 5px 16px; box-shadow: var(--comic-shadow); }
@media (max-width: 680px) { .cycle-panel__grid { grid-template-columns: 1fr; } }
</style>
