<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAvatar, NButton, NInput, NSwitch, NUpload, useMessage, type UploadFileInfo } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { useAuthStore } from '../stores/auth'
import { fetchStudentOverview, type StudentOverview } from '../api/studentOverview'
import { resolveAvatarUrl, updateMyProfile, uploadMyAvatar } from '../api/studentProfile'
import PlexRadarChart from '../components/charts/PlexRadarChart.vue'
import PlexLineChart from '../components/charts/PlexLineChart.vue'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
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
  return cls.name || `班级 #${cls.id}`
})

const avatarSrc = computed(() => {
  const url = avatarPreview.value || profile.value?.avatar_url || null
  return resolveAvatarUrl(url)
})

const notifyTrial = ref(true)
const notifyQuest = ref(true)
const notifyRank = ref(false)
const focusMode = ref(false)

function syncFormFromProfile() {
  editName.value = profile.value?.real_name || auth.profile?.real_name || ''
  editBio.value = profile.value?.bio || ''
  avatarPreview.value = profile.value?.avatar_url || ''
}

async function loadProfile() {
  loading.value = true
  try {
    overview.value = await fetchStudentOverview()
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

function savePreferences() {
  message.success('个人偏好已保存（本地演示）')
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
    active-nav="control"
    page-title="控制中枢"
    page-subtitle="管理你的探索偏好与账号信息"
    search-placeholder="搜索设置项…"
    hide-search
  >
    <section class="student-control" aria-label="学生控制中枢">
      <div class="student-control__hero">
        <div class="student-control__hero-main">
          <n-upload
            :show-file-list="false"
            accept="image/png,image/jpeg,image/gif,image/webp"
            @before-upload="handleBeforeUpload"
          >
            <button type="button" class="avatar-upload" :disabled="uploadingAvatar" aria-label="上传头像">
              <n-avatar round :size="72" :src="avatarSrc || undefined" class="avatar-upload__img">
                {{ displayName.slice(0, 1) }}
              </n-avatar>
              <span class="avatar-upload__hint">{{ uploadingAvatar ? '上传中…' : '更换头像' }}</span>
            </button>
          </n-upload>
          <div>
            <p class="student-control__eyebrow">EXPLORER CONTROL</p>
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
          <n-button type="primary" class="save-btn" :loading="savingProfile || loading" @click="saveProfile">
            保存资料
          </n-button>
        </article>

        <article class="panel">
          <header>
            <h3>探索偏好</h3>
            <p>通知与专注模式（本地保存演示）</p>
          </header>
          <ul class="pref-list">
            <li>
              <div>
                <strong>试炼提醒</strong>
                <span>班级试炼开放或即将结束时通知</span>
              </div>
              <n-switch v-model:value="notifyTrial" />
            </li>
            <li>
              <div>
                <strong>委托提醒</strong>
                <span>今日委托进度与奖励可领取时提醒</span>
              </div>
              <n-switch v-model:value="notifyQuest" />
            </li>
            <li>
              <div>
                <strong>排名变动</strong>
                <span>班级周榜名次变化时推送</span>
              </div>
              <n-switch v-model:value="notifyRank" />
            </li>
            <li>
              <div>
                <strong>专注模式</strong>
                <span>隐藏非必要动效，保持探索舱简洁</span>
              </div>
              <n-switch v-model:value="focusMode" />
            </li>
          </ul>
          <n-button type="primary" class="save-btn" :loading="loading" @click="savePreferences">保存偏好</n-button>
        </article>
      </div>

      <div class="student-control__charts">
        <article class="panel">
          <header>
            <h3>能力画像</h3>
            <p>基于历次试炼与星轨练习生成的多维能力雷达图</p>
          </header>
          <div class="student-control__chart-wrap">
            <plex-radar-chart
              :dimensions="['抽象建模', '算法设计', '分解问题', '调试能力', '逻辑推理']"
              :values="[
                Math.min(100, (profile?.total_points ?? 0) % 100 + 40),
                Math.min(100, (profile?.total_points ?? 0) % 90 + 35),
                Math.min(100, (profile?.total_points ?? 0) % 80 + 50),
                Math.min(100, (profile?.total_points ?? 0) % 70 + 60),
                Math.min(100, (profile?.total_points ?? 0) % 85 + 45),
              ]"
              color="#22c55e"
            />
          </div>
        </article>

        <article class="panel">
          <header>
            <h3>近 7 天学习趋势</h3>
            <p>练习次数与正确率变化曲线</p>
          </header>
          <div class="student-control__chart-wrap">
            <plex-line-chart
              :x-data="['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
              :series="[
                { name: '正确率(%)', data: [72, 78, 65, 85, 90, 88, 93], color: '#22c55e' },
                { name: '练习次数', data: [5, 8, 4, 10, 12, 9, 14], color: '#38bdf8' },
              ]"
            />
          </div>
        </article>
      </div>

      <p class="student-control__hint">
        班级规则、AI 策略与系统配置由教师在「教师端 · 控制中枢」管理；此处可修改你的 Explorer 昵称、签名与头像。
      </p>
    </section>
  </DashboardShell>
</template>

<style scoped>
.student-control {
  padding: 0 var(--plex-page-gutter-x) 2.5rem;
}

.student-control__hero {
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
}

.student-control__hero-main {
  display: flex;
  align-items: center;
  gap: 1.1rem;
}

.avatar-upload {
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

.avatar-upload:disabled {
  opacity: 0.65;
  cursor: wait;
}

.avatar-upload__img {
  border: 2px solid rgba(37, 245, 238, 0.35);
}

.avatar-upload__hint {
  color: #52fff1;
}

.student-control__eyebrow {
  margin: 0 0 0.35rem;
  color: #52fff1;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
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
}

.panel {
  padding: 1.25rem 1.35rem 1.4rem;
  border: 1px solid rgba(110, 228, 255, 0.12);
  border-radius: 16px;
  background: rgba(3, 16, 28, 0.78);
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

.pref-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.95rem;
}

.pref-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.pref-list strong {
  display: block;
  color: #edf7ff;
  font-size: 0.95rem;
}

.pref-list span {
  display: block;
  margin-top: 0.2rem;
  color: rgba(198, 214, 230, 0.62);
  font-size: 0.8rem;
}

.save-btn {
  margin-top: 0.25rem;
}

.student-control__charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  margin-top: 1.25rem;
}

.student-control__chart-wrap {
  height: 260px;
  margin-top: 0.5rem;
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
