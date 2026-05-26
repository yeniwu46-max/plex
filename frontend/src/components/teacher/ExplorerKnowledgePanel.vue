<script setup lang="ts">
import type { UserAchievementRecord } from '../../api/studentOverview'

defineProps<{
  loading: boolean
  error: string
  achievements: UserAchievementRecord[]
}>()

const rarityLabel: Record<string, string> = {
  common: '普通',
  rare: '稀有',
  epic: '史诗',
  legendary: '传说',
}
</script>

<template>
  <section class="explorer-knowledge" aria-label="知识掌握与成就">
    <div v-if="loading" class="explorer-knowledge__state">正在加载成就数据…</div>
    <div v-else-if="error" class="explorer-knowledge__state explorer-knowledge__state--error">{{ error }}</div>
    <ul v-else-if="achievements.length" class="explorer-knowledge__list">
      <li v-for="item in achievements" :key="item.id">
        <span class="explorer-knowledge__badge" aria-hidden="true">🏅</span>
        <div>
          <strong>{{ item.achievement?.name ?? '未命名成就' }}</strong>
          <p>{{ item.achievement?.description || '暂无描述' }}</p>
          <small>
            {{ rarityLabel[item.achievement?.rarity ?? 'common'] ?? item.achievement?.rarity }}
            <template v-if="item.unlocked_at"> · {{ item.unlocked_at.slice(0, 10) }}</template>
          </small>
        </div>
      </li>
    </ul>
    <p v-else class="explorer-knowledge__state">该 Explorer 尚未解锁成就勋章。</p>
  </section>
</template>

<style scoped>
.explorer-knowledge__state {
  margin: 0;
  padding: 1.5rem 0;
  color: var(--teacher-muted);
  font-size: 0.9rem;
  text-align: center;
}

.explorer-knowledge__state--error {
  color: #fecaca;
}

.explorer-knowledge__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.65rem;
  max-height: 320px;
  overflow: auto;
}

.explorer-knowledge__list li {
  display: flex;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(219, 235, 249, 0.08);
}

.explorer-knowledge__badge {
  font-size: 1.5rem;
  line-height: 1;
}

.explorer-knowledge__list strong {
  color: var(--teacher-text);
  font-size: 0.9rem;
}

.explorer-knowledge__list p {
  margin: 0.2rem 0 0;
  color: var(--teacher-muted);
  font-size: 0.8rem;
  line-height: 1.4;
}

.explorer-knowledge__list small {
  color: var(--teacher-orange);
  font-size: 0.72rem;
}
</style>
