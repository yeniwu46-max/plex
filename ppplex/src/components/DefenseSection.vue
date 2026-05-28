<script setup lang="ts">
import { computed } from 'vue'
import type { FeatureSection } from '../types/defense'
import DemoLink from './DemoLink.vue'
import ScreenshotFrame from './ScreenshotFrame.vue'
import ScriptSteps from './ScriptSteps.vue'

const props = defineProps<{
  section: FeatureSection
  extendedSteps?: FeatureSection['steps']
}>()

const steps = computed(() => props.extendedSteps ?? props.section.steps)
</script>

<template>
  <article class="card" :id="section.id">
    <h2>{{ section.title }}</h2>

    <p v-if="section.summary" class="section-summary">{{ section.summary }}</p>
    <p v-if="section.pitch" class="pitch">{{ section.pitch }}</p>

    <ul v-if="section.bullets?.length" class="bullet-list">
      <li v-for="(b, i) in section.bullets" :key="i">{{ b }}</li>
    </ul>

    <table v-if="section.table?.length" class="data-table">
      <tbody>
        <tr v-for="(row, i) in section.table" :key="i">
          <th v-if="row.length > 1">{{ row[0] }}</th>
          <td :colspan="row.length === 1 ? 2 : 1">{{ row.length > 1 ? row[1] : row[0] }}</td>
        </tr>
      </tbody>
    </table>

    <div v-if="section.cards?.length" class="user-cards">
      <div
        v-for="card in section.cards"
        :key="card.role"
        class="user-card"
        :style="{ borderColor: card.color }"
      >
        <h4 :style="{ color: card.color }">{{ card.label }}</h4>
        <code v-for="r in card.routes" :key="r">{{ r }}</code>
      </div>
    </div>

    <div v-if="section.commands?.length" class="commands">
      <code v-for="(c, i) in section.commands" :key="i">{{ c }}</code>
    </div>

    <table v-if="section.accounts?.length" class="data-table">
      <thead>
        <tr><th>角色</th><th>账号</th><th>密码</th></tr>
      </thead>
      <tbody>
        <tr v-for="a in section.accounts" :key="a.user">
          <td>{{ a.role }}</td>
          <td><code>{{ a.user }}</code></td>
          <td><code>{{ a.pass }}</code></td>
        </tr>
      </tbody>
    </table>

    <ScreenshotFrame
      v-if="section.screenshot"
      :file="section.screenshot"
      :alt="section.title"
    />

    <div v-if="section.demoUrl || section.demoUrlTeacher" class="demo-actions">
      <DemoLink :path="section.demoUrl" label="学生端演示" />
      <DemoLink
        v-if="section.demoUrlTeacher"
        :path="section.demoUrlTeacher"
        label="教师端演示"
        variant="teacher"
      />
    </div>

    <ScriptSteps v-if="steps?.length" :steps="steps" :section-id="section.id" />

    <div v-if="section.faqs?.length" class="faq">
      <details v-for="(f, i) in section.faqs" :key="i">
        <summary>{{ f.q }}</summary>
        <p>{{ f.a }}</p>
      </details>
    </div>
  </article>
</template>

<style scoped>
.section-summary {
  color: var(--plex-muted);
  margin-top: 0;
}

.commands {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin: 0.75rem 0;
}

.commands code {
  display: block;
  padding: 0.4rem 0.6rem;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 6px;
  font-size: 0.85rem;
}

.demo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.user-card code {
  display: block;
  margin-top: 0.2rem;
}
</style>
