<script setup lang="ts">
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { PeopleOutline, SchoolOutline, MailOpenOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import ExplorerMemberManage from '../components/teacher/ExplorerMemberManage.vue'
import TeacherClassManagePanel from '../components/teacher/TeacherClassManagePanel.vue'
import TeacherEnrollmentReviewPanel from '../components/teacher/TeacherEnrollmentReviewPanel.vue'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'

const { selectedClassId, loadOverview } = useTeacherOverviewInjected()

const activeTab = ref<'students' | 'classes' | 'enrollments'>('students')

const tabs = [
  { key: 'students' as const, label: 'Explorer 成员', sub: '学生增删改与状态', icon: PeopleOutline },
  { key: 'classes' as const, label: '班级信息', sub: '班级编辑与变更申请', icon: SchoolOutline },
  { key: 'enrollments' as const, label: '入班申请', sub: '审核学生加入请求', icon: MailOpenOutline },
]

function onChanged() {
  void loadOverview()
}
</script>

<template>
  <TeacherDashboardShell
    active-nav="classes"
    page-title="班级管理"
    page-subtitle="CLASS MANAGEMENT · 管理 Explorer 成员、班级信息与入班审核"
    hide-search
    :show-activity="false"
    :show-refresh="false"
  >
    <section class="class-manage teacher-page" aria-label="班级管理">
      <nav class="class-manage__tabs" role="tablist" aria-label="班级管理分区">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          role="tab"
          class="class-manage__tab"
          :aria-selected="activeTab === tab.key"
          :class="{ 'is-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <n-icon :component="tab.icon" class="class-manage__tab-icon" />
          <span class="class-manage__tab-copy">
            <strong>{{ tab.label }}</strong>
            <small>{{ tab.sub }}</small>
          </span>
        </button>
      </nav>

      <div class="class-manage__body teacher-panel">
        <explorer-member-manage
          v-if="activeTab === 'students'"
          :default-class-id="selectedClassId"
          @changed="onChanged"
        />
        <teacher-class-manage-panel
          v-else-if="activeTab === 'classes'"
          :default-class-id="selectedClassId"
          @changed="onChanged"
        />
        <teacher-enrollment-review-panel
          v-else
          :default-class-id="selectedClassId"
          @changed="onChanged"
        />
      </div>
    </section>
  </TeacherDashboardShell>
</template>

<style scoped>
.class-manage {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  min-height: 0;
}

.class-manage__tabs {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.class-manage__tab {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 1.1rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 14px;
  background: rgba(4, 12, 20, 0.55);
  color: var(--teacher-muted);
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.class-manage__tab:hover {
  border-color: rgba(251, 146, 60, 0.35);
  color: var(--teacher-text);
}

.class-manage__tab.is-active {
  border-color: rgba(251, 146, 60, 0.5);
  background: rgba(251, 146, 60, 0.12);
  color: var(--teacher-text);
  box-shadow: 0 0 22px rgba(251, 146, 60, 0.12);
}

.class-manage__tab-icon {
  font-size: 1.4rem;
  flex-shrink: 0;
}

.class-manage__tab-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.class-manage__tab-copy strong {
  font-size: 0.92rem;
  font-weight: 680;
}

.class-manage__tab-copy small {
  font-size: 0.72rem;
  color: var(--teacher-muted);
}

.class-manage__body {
  flex: 1;
  min-height: 0;
  padding: 1.25rem 1.35rem;
  overflow: auto;
}

@media (max-width: 760px) {
  .class-manage__tab-copy small {
    display: none;
  }
}
</style>
