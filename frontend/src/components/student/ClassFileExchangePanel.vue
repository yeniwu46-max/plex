<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton, NModal, NSlider, NSpin, useMessage } from 'naive-ui'
import PlexFileUploader from '../shared/upload/PlexFileUploader.vue'
import {
  fetchClassFiles,
  fetchUploadFileBlob,
  filePathFromUrl,
  isImagePreviewType,
  isPdfPreviewType,
  isTextPreviewType,
  saveClassFileScore,
  type ClassSharedFile,
} from '../../api/classFiles'
import { STUDENT_PRESETS, TEACHER_PRESETS, formatFileSize } from '../../config/upload/uploadPresets'

const props = withDefaults(
  defineProps<{
    role: 'student' | 'teacher'
    classId?: number | null
    /** 资源审核页仅展示学生提交，隐藏教师上传区 */
    submissionsOnly?: boolean
  }>(),
  { classId: null, submissionsOnly: false },
)

const message = useMessage()
const loading = ref(false)
const files = ref<ClassSharedFile[]>([])
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewFile = ref<ClassSharedFile | null>(null)
const previewKind = ref<'text' | 'pdf' | 'image' | 'unsupported'>('unsupported')
const previewText = ref('')
const previewObjectUrl = ref<string | null>(null)
const gradeScore = ref(80)
const savingScore = ref(false)
const QUICK_SCORES = [60, 70, 80, 90] as const

const visibleFiles = computed(() => {
  if (props.role !== 'teacher' || !props.submissionsOnly) return files.value
  return files.value.filter(
    (file) => file.owner_role === 'student' || file.scene === 'learning-report' || file.scene === 'code-file',
  )
})

const canGrade = computed(
  () => props.role === 'teacher' && Boolean(previewFile.value && previewFile.value.owner_role === 'student'),
)

const sceneLabels: Record<string, string> = {
  'course-material': '课程资料',
  'assignment-attachment': '作业附件',
  'code-file': '代码文件',
  'learning-report': '学习报告',
  screenshot: '学习截图',
}

async function loadFiles() {
  loading.value = true
  try {
    const result = await fetchClassFiles()
    files.value = result.items
  } catch (error) {
    message.error(error instanceof Error ? error.message : '文件列表加载失败')
  } finally {
    loading.value = false
  }
}

function revokePreviewUrl() {
  if (previewObjectUrl.value) {
    URL.revokeObjectURL(previewObjectUrl.value)
    previewObjectUrl.value = null
  }
}

async function openFile(file: ClassSharedFile) {
  revokePreviewUrl()
  previewFile.value = file
  previewText.value = ''
  previewKind.value = 'unsupported'
  gradeScore.value = typeof file.score === 'number' ? file.score : 80
  previewVisible.value = true
  previewLoading.value = true
  try {
    const blob = await fetchUploadFileBlob(file.url)
    if (isTextPreviewType(file.fileType, file.fileName)) {
      previewKind.value = 'text'
      previewText.value = await blob.text()
    } else if (isPdfPreviewType(file.fileType, file.fileName)) {
      previewKind.value = 'pdf'
      previewObjectUrl.value = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
    } else if (isImagePreviewType(file.fileType, file.fileName)) {
      previewKind.value = 'image'
      previewObjectUrl.value = URL.createObjectURL(blob)
    } else {
      previewKind.value = 'unsupported'
      previewObjectUrl.value = URL.createObjectURL(blob)
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '文件预览失败')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

function downloadPreview() {
  if (!previewFile.value) return
  let href = previewObjectUrl.value
  if (!href && previewKind.value === 'text' && previewText.value) {
    href = URL.createObjectURL(new Blob([previewText.value], { type: 'text/plain;charset=utf-8' }))
  }
  if (!href) return
  const anchor = document.createElement('a')
  anchor.href = href
  anchor.download = previewFile.value.fileName
  anchor.click()
  if (!previewObjectUrl.value && href) URL.revokeObjectURL(href)
}

function closePreview() {
  previewVisible.value = false
  revokePreviewUrl()
  previewFile.value = null
  previewText.value = ''
}

async function saveScore() {
  if (!previewFile.value || !canGrade.value || savingScore.value) return
  savingScore.value = true
  try {
    const filepath = filePathFromUrl(previewFile.value.url)
    const result = await saveClassFileScore(filepath, Math.round(gradeScore.value))
    const score = result.score ?? Math.round(gradeScore.value)
    previewFile.value = { ...previewFile.value, score, scored_at: result.scored_at }
    files.value = files.value.map((item) =>
      item.url === previewFile.value?.url ? { ...item, score, scored_at: result.scored_at } : item,
    )
    message.success(`已保存评分 ${score} 分`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '评分保存失败')
  } finally {
    savingScore.value = false
  }
}

watch(previewVisible, (show) => {
  if (!show) closePreview()
})

onMounted(() => {
  void loadFiles()
})

onBeforeUnmount(() => {
  revokePreviewUrl()
})

defineExpose({ reload: loadFiles })
</script>

<template>
  <section
    class="file-exchange"
    :class="{ 'file-exchange--teacher': role === 'teacher' }"
    :aria-label="role === 'student' ? '班级资料' : submissionsOnly ? '学生提交审核' : '学生提交'"
  >
    <header class="file-exchange__header">
      <div>
        <h3>{{ role === 'student' ? '教师共享资料' : submissionsOnly ? '学生提交文件审核' : '学生提交文件' }}</h3>
        <p>
          {{
            role === 'student'
              ? '查看教师上传的课程资料与作业附件'
              : submissionsOnly
                ? '审核班级学生提交的学习报告、代码与学习截图'
                : '查看班级学生提交的学习报告与代码文件'
          }}
        </p>
      </div>
      <n-button size="small" quaternary :loading="loading" @click="loadFiles">刷新</n-button>
    </header>

    <div v-if="loading && !files.length" class="file-exchange__empty">正在加载文件…</div>
    <div v-else-if="!visibleFiles.length" class="file-exchange__empty">
      {{ role === 'student' ? (classId ? '教师尚未共享文件' : '加入班级后可接收教师资料') : '暂无学生提交' }}
    </div>
    <ul v-else class="file-exchange__list">
      <li v-for="file in visibleFiles" :key="`${file.owner_id}-${file.url}`" class="file-exchange__item">
        <div>
          <strong>{{ file.fileName }}</strong>
          <span>
            {{ sceneLabels[file.scene] || file.scene }}
            · {{ file.owner_name || '未知' }}
            · {{ formatFileSize(file.fileSize) }}
            <template v-if="typeof file.score === 'number'"> · 已评分 {{ file.score }}</template>
          </span>
        </div>
        <n-button size="small" type="primary" ghost @click="openFile(file)">查看</n-button>
      </li>
    </ul>

    <div v-if="!submissionsOnly" class="file-exchange__upload">
      <h4>{{ role === 'student' ? '提交给教师' : '共享给学生' }}</h4>
      <div v-if="role === 'student'" class="file-exchange__upload-grid">
        <plex-file-uploader role="student" v-bind="STUDENT_PRESETS.learningReport" @upload-success="loadFiles" />
        <plex-file-uploader role="student" v-bind="STUDENT_PRESETS.codeFile" @upload-success="loadFiles" />
      </div>
      <div v-else class="file-exchange__upload-grid">
        <plex-file-uploader role="teacher" v-bind="TEACHER_PRESETS.courseMaterial" @upload-success="loadFiles" />
        <plex-file-uploader role="teacher" v-bind="TEACHER_PRESETS.assignmentAttachment" @upload-success="loadFiles" />
      </div>
    </div>

    <n-modal
      v-model:show="previewVisible"
      preset="card"
      :title="previewFile?.fileName || '文件预览'"
      class="file-preview-modal"
      :bordered="false"
      :z-index="5300"
      style="width: min(860px, calc(100vw - 32px))"
      @after-leave="closePreview"
    >
      <n-spin :show="previewLoading">
        <pre v-if="previewKind === 'text'" class="file-preview__code">{{ previewText }}</pre>
        <iframe
          v-else-if="previewKind === 'pdf' && previewObjectUrl"
          class="file-preview__frame"
          :src="previewObjectUrl"
          title="PDF 预览"
        />
        <img
          v-else-if="previewKind === 'image' && previewObjectUrl"
          class="file-preview__image"
          :src="previewObjectUrl"
          :alt="previewFile?.fileName || '图片预览'"
        />
        <div v-else class="file-preview__fallback">
          <p>该文件类型暂不支持在线预览，可下载后查看。</p>
          <n-button
            type="primary"
            :disabled="!previewObjectUrl && !(previewKind === 'text' && previewText)"
            @click="downloadPreview"
          >
            下载文件
          </n-button>
        </div>
      </n-spin>

      <section v-if="canGrade" class="file-preview__grade" aria-label="作业打分">
        <header>
          <strong>作业打分</strong>
          <span>{{ Math.round(gradeScore) }} 分</span>
        </header>
        <n-slider v-model:value="gradeScore" :min="0" :max="100" :step="1" />
        <div class="file-preview__quick">
          <n-button
            v-for="score in QUICK_SCORES"
            :key="score"
            size="small"
            secondary
            :type="Math.round(gradeScore) === score ? 'warning' : 'default'"
            @click="gradeScore = score"
          >
            {{ score }}
          </n-button>
        </div>
        <n-button type="warning" :loading="savingScore" @click="saveScore">保存评分</n-button>
      </section>
    </n-modal>
  </section>
</template>

<style scoped>
.file-exchange {
  padding: 1.2rem 1.35rem;
  border: 1px solid rgba(52, 230, 197, 0.14);
  border-radius: 16px;
  background: rgba(3, 16, 28, 0.78);
}

.file-exchange--teacher {
  border-color: rgba(249, 115, 22, 0.22);
  background:
    linear-gradient(145deg, rgba(67, 20, 7, 0.35), rgba(3, 16, 28, 0.78)),
    rgba(3, 16, 28, 0.78);
}

.file-exchange--teacher .file-exchange__header h3 {
  color: #fed7aa;
}

.file-exchange__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.file-exchange__header h3 {
  margin: 0;
  color: #eef8ff;
  font-size: 1.05rem;
}

.file-exchange__header p {
  margin: 0.35rem 0 0;
  color: rgba(205, 220, 235, 0.62);
  font-size: 0.85rem;
}

.file-exchange__empty {
  padding: 1rem 0;
  color: rgba(190, 208, 224, 0.62);
  font-size: 0.88rem;
}

.file-exchange__list {
  margin: 0 0 1.25rem;
  padding: 0;
  list-style: none;
}

.file-exchange__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.file-exchange__item strong {
  display: block;
  color: #e8f7ff;
  font-size: 0.92rem;
}

.file-exchange__item span {
  display: block;
  margin-top: 0.2rem;
  color: rgba(190, 208, 224, 0.62);
  font-size: 0.78rem;
}

.file-exchange__upload h4 {
  margin: 0 0 0.75rem;
  color: rgba(214, 230, 244, 0.82);
  font-size: 0.92rem;
}

.file-exchange__upload-grid {
  display: grid;
  gap: 1rem;
}

.file-preview__code {
  margin: 0;
  max-height: min(56vh, 520px);
  overflow: auto;
  padding: 1rem;
  border-radius: 12px;
  background: rgba(2, 8, 16, 0.92);
  color: #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.file-preview__frame {
  display: block;
  width: 100%;
  height: min(56vh, 520px);
  border: none;
  border-radius: 12px;
  background: #0b1220;
}

.file-preview__image {
  display: block;
  max-width: 100%;
  max-height: min(56vh, 520px);
  margin: 0 auto;
  border-radius: 12px;
}

.file-preview__fallback {
  display: grid;
  gap: 0.85rem;
  justify-items: start;
  color: rgba(203, 213, 225, 0.78);
}

.file-preview__grade {
  margin-top: 1rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(251, 146, 60, 0.24);
  border-radius: 12px;
  background: rgba(67, 20, 7, 0.28);
  display: grid;
  gap: 0.75rem;
}

.file-preview__grade header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fed7aa;
}

.file-preview__grade header span {
  font-weight: 700;
  color: #fff7ed;
}

.file-preview__quick {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

@media (min-width: 900px) {
  .file-exchange__upload-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

<style>
.file-preview-modal.n-card {
  background: rgba(8, 14, 22, 0.98) !important;
  border: 1px solid rgba(251, 146, 60, 0.22) !important;
}

.file-preview-modal .n-card-header__main {
  color: #fff7ed !important;
}
</style>
