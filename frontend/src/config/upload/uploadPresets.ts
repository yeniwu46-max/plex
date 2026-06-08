import type {
  AdminPresetKey,
  StudentPresetKey,
  TeacherPresetKey,
  UploadPresetConfig,
  UploadPresetKey,
  UploadRole,
} from '../../types/upload'

export const STUDENT_PRESETS: Record<StudentPresetKey, UploadPresetConfig> = {
  codeFile: {
    scene: 'code-file',
    title: '上传代码文件',
    description: '支持上传 .py、.txt 文件，用于代码记录与 AI 分析。',
    accept: ['.py', '.txt'],
    maxFileSize: 2 * 1024 * 1024,
    maxNumberOfFiles: 5,
    multiple: true,
  },
  learningReport: {
    scene: 'learning-report',
    title: '上传学习报告',
    description: '支持上传 PDF、Word 或 Markdown 文件，作为学习过程记录。',
    accept: ['.pdf', '.doc', '.docx', '.md'],
    maxFileSize: 10 * 1024 * 1024,
    maxNumberOfFiles: 3,
    multiple: true,
  },
  screenshot: {
    scene: 'screenshot',
    title: '上传学习截图',
    description: '支持上传 PNG、JPG 图片，用于记录运行结果或问题反馈。',
    accept: ['.png', '.jpg', '.jpeg'],
    maxFileSize: 5 * 1024 * 1024,
    maxNumberOfFiles: 6,
    multiple: true,
  },
}

export const TEACHER_PRESETS: Record<TeacherPresetKey, UploadPresetConfig> = {
  courseMaterial: {
    scene: 'course-material',
    title: '上传课程资料',
    description: '支持上传课件、讲义、PDF 文档，后续可进入知识库解析流程。',
    accept: ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.md'],
    maxFileSize: 50 * 1024 * 1024,
    maxNumberOfFiles: 10,
    multiple: true,
  },
  questionBank: {
    scene: 'question-bank',
    title: '上传题库文件',
    description: '支持上传 Excel、CSV 或 JSON 题库文件，用于批量导入练习题。',
    accept: ['.xlsx', '.xls', '.csv', '.json'],
    maxFileSize: 20 * 1024 * 1024,
    maxNumberOfFiles: 5,
    multiple: true,
  },
  assignmentAttachment: {
    scene: 'assignment-attachment',
    title: '上传作业附件',
    description: '支持上传作业说明、参考资料或补充文件。',
    accept: ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.zip'],
    maxFileSize: 50 * 1024 * 1024,
    maxNumberOfFiles: 8,
    multiple: true,
  },
}

export const ADMIN_PRESETS: Record<AdminPresetKey, UploadPresetConfig> = {
  knowledgeDoc: {
    scene: 'knowledge-doc',
    title: '上传知识库文档',
    description: '支持上传课程文档、知识说明和系统资料，用于后续 RAG 知识库构建。',
    accept: ['.pdf', '.doc', '.docx', '.md', '.txt'],
    maxFileSize: 100 * 1024 * 1024,
    maxNumberOfFiles: 20,
    multiple: true,
  },
  systemConfig: {
    scene: 'system-config',
    title: '上传系统配置',
    description: '支持上传 JSON 或 YAML 配置文件，用于系统参数导入。',
    accept: ['.json', '.yaml', '.yml'],
    maxFileSize: 5 * 1024 * 1024,
    maxNumberOfFiles: 3,
    multiple: true,
  },
  graphData: {
    scene: 'graph-data',
    title: '上传图谱数据',
    description: '支持上传知识图谱节点与关系数据。',
    accept: ['.json', '.csv', '.xlsx'],
    maxFileSize: 20 * 1024 * 1024,
    maxNumberOfFiles: 5,
    multiple: true,
  },
}

const ALL_PRESETS: Record<string, UploadPresetConfig> = {
  ...STUDENT_PRESETS,
  ...TEACHER_PRESETS,
  ...ADMIN_PRESETS,
}

export function getUploadPreset(role: UploadRole, presetKey: UploadPresetKey): UploadPresetConfig {
  const preset = ALL_PRESETS[presetKey]
  if (!preset) throw new Error(`Unknown upload preset: ${presetKey} for role ${role}`)
  return preset
}

/** 场景→允许角色映射，供前端预校验 */
export const SCENE_ROLE_MATRIX: Record<string, UploadRole[]> = {
  'code-file': ['student'],
  'learning-report': ['student'],
  screenshot: ['student'],
  'course-material': ['teacher', 'admin'],
  'question-bank': ['teacher', 'admin'],
  'assignment-attachment': ['teacher', 'admin'],
  'knowledge-doc': ['admin'],
  'system-config': ['admin'],
  'graph-data': ['admin'],
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
