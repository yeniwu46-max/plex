import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'
import { formatStarPathNodeLabel, getStarPathNode, getNodeOrderBonus } from '../data/starPathTrail'
import { getActiveMistakeRecords, type TrialMistakeRecord } from './trialMistakeLog'
import {
  filterMistakesByQuestionIds,
  mergeMistakesForRecommendation,
} from './studentMockMistakes'

export interface TrialRecommendationStep {
  label: string
  detail: string
}

export interface TrialPageRecommendation {
  recommendedQuestionId: string | null
  recommendedTitle: string | null
  matchPercent: number
  summary: string
  steps: TrialRecommendationStep[]
  rankedQuestionIds: string[]
}

function formatRelativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.floor(hours / 24)} 天前`
}

function errorTypeLabel(types: TrialMistakeRecord['errorTypes']) {
  if (types.includes('runtime_error') && types.includes('wrong_output')) {
    return '运行报错与输出不一致'
  }
  if (types.includes('runtime_error')) return '运行报错'
  return '输出与预期不符'
}

function mistakeUrgency(record: TrialMistakeRecord | undefined) {
  if (!record) return 0
  const recencyMs = Date.now() - new Date(record.lastFailedAt).getTime()
  const recency = Math.max(0, 100 - recencyMs / (1000 * 60 * 60 * 8))
  return Math.min(100, recency * 0.45 + record.failCount * 16 + record.failedCaseLabels.length * 12)
}

function getMistakesForNode(userId: number | string, questionIds: string[]) {
  const real = getActiveMistakeRecords(userId)
  const merged = mergeMistakesForRecommendation(userId, real)
  return filterMistakesByQuestionIds(merged, questionIds)
}

function computeRanked(
  nodeId: string,
  questions: PythonTrialQuestion[],
  mistakes: TrialMistakeRecord[],
) {
  const mistakeMap = new Map(mistakes.map((m) => [m.questionId, m]))

  return questions
    .map((question) => {
      const mistake = mistakeMap.get(question.id)
      const urgency = mistakeUrgency(mistake)
      const pathOrder = getNodeOrderBonus(nodeId, question.id)
      const totalScore = mistake
        ? Math.round(urgency * 0.72 + pathOrder * 0.28)
        : Math.round(pathOrder * 0.4)

      return { question, mistake, urgency, pathOrder, totalScore }
    })
    .sort((a, b) => b.totalScore - a.totalScore)
}

export function buildTrialPageRecommendation(
  userId: number | string,
  nodeId: string,
  questions: PythonTrialQuestion[],
): TrialPageRecommendation {
  if (!questions.length) {
    return {
      recommendedQuestionId: null,
      recommendedTitle: null,
      matchPercent: 0,
      summary: '当前板块暂无题目，请先在星轨路径解锁更多内容。',
      steps: [],
      rankedQuestionIds: [],
    }
  }

  const node = getStarPathNode(nodeId)
  const mistakes = getMistakesForNode(
    userId,
    questions.map((q) => q.id),
  )
  const ranked = computeRanked(nodeId, questions, mistakes)
  const top = ranked[0]
  const second = ranked[1]

  if (!top) {
    return {
      recommendedQuestionId: null,
      recommendedTitle: null,
      matchPercent: 0,
      summary: '无法生成推荐，请稍后重试。',
      steps: [],
      rankedQuestionIds: [],
    }
  }

  const { question, mistake, urgency, pathOrder, totalScore } = top
  const matchPercent = Math.min(98, totalScore)
  const index = questions.findIndex((q) => q.id === question.id) + 1

  const steps: TrialRecommendationStep[] = []

  if (mistake) {
    steps.push(
      {
        label: '① 错题来源',
        detail: `本题记录在案：累计未通过 ${mistake.failCount} 次，最近一次为 ${formatRelativeTime(mistake.lastFailedAt)}。`,
      },
      {
        label: '② 未通过测试点',
        detail: mistake.failedCaseLabels.length
          ? mistake.failedCaseLabels.join('、')
          : '未标注具体用例',
      },
      {
        label: '③ 错误类型',
        detail: errorTypeLabel(mistake.errorTypes),
      },
      {
        label: '④ 知识点',
        detail: `所属「${mistake.topic}」，相关标签：${mistake.tags.join('、') || '—'}。`,
      },
      {
        label: '⑤ 紧迫度',
        detail: `错题紧迫度 ${Math.round(urgency)} 分（近期出错越频繁、未通过用例越多，分数越高）。`,
      },
      {
        label: '⑥ 星轨顺序',
        detail: `在「${node ? formatStarPathNodeLabel(node) : nodeId}」中排第 ${index} 题，顺序加权 ${pathOrder} 分。`,
      },
      {
        label: '⑦ 推荐结论',
        detail: `综合错题紧迫度与做题顺序，优先推荐复习「${question.title}」${
          second?.mistake ? `（次优：${second.question.title}）` : ''
        }。`,
      },
    )
  } else {
    steps.push(
      {
        label: '① 错题匹配',
        detail: '本题在当前板块暂无错题记录，推荐分主要参考星轨做题顺序。',
      },
      {
        label: '② 推荐结论',
        detail: `建议按顺序完成第 ${index} 题「${question.title}」。`,
      },
    )
  }

  const summary = mistake
    ? `根据你的错题记录，优先推荐「${question.title}」：${formatRelativeTime(mistake.lastFailedAt)}曾未通过${mistake.failedCaseLabels[0] ? `（${mistake.failedCaseLabels[0]} 等）` : ''}，建议先巩固再往后做。`
    : `本板块中「${question.title}」暂无错题，建议按星轨顺序继续推进。`

  return {
    recommendedQuestionId: question.id,
    recommendedTitle: question.title,
    matchPercent,
    summary,
    steps,
    rankedQuestionIds: ranked.map((item) => item.question.id),
  }
}
