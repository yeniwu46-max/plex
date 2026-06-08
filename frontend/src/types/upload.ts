export type UploadScene =
  | 'code-file'
  | 'learning-report'
  | 'screenshot'
  | 'course-material'
  | 'question-bank'
  | 'assignment-attachment'
  | 'knowledge-doc'
  | 'system-config'
  | 'graph-data'

export type UploadStatus = 'idle' | 'queued' | 'uploading' | 'success' | 'error' | 'cancelled'

export type UploadRole = 'student' | 'teacher' | 'admin'

export interface UploadFileEntry {
  id: string
  name: string
  type: string
  size: number
  status: UploadStatus
  progress: number
  url?: string
  error?: string
  isDuplicate?: boolean
  uploadResponse?: UploadResponse
}

export interface UploadResponse {
  id: string
  fileName: string
  fileType: string
  fileSize: number
  url: string
  scene: UploadScene
  status: 'success' | 'failed'
  createdAt: string
}

export interface UploadRequestMeta {
  role: UploadRole
  scene: UploadScene
  relatedId?: string
}

export interface UploadPresetConfig {
  scene: UploadScene
  title: string
  description: string
  accept: string[]
  maxFileSize: number
  maxNumberOfFiles: number
  multiple: boolean
}

export type StudentPresetKey = 'codeFile' | 'learningReport' | 'screenshot'
export type TeacherPresetKey = 'courseMaterial' | 'questionBank' | 'assignmentAttachment'
export type AdminPresetKey = 'knowledgeDoc' | 'systemConfig' | 'graphData'
export type UploadPresetKey = StudentPresetKey | TeacherPresetKey | AdminPresetKey
