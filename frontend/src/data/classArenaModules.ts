/** 探索舱 · 班级协作模块目录 */

export type ClassArenaModuleKey = 'trials' | 'gladiator' | 'rps'

export interface ClassArenaModuleDef {
  key: ClassArenaModuleKey
  title: string
  subtitle: string
  description: string
  badge?: string
  status: 'live' | 'beta' | 'soon'
  tags: string[]
}

export const CLASS_ARENA_MODULES: ClassArenaModuleDef[] = [
  {
    key: 'trials',
    title: '教师试炼场',
    subtitle: 'Class Trials',
    description: '参与教师发布的班级试炼，完成关卡获取 XP 与班级积分。',
    status: 'live',
    tags: ['教师发布', '异步完成', '班级积分'],
  },
  {
    key: 'gladiator',
    title: '角斗士 · 竞速对决',
    subtitle: 'Speed Duel',
    description: '两名同班探索者同时在线，挑战同一道编程题，先通过全部用例者获胜。',
    badge: '实时',
    status: 'beta',
    tags: ['双人在线', '同题竞速', '计时排名'],
  },
  {
    key: 'rps',
    title: '代码攻防 · 猜拳对决',
    subtitle: 'Code RPS Arena',
    description: '各写一段 Python 策略输出 rock / paper / scissors，系统自动多轮对战决胜负。',
    badge: '策略',
    status: 'beta',
    tags: ['代码 vs 代码', '多轮博弈', '策略迭代'],
  },
]

export const GLADIATOR_SAMPLE_PROBLEM = {
  title: '两数之和',
  stem: '读入两个整数 a、b，输出它们的和。',
  samples: [
    { input: '3 5', output: '8' },
    { input: '-2 7', output: '5' },
  ],
  timeLimitSec: 300,
}

export const RPS_SAMPLE_RULES = [
  '每轮双方程序输出 rock、paper 或 scissors 之一（不区分大小写）。',
  '石头赢剪刀、剪刀赢布、布赢石头；相同则平局进入下一轮。',
  '先赢得 3 局者获胜；单局限时 2 秒。',
  '禁止访问网络与文件，仅允许标准输入输出博弈。',
]

export const RPS_STRATEGY_EXAMPLES = [
  { name: '固定石头', code: 'print("rock")' },
  { name: '循环出招', code: 'moves = ["rock","paper","scissors"]\nprint(moves[int(input()) % 3])' },
  { name: '随机干扰', code: 'import random\nprint(random.choice(["rock","paper","scissors"]))' },
]
