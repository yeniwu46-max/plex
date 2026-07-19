<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import PlexFileUploader from '../shared/upload/PlexFileUploader.vue'
import { fetchClassFiles, resolveUploadFileUrl, type ClassSharedFile } from '../../api/classFiles'
import { STUDENT_PRESETS, TEACHER_PRESETS } from '../../config/upload/uploadPresets'
import { formatFileSize } from '../../config/upload/uploadPresets'

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

const visibleFiles = computed(() => {
  if (props.role !== 'teacher' || !props.submissionsOnly) return files.value
  return files.value.filter((file) => file.owner_role === 'student' || file.scene === 'learning-report' || file.scene === 'code-file')
})

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

function openFile(file: ClassSharedFile) {
  window.open(resolveUploadFileUrl(file.url), '_blank')
}

onMounted(() => {
  void loadFiles()
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

@media (min-width: 900px) {
  .file-exchange__upload-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
