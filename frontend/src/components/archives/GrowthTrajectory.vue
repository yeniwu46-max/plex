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
    <div class="timeline__body">
      <ol class="timeline__list">
        <li v-for="(ev, i) in events" :key="ev.id" class="timeline__item">
          <span class="timeline__line" :class="{ 'timeline__line--last': i === events.length - 1 }" />
          <span class="timeline__dot" :style="{ borderColor: toneColor[ev.tone], color: toneColor[ev.tone] }">
            <span class="timeline__dot-inner" />
          </span>
          <div class="timeline__content">
            <div class="timeline__meta">
              <p class="timeline__title">{{ ev.title }}</p>
              <p class="timeline__date">{{ ev.date }}</p>
            </div>
            <p class="timeline__desc">{{ ev.description }}</p>
          </div>
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  border-radius: 1rem;
  border: 1px solid var(--plex-border);
  background: rgba(11, 22, 40, 0.72);
  backdrop-filter: blur(12px);
  padding: 1.65rem 1.5rem 1.5rem;
}

.card__title {
  margin: 0 0 1.15rem;
  padding-inline: 0.15rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--plex-accent);
}

.timeline__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: safe center;
  padding: 1.25rem clamp(0.75rem, 4%, 1.35rem);
  overflow-y: auto;
}

.timeline__list {
  list-style: none;
  width: min(100%, 36rem);
  margin: 0;
  padding: 0;
  flex-shrink: 0;
}

.timeline__item {
  position: relative;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 0 1.15rem;
  padding-bottom: 1.25rem;
}

.timeline__item:last-child {
  padding-bottom: 0;
}

.timeline__line {
  position: absolute;
  left: 15px;
  top: 32px;
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
  width: 32px;
  height: 32px;
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

.timeline__content {
  min-width: 0;
  padding: 0.15rem 0.25rem 0 0;
}

.timeline__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem 0.75rem;
  margin-bottom: 0.45rem;
}

.timeline__title {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 600;
  line-height: 1.35;
  color: #f1f5f9;
}

.timeline__date {
  margin: 0;
  flex-shrink: 0;
  font-size: 0.72rem;
  color: var(--plex-muted);
}

.timeline__desc {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
  color: rgba(224, 237, 247, 0.68);
}
</style>
