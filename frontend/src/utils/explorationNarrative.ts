/** 科幻探险叙事包装：你与小E 的星球任务（纯文本，不使用 Markdown 加粗） */

export interface StoryEpisode {
  /** 本幕场景描述 */
  scenario: string
  /** 承接上一幕的剧情桥接句（第 1 幕可省略） */
  bridge?: string
}

export interface KnowledgeStoryArc {
  /** 星球 / 区域名称 */
  planet: string
  /** 本知识点 5 幕连续剧情 */
  episodes: StoryEpisode[]
}

export interface WrapExplorationOptions {
  episode?: number
  chapterTotal?: number
  planet?: string
  bridge?: string
}

/** 各知识点串联迷你剧情（每知识点 5 幕，与试炼槽位一一对应） */
export const KNOWLEDGE_STORY_ARCS: Record<string, KnowledgeStoryArc> = {
  'stage1-intro': {
    planet: '数据星',
    episodes: [
      { scenario: '数据星轨道外，飞船「探索者号」完成首次着陆' },
      {
        scenario: '地面站回应了你的问候，中继卫星要求连续信标',
        bridge: '总部已收到问候信号，',
      },
      {
        scenario: '小E 启动算力模块，验证飞船核心是否就绪',
        bridge: '双行信标已同步，',
      },
      {
        scenario: '探险队呼号写入变量舱，准备个性化广播',
        bridge: '算力验算通过，',
      },
      {
        scenario: '火星轨道站上报两路能量读数，需要汇总后传回总部',
        bridge: '呼号已录入，',
      },
    ],
  },
  'stage1-comment': {
    planet: '数据星 · 航行日志舱',
    episodes: [
      { scenario: '小E 打开航行日志，教你用 # 在代码旁留下备注' },
      {
        scenario: '注释写好后，发送带呼号的标准问候',
        bridge: '日志备注已保存，',
      },
      {
        scenario: '日志舱要求输出双行识别码归档',
        bridge: '问候已送达，',
      },
      {
        scenario: '在日志中记录一次算力验算结果',
        bridge: '识别码已归档，',
      },
      {
        scenario: '汇总日志舱两路监测读数',
        bridge: '验算记录完毕，',
      },
    ],
  },
  'stage1-var': {
    planet: '数据星 · 变量舱',
    episodes: [
      { scenario: '变量舱接收两路能量读数 a 与 b，等待求和' },
      {
        scenario: '补给官记录两组物资数量，需要计算乘积',
        bridge: '能量总和已上报，',
      },
      {
        scenario: '对比两处能量池，计算差值',
        bridge: '物资乘积已统计，',
      },
      {
        scenario: '计算从 A 点到 B 点的整段跃迁步数',
        bridge: '差值监测完成，',
      },
      {
        scenario: '再次汇总双路读数，验证变量舱通讯稳定',
        bridge: '跃迁步数已记录，',
      },
    ],
  },
  'stage1-io': {
    planet: '数据星 · 通讯台',
    episodes: [
      { scenario: '地面站传来物资清单编码，需计算 a×b' },
      {
        scenario: '指令更新：计算整除步数 a//b',
        bridge: '乘积已回传，',
      },
      {
        scenario: '总部要求上报两路能量总和',
        bridge: '步数计算完成，',
      },
      {
        scenario: '对比新旧两版能量读数差值',
        bridge: '总和已确认，',
      },
      {
        scenario: '最后一轮物资数量复核',
        bridge: '差值已同步，',
      },
    ],
  },
  'stage2-ops': {
    planet: '运算星云',
    episodes: [
      { scenario: '运算星云飘浮着表达式碎片 a=3, b=4' },
      {
        scenario: '星云核心要求验证 6×7 算力模块',
        bridge: '表达式求值完成，',
      },
      {
        scenario: '计算整段跃迁步数 a//b',
        bridge: '算力自检通过，',
      },
      {
        scenario: '对比两处能量池读数差值',
        bridge: '步数已记录，',
      },
      {
        scenario: '两座太阳能塔上报读数，汇总总量',
        bridge: '差值监测完毕，',
      },
    ],
  },
  'stage2-cond': {
    planet: '分支峡谷',
    episodes: [
      { scenario: '峡谷探测器扫描到整数 n 的波动' },
      {
        scenario: '两路信号强度 a 与 b 需要择优转发',
        bridge: '奇偶判定完成，',
      },
      {
        scenario: '探险队成绩 score 需要及格判定',
        bridge: '信号已择优，',
      },
      {
        scenario: '坐标 n 需要判别正、负或零',
        bridge: '及格判定结束，',
      },
      {
        scenario: '再次对比两路信号，选出较强一路',
        bridge: '坐标判别完成，',
      },
    ],
  },
  'stage2-loop': {
    planet: '循环环带',
    episodes: [
      { scenario: '环带监测站要求统计 1 到 n 号星轨总长度' },
      {
        scenario: '小E 标记 1..n 号天体，统计偶数个数',
        bridge: '区间求和完成，',
      },
      {
        scenario: '引擎舱需要计算 n 的阶乘',
        bridge: '偶数统计完毕，',
      },
      {
        scenario: '导航台生成 n 倍星轨刻度',
        bridge: '阶乘验算通过，',
      },
      {
        scenario: '再次汇总星轨区间长度，复核数据',
        bridge: '刻度表已生成，',
      },
    ],
  },
  'stage2-range': {
    planet: '循环环带 · 控制塔',
    episodes: [
      { scenario: '控制塔生成 n 倍星轨刻度表' },
      {
        scenario: '复核 1 到 n 的区间总长',
        bridge: '刻度已广播，',
      },
      {
        scenario: '统计环带内偶数天体数量',
        bridge: '区间复核完成，',
      },
      {
        scenario: '计算引擎阶乘输出',
        bridge: '偶数统计结束，',
      },
      {
        scenario: '再次输出星轨刻度，确认控制塔在线',
        bridge: '阶乘验算完毕，',
      },
    ],
  },
  'stage3-str': {
    planet: '语符卫星',
    episodes: [
      { scenario: '语符卫星截获带噪声的电报 s，需去噪' },
      {
        scenario: '中继站要求发送两行识别码',
        bridge: '电报已去噪，',
      },
      {
        scenario: '首次连接需发送标准问候',
        bridge: '识别码已发送，',
      },
      {
        scenario: '验算模块等待 6×7 结果',
        bridge: '问候已送达，',
      },
      {
        scenario: '变量 name 写入探险队呼号后广播',
        bridge: '验算通过，',
      },
    ],
  },
  'stage3-list': {
    planet: '货舱 · 样本区',
    episodes: [
      { scenario: '货舱整数样本列表 nums 需要找最大值' },
      {
        scenario: '小E 在样本列表中寻找最低读数',
        bridge: '峰值扫描完成，',
      },
      {
        scenario: '汇总货舱样本总重量',
        bridge: '谷值已定位，',
      },
      {
        scenario: '只关心样本列表首尾两件',
        bridge: '总量统计完毕，',
      },
      {
        scenario: '封装函数汇总星链样本总量',
        bridge: '首尾求和完成，',
      },
    ],
  },
  'stage3-dict': {
    planet: '货舱 · 坐标索引区',
    episodes: [
      { scenario: '坐标索引表 nums 需要循环求和' },
      {
        scenario: '取出索引表首尾坐标之和',
        bridge: '循环求和完成，',
      },
      {
        scenario: '统计正数坐标点数量',
        bridge: '首尾坐标已提取，',
      },
      {
        scenario: '在样本列表中找最大值',
        bridge: '正数统计完毕，',
      },
      {
        scenario: '定位样本列表最小读数',
        bridge: '峰值复核完成，',
      },
    ],
  },
  'stage3-func': {
    planet: '封装空间站',
    episodes: [
      { scenario: '矩形舱室需要计算面积' },
      {
        scenario: '星环围栏需要计算矩形周长',
        bridge: '面积已测算，',
      },
      {
        scenario: '能量增幅器需要双倍输出模块',
        bridge: '周长已记录，',
      },
      {
        scenario: '导航系统在两个候选坐标中选更优者',
        bridge: '增幅模块就绪，',
      },
      {
        scenario: '再次测算矩形舱室面积，复核封装站',
        bridge: '坐标择优完成，',
      },
    ],
  },
  'stage4-algo-sum': {
    planet: '算法深空 · 能量带',
    episodes: [
      { scenario: '能量碎片列表 nums 等待循环汇总' },
      {
        scenario: '统计正数碎片数量',
        bridge: '能量累加完成，',
      },
      {
        scenario: '汇总 1 到 n 的星轨总长',
        bridge: '正数统计完毕，',
      },
      {
        scenario: '封装函数汇总星链样本',
        bridge: '区间求和完成，',
      },
      {
        scenario: '计算 a 到 b 区间整数之和',
        bridge: '样本聚合完毕，',
      },
    ],
  },
  'stage4-bubble': {
    planet: '算法深空 · 混沌星尘',
    episodes: [
      { scenario: '混沌星尘需要冒泡升序排列才能稳定跃迁' },
      {
        scenario: '执行一轮冒泡，观察最大元素如何移动',
        bridge: '全序排列完成，',
      },
      {
        scenario: '统计升序过程中交换次数',
        bridge: '单轮冒泡完成，',
      },
      {
        scenario: '再次完整冒泡排序，验证稳定性',
        bridge: '交换次数已记录，',
      },
      {
        scenario: '补做一轮冒泡，巩固相邻比较',
        bridge: '稳定性验证通过，',
      },
    ],
  },
  'stage4-selection': {
    planet: '算法深空 · 分拣台',
    episodes: [
      { scenario: '小E 用选择排序整理星尘样本' },
      {
        scenario: '在子区间中定位最小元素索引',
        bridge: '选择排序完成，',
      },
      {
        scenario: '执行一步选择交换',
        bridge: '最小索引已定位，',
      },
      {
        scenario: '再次选择排序，验证结果',
        bridge: '单步交换完成，',
      },
      {
        scenario: '补找一轮最小索引，巩固思路',
        bridge: '结果已验证，',
      },
    ],
  },
  'stage4-binary': {
    planet: '算法深空 · 有序星图',
    episodes: [
      { scenario: '有序星图里快速定位目标坐标' },
      {
        scenario: '判定目标是否存在于升序列表',
        bridge: '目标坐标已定位，',
      },
      {
        scenario: '查找第一个大于等于 x 的元素位置',
        bridge: '存在性判定完成，',
      },
      {
        scenario: '再次二分查找，复核星图精度',
        bridge: '左边界已确定，',
      },
      {
        scenario: '补做一次存在性判定',
        bridge: '精度复核通过，',
      },
    ],
  },
}

const DOMAIN_PLANET: Record<string, string> = {
  'data-vars': '数据星',
  operators: '运算星云',
  'flow-control': '分支峡谷',
  strings: '语符卫星',
  'lists-dicts': '货舱区',
  functions: '封装空间站',
  'recursion-iter': '算法深空',
}

export function getStoryArcForKnowledgePoint(kpId: string, domainKey: string): KnowledgeStoryArc {
  return (
    KNOWLEDGE_STORY_ARCS[kpId] ?? {
      planet: DOMAIN_PLANET[domainKey] ?? '未知星域',
      episodes: Array.from({ length: 5 }, (_, i) => ({
        scenario: `第 ${i + 1} 幕任务现场`,
        bridge: i > 0 ? '上一幕任务已完成，' : undefined,
      })),
    }
  )
}

export function wrapExploration(
  scenario: string,
  task: string,
  options?: WrapExplorationOptions,
): string {
  const planet = options?.planet
  const header = planet ? `🛸 星球探险 · ${planet}` : '🛸 星球探险'
  const episode =
    options?.episode && options?.chapterTotal
      ? `【第 ${options.episode}/${options.chapterTotal} 幕】`
      : options?.episode
        ? `【第 ${options.episode} 幕】`
        : ''
  const bridge = options?.bridge ? `${options.bridge}` : ''
  const lines = [header]
  if (episode) lines.push(episode)
  lines.push(`你和导航 AI「小E」在${scenario}。`)
  if (bridge) lines.push(bridge)
  lines.push(task)
  return lines.join('\n')
}

export function wrapEpisodeNarrative(
  kpId: string,
  domainKey: string,
  slotIndex: number,
  task: string,
): string {
  const arc = getStoryArcForKnowledgePoint(kpId, domainKey)
  const episode = arc.episodes[slotIndex] ?? arc.episodes[0]!
  return wrapExploration(episode.scenario, task, {
    episode: slotIndex + 1,
    chapterTotal: arc.episodes.length,
    planet: arc.planet,
    bridge: episode.bridge,
  })
}
