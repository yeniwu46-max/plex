import { http } from './http'
import type { UploadResponse } from '../types/upload'

interface ApiEnvelopeUpload {
  code: number
  message: string
  data: UploadResponse
}

/**
 * 调用统一上传接口。由 usePlexUploader 通过 Uppy XHR 直接上传，
 * 此函数仅用于非 Uppy 场景（如单文件直传）。
 */
export async function uploadFile(
  file: File,
  meta: { role: string; scene: string; relatedId?: string },
): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('role', meta.role)
  form.append('scene', meta.scene)
  if (meta.relatedId) form.append('relatedId', meta.relatedId)

  const { data } = await http.post<ApiEnvelopeUpload>('/v1/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  if (data.code !== 0) throw new Error(data.message || '上传失败')
  return data.data
}

/** 后续处理 stub：进入知识库解析 */
export async function parseDocument(fileId: string): Promise<void> {
  await http.post('/v1/kb/parse-document', { fileId })
}

/** 后续处理 stub：导入题库 */
export async function importQuestions(fileId: string): Promise<void> {
  await http.post('/v1/questions/import', { fileId })
}

/** 后续处理 stub：AI 分析代码 */
export async function analyzeCodeFile(fileId: string): Promise<void> {
  await http.post('/v1/code/analyze-file', { fileId })
}

/** 后续处理 stub：校验图谱数据 */
export async function importGraphData(fileId: string): Promise<void> {
  await http.post('/v1/graph/import', { fileId })
}

/** 后续处理 stub：验证配置文件 */
export async function validateConfig(fileId: string): Promise<void> {
  await http.post('/v1/config/validate', { fileId })
}
