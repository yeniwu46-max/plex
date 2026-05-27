import { getPythonTrialQuestion } from '../data/pythonTrialQuestions'
import {
  formatStarPathNodeLabel,
  getStarPathNode,
  getStarPathNodeByQuestionId,
  getUnlockedStarPathNodes,
  isStarPathNodeUnlocked,
} from '../data/starPathTrail'
import { getActiveMistakeRecords, type TrialMistakeRecord } from './trialMistakeLog'
import { mergeMistakesForRecommendation } from './studentMockMistakes'

export interface MessengerSuggestion {
  title: string
  desc: string
}

export interface RecommendationDecisionStep {
  label: string
  detail: string
}

export interface RecommendedTrial {
  questionId: string
  label: string
  matchPercent: number
  summary: string
  decisionSteps: RecommendationDecisionStep[]
}

export interface MessengerWeakPointAnalysis {
  suggestions: MessengerSuggestion[]
  fragmentCount: number
  recommended: RecommendedTrial | null
  hasMistakeData: boolean
  topTopics: { topic: string; failCount: number; questions: string[] }[]
}

function formatRelativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  return `${days} 天前`
}

function errorTypeLabel(types: TrialMistakeRecord['errorTypes']) {
  if (types.includes('runtime_error') && types.includes('wrong_output')) {
    return '运行报错与输出不符均有'
  }
  if (types.includes('runtime_error')) return '以运行报错为主'
  return '以输出与预期不一致为主'
}

function buildLabel(questionId: string) {
  const question = getPythonTrialQuestion(questionId)
  if (!question) return null
  const node = getStarPathNodeByQuestionId(questionId)
  const label = node
    ? `${formatStarPathNodeLabel(node)} · ${question.title}`
    : `${question.topic} · ${question.title}`
  return { question, node, label }
}

function scoreCandidate(record: TrialMistakeRecord) {
  const recencyMs = Date.now() - new Date(record.lastFailedAt).getTime()
  const recencyScore = Math.max(0, 100 - recencyMs / (1000 * 60 * 60 * 6))
  const failScore = record.failCount * 12
  const caseScore = record.failedCaseLabels.length * 8
  return recencyScore + failScore + caseScore
}

function buildRecommendationFromMistake(
  target: TrialMistakeRecord,
  allRecords: TrialMistakeRecord[],
): RecommendedTrial | null {
  const meta = buildLabel(target.questionId)
  if (!meta) return null

  const { node, label } = meta
  const ranked = [...allRecords].sort((a, b) => scoreCandidate(b) - scoreCandidate(a))
  const isTop = ranked[0]?.questionId === target.questionId
  const runnerUp = ranked[1]

  const recencyPart = Math.min(40, Math.round(scoreCandidate(target) * 0.4))
  const failPart = Math.min(30, target.failCount * 6)
  const casePart = Math.min(28, target.failedCaseLabels.length * 4)
  const matchPercent = Math.min(98, 62 + failPart + casePart + Math.round(recencyPart * 0.5))

  const steps: RecommendationDecisionStep[] = [
    {
      label: '① 选题策略',
      detail: isTop
        ? '在全部未修复错题中，本题综合得分最高，优先推荐复习。'
        : '本题进入推荐候选，但因其他题目优先级更高通常不会被选中。',
    },
    {
      label: '② 错题时效',
      detail: `最近一次未通过发生在 ${formatRelativeTime(target.lastFailedAt)}，越近期的错题越优先安排巩固。`,
    },
    {
      label: '③ 出错频率',
      detail: `累计未通过运行 ${target.failCount} 次${
        runnerUp ? `（${runnerUp.questionTitle} 为 ${runnerUp.failCount} 次）` : ''
      }，高频错题需要优先闭环。`,
    },
    {
      label: '④ 薄弱知识点',
      detail: `属于「${target.topic}」，涉及标签：${target.tags.join('、') || '无'}。`,
    },
  ]

  if (target.failedCaseLabels.length) {
    steps.push({
      label: '⑤ 未通过测试点',
      detail: target.failedCaseLabels.join('、'),
    })
  }

  steps.push({
    label: '⑥ 错误类型',
    detail: errorTypeLabel(target.errorTypes),
  })

  if (node) {
    const unlocked = isStarPathNodeUnlocked(node)
    steps.push({
      label: '⑦ 星轨关联',
      detail: unlocked
        ? `题目位于已解锁板块「${formatStarPathNodeLabel(node)}」，与当前学习路径一致。`
        : `题目属于板块「${formatStarPathNodeLabel(node)}」，需先解锁该星轨节点。`,
    })
  }

  steps.push({
    label: '⑧ 匹配度计算',
    detail: `基础 62 分 + 出错次数加权 ${failPart} + 失败用例 ${casePart} + 时效加权 ≈ ${matchPercent}%。`,
  })

  const summary = `因「${target.questionTitle}」${formatRelativeTime(target.lastFailedAt)}再次未通过，且累计出错 ${target.failCount} 次，建议优先攻克${target.failedCaseLabels.length ? `（${target.failedCaseLabels[0]} 等测试点）` : ''}。`

  return {
    questionId: target.questionId,
    label,
    matchPercent,
    summary,
    decisionSteps: steps,
  }
}

function buildFallbackRecommendation(): RecommendedTrial | null {
  const unlocked = getUnlockedStarPathNodes()
  const current = unlocked.find((n) => n.status === 'current')
    ?? unlocked.find((n) => n.status === 'progress')
    ?? unlocked[0]
  if (!current) return null

  const questionId = current.questionIds[0]
  const meta = buildLabel(questionId)
  if (!meta) return null

  const steps: RecommendationDecisionStep[] = [
    {
      label: '① 选题策略',
      detail: '当前尚无有效错题记录，采用「当前星轨进度」策略推荐首题。',
    },
    {
      label: '② 星轨进度',
      detail: `选中板块 ${formatStarPathNodeLabel(current)}（状态：${
        current.status === 'current' ? '当前所在' : current.status === 'progress' ? '进行中' : '已解锁'
      }）。`,
    },
    {
      label: '③ 题目顺序',
      detail: `该板块共 ${current.questionIds.length} 道题，从第 1 题开始建立练习基线。`,
    },
    {
      label: '④ 后续调整',
      detail: '完成运行测试后，若出现未通过用例，推荐将切换为「错题优先」策略。',
    },
  ]

  return {
    questionId,
    label: meta.label,
    matchPercent: 75,
    summary: `暂无错题数据，按当前星轨「${formatStarPathNodeLabel(current)}」推荐首题「${meta.question.title}」。`,
    decisionSteps: steps,
  }
}

function pickRecommendedTrial(records: TrialMistakeRecord[]): RecommendedTrial | null {
  if (!records.length) return buildFallbackRecommendation()

  const sorted = [...records].sort((a, b) => scoreCandidate(b) - scoreCandidate(a))
  const target = sorted[0]
  return buildRecommendationFromMistake(target, records)
}

function aggregateTopics(records: TrialMistakeRecord[]) {
  const map = new Map<string, { failCount: number; questions: Set<string> }>()
  for (const record of records) {
    const key = record.topic
    const entry = map.get(key) ?? { failCount: 0, questions: new Set<string>() }
    entry.failCount += record.failCount
    entry.questions.add(record.questionTitle)
    map.set(key, entry)
  }
  return [...map.entries()]
    .map(([topic, value]) => ({
      topic,
      failCount: value.failCount,
      questions: [...value.questions],
    }))
    .sort((a, b) => b.failCount - a.failCount)
}

function buildWeakPointSuggestion(records: TrialMistakeRecord[], topTopics: MessengerWeakPointAnalysis['topTopics']) {
  if (!records.length) {
    return {
      title: '薄弱点分析',
      desc: '暂无错题记录。去试炼关卡运行测试后，小E 会根据你的未通过用例给出针对性分析。',
    }
  }

  const primary = topTopics[0]
  const recent = records.slice(0, 3)
  const questionNames = recent.map((item) => `「${item.questionTitle}」`).join('、')
  const caseHint = recent
    .flatMap((item) => item.failedCaseLabels.slice(0, 2))
    .filter(Boolean)
    .slice(0, 3)
    .join('、')

  let desc = `根据最近错题，你在「${primary?.topic ?? recent[0].topic}」相关题目上出错较多（${questionNames}）。`
  if (caseHint) {
    desc += ` 未通过的测试点包括：${caseHint}。`
  }
  if (recent[0].errorTypes.includes('runtime_error')) {
    desc += ' 部分为运行报错，建议先检查缩进、变量名与语法。'
  } else {
    desc += ' 多为输出与预期不一致，建议对照样例逐行核对格式与边界。'
  }
  if (topTopics[1]) {
    desc += ` 次要薄弱点：${topTopics[1].topic}。`
  }

  return { title: '薄弱点分析', desc }
}

function buildRepairRouteSuggestion(records: TrialMistakeRecord[]) {
  if (!records.length) {
    return {
      title: '知识修复路线',
      desc: '完成试炼并产生错题后，将为你生成对应星轨板块的修复路线。',
    }
  }

  const byNode = new Map<string, TrialMistakeRecord[]>()
  for (const record of records) {
    if (!record.starPathNodeId) continue
    const list = byNode.get(record.starPathNodeId) ?? []
    list.push(record)
    byNode.set(record.starPathNodeId, list)
  }

  const nodeId = [...byNode.entries()].sort((a, b) => {
    const failA = a[1].reduce((sum, item) => sum + item.failCount, 0)
    const failB = b[1].reduce((sum, item) => sum + item.failCount, 0)
    return failB - failA
  })[0]?.[0]

  if (nodeId) {
    const node = getStarPathNode(nodeId)
    const nodeRecords = byNode.get(nodeId) ?? []
    const titles = nodeRecords.map((item) => item.questionTitle).join('、')
    const unlocked = node && isStarPathNodeUnlocked(node)
    return {
      title: '知识修复路线',
      desc: unlocked
        ? `建议回到星轨 ${formatStarPathNodeLabel(node!)}，优先重做：${titles}。按题目顺序巩固后再推进下一节点。`
        : `错题集中在「${node?.title ?? nodeId}」板块（${titles}），解锁该星轨节点后完成修复试炼。`,
    }
  }

  const topics = [...new Set(records.map((item) => item.topic))].slice(0, 2).join('、')
  return {
    title: '知识修复路线',
    desc: `建议按「${topics}」主题集中刷题，每题至少通过全部测试后再进入下一道。`,
  }
}

function buildRecommendationSuggestion(recommended: RecommendedTrial | null) {
  if (!recommended) {
    return {
      title: '推荐决策',
      desc: '完成试炼后，将展示为何推荐该题（时效、出错次数、测试点等）。',
    }
  }
  const stepPreview = recommended.decisionSteps
    .slice(1, 4)
    .map((s) => `${s.label.replace(/[①②③④⑤⑥⑦⑧]\s*/, '')}：${s.detail}`)
    .join(' ')
  return {
    title: '推荐决策',
    desc: `${recommended.summary} ${stepPreview}`,
  }
}

function buildDailySuggestion(recommended: RecommendedTrial | null) {
  if (!recommended) {
    return {
      title: '今日建议',
      desc: '今天可以先从 Python 入门试炼的当前星轨板块开始，运行测试让小E 了解你的薄弱点。',
    }
  }

  const question = getPythonTrialQuestion(recommended.questionId)
  const tagHint = question?.tags[0] ?? question?.topic ?? '基础语法'
  return {
    title: '今日建议',
    desc: `优先复习「${recommended.label}」（匹配度 ${recommended.matchPercent}%）。重点练习「${tagHint}」相关写法，每题目标：全部测试通过。`,
  }
}

export function analyzeMessengerWeakPoints(userId: number | string): MessengerWeakPointAnalysis {
  const real = getActiveMistakeRecords(userId)
  const records = mergeMistakesForRecommendation(userId, real)
  const topTopics = aggregateTopics(records)
  const recommended = pickRecommendedTrial(records)

  const suggestions: MessengerSuggestion[] = [
    buildWeakPointSuggestion(records, topTopics),
    buildRecommendationSuggestion(recommended),
    buildRepairRouteSuggestion(records),
    buildDailySuggestion(recommended),
  ]

  return {
    suggestions,
    fragmentCount: records.length,
    recommended,
    hasMistakeData: records.length > 0,
    topTopics,
  }
}
