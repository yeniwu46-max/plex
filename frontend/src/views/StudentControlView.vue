<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAvatar, NButton, NInput, NUpload, useMessage, type UploadFileInfo } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { useAuthStore } from '../stores/auth'
import type { StudentOverview } from '../api/studentOverview'
import { useStudentWorkspaceStore } from '../stores/studentWorkspace'
import { resolveAvatarUrl, updateMyProfile, uploadMyAvatar } from '../api/studentProfile'
import StudentJoinClassPanel from '../components/student/StudentJoinClassPanel.vue'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const workspace = useStudentWorkspaceStore()
const overview = ref<StudentOverview | null>(null)
const loading = ref(true)
const savingProfile = ref(false)
const uploadingAvatar = ref(false)

const editName = ref('')
const editBio = ref('')
const avatarPreview = ref('')

const profile = computed(() => overview.value?.profile)
const displayName = computed(
  () => profile.value?.real_name || profile.value?.username || auth.profile?.real_name || 'Explorer',
)
const classLabel = computed(() => {
  const cls = profile.value?.class
  if (!cls) return '暂未加入班级'
  const code = cls.join_code ? ` · 编号 ${cls.join_code}` : ''
  return `${cls.name || `班级 #${cls.id}`}${code}`
})
const hasClass = computed(() => Boolean(profile.value?.class?.id))

const avatarSrc = computed(() => {
  const url = avatarPreview.value || profile.value?.avatar_url || auth.profile?.avatar_url || null
  return url ? resolveAvatarUrl(url) : undefined
})

function syncFormFromProfile() {
  editName.value = profile.value?.real_name || auth.profile?.real_name || ''
  editBio.value = profile.value?.bio || ''
  avatarPreview.value = profile.value?.avatar_url || ''
}

async function loadProfile() {
  loading.value = true
  try {
    overview.value = await workspace.loadOverview()
    syncFormFromProfile()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '资料加载失败')
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  const name = editName.value.trim()
  if (!name) {
    message.warning('昵称不能为空')
    return
  }
  savingProfile.value = true
  try {
    await updateMyProfile({
      real_name: name,
      bio: editBio.value.trim(),
    })
    auth.syncProfile({
      real_name: name,
      bio: editBio.value.trim(),
      avatar_url: avatarPreview.value || profile.value?.avatar_url,
    })
    message.success('个人资料已保存')
    await loadProfile()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    savingProfile.value = false
  }
}

function handleBeforeUpload(data: { file: UploadFileInfo }) {
  void onAvatarUpload(data.file)
  return false
}

async function onAvatarUpload(fileInfo: UploadFileInfo) {
  const raw = fileInfo.file
  if (!raw) return
  if (raw.size > 2 * 1024 * 1024) {
    message.warning('图片不能超过 2MB')
    return
  }
  uploadingAvatar.value = true
  try {
    const url = await uploadMyAvatar(raw)
    avatarPreview.value = url
    auth.syncProfile({ avatar_url: url })
    message.success('头像已更新')
    await loadProfile()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '头像上传失败')
  } finally {
    uploadingAvatar.value = false
  }
}

async function logout() {
  await auth.logout()
  void router.replace('/login')
}

onMounted(() => {
  void loadProfile()
})
</script>

<template>
  <DashboardShell
    active-nav="me"
    page-title="账号设置"
    page-subtitle="管理个人资料与班级归属"
    search-placeholder="搜索设置项…"
    hide-search
  >
    <section class="student-control" aria-label="学生账号设置">
      <div class="student-control__hero">
        <span class="student-control__hero-scan" aria-hidden="true" />
        <span class="student-control__hero-corner student-control__hero-corner--tl" aria-hidden="true" />
        <span class="student-control__hero-corner student-control__hero-corner--tr" aria-hidden="true" />
        <span class="student-control__hero-corner student-control__hero-corner--bl" aria-hidden="true" />
        <span class="student-control__hero-corner student-control__hero-corner--br" aria-hidden="true" />
        <div class="student-control__hero-main">
          <n-upload
            :show-file-list="false"
            accept="image/png,image/jpeg,image/gif,image/webp"
            @before-upload="handleBeforeUpload"
          >
            <div class="avatar-upload" :class="{ 'avatar-upload--disabled': uploadingAvatar }" role="button" tabindex="0" aria-label="上传头像">
              <span class="avatar-upload__ring" aria-hidden="true" />
              <n-avatar round :size="72" :src="avatarSrc" class="avatar-upload__img">
                {{ displayName.slice(0, 1) }}
              </n-avatar>
              <span class="avatar-upload__hint">{{ uploadingAvatar ? '上传中…' : '更换头像' }}</span>
            </div>
          </n-upload>
          <div>
            <p class="student-control__eyebrow"><span class="student-control__status-dot" aria-hidden="true" />EXPLORER CONTROL</p>
            <h2>{{ displayName }}</h2>
            <p class="student-control__meta">
              <span>@{{ profile?.username || auth.profile?.username }}</span>
              <span>{{ classLabel }}</span>
              <span>Lv.{{ profile?.level ?? auth.profile?.level ?? 1 }}</span>
            </p>
          </div>
        </div>
        <n-button quaternary class="logout-btn" @click="logout">退出登录</n-button>
      </div>

      <div class="student-control__grid">
        <article class="panel">
          <header>
            <h3>个人资料</h3>
            <p>设置昵称与个性签名，头像支持 png/jpg/gif/webp（≤2MB）</p>
          </header>
          <label class="profile-field">
            <span>昵称</span>
            <n-input v-model:value="editName" placeholder="探索者昵称" maxlength="32" show-count />
          </label>
          <label class="profile-field">
            <span>个性签名</span>
            <n-input
              v-model:value="editBio"
              type="textarea"
              placeholder="写一句属于你的探索宣言…"
              :autosize="{ minRows: 2, maxRows: 4 }"
              maxlength="120"
              show-count
            />
          </label>
          <dl class="info-list info-list--compact">
            <div>
              <dt>所属班级</dt>
              <dd>{{ classLabel }}</dd>
            </div>
            <div>
              <dt>邮箱</dt>
              <dd>{{ profile?.email || auth.profile?.email || '—' }}</dd>
            </div>
            <div>
              <dt>累计 XP</dt>
              <dd>{{ profile?.total_points ?? auth.profile?.total_points ?? 0 }}</dd>
            </div>
            <div>
              <dt>连续探索</dt>
              <dd>{{ profile?.consecutive_days ?? 0 }} 天</dd>
            </div>
            <div>
              <dt>班级排名</dt>
              <dd>{{ profile?.class_rank ? `第 ${profile.class_rank} 名` : '暂无' }}</dd>
            </div>
          </dl>
          <div class="panel__footer">
            <n-button type="primary" class="save-btn" :loading="savingProfile || loading" @click="saveProfile">
              保存资料
            </n-button>
          </div>
        </article>

        <student-join-class-panel class="panel panel--join" :has-class="hasClass" @joined="loadProfile" />
      </div>

      <p class="student-control__hint">
        班级规则、AI 策略与系统配置由教师在「教师端 · 控制中枢」管理；此处可修改你的 Explorer 昵称、签名与头像。
      </p>
    </section>
  </DashboardShell>
</template>

<style scoped>
.student-control {
  flex: 1;
  width: 100%;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  overflow-y: auto;
  padding: 0 var(--plex-page-gutter-x) 2.5rem;
}

.student-control__hero {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1.35rem 1.5rem;
  border: 1px solid rgba(37, 245, 238, 0.18);
  border-radius: 18px;
  background:
    radial-gradient(circle at 12% 20%, rgba(37, 245, 238, 0.12), transparent 42%),
    linear-gradient(135deg, rgba(8, 32, 48, 0.92), rgba(4, 14, 24, 0.96));
  backdrop-filter: blur(14px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 0 32px rgba(37, 245, 238, 0.06);
  overflow: hidden;
}

.student-control__hero-scan {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(37, 245, 238, 0.04) 50%, transparent 100%);
  background-size: 100% 220%;
  animation: hero-scan 5s ease-in-out infinite;
  pointer-events: none;
}

.student-control__hero-corner {
  position: absolute;
  width: 14px;
  height: 14px;
  border-color: rgba(37, 245, 238, 0.55);
  border-style: solid;
  opacity: 0.85;
  pointer-events: none;
}

.student-control__hero-corner--tl {
  top: 10px;
  left: 10px;
  border-width: 2px 0 0 2px;
}

.student-control__hero-corner--tr {
  top: 10px;
  right: 10px;
  border-width: 2px 2px 0 0;
}

.student-control__hero-corner--bl {
  bottom: 10px;
  left: 10px;
  border-width: 0 0 2px 2px;
}

.student-control__hero-corner--br {
  right: 10px;
  bottom: 10px;
  border-width: 0 2px 2px 0;
}

@keyframes hero-scan {
  0%,
  100% {
    background-position: 0 -120%;
  }
  50% {
    background-position: 0 120%;
  }
}

.student-control__hero-main {
  display: flex;
  align-items: center;
  gap: 1.1rem;
}

.avatar-upload {
  position: relative;
  display: grid;
  gap: 0.35rem;
  justify-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: rgba(214, 230, 244, 0.72);
  font-size: 0.75rem;
}

.avatar-upload__ring {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 1px dashed rgba(37, 245, 238, 0.45);
  transform: translateX(-50%);
  animation: avatar-ring-spin 10s linear infinite;
  pointer-events: none;
}

@keyframes avatar-ring-spin {
  to {
    transform: translateX(-50%) rotate(360deg);
  }
}

.avatar-upload--disabled {
  opacity: 0.65;
  cursor: wait;
  pointer-events: none;
}

.avatar-upload__img {
  border: 2px solid rgba(37, 245, 238, 0.35);
  box-shadow: 0 0 22px rgba(37, 245, 238, 0.22);
}

.avatar-upload__hint {
  color: #52fff1;
}

.student-control__eyebrow {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0 0 0.35rem;
  color: #52fff1;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.student-control__status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #52fff1;
  box-shadow: 0 0 10px rgba(82, 255, 241, 0.85);
  animation: status-pulse 2s ease-in-out infinite;
}

@keyframes status-pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(0.92);
  }
  50% {
    opacity: 1;
    transform: scale(1.08);
  }
}

.student-control__hero h2 {
  margin: 0;
  font-size: 1.65rem;
  font-weight: 760;
  color: #f4fbff;
}

.student-control__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem 1rem;
  margin: 0.55rem 0 0;
  color: rgba(214, 230, 244, 0.72);
  font-size: 0.9rem;
}

.logout-btn {
  color: rgba(255, 196, 160, 0.92);
}

.student-control__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  width: 100%;
  align-items: stretch;
}

.panel {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding: 1.25rem 1.35rem 1.4rem;
  border: 1px solid rgba(110, 228, 255, 0.12);
  border-radius: 16px;
  background: rgba(3, 16, 28, 0.78);
}

.panel__footer {
  display: flex;
  align-items: center;
  margin-top: auto;
  padding-top: 1rem;
}

.panel--join :deep(.join-class) {
  height: 100%;
}

.panel header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #eef8ff;
}

.panel header p {
  margin: 0.35rem 0 1rem;
  color: rgba(205, 220, 235, 0.62);
  font-size: 0.85rem;
}

.profile-field {
  display: grid;
  gap: 0.4rem;
  margin-bottom: 0.9rem;
}

.profile-field > span {
  color: rgba(198, 214, 230, 0.68);
  font-size: 0.86rem;
}

.info-list {
  margin: 0 0 1rem;
  display: grid;
  gap: 0.85rem;
}

.info-list--compact {
  margin-top: 0.25rem;
}

.info-list div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.info-list dt {
  margin: 0;
  color: rgba(198, 214, 230, 0.68);
  font-size: 0.86rem;
}

.info-list dd {
  margin: 0;
  color: #e8f7ff;
  font-weight: 650;
}

.save-btn {
  margin-top: 0;
}

.student-control__hint {
  margin: 1.25rem 0 0;
  color: rgba(190, 208, 224, 0.58);
  font-size: 0.82rem;
  line-height: 1.55;
}

@media (max-width: 900px) {
  .student-control__grid {
    grid-template-columns: 1fr;
  }

  .student-control__hero {
    flex-direction: column;
  }
}
</style>
