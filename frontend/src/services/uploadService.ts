/**
 * PLEX 文件上传服务
 *
 * 系统基于 Uppy 构建模块化文件上传能力，在不改变原有三端 UI 架构的前提下，
 * 为教师资料管理、学生学习档案、管理员知识库维护提供统一的数据入口。
 * 上传后的资料可进一步用于 RAG 知识库构建、AI 代码分析、题库导入与知识图谱维护，
 * 从而支撑平台后续的智能分析与自适应推荐能力。
 */

import type { UploadResponse, UploadScene } from '../types/upload'

/** 上传成功后的联动提示文案 */
export function getSuccessMessage(scene: UploadScene, fileName: string): string {
  const msgs: Record<UploadScene, string> = {
    'code-file': `代码文件「${fileName}」上传成功，可用于后续 AI 代码分析。`,
    'learning-report': `学习报告「${fileName}」上传成功，已加入学习档案。`,
    screenshot: `截图「${fileName}」上传成功，可在问题反馈中引用。`,
    'course-material': `课程资料「${fileName}」上传成功，可进入知识库解析流程。`,
    'question-bank': `题库文件「${fileName}」上传成功，可进入题目导入流程。`,
    'assignment-attachment': `作业附件「${fileName}」上传成功，已关联到当前作业。`,
    'knowledge-doc': `知识库文档「${fileName}」上传成功，可进入 RAG 构建流程。`,
    'system-config': `系统配置「${fileName}」上传成功，等待管理员确认导入。`,
    'graph-data': `图谱数据「${fileName}」上传成功，可进入知识图谱校验流程。`,
  }
  return msgs[scene] ?? `「${fileName}」上传成功。`
}

/** 后续处理操作定义，第一阶段 UI 按钮 disabled */
export interface FollowUpAction {
  label: string
  scene: UploadScene[]
  apiPath: string
  disabled: true
}

export const FOLLOW_UP_ACTIONS: FollowUpAction[] = [
  {
    label: '进入知识库解析',
    scene: ['knowledge-doc', 'course-material'],
    apiPath: '/v1/kb/parse-document',
    disabled: true,
  },
  {
    label: '导入题库',
    scene: ['question-bank'],
    apiPath: '/v1/questions/import',
    disabled: true,
  },
  {
    label: 'AI 分析代码',
    scene: ['code-file'],
    apiPath: '/v1/code/analyze-file',
    disabled: true,
  },
  {
    label: '校验图谱数据',
    scene: ['graph-data'],
    apiPath: '/v1/graph/import',
    disabled: true,
  },
  {
    label: '验证配置文件',
    scene: ['system-config'],
    apiPath: '/v1/config/validate',
    disabled: true,
  },
]

export function getFollowUpActions(scene: UploadScene): FollowUpAction[] {
  return FOLLOW_UP_ACTIONS.filter((a) => a.scene.includes(scene))
}

export function buildUploadedFileUrl(resp: UploadResponse): string {
  return resp.url
}
