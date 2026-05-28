<script setup lang="ts">
import PlexRadarChart from './PlexRadarChart.vue'
import PlexLineChart from './PlexLineChart.vue'
import PlexBarChart from './PlexBarChart.vue'
import PlexPieChart from './PlexPieChart.vue'

withDefaults(
  defineProps<{
    mode?: 'student' | 'teacher' | 'admin'
    radarValues?: number[]
    trendDays?: string[]
    trendCorrect?: number[]
    trendCount?: number[]
    barLabels?: string[]
    barValues?: number[]
    pieData?: Array<{ name: string; value: number }>
  }>(),
  {
    mode: 'student',
    radarValues: () => [82, 74, 65, 88, 71],
    trendDays: () => ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    trendCorrect: () => [72, 78, 65, 85, 90, 88, 93],
    trendCount: () => [5, 8, 4, 10, 12, 9, 14],
    barLabels: () => ['Python', '算法', '数据结构', '面向对象', '工程实践'],
    barValues: () => [88, 72, 65, 58, 80],
    pieData: () => [
      { name: '语法错误', value: 28 },
      { name: '逻辑错误', value: 35 },
      { name: '边界条件', value: 22 },
      { name: '算法复杂度', value: 15 },
    ],
  },
)
</script>

<template>
  <div class="plex-dashboard" :class="`plex-dashboard--${mode}`">
    <div class="plex-dashboard__row">
      <div class="plex-dashboard__card plex-dashboard__card--radar">
        <h4>能力雷达</h4>
        <div class="plex-dashboard__chart-wrap">
          <plex-radar-chart
            :dimensions="['抽象建模', '算法设计', '分解问题', '调试能力', '逻辑推理']"
            :values="radarValues"
            :color="mode === 'student' ? '#22c55e' : mode === 'teacher' ? '#f97316' : '#818cf8'"
          />
        </div>
      </div>

      <div class="plex-dashboard__card plex-dashboard__card--line">
        <h4>近 7 天学习趋势</h4>
        <div class="plex-dashboard__chart-wrap">
          <plex-line-chart
            :x-data="trendDays"
            :series="[
              { name: '正确率(%)', data: trendCorrect, color: mode === 'student' ? '#22c55e' : mode === 'teacher' ? '#f97316' : '#818cf8' },
              { name: '练习次数', data: trendCount, color: '#38bdf8' },
            ]"
          />
        </div>
      </div>
    </div>

    <div class="plex-dashboard__row">
      <div class="plex-dashboard__card plex-dashboard__card--bar">
        <h4>知识域掌握度</h4>
        <div class="plex-dashboard__chart-wrap">
          <plex-bar-chart
            :x-data="barLabels"
            :series="[{ name: '掌握分', data: barValues, color: mode === 'student' ? '#22c55e' : mode === 'teacher' ? '#f97316' : '#818cf8' }]"
          />
        </div>
      </div>

      <div class="plex-dashboard__card plex-dashboard__card--pie">
        <h4>错题类型分布</h4>
        <div class="plex-dashboard__chart-wrap">
          <plex-pie-chart :data="pieData" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plex-dashboard {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.plex-dashboard__row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.plex-dashboard__card {
  padding: 1rem 1.1rem 0.75rem;
  border-radius: 12px;
  background: linear-gradient(145deg, rgba(4, 12, 22, 0.9), rgba(3, 10, 18, 0.85));
  border: 1px solid rgba(130, 212, 255, 0.08);
}

.plex-dashboard--student .plex-dashboard__card { border-color: rgba(34, 197, 94, 0.12); }
.plex-dashboard--teacher .plex-dashboard__card { border-color: rgba(249, 115, 22, 0.12); }
.plex-dashboard--admin .plex-dashboard__card { border-color: rgba(129, 140, 248, 0.12); }

.plex-dashboard__card h4 {
  margin: 0 0 0.5rem;
  color: rgba(255, 247, 237, 0.88);
  font-size: 0.88rem;
  font-weight: 650;
}

.plex-dashboard__chart-wrap {
  height: 220px;
}

@media (max-width: 768px) {
  .plex-dashboard__row {
    grid-template-columns: 1fr;
  }
}
</style>
