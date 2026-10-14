const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'docs', 'ican-submission', 'PLEX-ICAN-商业计划书.pptx');
const IMG = (name) => path.join(ROOT, 'picture', name);

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'PLEX 项目组';
pptx.subject = 'iCAN 大学生创新创业大赛商业计划书';
pptx.title = 'PLEX Universe 商业计划书';
pptx.company = 'PLEX 项目组';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Microsoft YaHei',
  bodyFontFace: 'Microsoft YaHei',
  lang: 'zh-CN'
};
pptx.defineSlideMaster({
  title: 'LIGHT',
  background: { color: 'F5F8F8' },
  objects: [
    { rect: { x: 0, y: 0, w: 13.333, h: 0.08, fill: { color: '18C7B5' }, line: { color: '18C7B5' } } },
    { text: { text: 'PLEX UNIVERSE · ICAN 创新赛道', options: { x: 0.55, y: 7.14, w: 5.2, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 6.5, color: '7A9099', margin: 0 } } },
    { text: { text: '商业计划书', options: { x: 11.6, y: 7.14, w: 1.15, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 6.5, color: '7A9099', align: 'right', margin: 0 } } }
  ],
  slideNumber: { x: 12.78, y: 7.14, w: 0.2, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 6.5, color: '7A9099', align: 'right', margin: 0 }
});

const C = {
  navy: '071824', navy2: '102B38', teal: '0B6470', mint: '18C7B5', orange: 'E9792B',
  ink: '1F3441', muted: '607783', pale: 'EDF5F6', white: 'FFFFFF', line: 'C9D9DE',
  paleOrange: 'FFF2E8', red: 'B34232', green: '277A58', sky: 'DCEFF2', gray: '8DA0A8'
};
const F = 'Microsoft YaHei';
const SW = 13.333, SH = 7.5;
const shadow = () => ({ type: 'outer', color: '67808A', blur: 1.5, angle: 45, distance: 1, opacity: 0.16 });

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h, fontFace: F, fontSize: opts.fontSize || 13, color: opts.color || C.ink,
    bold: opts.bold || false, margin: opts.margin ?? 0, valign: opts.valign || 'mid',
    align: opts.align || 'left', breakLine: false, fit: 'shrink', paraSpaceAfterPt: opts.paraSpaceAfterPt || 0,
    isTextBox: true, ...opts
  });
}

function title(slide, kicker, heading, sub = '') {
  addText(slide, kicker.toUpperCase(), 0.58, 0.30, 3.2, 0.22, { fontSize: 8.5, bold: true, color: C.orange, charSpacing: 1.5 });
  addText(slide, heading, 0.58, 0.57, 12.1, 0.55, { fontSize: 26, bold: true, color: C.navy });
  if (sub) addText(slide, sub, 0.60, 1.12, 11.8, 0.34, { fontSize: 10.5, color: C.muted });
}

function card(slide, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: opts.fill || C.white, transparency: opts.transparency || 0 },
    line: { color: opts.line || C.line, width: opts.lineWidth || 0.7 },
    shadow: opts.shadow === false ? undefined : shadow()
  });
}

function pill(slide, text, x, y, w, fill = C.teal, color = C.white) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h: 0.32, rectRadius: 0.14, fill: { color: fill }, line: { color: fill } });
  addText(slide, text, x, y, w, 0.32, { fontSize: 8.5, bold: true, color, align: 'center' });
}

function metric(slide, x, y, w, value, label, accent = C.mint, note = '') {
  card(slide, x, y, w, 1.18, { line: 'D4E1E5' });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.07, h: 1.18, fill: { color: accent }, line: { color: accent } });
  addText(slide, value, x + 0.22, y + 0.16, w - 0.35, 0.43, { fontSize: 22, bold: true, color: C.navy });
  addText(slide, label, x + 0.22, y + 0.61, w - 0.35, 0.25, { fontSize: 9.5, bold: true, color: C.ink });
  if (note) addText(slide, note, x + 0.22, y + 0.88, w - 0.35, 0.18, { fontSize: 7.5, color: C.muted });
}

function image(slide, file, x, y, w, h, transparency = 0) {
  slide.addImage({ path: IMG(file), x, y, w, h, transparency });
}

function sectionLabel(slide, n, text, x, y, accent = C.mint) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: 0.36, h: 0.36, fill: { color: accent }, line: { color: accent } });
  addText(slide, String(n), x, y, 0.36, 0.36, { fontSize: 10, bold: true, color: C.navy, align: 'center' });
  addText(slide, text, x + 0.46, y - 0.01, 2.0, 0.38, { fontSize: 11, bold: true, color: C.ink });
}

function bulletList(slide, items, x, y, w, h, opts = {}) {
  const runs = [];
  items.forEach((t, i) => {
    runs.push({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, hanging: 3 } });
  });
  slide.addText(runs, { x, y, w, h, fontFace: F, fontSize: opts.fontSize || 11, color: opts.color || C.ink, margin: 0.04, breakLine: false, fit: 'shrink', paraSpaceAfterPt: opts.space || 8, valign: 'top' });
}

function arrow(slide, x, y, w, color = C.mint) {
  slide.addShape(pptx.ShapeType.chevron, { x, y, w, h: 0.34, fill: { color }, line: { color } });
}

// 01 Cover
{
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  image(s, '探索舱.png', 6.45, 0, 6.88, 7.5);
  s.addShape(pptx.ShapeType.rect, { x: 6.45, y: 0, w: 6.88, h: 7.5, fill: { color: C.navy, transparency: 28 }, line: { color: C.navy, transparency: 100 } });
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 8.1, h: 7.5, fill: { color: C.navy, transparency: 0 }, line: { color: C.navy } });
  pill(s, 'iCAN 大学生创新创业大赛 · 创新赛道', 0.68, 0.64, 3.15, C.orange);
  addText(s, 'PLEX', 0.68, 1.35, 5.4, 1.0, { fontSize: 52, bold: true, color: C.white, charSpacing: 2 });
  addText(s, 'UNIVERSE', 0.72, 2.22, 5.4, 0.45, { fontSize: 20, bold: true, color: C.mint, charSpacing: 7 });
  addText(s, '面向高校编程教育的\n个性化学习操作系统', 0.68, 3.02, 5.25, 1.08, { fontSize: 25, bold: true, color: C.white, breakLine: true, valign: 'top', breakLineOnOverflow: false });
  addText(s, '动态画像 × 知识图谱 × 多智能体 × 教师闭环', 0.71, 4.33, 5.55, 0.34, { fontSize: 11.5, color: 'B8D7DA' });
  s.addShape(pptx.ShapeType.line, { x: 0.7, y: 5.16, w: 4.8, h: 0, line: { color: C.teal, width: 1.2 } });
  addText(s, '商业计划书', 0.7, 5.42, 2.2, 0.46, { fontSize: 18, bold: true, color: C.orange });
  addText(s, '参赛项目：PLEX Universe\n版本：V1.0｜2026 年 8 月', 0.7, 6.03, 4.6, 0.72, { fontSize: 10, color: 'AFC4CA', valign: 'top', breakLine: true });
}

// 02 Executive summary
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'EXECUTIVE SUMMARY', '一页看懂 PLEX', '用可解释、可干预、可迭代的智能学习闭环，解决高校编程教学“教得累、学不准、管不清”。');
  const blocks = [
    ['痛点', '传统平台记录“做了什么”，却难以解释“为什么不会”', C.red],
    ['方案', '动态学习画像驱动个性路径；教师始终保有审核与干预权', C.teal],
    ['客户', '高校计算机院系、职业院校、课程负责人及教务管理者', C.orange],
    ['模式', '院校 SaaS 订阅 + 私有化部署 + 课程共建服务', C.green]
  ];
  blocks.forEach((b, i) => {
    const x = 0.6 + (i % 2) * 6.12, y = 1.62 + Math.floor(i / 2) * 1.32;
    card(s, x, y, 5.78, 1.02);
    pill(s, b[0], x + 0.22, y + 0.18, 0.78, b[2]);
    addText(s, b[1], x + 1.18, y + 0.13, 4.28, 0.72, { fontSize: 12, bold: true, color: C.ink });
  });
  metric(s, 0.6, 4.52, 2.85, '2,919 所', '目标院校基数', C.teal, '本科 + 职业本科 + 高职');
  metric(s, 3.66, 4.52, 2.85, '10.8 百万', '第 3 年 SaaS ARR 目标', C.orange, '60 所 × 18 万元/年');
  metric(s, 6.72, 4.52, 2.85, '70%', '目标 SaaS 毛利率', C.green, '规模化阶段管理目标');
  metric(s, 9.78, 4.52, 2.85, '200 万元', '拟融资 / 等值资源', C.mint, '用于研发、试点与市场验证');
  addText(s, '当前阶段：软件系统已形成可演示闭环；商业化指标为内部测算，须以真实试点和合同验证。', 0.62, 6.18, 12.0, 0.36, { fontSize: 10, bold: true, color: C.red, align: 'center' });
}

// 03 Pain points
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'PROBLEM', '高校编程教学的三重断层', '数据不少，但缺少把“学习行为—能力诊断—教学行动”连起来的系统。');
  const personas = [
    ['学生', '路径不清', '知道自己“错了”，不知道知识断点在哪里；统一节奏造成掉队或低效重复。'],
    ['教师', '反馈滞后', '大班教学难以实时识别共性误区，备课、出题、批改与干预重复耗时。'],
    ['管理者', '效果难证', '过程数据散落，课程改革、资源投入与学习成效之间缺少可追踪证据。']
  ];
  personas.forEach((p, i) => {
    const x = 0.65 + i * 4.23;
    card(s, x, 1.65, 3.82, 3.28, { fill: i === 1 ? C.paleOrange : C.white });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 1.38, y: 1.96, w: 1.05, h: 1.05, fill: { color: [C.teal, C.orange, C.navy2][i] }, line: { color: [C.teal, C.orange, C.navy2][i] } });
    addText(s, ['学', '教', '管'][i], x + 1.38, 1.96, 1.05, 1.05, { fontSize: 24, bold: true, color: C.white, align: 'center' });
    addText(s, p[0], x + 0.25, 3.22, 3.32, 0.35, { fontSize: 16, bold: true, color: C.navy, align: 'center' });
    addText(s, p[1], x + 0.25, 3.65, 3.32, 0.3, { fontSize: 11, bold: true, color: C.orange, align: 'center' });
    addText(s, p[2], x + 0.42, 4.05, 2.98, 0.63, { fontSize: 10, color: C.muted, align: 'center', valign: 'top' });
  });
  card(s, 0.65, 5.30, 12.0, 0.95, { fill: C.navy, line: C.navy });
  addText(s, '机会窗口', 0.92, 5.54, 1.2, 0.35, { fontSize: 13, bold: true, color: C.mint });
  addText(s, '教育数字化进入“智能化、集成化、国际化”阶段，高校需要从工具堆叠走向面向教学结果的闭环系统。', 2.2, 5.46, 9.95, 0.48, { fontSize: 13, bold: true, color: C.white });
  addText(s, '政策来源：教育部 2026 年全国教育数字化工作会议；《教育强国建设规划纲要（2024—2035年）》', 0.67, 6.50, 11.9, 0.25, { fontSize: 7.5, color: C.gray });
}

// 04 Solution loop
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'SOLUTION', 'PLEX：从诊断到干预的学习闭环', '不是再做一个题库，而是让每次学习行为都进入可解释、可调整的教学循环。');
  const steps = [
    ['01', '采集', '作答、行为、节奏'], ['02', '诊断', '知识点与能力断点'], ['03', '规划', '个性化学习路径'],
    ['04', '生成', '多智能体生产资源'], ['05', '练习', '任务、试炼、复习'], ['06', '评估', '多维评分与反馈'], ['07', '干预', '教师审核与调整']
  ];
  steps.forEach((st, i) => {
    const x = 0.53 + i * 1.82;
    s.addShape(pptx.ShapeType.ellipse, { x, y: 2.2, w: 1.15, h: 1.15, fill: { color: i === 6 ? C.orange : C.teal }, line: { color: C.white, width: 1.5 }, shadow: shadow() });
    addText(s, st[0], x, 2.31, 1.15, 0.28, { fontSize: 9, bold: true, color: i === 6 ? C.navy : C.mint, align: 'center' });
    addText(s, st[1], x, 2.59, 1.15, 0.38, { fontSize: 15, bold: true, color: C.white, align: 'center' });
    addText(s, st[2], x - 0.15, 3.52, 1.45, 0.48, { fontSize: 9, color: C.muted, align: 'center' });
    if (i < 6) arrow(s, x + 1.27, 2.59, 0.37, C.line);
  });
  s.addShape(pptx.ShapeType.arc, { x: 1.05, y: 3.95, w: 10.95, h: 1.85, adjustPoint: 0.35, rotate: 180, fill: { color: C.white, transparency: 100 }, line: { color: C.mint, width: 2, beginArrowType: 'none', endArrowType: 'triangle' } });
  pill(s, '关键差异', 5.35, 4.78, 1.05, C.orange);
  addText(s, '教师在环：AI 给出建议，教师拥有发布、修订、驳回与追踪权', 3.03, 5.25, 7.75, 0.5, { fontSize: 17, bold: true, color: C.navy, align: 'center' });
  addText(s, '系统价值 = 更早发现问题 × 更低干预成本 × 更可证明的学习效果', 2.55, 6.06, 8.75, 0.38, { fontSize: 12, color: C.teal, bold: true, align: 'center' });
}

// 05 Product roles
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'PRODUCT', '一个底座，连接学生、教师与管理者', '正式产品基于 Vue 3 + Flask 构建，覆盖学习、教学管理和系统治理。');
  image(s, '教师端领航总览.png', 0.62, 1.60, 7.18, 4.04);
  s.addShape(pptx.ShapeType.roundRect, { x: 0.62, y: 1.60, w: 7.18, h: 4.04, rectRadius: 0.08, fill: { color: C.white, transparency: 100 }, line: { color: C.line, width: 0.8 }, shadow: shadow() });
  const rows = [
    ['学生端', '探索舱、今日委托、星轨、试炼关卡', C.teal],
    ['教师端', '班级总览、学情观测、任务发布、干预追踪', C.orange],
    ['管理端', '知识图谱、智能体编排、权限与运行监控', C.navy2]
  ];
  rows.forEach((r, i) => {
    const y = 1.62 + i * 1.36;
    card(s, 8.08, y, 4.58, 1.12, { fill: i === 1 ? C.paleOrange : C.white });
    s.addShape(pptx.ShapeType.rect, { x: 8.08, y, w: 0.09, h: 1.12, fill: { color: r[2] }, line: { color: r[2] } });
    addText(s, r[0], 8.34, y + 0.13, 1.1, 0.32, { fontSize: 13, bold: true, color: r[2] });
    addText(s, r[1], 8.34, y + 0.52, 3.93, 0.39, { fontSize: 10.5, color: C.ink });
  });
  card(s, 8.08, 5.70, 4.58, 0.72, { fill: C.navy, line: C.navy });
  addText(s, '共享同一套画像、知识与评价数据', 8.35, 5.88, 4.0, 0.32, { fontSize: 11.5, bold: true, color: C.white, align: 'center' });
}

// 06 Tech moat
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'TECHNOLOGY', '可落地的技术架构与数据飞轮', '工程能力不是模型调用次数，而是把数据、知识、智能体和教学治理稳定地组织起来。');
  const layers = [
    ['应用层', '学生端｜教师端｜管理端', C.orange],
    ['业务层', '学习路径｜试炼｜复习｜评价｜干预', C.teal],
    ['智能层', '9 个学习智能体 + 8 个评测智能体*', C.navy2],
    ['知识层', '知识图谱｜动态画像｜资源索引', C.green],
    ['基础层', 'Flask｜SQLAlchemy｜JWT｜MySQL / SQLite', C.gray]
  ];
  layers.forEach((l, i) => {
    const y = 1.57 + i * 0.83;
    s.addShape(pptx.ShapeType.roundRect, { x: 0.68 + i * 0.17, y, w: 6.55 - i * 0.34, h: 0.62, rectRadius: 0.07, fill: { color: l[2] }, line: { color: l[2] }, shadow: i < 2 ? shadow() : undefined });
    addText(s, l[0], 0.94 + i * 0.17, y, 1.0, 0.62, { fontSize: 11, bold: true, color: C.white });
    addText(s, l[1], 2.02 + i * 0.17, y, 4.7 - i * 0.34, 0.62, { fontSize: 10.5, color: C.white, align: 'right' });
  });
  image(s, '知识图谱.png', 7.55, 1.58, 5.12, 2.88);
  card(s, 7.55, 4.68, 5.12, 1.38, { fill: C.navy, line: C.navy });
  addText(s, '数据飞轮', 7.82, 4.91, 1.25, 0.3, { fontSize: 13, bold: true, color: C.mint });
  addText(s, '学习行为 → 画像更新 → 路径优化 → 教师反馈 → 规则与资源迭代', 9.05, 4.80, 3.23, 0.58, { fontSize: 11.5, bold: true, color: C.white, align: 'center' });
  addText(s, '护城河：可解释的过程数据、课程知识结构、教师反馈沉淀与可替换模型接口。', 7.82, 5.49, 4.45, 0.31, { fontSize: 8.8, color: 'B8D7DA', align: 'center' });
  addText(s, '* 数量来自当前仓库工程结构核验，不等同于生产环境性能或教学效果证明。', 0.69, 6.43, 11.8, 0.23, { fontSize: 7.5, color: C.gray });
}

// 07 Validation
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'TRACTION', '当前进展：从概念进入可演示系统', '以代码、界面、文档和可复核功能为证据；不虚构用户、收入或合同。');
  metric(s, 0.63, 1.58, 2.75, '100', '知识节点', C.teal, '本地工程核验');
  metric(s, 3.55, 1.58, 2.75, '256', '知识关系', C.orange, '本地工程核验');
  metric(s, 6.47, 1.58, 2.75, '17', '学习与评测智能体', C.green, '9 + 8，工程结构核验');
  metric(s, 9.39, 1.58, 3.27, '3 端', '学生 / 教师 / 管理', C.mint, '形成产品闭环界面');
  const stages = [
    ['已完成', '核心前后端、角色权限、知识图谱、学习链路、演示素材', C.green],
    ['进行中', '真实课程试点、效果指标定义、部署与运维标准化', C.orange],
    ['待验证', '付费意愿、规模化获客、模型成本、硬件样机与量产', C.red]
  ];
  stages.forEach((st, i) => {
    const y = 3.18 + i * 0.95;
    pill(s, st[0], 0.78, y + 0.16, 1.02, st[2]);
    s.addShape(pptx.ShapeType.line, { x: 1.93, y: y + 0.32, w: 0.55, h: 0, line: { color: st[2], width: 1.5 } });
    card(s, 2.45, y, 10.05, 0.66, { shadow: false, fill: i === 2 ? 'FFF6F3' : C.white });
    addText(s, st[1], 2.72, y + 0.09, 9.45, 0.45, { fontSize: 11.5, bold: true, color: C.ink });
  });
  addText(s, '下一关键里程碑：完成 1–2 门真实课程试点，沉淀前测/后测、完成率、教师节时与留存数据。', 0.68, 6.28, 12.0, 0.38, { fontSize: 12.5, bold: true, color: C.teal, align: 'center' });
}

// 08 Market
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'MARKET', '聚焦高校编程教育，先窄后宽', '市场测算采用院校付费的自下而上模型，避免用宏观教育支出替代可服务市场。');
  const circles = [
    { x: 0.66, y: 1.63, w: 4.65, c: C.sky, v: 'TAM', n: '5.84 亿元/年', d: '2,919 所 × 20 万元' },
    { x: 2.06, y: 2.37, w: 3.25, c: '8FD9D2', v: 'SAM', n: '2.04 亿元/年', d: '35% 可触达院校' },
    { x: 3.02, y: 3.11, w: 2.29, c: C.orange, v: 'SOM', n: '1,080 万元', d: '第 3 年 60 所' }
  ];
  circles.forEach((q) => {
    s.addShape(pptx.ShapeType.ellipse, { x: q.x, y: q.y, w: q.w, h: q.w, fill: { color: q.c, transparency: q.v === 'TAM' ? 7 : 0 }, line: { color: C.white, width: 1.2 } });
    const ty = q.y + (q.v === 'TAM' ? 0.35 : q.v === 'SAM' ? 0.28 : 0.29);
    addText(s, q.v, q.x + 0.12, ty, q.w - 0.24, 0.28, { fontSize: 9.5, bold: true, color: q.v === 'SOM' ? C.white : C.teal, align: 'center' });
    addText(s, q.n, q.x + 0.12, ty + 0.32, q.w - 0.24, 0.45, { fontSize: q.v === 'SOM' ? 14 : 17, bold: true, color: q.v === 'SOM' ? C.white : C.navy, align: 'center' });
    addText(s, q.d, q.x + 0.12, ty + 0.78, q.w - 0.24, 0.30, { fontSize: 8.2, color: q.v === 'SOM' ? C.white : C.muted, align: 'center' });
  });
  card(s, 6.02, 1.65, 6.62, 4.68);
  addText(s, '为什么现在', 6.35, 1.94, 2.2, 0.4, { fontSize: 17, bold: true, color: C.navy });
  bulletList(s, [
    '政策：教育数字化从平台建设转向智能化应用与数据治理',
    '供给：大模型降低内容生产成本，但教学可信与流程整合仍是缺口',
    '需求：高校需要提升大班教学效率、课程改革证据与个性支持能力',
    '切入：编程课程高频、可测量、反馈链清晰，适合形成首个标杆场景'
  ], 6.38, 2.52, 5.82, 2.34, { fontSize: 11.5, space: 11 });
  addText(s, '测算口径', 6.38, 5.08, 1.0, 0.3, { fontSize: 10, bold: true, color: C.orange });
  addText(s, 'TAM / SAM / SOM 均为内部经营模型，不代表已签约收入或第三方市场报告结论。', 7.45, 4.97, 4.72, 0.52, { fontSize: 9.5, color: C.muted });
  addText(s, '院校基数来源：教育部《2025年全国教育事业发展统计公报》（本科、职业本科、高职合计 2,919 所）。', 0.67, 6.51, 11.9, 0.25, { fontSize: 7.5, color: C.gray });
}

// 09 Competition
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'COMPETITION', '我们不替代所有平台，专注“智能学习闭环”', 'PLEX 的竞争策略是与教务/LMS 共存，以画像、路径与干预能力形成差异化。');
  const data = [
    ['类型 / 产品', '课程管理', '编程实训', '动态画像', '教师干预闭环', '可私有化'],
    ['雨课堂 / 超星 / 智慧树', '强', '弱—中', '中', '中', '部分'],
    ['EduCoder 等实训平台', '中', '强', '中', '中', '部分'],
    ['通用大模型', '弱', '中', '弱', '弱', '弱'],
    ['PLEX', '中', '强', '强', '强', '支持']
  ];
  const hdrs = ['类型 / 产品', '课程管理', '编程实训', '动态画像', '教师干预闭环', '可私有化'];
  const widths = [2.88, 1.62, 1.62, 1.62, 2.05, 2.24];
  const rows = data.slice(1);
  let hx = 0.65;
  hdrs.forEach((h, i) => {
    s.addShape(pptx.ShapeType.rect, { x: hx, y: 1.55, w: widths[i], h: 0.58, fill: { color: C.navy }, line: { color: C.line, width: 0.5 } });
    addText(s, h, hx, 1.55, widths[i], 0.58, { fontSize: 10, bold: true, color: C.white, align: 'center' });
    hx += widths[i];
  });
  rows.forEach((row, ri) => {
    let cx = 0.65;
    row.forEach((cell, ci) => {
      const cy = 2.13 + ri * 0.67;
      s.addShape(pptx.ShapeType.rect, { x: cx, y: cy, w: widths[ci], h: 0.67, fill: { color: ri === 3 ? C.paleOrange : C.white }, line: { color: C.line, width: 0.5 } });
      addText(s, cell, cx, cy, widths[ci], 0.67, { fontSize: 10.2, bold: ri === 3 || ci === 0, color: ri === 3 && ci === 0 ? C.orange : C.ink, align: 'center' });
      cx += widths[ci];
    });
  });
  card(s, 0.65, 5.15, 12.03, 0.95, { fill: C.paleOrange, line: 'F2C5A2' });
  addText(s, '定位原则', 0.92, 5.41, 1.15, 0.32, { fontSize: 12, bold: true, color: C.orange });
  addText(s, '先做“编程课程智能化增量层”，通过标准接口接入既有教学体系；用学习效果与教师节时建立采购理由。', 2.08, 5.33, 9.95, 0.47, { fontSize: 12, bold: true, color: C.ink });
  addText(s, '注：竞品比较基于公开产品定位与功能描述，具体能力随版本和采购方案变化。', 0.67, 6.46, 11.9, 0.25, { fontSize: 7.5, color: C.gray });
}

// 10 Business model
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'BUSINESS MODEL', '以院校订阅为主，服务与硬件为辅', '先用软件建立持续收入和数据闭环，再按真实需求扩展部署、共建与边缘终端。');
  const offers = [
    ['入门 SaaS', '8–12 万元 / 年', '单院系、基础画像与学习任务', C.teal],
    ['标准 SaaS', '15–25 万元 / 年', '多课程、教师闭环与数据看板', C.orange],
    ['校级 / 私有化', '35–80 万元 / 首年', '校级部署、接口、权限与运维', C.navy2],
    ['课程共建', '5–20 万元 / 项目', '知识图谱、题库和课程设计服务', C.green]
  ];
  offers.forEach((o, i) => {
    const x = 0.65 + i * 3.05;
    card(s, x, 1.62, 2.72, 2.55, { fill: i === 1 ? C.paleOrange : C.white, line: i === 1 ? 'F2B783' : C.line });
    pill(s, o[0], x + 0.30, 1.91, 1.45, o[3]);
    addText(s, o[1], x + 0.24, 2.55, 2.24, 0.55, { fontSize: 17, bold: true, color: C.navy, align: 'center' });
    addText(s, o[2], x + 0.32, 3.30, 2.08, 0.50, { fontSize: 9.5, color: C.muted, align: 'center' });
  });
  card(s, 0.65, 4.55, 12.02, 1.22, { fill: C.navy, line: C.navy });
  addText(s, '收入结构目标（第 3 年）', 0.93, 4.81, 2.25, 0.32, { fontSize: 12, bold: true, color: C.mint });
  const mix = [['SaaS', '75%', C.mint], ['实施 / 共建', '12.5%', C.orange], ['硬件', '12.5%', '6FA9B4']];
  mix.forEach((m, i) => {
    const x = 3.38 + i * 2.72;
    addText(s, m[0], x, 4.70, 1.2, 0.28, { fontSize: 9, color: 'B8D7DA' });
    addText(s, m[1], x, 4.98, 1.45, 0.46, { fontSize: 20, bold: true, color: m[2] });
  });
  addText(s, '硬件 PLEX Edge 建议售价 999–1,299 元 / 台，仅在样机、成本与需求验证后进入正式销售。', 0.65, 6.15, 12.0, 0.38, { fontSize: 10.5, bold: true, color: C.red, align: 'center' });
}

// 11 GTM
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'GO-TO-MARKET', '用课程试点拿下标杆，再复制到院系与学校', '高校采购周期长，第一年重点是验证效果、建立案例和打磨交付标准。');
  const phases = [
    ['0–3 月', '需求验证', '访谈 20+ 教师\n锁定 2 门试点课', C.teal],
    ['4–6 月', '试点运行', '完成前后测\n沉淀教师节时数据', C.orange],
    ['7–9 月', '付费转化', '形成标准方案\n获得首批付费客户', C.green],
    ['10–12 月', '案例复制', '院系扩科\n伙伴渠道与区域复制', C.navy2]
  ];
  s.addShape(pptx.ShapeType.line, { x: 1.18, y: 3.07, w: 10.85, h: 0, line: { color: C.line, width: 4 } });
  phases.forEach((p, i) => {
    const x = 0.68 + i * 3.03;
    addText(s, p[0], x, 1.65, 2.7, 0.34, { fontSize: 12, bold: true, color: p[3], align: 'center' });
    card(s, x, 2.02, 2.70, 2.34, { fill: i === 1 ? C.paleOrange : C.white });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 1.03, y: 2.78, w: 0.64, h: 0.64, fill: { color: p[3] }, line: { color: C.white, width: 1.2 } });
    addText(s, String(i + 1), x + 1.03, 2.78, 0.64, 0.64, { fontSize: 15, bold: true, color: C.white, align: 'center' });
    addText(s, p[1], x + 0.25, 3.48, 2.20, 0.34, { fontSize: 14, bold: true, color: C.navy, align: 'center' });
    addText(s, p[2], x + 0.28, 3.88, 2.14, 0.38, { fontSize: 9.5, color: C.muted, align: 'center', breakLine: true });
  });
  const ks = [['试点课', '2 门'], ['付费院校', '6 所'], ['年度合同额', '≥ 72 万'], ['可复用案例', '≥ 3 个']];
  ks.forEach((k, i) => {
    const x = 0.73 + i * 3.02;
    addText(s, k[0], x, 5.03, 1.35, 0.30, { fontSize: 9.5, color: C.muted, align: 'center' });
    addText(s, k[1], x, 5.38, 1.35, 0.48, { fontSize: 21, bold: true, color: i === 1 ? C.orange : C.teal, align: 'center' });
  });
  addText(s, '首年目标是经营假设，不是现有业绩；每个阶段均设置“继续 / 调整 / 停止”门槛。', 0.65, 6.34, 12.0, 0.34, { fontSize: 9.5, color: C.red, align: 'center' });
}

// 12 Delivery
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'DELIVERY', '标准化交付，降低高校采用门槛', '把项目制经验沉淀为可复制的实施包、培训包和成效报告。');
  const flow = [
    ['需求诊断', '课程、师生、数据边界'], ['轻量接入', '账号 / 课程 / 知识点'], ['教师共创', '规则、资源、评价口径'],
    ['试点运行', '4–8 周小范围验证'], ['成效复盘', '学习与效率指标'], ['扩容续费', '扩课程 / 扩院系']
  ];
  flow.forEach((f, i) => {
    const x = 0.55 + i * 2.08;
    card(s, x, 2.15, 1.70, 1.45, { fill: i === 3 ? C.paleOrange : C.white });
    addText(s, `0${i + 1}`, x + 0.18, 2.33, 0.36, 0.28, { fontSize: 9, bold: true, color: i === 3 ? C.orange : C.teal });
    addText(s, f[0], x + 0.17, 2.70, 1.36, 0.32, { fontSize: 12.5, bold: true, color: C.navy, align: 'center' });
    addText(s, f[1], x + 0.16, 3.12, 1.38, 0.30, { fontSize: 8.7, color: C.muted, align: 'center' });
    if (i < 5) arrow(s, x + 1.77, 2.70, 0.23, C.line);
  });
  card(s, 0.68, 4.38, 5.86, 1.30, { fill: C.navy, line: C.navy });
  addText(s, '试点成功指标', 0.95, 4.61, 1.42, 0.34, { fontSize: 13, bold: true, color: C.mint });
  addText(s, '完成率｜知识掌握提升｜教师备课/批改节时｜学生留存｜教师推荐意愿', 2.42, 4.51, 3.76, 0.52, { fontSize: 10.5, bold: true, color: C.white, align: 'center' });
  card(s, 6.80, 4.38, 5.86, 1.30, { fill: C.paleOrange, line: 'F2C5A2' });
  addText(s, '交付护栏', 7.08, 4.61, 1.15, 0.34, { fontSize: 13, bold: true, color: C.orange });
  addText(s, '数据最小化｜角色权限｜教师审核｜模型可替换｜日志追踪｜退出与数据返还机制', 8.29, 4.51, 3.98, 0.52, { fontSize: 10.5, bold: true, color: C.ink, align: 'center' });
}

// 13 Financial model
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'FINANCIALS', '三年收入模型：以 SaaS 扩张驱动规模化', '单位：万元；基准情景为内部经营测算，不构成业绩承诺。');
  s.addChart(pptx.ChartType.bar, [
    { name: 'SaaS', labels: ['第1年', '第2年', '第3年'], values: [72, 360, 1080] },
    { name: '实施/共建', labels: ['第1年', '第2年', '第3年'], values: [30, 96, 180] },
    { name: '硬件', labels: ['第1年', '第2年', '第3年'], values: [24, 80, 180] }
  ], {
    x: 0.65, y: 1.62, w: 7.25, h: 4.62, catAxisLabelFontFace: F, valAxisLabelFontFace: F,
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 9, showLegend: true, legendPos: 'b',
    showTitle: false, showValue: false, showCatName: false, showSerName: false, showPercent: false,
    chartColors: [C.teal, C.orange, '6FA9B4'], showCatName: false, grouping: 'stacked',
    valAxisMinVal: 0, valAxisMaxVal: 1500, valAxisMajorUnit: 300, showValue: false,
    showBorder: false, showGridLines: true, gridLine: { color: 'D9E4E7', width: 1 },
    legendFontFace: F, legendFontSize: 9
  });
  card(s, 8.18, 1.63, 4.49, 4.58);
  addText(s, '关键假设', 8.48, 1.92, 1.6, 0.38, { fontSize: 17, bold: true, color: C.navy });
  const assumptions = [
    ['付费院校', '6 → 24 → 60 所'],
    ['SaaS 客单价', '12 → 15 → 18 万元'],
    ['硬件销量', '200 → 800 → 2,000 台'],
    ['硬件单价', '1,200 → 1,000 → 900 元'],
    ['第 3 年收入', '1,440 万元']
  ];
  assumptions.forEach((a, i) => {
    const y = 2.55 + i * 0.58;
    addText(s, a[0], 8.48, y, 1.50, 0.29, { fontSize: 9.5, color: C.muted });
    addText(s, a[1], 9.98, y, 2.32, 0.29, { fontSize: 11.5, bold: true, color: i === 4 ? C.orange : C.ink, align: 'right' });
    s.addShape(pptx.ShapeType.line, { x: 8.48, y: y + 0.38, w: 3.82, h: 0, line: { color: C.line, width: 0.5 } });
  });
  addText(s, '增长逻辑：先用服务保证试点成功，再提高标准产品占比与续费收入。', 8.47, 5.62, 3.84, 0.42, { fontSize: 9.5, color: C.teal, bold: true, align: 'center' });
}

// 14 P&L and unit economics
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'FINANCIALS', '第 3 年跨越盈亏平衡，单位经济模型可成立', '现金流与毛利仍受试点转化、模型成本和交付标准化程度影响。');
  const table = [
    ['项目（万元）', '第 1 年', '第 2 年', '第 3 年'],
    ['营业收入', '126', '536', '1,440'],
    ['总成本', '255', '558', '1,110'],
    ['经营利润', '-129', '-22', '330']
  ];
  const tWidths = [2.25, 1.33, 1.33, 1.34];
  const tHeights = [0.55, 0.55, 0.55, 0.60];
  let ty = 1.62;
  table.forEach((row, ri) => {
    let tx = 0.66;
    row.forEach((cell, ci) => {
      const fill = ri === 0 ? C.navy : (ri === 3 ? C.paleOrange : C.white);
      s.addShape(pptx.ShapeType.rect, { x: tx, y: ty, w: tWidths[ci], h: tHeights[ri], fill: { color: fill }, line: { color: C.line, width: 0.5 } });
      addText(s, cell, tx, ty, tWidths[ci], tHeights[ri], { fontSize: ri === 0 ? 10.5 : 12, bold: ri === 0 || ri === 3, color: ri === 0 ? C.white : (ri === 3 && ci > 0 ? C.orange : C.ink), align: 'center' });
      tx += tWidths[ci];
    });
    ty += tHeights[ri];
  });
  card(s, 0.66, 4.20, 6.25, 1.42, { fill: C.paleOrange, line: 'F2C5A2' });
  addText(s, '盈亏平衡条件', 0.95, 4.47, 1.52, 0.35, { fontSize: 13, bold: true, color: C.orange });
  addText(s, '约 43–48 所标准 SaaS 客户，或以私有化项目补充收入；实际取决于续费率与交付成本。', 2.45, 4.36, 4.02, 0.58, { fontSize: 11, bold: true, color: C.ink, align: 'center' });
  const unit = [
    ['ACV', '15 万元'], ['目标毛利率', '70%'], ['CAC', '6 万元'], ['回收期', '6.9 个月'], ['3 年 LTV', '31.5 万元'], ['LTV / CAC', '5.3×']
  ];
  unit.forEach((u, i) => {
    const x = 7.24 + (i % 2) * 2.74, y = 1.62 + Math.floor(i / 2) * 1.36;
    card(s, x, y, 2.46, 1.05, { fill: i === 5 ? C.navy : C.white, line: i === 5 ? C.navy : C.line });
    addText(s, u[0], x + 0.18, y + 0.14, 2.10, 0.24, { fontSize: 9, color: i === 5 ? 'B8D7DA' : C.muted, align: 'center' });
    addText(s, u[1], x + 0.18, y + 0.45, 2.10, 0.38, { fontSize: 18, bold: true, color: i === 5 ? C.mint : C.navy, align: 'center' });
  });
  addText(s, '单位经济参数为规模化目标；试点期 CAC 与交付成本通常更高，需按季度复盘。', 7.24, 5.82, 5.20, 0.38, { fontSize: 9.5, color: C.red, align: 'center' });
}

// 15 Scenario and funding
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'FUNDING', '200 万元资源，换取两项关键验证', '融资或等值产业资源用于完成真实课程效果验证与可复制商业交付。');
  const alloc = [
    ['产品与研发', 45, C.teal], ['试点交付', 25, C.orange], ['市场拓展', 15, C.green], ['合规与安全', 10, '6FA9B4'], ['预备金', 5, C.gray]
  ];
  let ax = 0.68;
  alloc.forEach((a) => {
    const w = 5.82 * a[1] / 100;
    s.addShape(pptx.ShapeType.rect, { x: ax, y: 2.05, w, h: 0.66, fill: { color: a[2] }, line: { color: C.white, width: 0.8 } });
    ax += w;
  });
  addText(s, '200 万元', 0.68, 1.56, 2.2, 0.40, { fontSize: 20, bold: true, color: C.navy });
  alloc.forEach((a, i) => {
    const y = 3.05 + i * 0.54;
    s.addShape(pptx.ShapeType.ellipse, { x: 0.72, y: y + 0.06, w: 0.18, h: 0.18, fill: { color: a[2] }, line: { color: a[2] } });
    addText(s, a[0], 1.03, y, 1.55, 0.30, { fontSize: 10.5, color: C.ink });
    addText(s, `${a[1]}%`, 2.65, y, 0.55, 0.30, { fontSize: 11.5, bold: true, color: a[2], align: 'right' });
  });
  card(s, 6.88, 1.55, 5.78, 4.55, { fill: C.navy, line: C.navy });
  addText(s, '18 个月验收目标', 7.22, 1.88, 2.35, 0.40, { fontSize: 18, bold: true, color: C.white });
  const goals = [
    ['01', '完成不少于 2 门真实课程的对照式效果验证'],
    ['02', '形成可复制实施包并获得 6 所付费院校'],
    ['03', '验证 SaaS 毛利、交付周期与续费意愿'],
    ['04', '完成数据合规基线与模型成本治理机制']
  ];
  goals.forEach((g, i) => {
    const y = 2.58 + i * 0.74;
    pill(s, g[0], 7.22, y, 0.55, i === 0 ? C.orange : C.teal);
    addText(s, g[1], 7.97, y - 0.01, 4.10, 0.36, { fontSize: 11.2, bold: true, color: C.white });
  });
  addText(s, '若关键指标未达标：收缩硬件投入，优先保留软件试点与课程共建能力。', 7.24, 5.55, 4.85, 0.34, { fontSize: 9, color: 'B8D7DA', align: 'center' });
}

// 16 Hardware
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'HARDWARE', 'PLEX Edge：低打扰的学习交互终端', '硬件不是主业务前提，而是为课堂签到、任务提醒、学习节奏与状态反馈提供可选入口。');
  card(s, 0.66, 1.58, 5.25, 4.74, { fill: C.navy, line: C.navy });
  s.addShape(pptx.ShapeType.roundRect, { x: 1.45, y: 2.02, w: 3.66, h: 2.20, rectRadius: 0.18, fill: { color: '173C4B' }, line: { color: C.mint, width: 1.6 }, shadow: shadow() });
  s.addShape(pptx.ShapeType.roundRect, { x: 1.83, y: 2.37, w: 2.90, h: 1.02, rectRadius: 0.08, fill: { color: 'D9F3EF' }, line: { color: C.teal, width: 1 } });
  addText(s, '今日任务  3 / 5', 1.97, 2.56, 2.62, 0.35, { fontSize: 13, bold: true, color: C.navy, align: 'center' });
  ['A', 'B', 'C', 'D'].forEach((b, i) => {
    s.addShape(pptx.ShapeType.ellipse, { x: 1.72 + i * 0.83, y: 3.60, w: 0.48, h: 0.48, fill: { color: i === 1 ? C.orange : C.teal }, line: { color: C.white, width: 0.7 } });
    addText(s, b, 1.72 + i * 0.83, 3.60, 0.48, 0.48, { fontSize: 10, bold: true, color: C.white, align: 'center' });
  });
  addText(s, 'ESP32-S3 · NFC · 屏幕 · 4 键 · RGB', 1.17, 4.55, 4.26, 0.34, { fontSize: 11, bold: true, color: C.mint, align: 'center' });
  addText(s, '默认不配置摄像头与麦克风，降低隐私与部署复杂度', 1.12, 5.05, 4.36, 0.45, { fontSize: 9.5, color: C.white, align: 'center' });
  pill(s, '工程候选方案', 2.13, 5.65, 2.05, C.orange);
  const hrows = [
    ['价值假设', '比手机更低打扰；在教室与自习场景提供轻量反馈'],
    ['目标售价', '999–1,299 元 / 台'],
    ['量产前门槛', '样机稳定性、BOM、续航、联网、需求与售后验证'],
    ['止损机制', '若采用率或单位经济不成立，保持软件优先，不进入量产']
  ];
  hrows.forEach((r, i) => {
    const y = 1.66 + i * 1.05;
    card(s, 6.23, y, 6.42, 0.82, { fill: i === 3 ? C.paleOrange : C.white, shadow: false });
    addText(s, r[0], 6.48, y + 0.14, 1.28, 0.28, { fontSize: 10.5, bold: true, color: i === 3 ? C.orange : C.teal });
    addText(s, r[1], 7.85, y + 0.09, 4.48, 0.42, { fontSize: 10.5, bold: true, color: C.ink });
  });
  addText(s, '本页为方案设计，不代表已完成实物打样、检测认证或量产。', 6.25, 6.03, 6.37, 0.38, { fontSize: 11, bold: true, color: C.red, align: 'center' });
}

// 17 Risks + roadmap
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'RISK & ROADMAP', '把风险写进路线图，而不是藏在附录里', '每项重大风险都有验证指标、责任动作和退出机制。');
  const risks = [
    ['采购周期', '用小额课程试点切入，提前建立预算与采购节奏'],
    ['学习效果', '前测/后测 + 完成率 + 教师评价，避免只看活跃度'],
    ['AI 可信', '教师审核、引用追踪、规则校验与可替换模型'],
    ['数据合规', '最小化收集、分级权限、日志与数据返还机制'],
    ['硬件风险', '阶段门控制：样机—小批—量产，未达标即停止']
  ];
  risks.forEach((r, i) => {
    const y = 1.56 + i * 0.83;
    pill(s, r[0], 0.68, y + 0.09, 1.24, i === 4 ? C.orange : C.teal);
    addText(s, r[1], 2.10, y, 4.14, 0.50, { fontSize: 10.5, bold: true, color: C.ink });
    s.addShape(pptx.ShapeType.line, { x: 0.68, y: y + 0.68, w: 5.66, h: 0, line: { color: C.line, width: 0.5 } });
  });
  card(s, 6.65, 1.56, 5.98, 4.50, { fill: C.navy, line: C.navy });
  addText(s, '18 个月路线图', 6.98, 1.87, 2.1, 0.38, { fontSize: 17, bold: true, color: C.white });
  const road = [
    ['M1–3', '试点准备', '指标、课程与数据边界'],
    ['M4–8', '真实验证', '2 门课程、前后测、教师节时'],
    ['M9–12', '商业转化', '标准合同、6 所付费院校'],
    ['M13–18', '规模复制', '扩课程、渠道与交付体系']
  ];
  road.forEach((r, i) => {
    const y = 2.45 + i * 0.78;
    addText(s, r[0], 6.98, y, 0.80, 0.30, { fontSize: 9.5, bold: true, color: i === 2 ? C.orange : C.mint });
    addText(s, r[1], 7.92, y, 1.32, 0.30, { fontSize: 11, bold: true, color: C.white });
    addText(s, r[2], 9.38, y, 2.78, 0.30, { fontSize: 9.5, color: 'B8D7DA' });
  });
  addText(s, '决策原则：软件价值成立后再放大硬件；效果证据优先于功能数量。', 6.98, 5.61, 5.20, 0.30, { fontSize: 9.5, bold: true, color: C.orange, align: 'center' });
}

// 18 Sources and assumptions
{
  const s = pptx.addSlide('LIGHT');
  title(s, 'APPENDIX', '数据来源与测算口径', '外部事实引用官方公开信息；经营数字均为内部模型，需以后续试点和合同验证。');
  card(s, 0.65, 1.52, 6.00, 4.82);
  addText(s, '主要公开来源', 0.95, 1.82, 2.0, 0.38, { fontSize: 17, bold: true, color: C.navy });
  const sources = [
    ['01', '教育部《2025年全国教育事业发展统计公报》', 'moe.gov.cn｜院校与在校生规模'],
    ['02', '《教育强国建设规划纲要（2024—2035年）》', 'moe.gov.cn｜教育数字化政策方向'],
    ['03', '九部门《关于加快推进教育数字化的意见》', 'moe.gov.cn｜智能化应用与治理'],
    ['04', '2026 年全国教育数字化工作会议', 'moe.gov.cn｜智能化、集成化、国际化'],
    ['05', '《个人信息保护法》与生成式 AI 暂行办法', 'gov.cn / cac.gov.cn｜数据与 AI 合规']
  ];
  sources.forEach((r, i) => {
    const y = 2.37 + i * 0.70;
    pill(s, r[0], 0.95, y, 0.48, i === 0 ? C.orange : C.teal);
    addText(s, r[1], 1.60, y - 0.03, 4.56, 0.30, { fontSize: 10.5, bold: true, color: C.ink });
    addText(s, r[2], 1.60, y + 0.28, 4.56, 0.24, { fontSize: 8.2, color: C.muted });
  });
  card(s, 6.90, 1.52, 5.76, 4.82, { fill: C.navy, line: C.navy });
  addText(s, '内部测算口径', 7.23, 1.82, 2.25, 0.38, { fontSize: 17, bold: true, color: C.white });
  const assumptions = [
    ['市场规模', '院校数 × 年均合同额，自下而上计算'],
    ['SOM', '第 3 年 60 所付费院校 × 18 万元 SaaS'],
    ['财务预测', '基准情景；未计融资、税费与营运资金波动'],
    ['单位经济', '规模化目标值，试点期 CAC 与交付成本更高'],
    ['硬件', '价格、销量与成本均须经样机和小批量验证']
  ];
  assumptions.forEach((a, i) => {
    const y = 2.38 + i * 0.70;
    addText(s, a[0], 7.24, y, 1.12, 0.30, { fontSize: 10.5, bold: true, color: i === 4 ? C.orange : C.mint });
    addText(s, a[1], 8.48, y - 0.02, 3.72, 0.38, { fontSize: 10.2, bold: true, color: C.white });
    s.addShape(pptx.ShapeType.line, { x: 7.24, y: y + 0.48, w: 4.96, h: 0, line: { color: '31515D', width: 0.6 } });
  });
  addText(s, '完整链接、计算过程与风险说明见同目录 Word / PDF 源材料；本 PPTX 为比赛上传版。', 0.68, 6.48, 11.98, 0.28, { fontSize: 8.3, color: C.gray, align: 'center' });
}

// 19 Team and close
{
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  image(s, '中央调控.png', 7.1, 0, 6.23, 7.5);
  s.addShape(pptx.ShapeType.rect, { x: 7.1, y: 0, w: 6.23, h: 7.5, fill: { color: C.navy, transparency: 23 }, line: { color: C.navy, transparency: 100 } });
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 8.05, h: 7.5, fill: { color: C.navy }, line: { color: C.navy } });
  addText(s, 'TEAM & ASK', 0.68, 0.56, 2.4, 0.28, { fontSize: 9, bold: true, color: C.orange, charSpacing: 1.4 });
  addText(s, '让每个学习者\n拥有一条可解释的成长路径', 0.68, 1.04, 6.10, 1.32, { fontSize: 29, bold: true, color: C.white, valign: 'top', breakLine: true });
  const team = [
    ['邬 / wuyeni0806', '项目统筹与技术研发'],
    ['高梦琴 / gaomengqin97-ui', 'UI、前端与产品运营'],
    ['王（待补全姓名）', '财务与商业模型'],
    ['指导教师（待补充）', '教学与项目指导']
  ];
  team.forEach((t, i) => {
    const y = 2.72 + i * 0.60;
    addText(s, t[0], 0.72, y, 2.66, 0.30, { fontSize: 10.5, bold: true, color: i < 2 ? C.mint : 'AFC4CA' });
    addText(s, t[1], 3.42, y, 2.72, 0.30, { fontSize: 10.5, color: C.white });
  });
  card(s, 0.68, 5.43, 5.70, 0.85, { fill: C.orange, line: C.orange });
  addText(s, '寻求：200 万元融资或等值试点、产业与渠道资源', 0.96, 5.60, 5.14, 0.43, { fontSize: 13, bold: true, color: C.navy, align: 'center' });
  addText(s, '真实性声明：现有功能与工程数据可通过代码、演示和证明材料核验；市场、财务和硬件数据均为规划假设，需以后续试点、合同与样机结果验证。', 0.72, 6.54, 6.05, 0.47, { fontSize: 8.5, color: 'AFC4CA', valign: 'top' });
  addText(s, 'PLEX UNIVERSE', 8.30, 5.65, 4.25, 0.62, { fontSize: 27, bold: true, color: C.white, align: 'center' });
  addText(s, '谢谢', 8.30, 6.30, 4.25, 0.40, { fontSize: 15, bold: true, color: C.mint, align: 'center' });
}

// Speaker-note-style metadata is intentionally kept out of visible slides.
for (const slide of pptx._slides) {
  slide.background = slide.background || { color: 'F5F8F8' };
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
const maxSlides = Number(process.env.PLEX_MAX_SLIDES || 0);
if (maxSlides > 0) pptx._slides = pptx._slides.slice(0, maxSlides);

(async () => {
  await pptx.writeFile({ fileName: process.env.PLEX_PPTX_OUT || OUT });
})().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
