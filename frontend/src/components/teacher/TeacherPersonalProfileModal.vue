<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NAvatar,
  NButton,
  NEmpty,
  NInput,
  NModal,
  NSelect,
  NSpin,
  NTag,
  NUpload,
  useMessage,
  type SelectOption,
  type UploadFileInfo,
} from 'naive-ui'
import {
  fetchTeacherPersonalProfile,
  type TeacherPersonalProfile,
} from '../../api/teacherPresence'
import { resolveAvatarUrl, updateMyProfile, uploadMyAvatar } from '../../api/studentProfile'
import { useAuthStore } from '../../stores/auth'

const props = defineProps<{
  show: boolean
  /** 外部直接传入时不请求当前登录教师接口，且只读（学生查看任课教师） */
  profile?: TeacherPersonalProfile | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const message = useMessage()
const auth = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const uploadingAvatar = ref(false)
const errorText = ref('')
const loaded = ref<TeacherPersonalProfile | null>(null)
const editing = ref(false)

const formName = ref('')
const formPhone = ref('')
const formGender = ref('other')
const formBio = ref('')
const avatarPreview = ref('')

const readonly = computed(() => Boolean(props.profile))
const data = computed(() => props.profile ?? loaded.value)

const genderOptions: SelectOption[] = [
  { label: '未设置', value: 'other' },
  { label: '男', value: 'male' },
  { label: '女', value: 'female' },
]

const genderLabel = computed(() => {
  const g = editing.value ? formGender.value : data.value?.gender
  if (g === 'male') return '男'
  if (g === 'female') return '女'
  return '未设置'
})

const displayName = computed(
  () => (editing.value ? formName.value : data.value?.real_name) || data.value?.username || '教师',
)

const avatarSrc = computed(() => {
  const url = editing.value
    ? avatarPreview.value || data.value?.avatar_url
    : data.value?.avatar_url
  return url ? resolveAvatarUrl(url) : undefined
})

function syncForm(source: TeacherPersonalProfile | null | undefined) {
  formName.value = source?.real_name || source?.username || ''
  formPhone.value = source?.phone || ''
  formGender.value = source?.gender || 'other'
  formBio.value = source?.bio || ''
  avatarPreview.value = source?.avatar_url || ''
}

async function load() {
  if (props.profile) {
    syncForm(props.profile)
    editing.value = false
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    loaded.value = await fetchTeacherPersonalProfile()
    syncForm(loaded.value)
    editing.value = false
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : '加载失败'
    loaded.value = null
  } finally {
    loading.value = false
  }
}

function startEdit() {
  if (readonly.value) return
  syncForm(data.value)
  editing.value = true
}

function cancelEdit() {
  syncForm(data.value)
  editing.value = false
}

async function saveProfile() {
  const name = formName.value.trim()
  if (!name) {
    message.warning('姓名不能为空')
    return
  }
  saving.value = true
  try {
    await updateMyProfile({
      real_name: name,
      phone: formPhone.value.trim() || '',
      gender: formGender.value || 'other',
      bio: formBio.value.trim(),
      avatar_url: avatarPreview.value || undefined,
    })
    auth.syncProfile({
      real_name: name,
      bio: formBio.value.trim() || null,
      avatar_url: avatarPreview.value || data.value?.avatar_url || null,
    })
    message.success('教师资料已保存')
    editing.value = false
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function handleBeforeUpload(payload: { file: UploadFileInfo }) {
  void onAvatarUpload(payload.file)
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
    if (!editing.value) {
      // 非编辑态直接上传时立刻同步资料
      await updateMyProfile({ avatar_url: url })
      auth.syncProfile({ avatar_url: url })
      message.success('头像已更新')
      await load()
    } else {
      message.success('头像已更换，记得保存资料')
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '头像上传失败')
  } finally {
    uploadingAvatar.value = false
  }
}

watch(
  () => props.show,
  (open) => {
    if (open) void load()
  },
)
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    title="教师个人信息"
    :bordered="false"
    style="width: min(520px, calc(100vw - 32px))"
    @update:show="emit('update:show', $event)"
  >
    <div v-if="loading" class="teacher-profile-modal__state"><n-spin size="small" /> 加载中…</div>
    <p v-else-if="errorText" class="teacher-profile-modal__error">{{ errorText }}</p>
    <n-empty v-else-if="!data" description="暂无教师信息" />
    <div v-else class="teacher-profile-modal">
      <header>
        <n-upload
          v-if="!readonly"
          :show-file-list="false"
          accept="image/png,image/jpeg,image/gif,image/webp"
          @before-upload="handleBeforeUpload"
        >
          <div
            class="teacher-profile-modal__avatar"
            :class="{ 'teacher-profile-modal__avatar--busy': uploadingAvatar }"
            role="button"
            tabindex="0"
            aria-label="上传头像"
          >
            <n-avatar round :size="64" :src="avatarSrc">
              {{ displayName.slice(0, 1) }}
            </n-avatar>
            <span>{{ uploadingAvatar ? '上传中…' : '更换' }}</span>
          </div>
        </n-upload>
        <n-avatar v-else round :size="64" :src="avatarSrc">
          {{ displayName.slice(0, 1) }}
        </n-avatar>
        <div class="teacher-profile-modal__identity">
          <template v-if="editing">
            <n-input v-model:value="formName" maxlength="40" placeholder="姓名或昵称" />
            <n-select v-model:value="formGender" :options="genderOptions" size="small" />
          </template>
          <template v-else>
            <strong>{{ displayName }}</strong>
            <p>
              {{ genderLabel }}
              ·
              <n-tag size="small" :type="data.online || data.status === 'active' ? 'success' : 'default'">
                {{ data.online || data.status === 'active' ? '在线' : data.status }}
              </n-tag>
            </p>
          </template>
        </div>
      </header>

      <dl>
        <div>
          <dt>联系方式</dt>
          <dd>
            <n-input
              v-if="editing"
              v-model:value="formPhone"
              maxlength="20"
              placeholder="手机号或其它联系方式"
            />
            <template v-else>{{ data.phone || '—' }}</template>
          </dd>
        </div>
        <div>
          <dt>邮箱</dt>
          <dd>{{ data.email || '—' }}</dd>
        </div>
        <div v-if="editing || data.bio">
          <dt>简介</dt>
          <dd>
            <n-input
              v-if="editing"
              v-model:value="formBio"
              type="textarea"
              :rows="2"
              maxlength="200"
              placeholder="一句话介绍自己"
              show-count
            />
            <template v-else>{{ data.bio }}</template>
          </dd>
        </div>
        <div>
          <dt>管理班级</dt>
          <dd>
            <template v-if="data.classes?.length">
              <span v-for="cls in data.classes" :key="cls.id" class="teacher-profile-modal__class">
                {{ cls.name }} · {{ cls.student_count }} 人
              </span>
            </template>
            <template v-else>—</template>
          </dd>
        </div>
      </dl>

      <footer v-if="!readonly" class="teacher-profile-modal__actions">
        <template v-if="editing">
          <n-button quaternary :disabled="saving" @click="cancelEdit">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveProfile">保存</n-button>
        </template>
        <n-button v-else type="primary" secondary @click="startEdit">修改资料</n-button>
      </footer>
    </div>
  </n-modal>
</template>

<style scoped>
.teacher-profile-modal__state,
.teacher-profile-modal__error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: rgba(214, 230, 244, 0.78);
}

.teacher-profile-modal__error {
  color: #ff9da5;
}

.teacher-profile-modal header {
  display: flex;
  gap: 0.9rem;
  align-items: center;
  margin-bottom: 1rem;
}

.teacher-profile-modal__identity {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 0.4rem;
}

.teacher-profile-modal strong {
  display: block;
  color: #fff7ed;
  font-size: 1.05rem;
}

.teacher-profile-modal header p {
  margin: 0;
  color: rgba(214, 230, 244, 0.72);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.teacher-profile-modal__avatar {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 999px;
  cursor: pointer;
  overflow: hidden;
}

.teacher-profile-modal__avatar span {
  position: absolute;
  inset: auto 0 0;
  padding: 0.15rem 0;
  background: rgba(4, 18, 28, 0.78);
  color: #9fe9ff;
  font-size: 0.68rem;
  text-align: center;
}

.teacher-profile-modal__avatar--busy {
  opacity: 0.7;
  pointer-events: none;
}

.teacher-profile-modal dl {
  margin: 0;
  display: grid;
  gap: 0.65rem;
}

.teacher-profile-modal dl > div {
  display: grid;
  grid-template-columns: 5.5rem 1fr;
  gap: 0.5rem;
  align-items: start;
  padding: 0.55rem 0.65rem;
  border-radius: 10px;
  background: rgba(4, 14, 24, 0.55);
  border: 1px solid rgba(130, 212, 255, 0.1);
}

.teacher-profile-modal dt {
  color: rgba(214, 230, 244, 0.55);
  font-size: 0.8rem;
  padding-top: 0.35rem;
}

.teacher-profile-modal dd {
  margin: 0;
  color: #eef8ff;
  font-size: 0.88rem;
}

.teacher-profile-modal__class {
  display: inline-block;
  margin-right: 0.55rem;
  margin-bottom: 0.25rem;
}

.teacher-profile-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
