<script setup lang="ts">
import { NButton, NIcon, NSelect } from 'naive-ui'
import { ChevronDownOutline, RefreshOutline } from '@vicons/ionicons5'
import { useTeacherOverviewInjected } from '../../composables/useTeacherOverview'

withDefaults(
  defineProps<{
    ariaLabel?: string
    showPeriod?: boolean
    showActivity?: boolean
    showRefresh?: boolean
  }>(),
  {
    ariaLabel: '教师端筛选与状态',
    showPeriod: false,
    showActivity: true,
    showRefresh: true,
  },
)

const {
  loading,
  selectedClassId,
  period,
  classOptions,
  activityScore,
  activeLineWidth,
  periodOptions,
  loadOverview,
  changeClass,
  changePeriod,
} = useTeacherOverviewInjected()
</script>

<template>
  <section class="teacher-toolbar" :aria-label="ariaLabel">
    <n-select
      :value="selectedClassId"
      :options="classOptions"
      :disabled="loading || !classOptions.length"
      placeholder="选择班级"
      class="teacher-toolbar__class"
      @update:value="changeClass"
    >
      <template #arrow>
        <n-icon :component="ChevronDownOutline" />
      </template>
    </n-select>

    <slot name="filters" />

    <n-select
      v-if="showPeriod"
      :value="period"
      :options="periodOptions"
      class="teacher-toolbar__filter"
      @update:value="changePeriod"
    />

    <div v-if="showActivity" class="teacher-toolbar__activity">
      <span>班级活跃度</span>
      <strong>{{ activityScore }}%</strong>
      <i :style="{ width: activeLineWidth }" />
    </div>

    <div class="teacher-toolbar__keeper">
      <span class="teacher-toolbar__keeper-avatar" aria-hidden="true"><span /></span>
      <div>
        <strong>Waystation Keeper</strong>
        <small>在线</small>
      </div>
    </div>

    <slot name="trailing" />

    <n-button
      v-if="showRefresh"
      circle
      quaternary
      class="teacher-toolbar__refresh"
      aria-label="刷新"
      :loading="loading"
      @click="loadOverview()"
    >
      <template #icon>
        <n-icon :component="RefreshOutline" />
      </template>
    </n-button>
  </section>
</template>

<style scoped>
.teacher-toolbar {
  position: relative;
  z-index: 4;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem 1.25rem;
  width: 100%;
  max-width: 100%;
  margin: -3.95rem var(--plex-page-gutter-x) 1.35rem;
  padding: 0.35rem 0;
  box-sizing: border-box;
}

.teacher-toolbar__class {
  width: 220px;
  flex-shrink: 0;
}

.teacher-toolbar__filter {
  width: 132px;
  flex-shrink: 0;
}

.teacher-toolbar__filter :deep(.n-base-selection),
.teacher-toolbar__class :deep(.n-base-selection) {
  --n-height: 52px !important;
  --n-color: rgba(4, 15, 25, 0.72) !important;
  --n-border: 1px solid var(--teacher-border, rgba(130, 212, 255, 0.12)) !important;
  --n-border-hover: 1px solid rgba(255, 145, 31, 0.45) !important;
  --n-text-color: var(--teacher-text, #fff7ed) !important;
  border-radius: 14px !important;
}

.teacher-toolbar__activity {
  display: grid;
  grid-template-columns: auto 4.5rem;
  align-items: center;
  min-width: 200px;
  gap: 0.25rem 0.85rem;
  padding-left: 1.1rem;
  border-left: 1px solid rgba(219, 235, 249, 0.1);
  flex-shrink: 0;
}

.teacher-toolbar__activity span {
  color: var(--teacher-muted);
  font-size: 0.82rem;
}

.teacher-toolbar__activity strong {
  color: var(--teacher-orange);
  font-size: 1.22rem;
}

.teacher-toolbar__activity i {
  grid-column: 2;
  display: block;
  height: 3px;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--teacher-orange), var(--teacher-gold));
  box-shadow: 0 0 16px var(--teacher-orange-glow);
}

.teacher-toolbar__keeper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-left: 1.1rem;
  border-left: 1px solid rgba(219, 235, 249, 0.1);
  flex-shrink: 0;
}

.teacher-toolbar__keeper strong {
  display: block;
  color: rgba(255, 247, 237, 0.88);
  font-size: 0.88rem;
  white-space: nowrap;
}

.teacher-toolbar__keeper small {
  display: block;
  color: var(--teacher-muted);
  font-size: 0.78rem;
  white-space: nowrap;
}

.teacher-toolbar__keeper small::before {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 0.3rem;
  border-radius: 50%;
  background: #22cfa4;
  content: '';
}

.teacher-toolbar__keeper-avatar {
  display: grid;
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background:
    radial-gradient(circle at center, rgba(59, 130, 246, 0.28), transparent 62%),
    #061827;
}

.teacher-toolbar__keeper-avatar span {
  width: 28px;
  height: 20px;
  border-radius: 9px;
  background: #e9f3fb;
  box-shadow: inset 0 -7px #111926;
}

.teacher-toolbar__refresh {
  flex-shrink: 0;
  color: #fed7aa !important;
}

:deep(.teacher-toolbar__notify) {
  position: relative;
  display: grid;
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(219, 235, 249, 0.1);
  border-radius: 13px;
  background: rgba(5, 18, 30, 0.62);
  cursor: pointer;
}

:deep(.teacher-toolbar__notify span) {
  width: 14px;
  height: 16px;
  border: 2px solid rgba(255, 247, 237, 0.8);
  border-radius: 4px 4px 2px 2px;
}

@media (max-width: 1280px) {
  .teacher-toolbar {
    margin-top: 0.5rem;
    margin-bottom: 1rem;
  }
}

@media (max-width: 760px) {
  .teacher-toolbar {
    flex-direction: column;
    align-items: stretch;
    margin-inline: 1rem;
  }

  .teacher-toolbar__class,
  .teacher-toolbar__filter,
  .teacher-toolbar__activity {
    width: 100%;
    min-width: 0;
  }

  .teacher-toolbar__activity,
  .teacher-toolbar__keeper {
    padding-left: 0;
    border-left: 0;
  }
}
</style>
