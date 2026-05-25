<script setup lang="ts">
import { NIcon } from 'naive-ui'
import {
  CodeSlashOutline,
  LayersOutline,
  ColorPaletteOutline,
  ServerOutline,
  GridOutline,
} from '@vicons/ionicons5'
import type { Component } from 'vue'
import type { SkillItem } from '../../data/archivesMock'

defineProps<{
  skills: SkillItem[]
}>()

const iconMap: Record<string, Component> = {
  algo: CodeSlashOutline,
  ds: LayersOutline,
  fe: ColorPaletteOutline,
  be: ServerOutline,
  db: GridOutline,
}
</script>

<template>
  <section class="card skills" aria-label="能力分布">
    <h2 class="card__title">能力分布</h2>
    <ul class="skills__list">
      <li v-for="skill in skills" :key="skill.key" class="skills__item">
        <span class="skills__icon-wrap">
          <n-icon :component="iconMap[skill.key] ?? CodeSlashOutline" class="skills__icon" />
        </span>
        <div class="skills__bar-wrap">
          <div class="skills__label-row">
            <span class="skills__label">{{ skill.label }}</span>
            <span class="skills__pct">{{ skill.percent }}%</span>
          </div>
          <div class="skills__track">
            <div class="skills__fill" :style="{ width: `${skill.percent}%` }" />
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.card {
  border-radius: 1rem;
  border: 1px solid var(--plex-border);
  background: rgba(11, 22, 40, 0.72);
  backdrop-filter: blur(12px);
  padding: 1.1rem 1.25rem;
}

.card__title {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--plex-accent);
}

.skills__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.skills__item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.skills__icon-wrap {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 240, 192, 0.08);
  border: 1px solid var(--plex-border);
  color: var(--plex-accent);
}

.skills__icon {
  font-size: 1.1rem;
}

.skills__bar-wrap {
  flex: 1;
  min-width: 0;
}

.skills__label-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.3rem;
  font-size: 0.78rem;
}

.skills__label {
  color: rgba(241, 245, 249, 0.9);
}

.skills__pct {
  color: var(--plex-muted);
}

.skills__track {
  height: 6px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.skills__fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--plex-accent), var(--plex-node-blue));
  box-shadow: 0 0 10px rgba(16, 240, 192, 0.35);
}
</style>
