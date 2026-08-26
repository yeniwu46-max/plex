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

/**
 * 26 个知识点各 5 幕迷你剧情，与 starPathQuestionGenerator 的 KP_TEMPLATE_PLANS 槽位一一对应，
 * 每一幕的场景描述都对准该槽位实际要做的题，改题目计划时请同步改这里。
 */
export const KNOWLEDGE_STORY_ARCS: Record<string, KnowledgeStoryArc> = {
  'lang-print': {
    planet: '启航星',
    episodes: [
      { scenario: '启航星轨道外，飞船「探索者号」完成首次着陆' },
      { scenario: '中继卫星要求连续发送两行信标', bridge: '首束信号已送达，' },
      { scenario: '探险队呼号写入变量舱，准备署名广播', bridge: '双行信标已同步，' },
      { scenario: '小E 启动算力模块，验证飞船核心是否就绪', bridge: '署名广播已发出，' },
      { scenario: '轨道站上报两路能量读数，需要汇总回传', bridge: '算力验算通过，' },
    ],
  },
  'lang-var': {
    planet: '启航星 · 变量舱',
    episodes: [
      { scenario: '变量舱接收两路能量读数 a 与 b，等待求和' },
      { scenario: '补给官记录两组物资数量，需要计算乘积', bridge: '能量总和已上报，' },
      { scenario: '对比两处能量池，计算差值', bridge: '物资乘积已统计，' },
      { scenario: '导航台要求复核 a + b 的表达式结果', bridge: '差值监测完成，' },
      { scenario: '计算整段跃迁需要多少个标准步长', bridge: '表达式复核通过，' },
    ],
  },
  'lang-input': {
    planet: '启航星 · 通讯台',
    episodes: [
      { scenario: '地面站传来物资清单编码，需计算 a×b' },
      { scenario: '指令更新：计算整除步数 a//b', bridge: '乘积已回传，' },
      { scenario: '总部要求上报两路能量总和', bridge: '步数计算完成，' },
      { scenario: '对比新旧两版能量读数差值', bridge: '总和已确认，' },
      { scenario: '通讯台自检，验算算力模块 6×7', bridge: '差值已同步，' },
    ],
  },
  'seq-arith': {
    planet: '运算星云',
    episodes: [
      { scenario: '运算星云飘浮着表达式碎片 a 与 b，等待求和' },
      { scenario: '星云核心要求验证 6×7 算力模块', bridge: '碎片求和完成，' },
      { scenario: '计算整段跃迁步数 a//b', bridge: '算力自检通过，' },
      { scenario: '对比两处能量池读数差值', bridge: '步数已记录，' },
      { scenario: '清点两批物资的总件数', bridge: '差值监测完毕，' },
    ],
  },
  'seq-expr': {
    planet: '运算星云 · 优先级环',
    episodes: [
      { scenario: '优先级环上，6×7 的算式等待求值' },
      { scenario: '把 a 与 b 组合进同一条表达式求和', bridge: '算式求值完成，' },
      { scenario: '调整运算顺序，先算差值再回传', bridge: '表达式已组合，' },
      { scenario: '用整除截断跃迁步数的小数部分', bridge: '差值已回传，' },
      { scenario: '最后复核两路能量读数之和', bridge: '步数截断完成，' },
    ],
  },
  'seq-type': {
    planet: '运算星云 · 换算舱',
    episodes: [
      { scenario: '换算舱把两组读数相乘，统一成标准单位' },
      { scenario: '把两路读数相加，检查类型是否一致', bridge: '单位换算完成，' },
      { scenario: '验算 6×7，确认整数运算不失真', bridge: '类型校验通过，' },
      { scenario: '用整除把结果取整为跃迁步数', bridge: '验算无误，' },
      { scenario: '重新组合表达式，输出最终读数', bridge: '取整完成，' },
    ],
  },
  'branch-if': {
    planet: '分支峡谷',
    episodes: [
      { scenario: '峡谷探测器扫描到整数 n 的波动，需判定奇偶' },
      { scenario: '两路信号强度 a 与 b 需要择优转发', bridge: '奇偶判定完成，' },
      { scenario: '探险队成绩 score 需要及格判定', bridge: '信号已择优，' },
      { scenario: '坐标 n 需要判别正、负或零', bridge: '及格判定结束，' },
      { scenario: '再次扫描波动，复核奇偶通道', bridge: '坐标判别完成，' },
    ],
  },
  'branch-elif': {
    planet: '分支峡谷 · 三岔口',
    episodes: [
      { scenario: '三岔口需要把坐标 n 判别为正、负或零' },
      { scenario: '按 score 划出及格与不及格两条通道', bridge: '坐标已分流，' },
      { scenario: '在两路信号中选出更强的一路', bridge: '通道划分完成，' },
      { scenario: '检查编号 n 的奇偶，决定停靠舷侧', bridge: '信号已择优，' },
      { scenario: '再走一遍三岔口，确认分支顺序无误', bridge: '舷侧已确定，' },
    ],
  },
  'branch-nested': {
    planet: '分支峡谷 · 嵌套回廊',
    episodes: [
      { scenario: '嵌套回廊先判断坐标正负，再决定进入哪一层通道' },
      { scenario: '在内层通道里比较 a 与 b 的强弱', bridge: '正负已判定，' },
      { scenario: '复合条件下判断 score 是否放行', bridge: '强弱比较完成，' },
      { scenario: '最内层按奇偶决定闸门开合', bridge: '放行结果已记录，' },
      { scenario: '回溯整条回廊，复核每一层条件', bridge: '闸门已就位，' },
    ],
  },
  'loop-for': {
    planet: '循环环带',
    episodes: [
      { scenario: '环带监测站要求统计 1 到 n 号星轨总长度' },
      { scenario: '小E 标记 1..n 号天体，统计偶数个数', bridge: '区间求和完成，' },
      { scenario: '导航台生成 n 倍星轨刻度表', bridge: '偶数统计完毕，' },
      { scenario: '引擎舱需要计算 n 的阶乘', bridge: '刻度表已生成，' },
      { scenario: '再次汇总星轨区间长度，复核数据', bridge: '阶乘验算通过，' },
    ],
  },
  'loop-while': {
    planet: '循环环带 · 条件闸',
    episodes: [
      { scenario: '条件闸要求持续累加，直到覆盖 1 到 n 全段' },
      { scenario: '引擎持续自乘，算出 n 的阶乘后停机', bridge: '累加已达终点，' },
      { scenario: '一边推进一边计数，统计偶数天体', bridge: '阶乘计算完成，' },
      { scenario: '循环输出 n 倍刻度，满 5 格即停', bridge: '偶数计数完毕，' },
      { scenario: '复核终止条件，重跑一遍区间求和', bridge: '刻度已输出，' },
    ],
  },
  'loop-nested': {
    planet: '循环环带 · 双层轨道',
    episodes: [
      { scenario: '双层轨道逐行生成 n 倍刻度表' },
      { scenario: '外层推进、内层累乘，算出 n 的阶乘', bridge: '刻度表已排布，' },
      { scenario: '逐层扫描，统计偶数天体数量', bridge: '阶乘验算通过，' },
      { scenario: '把每一层的区间长度加总', bridge: '偶数扫描完成，' },
      { scenario: '重排双层轨道，复核每行输出', bridge: '长度已汇总，' },
    ],
  },
  'loop-control': {
    planet: '循环环带 · 急停舱',
    episodes: [
      { scenario: '急停舱只放行偶数天体，其余一律跳过' },
      { scenario: '满足条件即累加，凑齐 1 到 n 的总长', bridge: '偶数已筛出，' },
      { scenario: '输出 n 倍刻度，到第 5 格立即跳出', bridge: '区间求和完成，' },
      { scenario: '阶乘推进途中遇到异常就提前终止', bridge: '刻度已截断，' },
      { scenario: '复核「跳过本轮」与「跳出循环」的分界线', bridge: '阶乘已收敛，' },
    ],
  },
  'array-basic': {
    planet: '货舱区 · 样本架',
    episodes: [
      { scenario: '货舱整数样本列表 nums 需要找出最大值' },
      { scenario: '小E 在样本列表中寻找最低读数', bridge: '峰值扫描完成，' },
      { scenario: '只取样本列表首尾两件，求其和', bridge: '谷值已定位，' },
      { scenario: '遍历货舱，汇总样本总重量', bridge: '首尾已清点，' },
      { scenario: '统计其中读数为正的样本件数', bridge: '总量统计完毕，' },
    ],
  },
  'array-traverse': {
    planet: '货舱区 · 巡检道',
    episodes: [
      { scenario: '巡检道逐格遍历货架，汇总样本总量' },
      { scenario: '统计读数为正的样本件数', bridge: '总量已汇总，' },
      { scenario: '找出整批样本中的最高读数', bridge: '正数统计完毕，' },
      { scenario: '定位整批样本中的最低读数', bridge: '峰值已记录，' },
      { scenario: '把巡检流程封装成函数，一次返回总量', bridge: '谷值已记录，' },
    ],
  },
  'array-2d': {
    planet: '货舱区 · 立体仓',
    episodes: [
      { scenario: '立体仓按行遍历，先把一层货物加总' },
      { scenario: '封装函数，返回整层样本总量', bridge: '单层已加总，' },
      { scenario: '统计整层中读数为正的格位', bridge: '层总量已封装，' },
      { scenario: '找出该层最高读数所在的格位', bridge: '正数格位已统计，' },
      { scenario: '按行列打印一张 n 倍库位表', bridge: '峰值格位已标注，' },
    ],
  },
  'string-index': {
    planet: '语符卫星',
    episodes: [
      { scenario: '语符卫星截获带噪声的电报 s，需去掉首尾空白' },
      { scenario: '中继站要求分两行发送识别码', bridge: '电报已去噪，' },
      { scenario: '把呼号 name 拼进标准问候语', bridge: '识别码已发送，' },
      { scenario: '首次连接需发送固定问候串', bridge: '问候已署名，' },
      { scenario: '验算模块等待 6×7 的结果回传', bridge: '连接已建立，' },
    ],
  },
  'string-method': {
    planet: '语符卫星 · 编解码舱',
    episodes: [
      { scenario: '编解码舱用 strip 清掉电文两端的杂讯' },
      { scenario: '用呼号 name 组装个性化问候', bridge: '杂讯已清除，' },
      { scenario: '拆成两行分别发送，避免电文超长', bridge: '问候已组装，' },
      { scenario: '回落到标准问候串，确保老设备兼容', bridge: '分行发送完成，' },
      { scenario: '在末尾附上一段算力校验值 6×7', bridge: '兼容性已确认，' },
    ],
  },
  'string-scan': {
    planet: '语符卫星 · 逐字扫描台',
    episodes: [
      { scenario: '扫描台先削掉电文首尾的空白' },
      { scenario: '逐位统计有效读数的个数', bridge: '首尾已修剪，' },
      { scenario: '把逐位读数累加成校验和', bridge: '有效位已计数，' },
      { scenario: '分两行回送扫描结果', bridge: '校验和已算出，' },
      { scenario: '在回执里署上探险队呼号', bridge: '结果已回送，' },
    ],
  },
  'func-define': {
    planet: '封装空间站',
    episodes: [
      { scenario: '矩形舱室需要一个计算面积的函数' },
      { scenario: '能量增幅器需要双倍输出模块', bridge: '面积函数已就绪，' },
      { scenario: '星环围栏需要计算矩形周长', bridge: '增幅模块已上线，' },
      { scenario: '导航系统要在两个候选坐标中选更优者', bridge: '周长已封装，' },
      { scenario: '把星链样本汇总也封装成函数', bridge: '择优模块已接入，' },
    ],
  },
  'func-param': {
    planet: '封装空间站 · 接口舱',
    episodes: [
      { scenario: '接口舱要求传入两个坐标并返回更优者' },
      { scenario: '传入宽与高两个参数，返回围栏周长', bridge: '择优接口已联调，' },
      { scenario: '传入区间端点 a 与 b，返回整段之和', bridge: '周长接口已开放，' },
      { scenario: '只收一个参数的增幅器，返回两倍值', bridge: '区间接口已验收，' },
      { scenario: '回到面积接口，复核参数与返回值', bridge: '增幅接口已部署，' },
    ],
  },
  'func-recursion': {
    planet: '封装空间站 · 回响塔',
    episodes: [
      { scenario: '回响塔把区间 a..b 拆成一层层子任务求和' },
      { scenario: '样本总量同样可以层层拆解', bridge: '区间已收敛，' },
      { scenario: '阶乘是最经典的一层套一层', bridge: '样本已聚合，' },
      { scenario: '出口条件写好后，回到面积计算复核', bridge: '阶乘已回溯，' },
      { scenario: '最后用择优函数验证每层的返回值', bridge: '出口条件已确认，' },
    ],
  },
  'search-linear': {
    planet: '算法深空 · 巡航扫描',
    episodes: [
      { scenario: '深空扫描逐个比对样本，先找出最大读数' },
      { scenario: '同样逐个比对，定位最小读数', bridge: '峰值已找到，' },
      { scenario: '顺序扫描，数出读数为正的样本', bridge: '谷值已定位，' },
      { scenario: '边扫描边累加，得到总读数', bridge: '正数已计数，' },
      { scenario: '只取首尾两个样本做一次快速抽检', bridge: '总读数已汇总，' },
    ],
  },
  'search-binary': {
    planet: '算法深空 · 有序星图',
    episodes: [
      { scenario: '有序星图里快速定位目标坐标' },
      { scenario: '判定目标是否存在于升序列表', bridge: '目标坐标已定位，' },
      { scenario: '查找第一个大于等于 x 的元素位置', bridge: '存在性判定完成，' },
      { scenario: '换一批星图，再做一次存在性判定', bridge: '左边界已确定，' },
      { scenario: '复核二分精度，重跑一次定位', bridge: '判定结果一致，' },
    ],
  },
  'search-sort': {
    planet: '算法深空 · 分拣台',
    episodes: [
      { scenario: '混沌星尘需要冒泡升序排列才能稳定跃迁' },
      { scenario: '只执行一轮冒泡，观察最大元素如何上浮', bridge: '全序排列完成，' },
      { scenario: '换用选择排序整理同一批星尘', bridge: '单轮冒泡完成，' },
      { scenario: '在子区间中定位最小元素索引', bridge: '选择排序完成，' },
      { scenario: '统计整个冒泡过程中的交换次数', bridge: '最小索引已定位，' },
    ],
  },
  'search-stat': {
    planet: '算法深空 · 统计站',
    episodes: [
      { scenario: '统计站把能量碎片列表逐个累加' },
      { scenario: '数出其中读数为正的碎片', bridge: '能量累加完成，' },
      { scenario: '汇总 a 到 b 区间的整数总和', bridge: '正数统计完毕，' },
      { scenario: '封装函数，一次返回星链样本总量', bridge: '区间求和完成，' },
      { scenario: '最后标出整批数据的最高读数', bridge: '样本已聚合，' },
    ],
  },
}

const DOMAIN_PLANET: Record<string, string> = {
  'lang-basics': '启航星',
  sequence: '运算星云',
  branch: '分支峡谷',
  loop: '循环环带',
  array: '货舱区',
  string: '语符卫星',
  function: '封装空间站',
  search: '算法深空',
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
