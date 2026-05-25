<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { LockClosedOutline, TrophyOutline } from '@vicons/ionicons5'
import type { AchievementItem } from '../../data/archivesMock'

defineProps<{
  items: AchievementItem[]
}>()

const toneGlow: Record<string, string> = {
  teal: 'rgba(16, 240, 192, 0.45)',
  gold: 'rgba(251, 191, 36, 0.45)',
  blue: 'rgba(6, 182, 212, 0.45)',
}
</script>

<template>
  <section class="card achievements" aria-label="成就收藏">
    <h2 class="card__title">成就收藏</h2>
    <div class="achievements__grid">
      <article
        v-for="item in items"
        :key="item.id"
        class="badge"
        :class="{ 'badge--locked': item.locked }"
      >
        <span
          v-if="!item.locked"
          class="badge__glow"
          :style="{ boxShadow: `0 0 24px ${toneGlow[item.tone] ?? toneGlow.teal}` }"
        />
        <span class="badge__icon-wrap">
          <n-icon
            :component="item.locked ? LockClosedOutline : TrophyOutline"
            class="badge__icon"
          />
        </span>
        <p class="badge__title">{{ item.title }}</p>
        <p v-if="item.date" class="badge__date">{{ item.date }}</p>
        <p v-else class="badge__date badge__date--muted">未解锁</p>
      </article>
    </div>
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

.achievements__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.badge {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 0.65rem 0.35rem;
  border-radius: 0.75rem;
  border: 1px solid var(--plex-border);
  background: rgba(7, 17, 31, 0.5);
}

.badge--locked {
  opacity: 0.55;
}

.badge__glow {
  position: absolute;
  inset: 20% 15%;
  border-radius: 50%;
  pointer-events: none;
}

.badge__icon-wrap {
  position: relative;
  z-index: 1;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(16, 240, 192, 0.25);
  color: var(--plex-accent);
  margin-bottom: 0.4rem;
}

.badge--locked .badge__icon-wrap {
  color: var(--plex-muted);
  border-color: rgba(148, 163, 184, 0.2);
}

.badge__icon {
  font-size: 1.25rem;
}

.badge__title {
  margin: 0;
  font-size: 0.68rem;
  font-weight: 600;
}

.badge__date {
  margin: 0.25rem 0 0;
  font-size: 0.62rem;
  color: var(--plex-muted);
}

.badge__date--muted {
  color: rgba(148, 163, 184, 0.65);
}

@media (max-width: 900px) {
  .achievements__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
