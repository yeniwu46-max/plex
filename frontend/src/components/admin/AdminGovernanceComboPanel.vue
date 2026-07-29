<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NInput, NInputNumber, NSwitch, useMessage } from 'naive-ui'
import AdminClassRequestPanel from './AdminClassRequestPanel.vue'
import { fetchAdminSettings, saveAdminSettings } from '../../api/adminSettings'
import { useThemeStore, type ColorMode } from '../../stores/theme'

const emit = defineEmits<{ reviewed: [] }>()
const message = useMessage()
const themeStore = useThemeStore()

type GovTab = 'approval' | 'settings'
const activeTab = ref<GovTab>('approval')

const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsError = ref('')
const settingsOpenTime = ref('00:00')
const settingsDailyLimit = ref('10')
const settingsDifficulty = ref(50)
const settingsNotices = ref<{ key: string; label: string; enabled: boolean }[]>([])

const NOTICE_LABELS: Record<string, string> = {
  trial_publish: '试炼发布通知',
  resource_review: '资源审核通知',
  class_change: '班级变更通知',
  system_maintenance: '系统维护通知',
}

const themeMode = ref<ColorMode>((themeStore.mode as ColorMode) || 'dark')

async function loadSettings() {
  settingsLoading.value = true
  settingsError.value = ''
  try {
    const result = await fetchAdminSettings()
    const s = result.settings
    settingsOpenTime.value = s.rules?.open_time ?? '00:00'
    settingsDailyLimit.value = s.rules?.daily_limit ?? '10'
    settingsDifficulty.value = s.rules?.difficulty ?? 50
    settingsNotices.value = (s.notices ?? []).map((item) => ({
      key: item.key,
      label: NOTICE_LABELS[item.key] || item.key,
      enabled: item.enabled,
    }))
    if (!settingsNotices.value.length) {
      settingsNotices.value = Object.keys(NOTICE_LABELS).map((key) => ({
        key,
        label: NOTICE_LABELS[key],
        enabled: true,
      }))
    }
  } catch (err) {
    settingsError.value = err instanceof Error ? err.message : '加载设置失败'
  } finally {
    settingsLoading.value = false
  }
}

async function saveSettings() {
  settingsSaving.value = true
  try {
    await saveAdminSettings({
      rules: {
        open_time: settingsOpenTime.value,
        daily_limit: settingsDailyLimit.value,
        difficulty: settingsDifficulty.value,
        punish: 'warn',
      },
      notices: settingsNotices.value.map(({ key, enabled }) => ({ key, enabled })),
    })
    themeStore.setMode(themeMode.value)
    message.success('系统设置已保存')
  } catch (err) {
    message.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    settingsSaving.value = false
  }
}

function setTheme(mode: ColorMode) {
  themeMode.value = mode
  themeStore.setMode(mode)
}

onMounted(() => {
  void loadSettings()
})
</script>

<template>
  <section class="gov-combo panel" aria-label="班级审批与系统设置">
    <nav class="gov-combo__tabs" aria-label="权限子导航">
      <button
        type="button"
        class="gov-combo__tab"
        :class="{ 'gov-combo__tab--active': activeTab === 'approval' }"
        @click="activeTab = 'approval'"
      >
        班级变更审批
      </button>
      <button
        type="button"
        class="gov-combo__tab"
        :class="{ 'gov-combo__tab--active': activeTab === 'settings' }"
        @click="activeTab = 'settings'"
      >
        系统设置
      </button>
    </nav>

    <div v-show="activeTab === 'approval'" class="gov-combo__pane">
      <AdminClassRequestPanel @reviewed="emit('reviewed')" />
    </div>

    <div v-show="activeTab === 'settings'" class="gov-combo__pane gov-combo__pane--settings" data-tour="admin-feature-flags">
      <header class="gov-combo__head">
        <h2>系统设置</h2>
        <n-button quaternary size="small" :loading="settingsLoading" @click="loadSettings()">刷新</n-button>
      </header>
      <div v-if="settingsLoading" class="gov-combo__empty">加载中…</div>
      <div v-else-if="settingsError" class="gov-combo__empty gov-combo__empty--err">{{ settingsError }}</div>
      <template v-else>
        <section class="gov-combo__section">
          <h3>界面主题</h3>
          <div class="gov-theme-options">
            <button
              v-for="opt in [
                { key: 'dark' as const, label: '深色' },
                { key: 'light' as const, label: '浅色' },
                { key: 'auto' as const, label: '跟随系统' },
              ]"
              :key="opt.key"
              type="button"
              class="gov-theme-btn"
              :class="{ 'gov-theme-btn--active': themeMode === opt.key }"
              @click="setTheme(opt.key)"
            >
              {{ opt.label }}
            </button>
          </div>
        </section>
        <section class="gov-combo__section">
          <h3>平台规则</h3>
          <label class="gov-field">
            <span>每日任务上限</span>
            <n-input v-model:value="settingsDailyLimit" style="width: 100px" />
          </label>
          <label class="gov-field">
            <span>开放时间</span>
            <n-input v-model:value="settingsOpenTime" placeholder="00:00" style="width: 120px" />
          </label>
          <label class="gov-field">
            <span>默认难度</span>
            <n-input-number v-model:value="settingsDifficulty" :min="0" :max="100" style="width: 120px" />
          </label>
        </section>
        <section class="gov-combo__section">
          <h3>通知开关</h3>
          <label
            v-for="item in settingsNotices"
            :key="item.key"
            class="gov-field gov-field--switch"
          >
            <span>{{ item.label }}</span>
            <n-switch v-model:value="item.enabled" size="small" />
          </label>
        </section>
        <n-button type="primary" :loading="settingsSaving" @click="saveSettings()">保存设置</n-button>
      </template>
    </div>
  </section>
</template>

<style scoped>
.gov-combo {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  min-height: 320px;
}

.gov-combo__tabs {
  display: flex;
  gap: 0.45rem;
  padding: 0.15rem;
  border-radius: 999px;
  background: rgba(88, 60, 180, 0.16);
  width: fit-content;
}

.gov-combo__tab {
  border: 0;
  border-radius: 999px;
  padding: 0.45rem 0.95rem;
  background: transparent;
  color: rgba(226, 214, 255, 0.72);
  cursor: pointer;
}

.gov-combo__tab--active {
  background: rgba(167, 139, 250, 0.28);
  color: #f5f3ff;
}

.gov-combo__pane :deep(.gov-class-panel) {
  border: 0;
  background: transparent;
  padding: 0;
  box-shadow: none;
}

.gov-combo__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.gov-combo__head h2 {
  margin: 0;
  font-size: 1rem;
}

.gov-combo__section {
  margin-bottom: 1rem;
}

.gov-combo__section h3 {
  margin: 0 0 0.55rem;
  color: rgba(214, 200, 255, 0.86);
  font-size: 0.86rem;
}

.gov-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
  color: rgba(226, 214, 255, 0.82);
  font-size: 0.86rem;
}

.gov-field--switch {
  padding: 0.35rem 0;
}

.gov-theme-options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.gov-theme-btn {
  border: 1px solid rgba(167, 139, 250, 0.28);
  border-radius: 999px;
  padding: 0.35rem 0.8rem;
  background: rgba(30, 20, 60, 0.55);
  color: rgba(226, 214, 255, 0.8);
  cursor: pointer;
}

.gov-theme-btn--active {
  border-color: rgba(196, 181, 253, 0.7);
  background: rgba(139, 92, 246, 0.35);
  color: #fff;
}

.gov-combo__empty {
  padding: 1.5rem 0;
  color: rgba(196, 181, 253, 0.7);
}

.gov-combo__empty--err {
  color: #fecaca;
}
</style>
