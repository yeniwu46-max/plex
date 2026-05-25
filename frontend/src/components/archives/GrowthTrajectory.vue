<script setup lang="ts">
import type { GrowthEvent } from '../../data/archivesMock'

defineProps<{
  events: GrowthEvent[]
}>()

const toneColor: Record<GrowthEvent['tone'], string> = {
  teal: 'var(--plex-accent)',
  gold: '#fbbf24',
  blue: 'var(--plex-node-blue)',
  purple: 'var(--plex-node-purple)',
}
</script>

<template>
  <section class="card timeline" aria-label="成长轨迹">
    <h2 class="card__title">成长轨迹</h2>
    <ol class="timeline__list">
      <li v-for="(ev, i) in events" :key="ev.id" class="timeline__item">
        <span class="timeline__line" :class="{ 'timeline__line--last': i === events.length - 1 }" />
        <span class="timeline__dot" :style="{ borderColor: toneColor[ev.tone], color: toneColor[ev.tone] }">
          <span class="timeline__dot-inner" />
        </span>
        <div class="timeline__content">
          <p class="timeline__title">{{ ev.title }}</p>
          <p class="timeline__date">{{ ev.date }}</p>
          <p class="timeline__desc">{{ ev.description }}</p>
        </div>
      </li>
    </ol>
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

.timeline__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline__item {
  position: relative;
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 0 0.85rem;
  padding-bottom: 1.1rem;
}

.timeline__item:last-child {
  padding-bottom: 0;
}

.timeline__line {
  position: absolute;
  left: 13px;
  top: 28px;
  bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, rgba(16, 240, 192, 0.35), rgba(148, 163, 184, 0.15));
}

.timeline__line--last {
  display: none;
}

.timeline__dot {
  position: relative;
  z-index: 1;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--plex-bg-elevated);
  box-shadow: 0 0 14px currentColor;
}

.timeline__dot-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.timeline__title {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 600;
}

.timeline__date {
  margin: 0.2rem 0 0.35rem;
  font-size: 0.68rem;
  color: var(--plex-muted);
}

.timeline__desc {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.45;
  color: rgba(226, 232, 240, 0.82);
}
</style>
