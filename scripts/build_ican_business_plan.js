const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  BorderStyle,
  Document,
  ExternalHyperlink,
  Footer,
  Header,
  HeadingLevel,
  ImageRun,
  LevelFormat,
  PageBreak,
  PageNumber,
  Packer,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  VerticalAlign,
  WidthType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "docs", "ican-submission");
const OUTPUT = path.join(OUT, "PLEX-ICAN-商业计划书.docx");
const CONTENT_W = 9864;
const FONT = "Microsoft YaHei";
const C = {
  navy: "071824",
  teal: "0B6470",
  mint: "18C7B5",
  orange: "E9792B",
  ink: "1F3441",
  muted: "607783",
  pale: "EDF5F6",
  paleOrange: "FFF2E8",
  line: "B8CDD5",
  white: "FFFFFF",
  red: "B34232",
  green: "277A58",
};

const border = { style: BorderStyle.SINGLE, size: 1, color: C.line };
const borders = { top: border, bottom: border, left: border, right: border };

function textParagraph(text, options = {}) {
  return new Paragraph({
    alignment: options.alignment || AlignmentType.JUSTIFIED,
    spacing: { after: options.after ?? 120, line: options.line ?? 360 },
    keepNext: options.keepNext || false,
    children: [new TextRun({
      text,
      font: FONT,
      size: options.size || 21,
      bold: options.bold || false,
      color: options.color || C.ink,
      italics: options.italics || false,
    })],
  });
}

function heading(text, level = 1) {
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2,
    spacing: { before: level === 1 ? 300 : 180, after: level === 1 ? 180 : 120 },
    keepNext: true,
    children: [new TextRun({
      text,
      font: FONT,
      size: level === 1 ? 34 : 26,
      bold: true,
      color: level === 1 ? C.teal : C.orange,
    })],
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "plex-bullets", level },
    spacing: { after: 90, line: 330 },
    children: [new TextRun({ text, font: FONT, size: 20, color: C.ink })],
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function cell(content, width, opts = {}) {
  const children = Array.isArray(content) ? content : [textParagraph(String(content), {
    size: opts.header ? 18 : 17,
    bold: opts.header || opts.bold,
    color: opts.header ? C.white : C.ink,
    alignment: opts.align || AlignmentType.LEFT,
    after: 0,
    line: 270,
  })];
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    shading: { fill: opts.fill || (opts.header ? C.teal : C.white), type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 90, bottom: 90, left: 110, right: 110 },
    children,
  });
}

function table(headers, rows, widths) {
  const result = [new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => cell(h, widths[i], { header: true })),
  })];
  rows.forEach((row, idx) => {
    result.push(new TableRow({
      children: row.map((value, i) => cell(value, widths[i], {
        fill: idx % 2 ? C.pale : C.white,
      })),
    }));
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: result,
  });
}

function callout(title, body, color = C.teal, fill = C.pale) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [180, CONTENT_W - 180],
    rows: [new TableRow({ children: [
      new TableCell({
        width: { size: 180, type: WidthType.DXA },
        borders: { top: border, bottom: border, left: border, right: { style: BorderStyle.NONE, size: 0, color } },
        shading: { fill: color, type: ShadingType.CLEAR },
        children: [new Paragraph("")],
      }),
      new TableCell({
        width: { size: CONTENT_W - 180, type: WidthType.DXA },
        borders: { top: border, bottom: border, left: { style: BorderStyle.NONE, size: 0, color }, right: border },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 140, bottom: 140, left: 180, right: 180 },
        children: [
          textParagraph(title, { size: 21, bold: true, color, after: 70 }),
          textParagraph(body, { size: 19, after: 0, line: 320 }),
        ],
      }),
    ] })],
  });
}

function imageBlock(filename, caption) {
  const imgPath = path.join(ROOT, "picture", filename);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 140, after: 70 },
      children: [new ImageRun({
        type: "png",
        data: fs.readFileSync(imgPath),
        transformation: { width: 620, height: 349 },
        altText: { title: caption, description: caption, name: filename },
      })],
    }),
    textParagraph(caption, { size: 16, color: C.muted, alignment: AlignmentType.CENTER, after: 120 }),
  ];
}

function sourceParagraph(index, title, url) {
  return new Paragraph({
    spacing: { after: 110, line: 300 },
    children: [
      new TextRun({ text: `[${index}] ${title}：`, font: FONT, size: 17, color: C.ink }),
      new ExternalHyperlink({
        link: url,
        children: [new TextRun({ text: url, style: "Hyperlink", font: FONT, size: 17 })],
      }),
    ],
  });
}

function sectionTitlePage(kicker, title, subtitle) {
  return [
    new Paragraph({ pageBreakBefore: true, spacing: { before: 900, after: 180 }, children: [new TextRun({ text: kicker, font: FONT, size: 19, bold: true, color: C.mint, charSpacing: 80 })] }),
    new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: title, font: FONT, size: 46, bold: true, color: C.navy })] }),
    textParagraph(subtitle, { size: 23, color: C.muted, line: 380 }),
  ];
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const children = [];

  // Cover
  children.push(new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: CONTENT_W, type: WidthType.DXA },
      borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
      shading: { fill: C.navy, type: ShadingType.CLEAR },
      margins: { top: 680, bottom: 680, left: 520, right: 520 },
      children: [
        textParagraph("ICAN 创新赛道 · 商业计划书", { size: 21, bold: true, color: C.mint, alignment: AlignmentType.LEFT, after: 260 }),
        textParagraph("PLEX Universe", { size: 52, bold: true, color: C.white, alignment: AlignmentType.LEFT, after: 180, line: 560 }),
        textParagraph("基于多智能体协同、学习者画像与知识图谱的个性化编程学习平台", { size: 27, color: "C0D8E2", alignment: AlignmentType.LEFT, after: 260, line: 420 }),
        textParagraph("从“资源展示平台”升级为“可解释、可审核、可持续优化的教学闭环”", { size: 20, color: C.white, alignment: AlignmentType.LEFT, after: 0 }),
      ],
    })] })],
  }));
  children.push(...imageBlock("探索舱.png", "PLEX Universe 学生端探索舱（现有产品截图）"));
  children.push(table(["文档属性", "内容"], [
    ["项目阶段", "高校编程学习平台 MVP / 商业化验证前期（Pre-revenue）"],
    ["计划周期", "2026—2029 年"],
    ["编制日期", "2026 年 8 月 31 日"],
    ["事实口径", "已验证事实、公开数据与测算假设分开标注"],
  ], [2500, 7364]));

  // Contents and document conventions
  children.push(...sectionTitlePage("DOCUMENT MAP", "目录与阅读说明", "商业计划书按照投资人、学校采购方与竞赛评审共同关心的问题组织。"));
  children.push(table(["章节", "核心问题"], [
    ["1. 执行摘要", "PLEX 做什么、解决谁的问题、为何现在、需要什么资源"],
    ["2. 项目与团队", "当前阶段、产品基础、团队能力与事实边界"],
    ["3. 痛点与用户", "高校编程教学中的具体损失和关键决策人"],
    ["4. 产品与技术", "闭环、功能、架构、壁垒与硬件延伸"],
    ["5. 市场与政策", "政策时机、目标市场、TAM/SAM/SOM 测算"],
    ["6. 竞争格局", "竞品优势、PLEX 差异化与进入策略"],
    ["7. 商业模式", "客户如何购买、收入从哪里来、如何交付"],
    ["8. 市场进入", "试点、转化、续费、渠道和销售节奏"],
    ["9. 运营与实施", "产品交付、客户成功、质量和合规流程"],
    ["10. 财务预测", "三年收入成本、盈亏、单位经济与情景分析"],
    ["11. 融资计划", "资金需求、用途、里程碑和约束"],
    ["12. 风险与路线图", "主要风险、缓释动作、阶段目标"],
    ["附录", "测算假设、证据索引、公开来源与待补信息"],
  ], [2600, 7264]));
  children.push(callout("口径说明", "文中“已完成”仅指仓库中有代码、截图或可复现本地报告的能力；市场规模、价格、客户数量和收入均为计划期测算，不代表已签合同或已实现收入。", C.orange, C.paleOrange));

  // Executive summary
  children.push(...sectionTitlePage("01 / EXECUTIVE SUMMARY", "执行摘要", "一页读懂 PLEX 的商业逻辑、市场入口与三年目标。"));
  children.push(heading("1.1 项目概述", 2));
  children.push(textParagraph("PLEX Universe 是面向高校编程基础课程的个性化学习平台。产品把学习者画像、知识图谱、多智能体资源生产、教师审核、试炼任务、错题复习和效果评估连接为同一条业务闭环，为学生提供差异化学习路径，为教师提供可解释的班级诊断和可执行干预。"));
  children.push(heading("1.2 市场问题", 2));
  children.push(textParagraph("高校数字教学平台已普及课程、作业与互动能力，但在编程教学场景中，学生起点差异、错误类型和学习节奏高度分化。教师面对大班时难以持续追踪每名学生，通用资源又难以随画像和错题动态变化。学校因此需要一种能够接入现有教学体系、由教师掌控、过程可审计的智能学习工具。"));
  children.push(heading("1.3 解决方案与差异化", 2));
  children.push(table(["核心能力", "PLEX 方案", "客户价值"], [
    ["动态画像", "综合作答、错题、复习、任务和知识掌握度", "更早识别掉队风险"],
    ["多智能体", "生成、评估、审核和路径任务分工并留 trace", "降低教师重复劳动"],
    ["知识图谱", "以先修关系和课程边界约束资源与路径", "减少内容漂移"],
    ["教师在环", "生成内容先审核，风险和工单可追踪", "符合教学责任边界"],
    ["游戏化闭环", "星轨、试炼、委托、成长档案和反馈", "提升学习持续性"],
  ], [2100, 4560, 3204]));
  children.push(heading("1.4 商业目标与资源诉求", 2));
  children.push(textParagraph("PLEX 计划以高校院系级试点切入，采用校园 SaaS、私有化部署、实施服务、课程共建和可选 PLEX Edge 终端形成组合收入。基准情景下，计划在第三年服务 60 所付费院校，实现约 1,440 万元年度收入并达到经营盈亏平衡。团队拟寻求 200 万元种子资金或等值算力、试点学校与产业资源支持；全部财务数字均为内部预测。"));
  children.push(callout("投资判断摘要", "优势在于现有三端产品与工程证据、面向编程教学的垂直闭环和教师在环；主要不确定性在于真实付费验证、长周期校采流程、外部模型成本和教育数据合规。", C.teal, C.pale));

  // Project and team
  children.push(...sectionTitlePage("02 / COMPANY & TEAM", "项目基础与团队", "从代码原型走向可采购产品，需要把现有工程能力转成稳定交付能力。"));
  children.push(heading("2.1 项目现状", 2));
  children.push(textParagraph("项目代号 A3，产品名称 PLEX Universe。当前为商业化验证前期，尚未确认实际营业收入、正式合同或融资。仓库已形成 Vue 3 前端、Flask 后端、SQLite/MySQL 数据路径、JWT 权限体系，以及学生、教师和管理员三端原型。"));
  children.push(table(["证据维度", "当前可追溯状态", "商业化意义"], [
    ["产品", "学生、教师、管理员三端页面与关键流程", "可开展需求访谈与院系试点"],
    ["知识", "100 个知识节点、256 条唯一关系的本地校验", "具备课程知识结构化基础"],
    ["智能体", "9 个学习 Agent、8 个评分 Agent 的工程注册与编排字段", "可继续接入真实模型与审计"],
    ["工程", "统一 API、权限、安全测试、幂等与恢复报告", "降低试点部署风险"],
    ["材料", "Git 记录、会议纪要、阶段文档、测试报告与截图", "便于竞赛和合作方尽调"],
  ], [2200, 4600, 3064]));
  children.push(...imageBlock("教师端领航总览.png", "教师端领航总览：班级指标、风险学生与教学洞察（现有产品截图）"));
  children.push(heading("2.2 团队与治理", 2));
  children.push(table(["角色", "职责", "待补强能力"], [
    ["项目/技术负责人：邬", "系统、后端、接口、数据、安全、部署与版本冻结", "企业销售与组织管理"],
    ["前端与体验：高梦琴", "前端 UI、教师/学生体验、页面联调与运营协同", "客户成功与规模化交付"],
    ["财务接口：王（待补全）", "预算、采购、外部服务授权、票据与投入产出", "完整姓名和正式职责确认"],
    ["指导教师/顾问（待补）", "教学场景、学校资源、口径审核与真实性签字", "行业顾问与法律合规"],
  ], [2400, 4600, 2864]));
  children.push(textParagraph("组织原则：产品、技术、数据和商业承诺均设置负责人；任何真实课堂实验必须先取得学校授权、教师确认与必要的知情说明；竞赛材料由项目负责人和指导教师双签。"));

  // Problem and users
  children.push(...sectionTitlePage("03 / PROBLEM & CUSTOMER", "痛点、用户与价值主张", "真正的客户是学校和教师，真正的使用者是学生；三方价值必须同时成立。"));
  children.push(heading("3.1 核心痛点", 2));
  children.push(table(["对象", "典型痛点", "造成的损失"], [
    ["学生", "基础差异大；错误原因反复；通用资源与当前薄弱点不匹配", "挫败、拖延、低完成率，难形成持续复习"],
    ["教师", "大班作业和错误类型多；个别辅导时间有限；生成内容需人工把关", "重复分析与答疑占用时间，干预滞后"],
    ["院系/学校", "平台数据分散；建设效果难量化；AI 应用存在内容和数据风险", "采购价值难证明，合规和持续运营压力高"],
  ], [1700, 4800, 3364]));
  children.push(heading("3.2 目标客户与决策链", 2));
  children.push(bullet("首要客户：开设 Python、程序设计基础、数据结构等课程的本科与高职院系。"));
  children.push(bullet("决策者：院系负责人、教务/信息化部门；影响者：课程负责人和一线教师；使用者：学生。"));
  children.push(bullet("切入单元：一门课程或一个专业的 1 学期试点，先证明教师节时、学生完成率和错题修复率。"));
  children.push(bullet("采购扩展：课程试点通过后扩至院系，再与学校统一身份、教务和数据平台对接。"));
  children.push(heading("3.3 价值主张", 2));
  children.push(callout("对学生", "得到与当前知识状态相匹配的学习任务和复习节奏；知道为什么学、下一步学什么。", C.mint, C.pale));
  children.push(callout("对教师", "从逐人排查转为风险优先的教学决策；AI 负责建议，教师保留审核和最终责任。", C.orange, C.paleOrange));
  children.push(callout("对学校", "以可追踪指标证明数字教学投入，支持本地化部署、数据治理和分级审计。", C.teal, C.pale));

  // Product and tech
  children.push(...sectionTitlePage("04 / PRODUCT & TECHNOLOGY", "产品、技术与硬件延伸", "软件闭环是主体，硬件只在能够提升课堂触达且不扩大隐私风险时进入方案。"));
  children.push(heading("4.1 产品闭环", 2));
  children.push(table(["步骤", "系统动作", "人工责任"], [
    ["1. 采集", "接收作答、错题、任务、复习和课堂反馈", "学校确定数据范围和授权"],
    ["2. 画像", "计算知识掌握、学习节奏和风险标签", "教师复核异常结论"],
    ["3. 生成/推荐", "多智能体产出讲解、示例、练习和测验", "教师审核后发布"],
    ["4. 学习", "学生完成委托、试炼和星轨任务", "教师提供必要辅导"],
    ["5. 复习", "SM-2 队列触发到期错题并影响路径", "教师可调整优先级"],
    ["6. 评估", "形成前后测和班级趋势，回流画像", "学校解释和使用结果"],
  ], [1800, 4800, 3264]));
  children.push(...imageBlock("智能体编排.png", "管理端智能体编排：生成、评估、治理与状态追踪（现有产品截图）"));
  children.push(heading("4.2 技术架构", 2));
  children.push(table(["层级", "技术选择", "商业化要求"], [
    ["体验层", "Vue 3、Vite、Naive UI、Pinia、Axios", "无障碍、移动适配、角色化体验"],
    ["业务层", "Flask、SQLAlchemy、JWT、REST JSON、SSE", "多租户、审计日志、限流与 SLA"],
    ["数据层", "SQLite 本地开发；MySQL 生产目标；知识图谱", "备份、迁移、分级分类和脱敏"],
    ["智能层", "模型适配器、学习/评分 Agent、规则兜底", "模型可替换、成本路由、内容审核"],
    ["运维层", "一键启动、测试、报告、密钥扫描", "CI/CD、可观测性、灾备和等保规划"],
  ], [1800, 4400, 3664]));
  children.push(heading("4.3 可形成的技术壁垒", 2));
  children.push(bullet("垂直数据闭环：错题、复习、画像、知识图谱和教师干预形成连续事件链。"));
  children.push(bullet("课程知识资产：节点、关系、题目、评价规则和教师审核记录可持续沉淀。"));
  children.push(bullet("可审计智能体：任务依赖、步骤、重试和审核角色留痕，便于学校治理。"));
  children.push(bullet("部署适配能力：支持校园 SaaS 与私有化两种路径，降低学校接入门槛。"));
  children.push(heading("4.4 PLEX Edge 硬件项目", 2));
  children.push(textParagraph("PLEX Edge 是面向课堂与自习空间的低隐私采集终端候选方案，采用 ESP32-S3、NFC、屏幕、按键和状态灯实现签到、理解度反馈、任务提醒与匿名求助。默认不配置摄像头和麦克风，避免把人脸、声音等敏感信息引入首版。硬件工程包提供 BOM、接线表、接口协议和固件骨架，但截至本计划书日期尚未完成实物打样与可靠性测试。"));
  children.push(table(["模块", "目标", "状态"], [
    ["身份/会话", "NFC 或课程二维码绑定当次课堂，不在设备长期保存个人信息", "工程方案"],
    ["反馈", "四键上报理解、需要帮助、完成与匿名求助", "固件骨架"],
    ["显示", "展示今日委托、倒计时和教师广播", "工程方案"],
    ["联网", "Wi-Fi + HTTPS，设备证书/令牌按校级隔离", "接口提案"],
    ["管理", "设备注册、远程配置、固件版本与在线状态", "待后端实现"],
  ], [2100, 5000, 2764]));

  // Market and policy
  children.push(...sectionTitlePage("05 / MARKET & POLICY", "市场机会与政策环境", "不引用模糊的“万亿市场”，采用高校数量与可实现客单价进行自下而上测算。"));
  children.push(heading("5.1 政策与行业时机", 2));
  children.push(textParagraph("教育部 2026 年统计公报显示，2025 年全国共有高等学校 3,167 所，高等教育在学总规模 4,872.57 万人；其中普通本科学校 1,278 所、本科层次职业学校 87 所、高职（专科）学校 1,554 所。国家教育数字化战略持续强调人工智能融入助学、助教、助研和助管，同时要求数据安全、算法安全、内容审核与教师数字能力同步建设。[1][2][3][4]"));
  children.push(textParagraph("CNNIC 第 57 次报告显示，截至 2025 年 12 月，我国在线教育用户规模为 3.27 亿。该数据说明数字学习已具备广泛用户基础，但 PLEX 的付费市场仍以高校机构采购为主，不能直接把全部在线教育用户换算为收入市场。[5]"));
  children.push(heading("5.2 TAM / SAM / SOM（内部测算）", 2));
  children.push(table(["层级", "测算方法", "结果", "口径"], [
    ["TAM", "2,919 所本科/职业本科/高职 × 20 万元年均软件与服务预算", "约 5.84 亿元/年", "可服务机构理论上限；预算为内部假设"],
    ["SAM", "TAM 院校中 35% 具备编程课程与数字化采购条件 × 20 万元", "约 2.04 亿元/年", "可触达市场；35% 为内部假设"],
    ["SOM", "第三年 60 所付费院校 × 18 万元平均 SaaS 年费", "1,080 万元 ARR", "三年可获得市场目标，不含服务和硬件"],
  ], [1300, 4200, 2000, 2364]));
  children.push(callout("测算纪律", "TAM/SAM/SOM 不是第三方市场规模报告。学校数量来自教育部，渗透率、客单价和目标客户数均为团队假设，必须通过试点报价与采购访谈持续校准。", C.orange, C.paleOrange));
  children.push(heading("5.3 PESTLE 摘要", 2));
  children.push(table(["维度", "机会", "约束"], [
    ["政策", "教育数字化与“人工智能+教育”持续推进", "学校采购需符合主管部门和校内制度"],
    ["经济", "院校重视教学质量和数字化投入产出", "财政预算和采购周期可能波动"],
    ["社会", "学生接受在线学习和智能工具", "对 AI 依赖、学术诚信和公平性存在担忧"],
    ["技术", "大模型、知识图谱与边缘终端成本下降", "模型幻觉、延迟和供应商依赖"],
    ["法律", "合规框架日趋明确", "个人信息、教育数据和生成内容标识要求提升"],
    ["环境", "在线资源减少重复印刷和差旅", "算力能耗和硬件电子废弃物需治理"],
  ], [1200, 4100, 4564]));

  // Competition
  children.push(...sectionTitlePage("06 / COMPETITION", "竞争格局与定位", "不回避成熟平台的优势，PLEX 以编程学习闭环和可审核个性化切入。"));
  children.push(heading("6.1 主要竞品与替代方案", 2));
  children.push(table(["产品/方案", "公开优势", "相对 PLEX 的空位", "竞争判断"], [
    ["雨课堂", "课堂互动、PPT/微信生态、全周期教学数据；2026 版本强化 AI 课程功能", "PLEX 需在编程错题—复习—路径闭环上做深", "强渠道与课堂入口竞品"],
    ["超星学习通", "覆盖课前课中课后、课程资源、管理端与广泛校内应用", "PLEX 不宜正面替代 LMS，应做垂直增量模块", "强平台型竞品/潜在集成方"],
    ["智慧树/知到", "共享课程、作业考试与跨校课程生态", "PLEX 聚焦校内编程过程数据和个体路径", "内容与课程平台竞品"],
    ["头歌 EduCoder", "工程实践、在线实验、自动评测和能力画像", "PLEX 需以教师审核、多智能体资源和游戏化体验形成区别", "最接近的垂直竞品"],
    ["通用大模型", "回答灵活、边际使用成本低", "缺课程边界、连续画像、校级治理与教师审核", "替代品与底层供应商"],
  ], [1750, 3250, 3150, 1714]));
  children.push(heading("6.2 差异化定位", 2));
  children.push(callout("定位陈述", "对于需要提升编程课程个性化与教学可解释性的高校院系，PLEX 是一套教师可控的学习闭环平台；与通用 LMS 或一次性 AI 问答不同，PLEX 将错题、复习、画像、知识图谱、资源和教师干预持续连接。", C.teal, C.pale));
  children.push(heading("6.3 进入策略", 2));
  children.push(bullet("不替换学校现有 LMS：优先通过标准 API、名单导入和单点登录形成增量能力。"));
  children.push(bullet("从 Python 程序设计基础单课程做出指标样板，再扩展至数据结构与算法。"));
  children.push(bullet("把“教师节省时间、错题修复率、学习完成率、风险发现提前量”作为采购证据。"));
  children.push(bullet("在大型平台强势的学校，采用课程插件、联合方案或内容共建，而非全栈替代。"));

  // Business model
  children.push(...sectionTitlePage("07 / BUSINESS MODEL", "商业模式与产品定价", "收入模型围绕学校可采购、团队可交付、客户可续费三项条件设计。"));
  children.push(heading("7.1 收入结构", 2));
  children.push(table(["收入项", "建议价格（含税前测算）", "交付内容", "续费属性"], [
    ["院系入门版 SaaS", "8—12 万元/年", "≤500 学生、3 门课、标准画像/星轨/试炼", "高"],
    ["院系标准版 SaaS", "15—25 万元/年", "≤2,000 学生、多课程、教师看板、Agent 编排", "高"],
    ["校级/私有化版", "35—80 万元首年", "统一身份、校内部署、审计、接口和运维", "中高"],
    ["课程与题库共建", "5—20 万元/项目", "知识图谱、题库清洗、评价规则和教师培训", "项目型"],
    ["PLEX Edge 套件", "999—1,299 元/台", "终端、配置、基础保修；需在实物验证后销售", "低，带运维"],
  ], [2000, 2200, 4200, 1464]));
  children.push(textParagraph("上述价格均为内部建议区间，不是已成交价格。首次试点可采用 1 学期低价或资源置换，但必须设置数据使用边界、验收指标和转正式采购条件，避免长期免费。"));
  children.push(heading("7.2 客户购买路径", 2));
  children.push(table(["阶段", "客户动作", "PLEX 动作", "转化门槛"], [
    ["发现", "教师/院系看到案例或竞赛展示", "内容传播、研讨会、教师社群", "场景相关性"],
    ["评估", "课程负责人提出数据与功能要求", "需求访谈、数据影响评估、演示", "合规和系统适配"],
    ["试点", "1 门课、1 学期、明确验收", "部署、培训、周报、问题闭环", "教师真实使用"],
    ["采购", "院系或学校完成预算与流程", "报价、合同、实施与安全材料", "预算与采购周期"],
    ["扩展", "增课程、增院系、私有化", "客户成功、效果报告、接口扩展", "可证明的教学价值"],
  ], [1350, 2850, 3300, 2364]));
  children.push(heading("7.3 商业模式画布摘要", 2));
  children.push(table(["模块", "内容"], [
    ["客户细分", "本科/高职院系、教务和信息化部门；首批聚焦编程基础课程"],
    ["价值主张", "教师可控的个性化闭环、课程知识资产、可解释风险与持续复习"],
    ["渠道", "指导教师网络、教学改革项目、竞赛、区域合作伙伴、行业会议"],
    ["关键活动", "产品研发、课程知识建模、试点实施、客户成功、合规与运维"],
    ["关键资源", "软件平台、知识图谱、题库/规则、教师合作、模型与算力"],
    ["关键伙伴", "高校教师、云/模型厂商、集成商、硬件供应商和法律顾问"],
    ["成本结构", "研发人力、模型/云资源、实施交付、销售、合规和硬件成本"],
  ], [2100, 7764]));

  // GTM
  children.push(...sectionTitlePage("08 / GO-TO-MARKET", "市场进入与增长计划", "以可量化课程试点为起点，而不是先追求大规模注册用户。"));
  children.push(heading("8.1 12 个月市场进入计划", 2));
  children.push(table(["阶段", "时间", "目标", "关键指标"], [
    ["验证", "0—3 个月", "完成 2—3 所合作院校访谈和 1 个授权试点", "≥15 名教师访谈；试点协议 1 份"],
    ["试点", "4—6 个月", "运行完整学期链路，建立客户成功流程", "教师周活跃、任务完成率、错题修复率"],
    ["转化", "7—9 个月", "形成案例与报价，推动首批付费", "付费院校 2—3 所；试点转化率 ≥30%"],
    ["复制", "10—12 个月", "扩至区域院校与合作伙伴", "付费院校 6 所；续费意向 ≥80%"],
  ], [1700, 1500, 4100, 2564]));
  children.push(heading("8.2 获客渠道", 2));
  children.push(bullet("学术与教学渠道：指导教师、课程教研室、教学改革项目、专业建设会议。"));
  children.push(bullet("示范内容：公开脱敏案例、课程实施白皮书、教师工作量节省与学习效果报告。"));
  children.push(bullet("竞赛与生态：ICAN 等创新赛事、模型/云厂商生态计划、区域教育集成商。"));
  children.push(bullet("产品驱动：允许教师申请沙盒班级，体验知识图谱、试炼和班级诊断。"));
  children.push(heading("8.3 销售与客户成功指标", 2));
  children.push(table(["漏斗阶段", "目标指标", "原因"], [
    ["有效线索", "每月 15 个院系/教师联系人", "早期以高质量关系为主"],
    ["需求访谈", "线索→访谈 ≥40%", "验证是否有预算、课程和负责人"],
    ["试点", "访谈→试点 ≥20%", "严格筛选可执行试点"],
    ["付费", "试点→付费 ≥30%", "以明确验收和采购路径提高转化"],
    ["续费", "年度续费率目标 ≥85%", "B2B 教育 SaaS 的核心健康指标"],
  ], [2300, 2600, 4964]));

  // Operations
  children.push(...sectionTitlePage("09 / OPERATIONS", "运营、交付与质量体系", "商业化不是把代码交给学校，而是持续提供课程价值、稳定服务和合规保障。"));
  children.push(heading("9.1 标准交付流程", 2));
  children.push(table(["环节", "主要输出", "建议周期", "责任角色"], [
    ["需求与合规评估", "范围、数据清单、验收指标、责任矩阵", "1—2 周", "项目+学校"],
    ["课程建模", "知识节点、先修关系、题目与评价规则", "2—4 周", "产品+教师"],
    ["部署与联调", "账号、班级、接口、权限、备份和监控", "1—3 周", "技术"],
    ["教师培训", "操作手册、审核流程、课堂脚本", "1 周", "客户成功"],
    ["试运行", "周报、缺陷、数据质量和效果基线", "4—8 周", "联合项目组"],
    ["验收与续费", "效果报告、问题清单、扩展方案", "1—2 周", "项目+采购方"],
  ], [1850, 3900, 1800, 2314]));
  children.push(heading("9.2 关键运营机制", 2));
  children.push(bullet("内容治理：AI 生成资源先通过课程安全检查，再由教师审核后发布。"));
  children.push(bullet("模型治理：保留模型版本、提示模板、请求状态、失败原因和人工复核记录。"));
  children.push(bullet("数据治理：数据最小化、分类分级、角色权限、保留期限和删除流程。"));
  children.push(bullet("客户成功：每周使用报告、教师办公时间、季度价值复盘和续费风险清单。"));
  children.push(bullet("质量保障：自动化测试、版本冻结、回滚、备份恢复、性能和安全巡检。"));
  children.push(heading("9.3 合规底线", 2));
  children.push(textParagraph("PLEX 需遵守《个人信息保护法》《数据安全法》《生成式人工智能服务管理暂行办法》以及教育数据分类分级和智慧教育平台个人信息保护相关要求。商业化前应由专业法律顾问根据实际部署和服务边界复核；本计划书不构成法律意见。[6][7][8][9]"));

  // Finance
  children.push(...sectionTitlePage("10 / FINANCIAL PLAN", "三年财务预测与单位经济", "所有数字均为内部基准情景，目的在于检验商业模式是否自洽。单位：人民币万元。"));
  children.push(heading("10.1 关键假设", 2));
  children.push(table(["驱动因素", "第 1 年", "第 2 年", "第 3 年"], [
    ["付费院校数", "6", "24", "60"],
    ["SaaS 平均年费", "12", "15", "18"],
    ["硬件套件销量（台）", "200", "800", "2,000"],
    ["硬件平均售价（元/台）", "1,200", "1,000", "900"],
    ["年度续费率目标", "—", "80%", "85%"],
  ], [3300, 2188, 2188, 2188]));
  children.push(heading("10.2 基准情景损益预测", 2));
  children.push(table(["项目", "第 1 年", "第 2 年", "第 3 年"], [
    ["SaaS 订阅收入", "72", "360", "1,080"],
    ["实施/课程共建收入", "30", "96", "180"],
    ["硬件收入", "24", "80", "180"],
    ["营业收入合计", "126", "536", "1,440"],
    ["研发人力", "160", "260", "420"],
    ["云与模型成本", "18", "60", "150"],
    ["销售与市场", "25", "90", "220"],
    ["管理与合规", "20", "45", "90"],
    ["硬件直接成本", "14", "48", "110"],
    ["实施交付成本", "18", "55", "120"],
    ["成本费用合计", "255", "558", "1,110"],
    ["经营利润（亏损）", "(129)", "(22)", "330"],
  ], [3800, 2021, 2021, 2022]));
  children.push(textParagraph("基准情景预计第三年达到年度经营盈亏平衡。该预测未计所得税、折旧、融资成本和政府补助，也未把竞赛奖金计入收入。实际结果对付费院校数、采购周期、续费率和模型成本高度敏感。"));
  children.push(heading("10.3 单位经济目标（非历史数据）", 2));
  children.push(table(["指标", "目标值", "计算方法"], [
    ["平均合同年费（ACV）", "15 万元", "标准版与入门版加权目标"],
    ["订阅毛利率", "70%", "扣除云/模型与直接交付后的目标"],
    ["单校获客成本（CAC）", "6 万元", "销售、差旅、试点支持摊销"],
    ["CAC 回收期", "约 6.9 个月", "6 ÷（15×70%÷12）"],
    ["3 年毛利 LTV", "31.5 万元", "15×70%×3；未计流失"],
    ["LTV/CAC", "约 5.3 倍", "31.5 ÷ 6"],
  ], [3000, 2400, 4464]));
  children.push(heading("10.4 情景分析：年度收入", 2));
  children.push(table(["情景", "第 1 年", "第 2 年", "第 3 年", "触发条件"], [
    ["保守", "85", "320", "780", "采购周期延长、试点转化偏低"],
    ["基准", "126", "536", "1,440", "按 6/24/60 所付费院校推进"],
    ["增长", "170", "780", "2,200", "渠道合作和校级采购提前形成"],
  ], [1700, 1500, 1500, 1500, 3664]));

  // Financing
  children.push(...sectionTitlePage("11 / FUNDING", "融资需求与资金用途", "融资不是收入证明，而是达成下一阶段可验证里程碑的资源计划。"));
  children.push(heading("11.1 资金需求", 2));
  children.push(textParagraph("团队拟寻求 200 万元种子资金，或由算力额度、试点院校、产业渠道、硬件供应和现金组成的等值资源组合。目标运行周期约 18 个月，以完成真实付费验证、产品合规补强和可复制交付为核心。具体股权比例、估值和投资条款需在公司主体、知识产权归属和财务尽调完成后协商。"));
  children.push(table(["用途", "金额", "占比", "关键产出"], [
    ["产品与研发", "90 万元", "45%", "多租户、审计、真实模型路由、稳定性与硬件打样"],
    ["试点与实施", "50 万元", "25%", "3—6 所试点、课程建模、教师支持和效果报告"],
    ["市场与销售", "30 万元", "15%", "案例、渠道、投标材料和区域拓展"],
    ["安全与合规", "20 万元", "10%", "法律复核、数据影响评估、渗透测试和制度建设"],
    ["预备金", "10 万元", "5%", "供应链、模型价格和项目延期缓冲"],
  ], [2100, 1600, 1400, 4764]));
  children.push(heading("11.2 18 个月融资里程碑", 2));
  children.push(table(["里程碑", "验证标准", "未达标处理"], [
    ["M1：授权试点", "至少 1 所学校、1 门课程、明确数据和验收", "缩小功能范围，停止无授权数据采集"],
    ["M2：首批付费", "累计 2—3 所付费院校", "复盘价格、决策链和交付成本"],
    ["M3：可复制交付", "部署周期 ≤4 周，关键流程有 SOP", "暂停扩张，优先产品化"],
    ["M4：续费证据", "首批客户续费意向 ≥80%", "分析使用深度与价值缺口"],
    ["M5：硬件决策", "完成 10 台小批量和安全/稳定测试", "不达标则保留软件方案、停止量产"],
  ], [2400, 4600, 2864]));

  // Risk and roadmap
  children.push(...sectionTitlePage("12 / RISK & ROADMAP", "风险、缓释与实施路线图", "优秀商业计划书不回避风险，而是说明如何在证据不足时停止、修正或收缩。"));
  children.push(heading("12.1 风险登记表", 2));
  children.push(table(["风险", "概率", "影响", "缓释措施"], [
    ["学校采购周期长", "高", "高", "院系小额试点、年度预算前置、渠道合作和阶段验收"],
    ["真实学习效果不足", "中", "高", "预注册指标、对照/前后测、教师复核和不显著结果披露"],
    ["生成内容错误或越界", "中", "高", "知识约束、安全检查、教师审核、模型版本与投诉闭环"],
    ["学生数据与隐私风险", "中", "高", "最小化、分级分类、私有化、权限审计、影响评估和删除机制"],
    ["模型成本或供应商变化", "中", "中高", "多供应商适配、规则兜底、缓存、配额和成本路由"],
    ["成熟平台复制功能", "中", "中高", "深耕编程闭环、教师资产、交付能力与集成合作"],
    ["团队关键人依赖", "高", "中高", "文档、代码审查、双人关键权限、顾问和阶段招聘"],
    ["硬件供应与售后", "中", "中", "先 10 台验证、通用器件、可替代 BOM、不过早量产"],
  ], [2350, 1100, 1300, 5114]));
  children.push(heading("12.2 三阶段路线图", 2));
  children.push(table(["阶段", "时间", "产品与市场目标", "退出/调整条件"], [
    ["验证期", "0—6 月", "真实课程试点、付费意愿、数据合规、硬件 1—3 台工程样机", "无授权场景或教师周活跃不足则重做需求"],
    ["复制期", "7—18 月", "6 所付费院校、标准部署包、客户成功 SOP、10 台硬件小批量", "交付毛利长期为负则收缩定制"],
    ["扩张期", "19—36 月", "60 所付费院校、区域渠道、校级集成和多学科探索", "续费率低于 70% 则暂停扩张"],
  ], [1700, 1600, 4100, 2464]));
  children.push(heading("12.3 社会价值", 2));
  children.push(bullet("降低大班编程教学中个体差异被忽视的概率，支持基础薄弱学生持续学习。"));
  children.push(bullet("把 AI 定位为教师的可审核助手，而不是替代教师的自动决策者。"));
  children.push(bullet("以可解释画像和知识路径帮助学校评估数字教学投入效果。"));
  children.push(bullet("通过私有化、数据最小化和无摄像头/麦克风硬件首版减少隐私风险。"));

  // Appendix
  children.push(...sectionTitlePage("APPENDIX A", "测算假设与证据边界", "本附录是计划书可信度的核心：明确哪些是事实、哪些是计划、哪些仍待验证。"));
  children.push(table(["陈述", "类型", "依据/处理"], [
    ["三端软件原型、统一 API、测试与截图", "仓库事实", "以当前代码、报告和截图为准"],
    ["100 节点、256 关系、9+8 Agent", "本地工程验证", "不等同真实课堂效果或真实模型质量"],
    ["高校 3,167 所、高教规模 4,872.57 万人", "公开统计", "教育部 2025 年统计公报"],
    ["TAM 5.84 亿元、SAM 2.04 亿元", "内部测算", "学校数为公开数据，预算与渗透率为假设"],
    ["三年 6/24/60 所付费院校", "经营目标", "尚无合同或收入证明"],
    ["第三年收入 1,440 万元、利润 330 万元", "财务预测", "基准情景，需按实际销售和成本滚动更新"],
    ["PLEX Edge", "工程候选方案", "有 BOM、接线和固件骨架；无实物与可靠性报告"],
    ["软著", "申请材料初稿", "不得表述为已获授权证书"],
  ], [4200, 2100, 3564]));
  children.push(heading("提交前待补信息", 2));
  children.push(bullet("团队全体成员完整姓名、学校、学院、专业、联系方式和股权/知识产权安排。"));
  children.push(bullet("指导教师姓名、职称、联系方式与真实性签字。"));
  children.push(bullet("真实客户访谈记录、试点授权、报价反馈和采购路径。"));
  children.push(bullet("若有真实实验：脱敏参与记录、知情说明、前后测方法、统计结果和教师证明。"));
  children.push(bullet("如计划融资：公司主体、银行账户、财务预算、估值依据和法律顾问意见。"));

  children.push(...sectionTitlePage("APPENDIX B", "证据索引与公开来源", "公开统计和政策均保留原始链接，访问日期为 2026-08-31。"));
  children.push(heading("B.1 项目内部证据", 2));
  children.push(table(["材料", "路径", "用途"], [
    ["产品介绍", "docs/ican-submission/PLEX-产品介绍-网页粘贴版.md", "产品定位与功能摘要"],
    ["开发日志", "docs/ican-submission/PLEX-ICAN-开发日志.pdf", "开发过程、测试、问题和分工"],
    ["其他证明", "docs/ican-submission/PLEX-ICAN-其他证明材料.zip", "Git、会议、报告、截图和软著初稿"],
    ["技术说明", "README.md / 技术选型与约定.md / TECH_PLAN.md", "技术栈与架构事实"],
    ["硬件工程包", "docs/ican-submission/PLEX-Edge-硬件项目工程包.zip", "概念设计、BOM、固件和测试计划"],
  ], [1900, 5000, 2964]));
  children.push(heading("B.2 公开来源", 2));
  children.push(sourceParagraph(1, "教育部：《2025年全国教育事业发展统计公报》", "https://www.moe.gov.cn/jyb_sjzl/sjzl_fztjgb/202607/t20260706_1442870.html"));
  children.push(sourceParagraph(2, "教育部：国家教育数字化战略行动2026年部署会", "https://www.moe.gov.cn/jyb_zzjg/huodong/202603/t20260331_1432621.html"));
  children.push(sourceParagraph(3, "中共中央、国务院：《教育强国建设规划纲要（2024—2035年）》", "https://hudong.moe.gov.cn/jyb_xxgk/moe_1777/moe_1778/202501/t20250119_1176193.html"));
  children.push(sourceParagraph(4, "教育部等九部门：《关于加快推进教育数字化的意见》", "https://www.moe.gov.cn/srcsite/A01/s7048/202504/t20250416_1187476.html"));
  children.push(sourceParagraph(5, "CNNIC：第57次《中国互联网络发展状况统计报告》", "https://www3.cnnic.cn/n4/2026/0304/c88-11549.html"));
  children.push(sourceParagraph(6, "中国人大网：《中华人民共和国个人信息保护法》", "https://www.npc.gov.cn/WZWSREL25wYy9jMi9jMzA4MzQvMjAyMTA4L3QyMDIxMDgyMF8zMTMwODguaHRtbA=="));
  children.push(sourceParagraph(7, "国家网信办：《生成式人工智能服务管理暂行办法》", "https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm"));
  children.push(sourceParagraph(8, "教育部：JY/T 0661—2025《教育数据分类分级指南》", "https://www.moe.gov.cn/srcsite/A16/s3342/202601/W020260107510856466340.pdf"));
  children.push(sourceParagraph(9, "教育部：智慧教育平台个人信息保护通用要求", "https://www.moe.gov.cn/srcsite/A16/s3342/202507/t20250731_1200912.html"));
  children.push(sourceParagraph(10, "雨课堂官方产品与版本信息", "https://www.ykt.io/download"));
  children.push(sourceParagraph(11, "智慧树官方网站", "https://www.zhihuishu.com/"));
  children.push(sourceParagraph(12, "头歌实践教学平台", "https://www.educoder.net/welcome/"));
  children.push(sourceParagraph(13, "超星一平三端产品介绍", "https://www.chaoxingbook.com/"));
  children.push(heading("B.3 GitHub Skill 参考", 2));
  children.push(textParagraph("商业计划书结构参考了本机已安装的 business-plan Skill，并检索了 GitHub/skills.sh 上的 business-document-generator、JK-0001/skills business-plan 与 astDeniss/business-skills。采用了执行摘要后写、市场自下而上测算、竞品诚实评估、单位经济、风险登记和假设分离等原则；未直接复制任何模板正文。"));

  children.push(pageBreak());
  children.push(heading("真实性确认", 1));
  children.push(textParagraph("本商业计划书基于当前项目仓库、公开政策与统计资料整理。除明确标注的仓库事实和公开数据外，价格、市场规模、客户数、收入、成本、融资和硬件量产均为计划或测算，不构成已经实现的业绩、订单或承诺。正式提交前应由项目负责人、财务负责人和指导教师逐项核对。"));
  children.push(new Paragraph({ spacing: { before: 700, after: 220 }, children: [new TextRun({ text: "项目负责人签字：________________________", font: FONT, size: 22, color: C.ink })] }));
  children.push(new Paragraph({ spacing: { after: 220 }, children: [new TextRun({ text: "指导教师签字：________________________", font: FONT, size: 22, color: C.ink })] }));
  children.push(new Paragraph({ spacing: { after: 220 }, children: [new TextRun({ text: "日期：________年____月____日", font: FONT, size: 22, color: C.ink })] }));

  const doc = new Document({
    creator: "PLEX 项目组",
    title: "PLEX Universe ICAN 商业计划书",
    description: "ICAN 创新赛道商业计划书",
    styles: {
      default: { document: { run: { font: FONT, size: 21, color: C.ink }, paragraph: { spacing: { line: 360 } } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 34, bold: true, color: C.teal },
          paragraph: { spacing: { before: 300, after: 180 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 26, bold: true, color: C.orange },
          paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 1 } },
      ],
    },
    numbering: {
      config: [{
        reference: "plex-bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 520, hanging: 260 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "○", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 920, hanging: 260 } } } },
        ],
      }],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1020, right: 1021, bottom: 1020, left: 1021, header: 520, footer: 520 },
        },
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.line, space: 1 } },
          children: [new TextRun({ text: "PLEX Universe  |  ICAN 创新赛道商业计划书", font: FONT, size: 15, color: C.muted })],
        })] }),
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          tabStops: [{ type: "right", position: 9864 }],
          children: [
            new TextRun({ text: "内部测算与竞赛材料  ·  2026-08-31", font: FONT, size: 14, color: C.muted }),
            new TextRun({ text: "\t第 ", font: FONT, size: 14, color: C.muted }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 14, color: C.muted }),
            new TextRun({ text: " 页", font: FONT, size: 14, color: C.muted }),
          ],
        })] }),
      },
      children,
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(OUTPUT, buffer);
  console.log(OUTPUT);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
