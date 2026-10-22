<script setup lang="ts">
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import CounterexampleWorkbench from '../components/teacher/CounterexampleWorkbench.vue'
defineOptions({ name: 'TeacherCounterexampleView' })
</script>
<template>
  <TeacherDashboardShell active-nav="trial" page-title="反例挑战" page-subtitle="建立独立基准，核对执行证据与学生解释" hide-search>
    <CounterexampleWorkbench />
  </TeacherDashboardShell>
</template>
