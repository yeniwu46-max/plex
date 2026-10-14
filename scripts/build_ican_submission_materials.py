from __future__ import annotations

import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ican-submission"
PDF_PATH = OUT / "PLEX-ICAN-开发日志.pdf"
ZIP_PATH = OUT / "PLEX-ICAN-其他证明材料.zip"

PRODUCT_INTRO = """# PLEX Universe 产品介绍（ICAN 网页粘贴版）

## 推荐产品名称

PLEX Universe

## 推荐一句话定位

基于多智能体协同、学习者画像与知识图谱的个性化编程学习平台。

## 产品介绍正文

PLEX Universe 是一套面向高校编程基础课程的个性化学习平台，致力于解决传统教学中“学生差异难识别、学习资源难匹配、教师干预不及时、学习效果难追踪”等问题。平台以学习者画像为起点，将知识图谱、错题复习、资源生成、学习路径推荐、教师审核与效果评估串联成可运行的教学闭环，让每名学生获得更适合自身基础、节奏与薄弱点的学习支持。

产品采用学生端、教师端和管理端三端协同设计。学生可在“探索舱”“今日委托”“知识星轨”“试炼关卡”和“探索档案”中完成任务、查看成长轨迹并获得个性化资源；教师可通过领航总览、星域观测和 Explorer 档案识别班级风险、定位薄弱知识点、发布试炼并审核智能体生成内容；管理员可统一配置智能体策略、通知、权限、数据安全和教学规则。

PLEX 的核心创新是把个性化学习从单次问答升级为持续闭环：系统综合学习记录、知识掌握度、错题与复习状态形成动态画像；多智能体按画像生成或推荐文本讲解、示例、练习、测验等多类资源；知识图谱约束知识范围与先修关系；SM-2 复习机制把错题重新带入画像、图谱和路径规划；教师始终保留审核与干预权，关键过程可追踪、可解释。

项目采用 Vue 3、Vite、Naive UI、Pinia 和 Axios 构建前端，采用 Flask、SQLAlchemy 与 JWT 构建后端，统一使用 `/api/v1` REST JSON 接口；本地支持 SQLite，生产环境面向 MySQL。当前已形成学生、教师、管理员三端可运行原型，完成 100 个知识节点、256 条唯一关系、9 个学习智能体与 8 个评分智能体的本地工程验证，并保留测试报告、版本提交、阶段总结、会议纪要和界面截图等可追溯材料。

PLEX 以“宇宙探索”为游戏化叙事，把知识点变成星轨、把练习变成试炼、把成长变成可视化档案，在降低编程初学者挫败感的同时，为教师提供可执行的教学洞察。产品可服务于高校 Python 程序设计等课程，并具备向其他学科和职业技能训练场景扩展的潜力。

## 150 字精简版（如网页编辑器字数有限）

PLEX Universe 是面向高校编程课程的个性化学习平台。系统以学习者画像和知识图谱为基础，通过多智能体协同生成或推荐讲解、示例、练习和测验，并将错题复习、路径规划、教师审核和效果评估串成闭环。学生在游戏化“星轨—试炼—成长档案”中学习，教师可定位班级风险与薄弱知识点，管理员统一管理策略、权限和数据安全。项目已形成学生、教师、管理三端可运行原型。
"""


UPLOAD_CHECKLIST = """# PLEX Universe — ICAN 校园赛上传清单

整理日期：2026-08-31

| 平台字段 | 推荐内容/文件 | 限制 | 当前结论 |
|---|---|---|---|
| 产品名称 | `PLEX Universe` | 必填 | 建议删除输入框里多余的冒号 |
| 产品海报/封面图 | `PLEX-产品封面图.png` | jpg/jpeg/png，≤8MB；建议 1200×560 | 现有图 1672×941、约 1.42MB，可上传；尺寸比例与建议值略有差异 |
| 产品介绍 | `PLEX-产品介绍-网页粘贴版.md` | 富文本 | 已提供完整版与 150 字精简版 |
| 产品说明 PPT | `../submission/artifacts/PLEX-iflytek-990-defense.pptx` | pptx，≤50MB | 仅可作候选底稿；10 页、约 0.04MB，但含旧赛事语境，未改成 ICAN 前不能直接提交 |
| 实物演示视频 | 现有视频需重剪或重录 | mp4，≤200MB，≤3分钟 | 现有视频约 6分44秒、37.47MB；体积合格、时长不合格，不能原样上传 |
| 开发日志 | `PLEX-ICAN-开发日志.pdf` | pdf，≤50MB | 已生成；包含时间线、测试、问题解决、版本迭代、团队分工与截图 |
| 其他证明材料 | `PLEX-ICAN-其他证明材料.zip` | zip，≤100MB | 已生成；包含会议纪要、Git 记录、测试报告、截图、AI 使用报告、软著初稿等 |

## 提交前必须人工补充

1. 团队成员完整姓名、学校、学院、指导教师与联系方式。
2. 财务负责人“王”的完整姓名；开发日志当前按现有分工表保留为“王（待补全）”。
3. 若有真实课堂试用，请补充教师签字证明、脱敏参与记录、前后测数据和授权说明。
4. 软著材料目前是“申请材料初稿”，不是已授权证书，答辩和申报中不得表述为“已获软著”。
5. 外部大模型、ASR/TTS、真实课程实验等未形成真实证据的指标，不应写成已完成。
"""


DEV_LOG_MD = """# PLEX Universe 开发日志

**参赛方向：** ICAN 创新赛道（校园赛）  
**产品定位：** 基于多智能体协同、学习者画像与知识图谱的个性化编程学习平台  
**记录周期：** 2026-04-15 至 2026-08-31  
**版本依据：** Git 提交记录、阶段总结、测试报告、会议纪要与界面截图

## 一、项目缘起与目标

PLEX 面向高校编程基础课程，聚焦学生差异识别、资源个性化、学习路径动态调整、教师干预和效果评估。产品以“学生画像—资源生成/推荐—教师审核—学习任务—错题复习—效果回流”为主闭环，并通过宇宙探索式游戏化设计提升持续学习意愿。

## 二、总体方案

- 前端：Vue 3 + Vite + Naive UI + Pinia + Axios。
- 后端：Flask + SQLAlchemy + JWT，REST JSON 接口统一使用 `/api/v1` 前缀。
- 数据：本地 SQLite，生产目标 MySQL；知识图谱与学习记录共同支撑路径规划。
- 角色：学生端、教师端、管理端三端隔离。
- 智能能力：学习者画像、多智能体编排、资源生成与审核、错题复习、知识图谱、学习路径重规划。

## 三、开发时间线与阶段成果

### 2026-04-15：立项与需求讨论

召开第一次项目会议，确定个性化学习、教师辅助和三端协同方向，形成早期需求与任务分解。证据：`request/0415-A3-第一次会议记录.pdf`。

### 2026-05-11—05-19：工程基线与视觉体系

搭建 Flask 后端框架，完成认证、权限、用户、班级、成就等核心模块；随后建立 Vue 3 正式前端、PLEX 主题变量与 Naive UI 覆盖，补充试炼中枢的页面与模块设计。

### 2026-05-25—05-29：学生—教师演示闭环

完成学生每日委托、试炼、知识星轨和成长档案；建设教师工作台、班级看板与 Explorer 档案；实现三端路由隔离。接入 Monaco Editor、AntV G6、ECharts、Vue Flow 等组件，并把关键统计从静态数据逐步切换至 API。

### 2026-06-08—06-12：个性化闭环与可信验证

实现学生画像、资源生成任务、教师审核、路径推送、学习前后测和三轮反馈闭环；统一课程安全检查，补充恶意上传识别、并发幂等、过期任务恢复和证据索引。形成学习效果、安全专项、性能恢复与洁净环境等机器可读报告。

### 2026-06-25—06-27：质量闭环与多智能体平台

优化学生端质量闭环，完成多智能体学习平台基线，并重构学习流程和 API 异常处理。重点解决生成任务状态不一致、角色边界不清晰和前后端响应结构不统一等问题。

### 2026-07-06—07-20：数据、星轨与智能体编排

冻结数据导入前基线；完成星轨内嵌试炼、题库智能命名、AC 进度反馈、启动迁移修复；完善教师/学生界面、多智能体可视化和管理端编排面板；形成首轮提交包构建脚本。

### 2026-07-29：流式体验与自动审批

补充对话类接口 SSE 流式体验、任务过程反馈和资源审批策略，统一学生、教师、管理端的状态展示，并沉淀日终总结和专项技术文档。

### 2026-08-26—08-28：主工程冻结与专项审计

冻结主工程题库、知识重建与学生教师体验闭环；完成 100 个知识节点、256 条唯一关系、10 类关系语义、本地无孤立节点等图谱校验；确认 9 个学习智能体与 8 个评分智能体；对 SM-2 复习、路径重规划、风险解释和教师看板进行专项审计。

## 四、实验测试与数据

### 本地工程基线（2026-06-12）

- 学习效果回放：前测 3 次错误、后测 3 次正确，正确率与掌握度变化 +100，错题变化 -3。
- 并发与恢复：8 个并发请求成功率 100%，P50 106.86ms，P95 162.03ms，幂等率 100%，仅形成 1 个任务与 5 个资源。
- 安全专项：提示注入、超课程范围、敏感内容、知识库越权、教师审核越权、非法资源类型、扩展名伪装和阻断后不持久化均通过本地验证。

以上结果来自本机隔离 SQLite 与 `local_rules` 后端，只作为本地工程基线，不等同生产 MySQL 或真实外部大模型性能。

### 2026-08-28 专项审计

- 知识图谱：100 个节点、256 条唯一关系，覆盖 10 类关系；本地校验无孤立、重复和非法引用。
- 智能体：9 个学习智能体、8 个评分智能体；具备 trace、任务步骤与重试字段。
- 学习闭环：错题、复习队列、画像、图谱与路径重规划已通过回归测试。
- 仍未完成外部验收：真实模型 100 条输出核验、ASR/TTS/数字人 30 轮实测、真实课程 ≥100 人次实验、生产 MySQL 8 洁净环境结果。

## 五、典型问题与解决过程

1. **正式前端栈易混用。** 早期外部原型存在 React 倾向，团队最终统一 Vue 3 + Vite 为正式栈，并在技术约定和仓库入口文档中固化。
2. **静态演示数据与真实接口混杂。** 通过 API 服务层、统一响应结构和阶段性数据同步，将教师统计、学生档案和资源状态逐步连接到同一后端事实源。
3. **资源生成任务可能重复或卡死。** 增加幂等保护、并发验证和过期 `running` 任务恢复，确保重复请求不产生多份资源。
4. **错题与学习路径脱节。** 引入 SM-2 复习队列与路径 due bonus，使到期错题能够影响画像、图谱和后续路径。
5. **AI 能力容易被过度宣传。** 建立证据索引，将“本地规则验收”“真实外部服务验收”“外部条件阻塞”“尚未实现”分级记录。
6. **提交材料难以复现。** 增加一键启动、环境检查、提交包构建脚本、阶段日志、机器可读测试报告和截图索引。

## 六、版本迭代摘要

Git 记录覆盖 2026-05-11 至 2026-08-26，共 31 次当前可见提交。关键版本依次为：后端基线、Vue 前端基线、学生演示闭环、教师工作台、多智能体学习平台、星轨学习闭环、提交包构建、流式体验与主工程冻结。

## 七、团队分工

- 邬（Git 主账号 `wuyeni0806`）：项目负责人、系统与后端、接口与数据、安全、部署和材料冻结；当前 Git 记录 27 次提交。
- 高梦琴（Git 账号 `高梦琴` / `gaomengqin97-ui`）：前端 UI、教师端与学生端体验、页面联调，并参与教学实验和运营协调；当前同邮箱合计 4 次提交。
- 王（完整姓名待团队补充）：预算、采购、外部服务授权、发票与投入产出材料。
- 指导教师/领导层（姓名待补充）：命题口径、学校资源协调、外部合作与最终真实性签字。

Git 提交数量仅用于说明版本可追溯性，不代表个人工作量占比。

## 八、当前状态与后续计划

当前已形成可运行的三端产品原型和较完整的本地工程证据。提交前重点任务为：把演示视频压缩至 3 分钟以内；补全团队与指导教师信息；如具备真实课堂条件，补充教师签字、脱敏参与记录和前后测；如获得外部服务权限，再补真实模型与语音链路报告。软著文件目前仅为申请材料初稿，不作为已授权证书宣传。
"""


def register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\msyh.ttc")
    bold = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("PlexCN", str(regular)))
        pdfmetrics.registerFont(TTFont("PlexCN-Bold", str(bold)))
        return "PlexCN", "PlexCN-Bold"
    fallback = Path(r"C:\Windows\Fonts\simhei.ttf")
    pdfmetrics.registerFont(TTFont("PlexCN", str(fallback)))
    return "PlexCN", "PlexCN"


def styles_for(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCN", parent=base["Title"], fontName=bold, fontSize=28,
            leading=38, textColor=colors.HexColor("#F2F8FF"), alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCN", parent=base["Normal"], fontName=regular, fontSize=12,
            leading=20, textColor=colors.HexColor("#A9C6D9"), spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1CN", parent=base["Heading1"], fontName=bold, fontSize=18,
            leading=26, textColor=colors.HexColor("#0B5C69"), spaceBefore=12,
            spaceAfter=10, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2CN", parent=base["Heading2"], fontName=bold, fontSize=13,
            leading=20, textColor=colors.HexColor("#C25B18"), spaceBefore=9,
            spaceAfter=6, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyCN", parent=base["BodyText"], fontName=regular, fontSize=9.5,
            leading=16, textColor=colors.HexColor("#243746"), spaceAfter=6,
            wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "SmallCN", parent=base["BodyText"], fontName=regular, fontSize=8,
            leading=12, textColor=colors.HexColor("#526A78"), wordWrap="CJK",
        ),
        "table": ParagraphStyle(
            "TableCN", parent=base["BodyText"], fontName=regular, fontSize=7.7,
            leading=11.5, textColor=colors.HexColor("#243746"), wordWrap="CJK",
        ),
        "table_head": ParagraphStyle(
            "TableHeadCN", parent=base["BodyText"], fontName=bold, fontSize=8,
            leading=12, textColor=colors.white, wordWrap="CJK",
        ),
        "cover_tag": ParagraphStyle(
            "CoverTagCN", parent=base["BodyText"], fontName=bold, fontSize=9,
            leading=14, textColor=colors.HexColor("#34E6C5"),
        ),
    }


def P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def rich(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def make_table(rows, widths, st, header=True):
    body = []
    for idx, row in enumerate(rows):
        style = st["table_head"] if header and idx == 0 else st["table"]
        body.append([P(str(cell), style) for cell in row])
    table = Table(body, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B9CCD5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5C69")),
    ]
    for r in range(1, len(rows)):
        if r % 2 == 0:
            commands.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F1F6F8")))
    table.setStyle(TableStyle(commands))
    return table


def add_image(story, path: Path, max_w=16.8 * cm, max_h=9.5 * cm, caption=None, st=None):
    from PIL import Image as PILImage

    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    story.append(Image(str(path), width=w * scale, height=h * scale))
    if caption and st:
        story.append(P(caption, st["small"]))
    story.append(Spacer(1, 7))


def draw_page(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(colors.HexColor("#061522"))
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    else:
        canvas.setStrokeColor(colors.HexColor("#C9D9E1"))
        canvas.line(1.8 * cm, 1.45 * cm, A4[0] - 1.8 * cm, 1.45 * cm)
        canvas.setFont("PlexCN", 7.5)
        canvas.setFillColor(colors.HexColor("#617985"))
        canvas.drawString(1.8 * cm, 1.0 * cm, "PLEX Universe · ICAN 创新赛道开发日志")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"第 {doc.page} 页")
    canvas.restoreState()


def build_pdf():
    regular, bold = register_fonts()
    st = styles_for(regular, bold)
    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        rightMargin=1.8 * cm, leftMargin=1.8 * cm,
        topMargin=1.7 * cm, bottomMargin=1.8 * cm,
        title="PLEX Universe ICAN 开发日志",
        author="PLEX 项目组",
        subject="ICAN 创新赛道提交材料",
    )
    story = []
    story.append(Spacer(1, 1.2 * cm))
    story.append(P("ICAN 创新赛道 · 校园赛提交材料", st["cover_tag"]))
    story.append(Spacer(1, 0.8 * cm))
    story.append(P("PLEX Universe", st["title"]))
    story.append(P("开发日志与工程证据摘要", st["title"]))
    story.append(P("基于多智能体协同、学习者画像与知识图谱的个性化编程学习平台", st["subtitle"]))
    story.append(Spacer(1, 0.5 * cm))
    add_image(story, ROOT / "picture" / "登录.png", max_w=17 * cm, max_h=8.6 * cm)
    cover_meta = [
        ["记录周期", "2026-04-15 至 2026-08-31"],
        ["证据依据", "Git 提交、阶段总结、测试报告、会议纪要、界面截图"],
        ["事实口径", "已验证 / 本地规则验收 / 外部条件待验证分开陈述"],
    ]
    cover_table = Table(
        [[P(a, st["cover_tag"]), P(b, st["subtitle"])] for a, b in cover_meta],
        colWidths=[3.0 * cm, 13.4 * cm],
    )
    cover_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#234252")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    story.append(P("1. 项目概述", st["h1"]))
    story.append(P("PLEX Universe 面向高校编程基础课程，聚焦学生差异识别、资源个性化、学习路径动态调整、教师干预和效果评估。产品以“学生画像—资源生成/推荐—教师审核—学习任务—错题复习—效果回流”为主闭环，并通过宇宙探索式游戏化设计提升持续学习意愿。", st["body"]))
    overview = [
        ["维度", "当前方案"],
        ["用户与场景", "学生个性化学习、教师班级诊断与干预、管理员策略与安全治理"],
        ["技术架构", "Vue 3 + Vite 前端；Flask + SQLAlchemy + JWT 后端；REST JSON / SSE"],
        ["数据基础", "SQLite 本地开发、MySQL 生产目标；学习记录、错题、画像与知识图谱"],
        ["智能闭环", "画像、资源、审核、任务、复习、路径、评估与回流"],
        ["交付形态", "学生端、教师端、管理端可运行原型及配套文档和测试证据"],
    ]
    story.append(make_table(overview, [3.1 * cm, 13.3 * cm], st))
    story.append(Spacer(1, 8))
    story.append(P("2. 总体方案与关键创新", st["h1"]))
    innovations = [
        ["创新点", "实现方式", "价值"],
        ["持续个性化闭环", "把画像、资源、教师审核、错题复习和效果回流串成流程", "避免个性化停留在一次问答"],
        ["知识图谱约束", "以节点、关系和先修结构约束推荐与路径", "提高资源与课程范围的一致性"],
        ["多智能体协同", "学习智能体、评分智能体与可追踪编排步骤", "分离生成、评估和治理职责"],
        ["教师在环", "教师审核资源、定位风险、发布试炼和跟进学生", "保留教学责任与干预权"],
        ["游戏化表达", "星轨、试炼、委托、成长档案和成就反馈", "降低初学者焦虑并增强持续性"],
    ]
    story.append(make_table(innovations, [3.5 * cm, 7.8 * cm, 5.1 * cm], st))
    story.append(Spacer(1, 8))
    add_image(story, ROOT / "picture" / "智能体编排.png", caption="图 1  管理端智能体编排界面（现有产品截图）", st=st)

    story.append(PageBreak())
    story.append(P("3. 开发时间线", st["h1"]))
    timeline = [
        ["时间", "阶段", "主要工作与交付"],
        ["04-15", "立项与需求讨论", "第一次项目会议，确定个性化学习、教师辅助与三端协同方向。"],
        ["05-11—05-19", "工程基线", "Flask 后端、认证权限、用户班级；Vue 3 前端、PLEX 视觉体系、试炼中枢设计。"],
        ["05-25—05-29", "演示闭环", "学生委托/试炼/星轨/档案；教师工作台；三端隔离；编辑器、图谱与图表组件。"],
        ["06-08—06-12", "个性化与可信验证", "画像、资源、审核、路径、前后测、三轮反馈；安全、并发、幂等、恢复与证据索引。"],
        ["06-25—06-27", "质量闭环", "学生体验优化、多智能体平台基线、学习流程和 API 异常处理重构。"],
        ["07-06—07-20", "数据与星轨", "数据导入基线、星轨内嵌试炼、AC 反馈、多智能体可视化、提交包构建。"],
        ["07-29", "流式体验", "SSE 过程反馈、资源审批策略、三端状态统一和专项技术文档。"],
        ["08-26—08-28", "冻结与审计", "题库与体验冻结；100 节点/256 关系；智能体、复习、路径、风险和教师看板审计。"],
    ]
    story.append(make_table(timeline, [2.3 * cm, 3.7 * cm, 10.4 * cm], st))
    story.append(Spacer(1, 10))
    story.append(P("版本依据", st["h2"]))
    story.append(P("Git 记录覆盖 2026-05-11 至 2026-08-26，共 31 次当前可见提交。提交主题从后端初始化、Vue 前端基线、学生/教师闭环，逐步推进至多智能体平台、知识星轨、流式体验和主工程冻结。完整提交列表已放入“其他证明材料”ZIP。", st["body"]))
    add_image(story, ROOT / "picture" / "探索舱.png", caption="图 2  学生端探索舱与学习入口", st=st)

    story.append(PageBreak())
    story.append(P("4. 阶段开发记录", st["h1"]))
    stages = [
        ("4.1 工程基线与三端角色", "完成 Flask + SQLAlchemy + JWT 后端骨架，统一 `/api/v1` 接口与 JSON 响应；正式前端确定为 Vue 3 + Vite，并将学生、教师和管理员页面按路由及权限隔离。此阶段解决了原型栈可能混用、身份边界模糊和页面风格不一致的问题。"),
        ("4.2 学生—教师教学闭环", "学生侧形成今日委托、班级试炼、知识星轨和成长档案；教师侧形成领航总览、星域观测和 Explorer 档案。教师发布试炼后，学生可接收并完成任务，学习记录回流教师看板。"),
        ("4.3 个性化资源与教师审核", "资源生成任务以学生画像和薄弱知识点为输入，产出讲解、示例、练习和测验等内容；教师审核后再进入学生学习路径。任务状态、审核角色和结果保存在后端事实源，减少前端静态状态漂移。"),
        ("4.4 错题复习与路径重规划", "针对错题与到期复习脱节，引入 SM-2 复习队列和路径 due bonus。复习状态会影响画像、知识图谱节点权重及后续路径，从而形成“错题—复习—画像—图谱—路径”闭环。"),
        ("4.5 工程可信与提交冻结", "建立本地测试报告和证据索引，将真实外部服务、本地规则和未实现能力分级；增加并发幂等、过期任务恢复、恶意上传检查、密钥扫描、一键启动和提交包构建。"),
    ]
    for title, body in stages:
        story.append(P(title, st["h2"]))
        story.append(P(body, st["body"]))
    add_image(story, ROOT / "picture" / "教师端领航总览.png", caption="图 3  教师端领航总览与班级数据看板", st=st)

    story.append(PageBreak())
    story.append(P("5. 实验测试与数据", st["h1"]))
    story.append(P("以下数据均来自仓库内保留的机器可读报告。为保证材料可信，测试环境和适用范围与结果同时标注。", st["body"]))
    tests = [
        ["测试项", "结果", "环境/边界", "证据文件"],
        ["学习效果回放", "前测3错、后测3对；正确率/掌握度 +100；错题 -3", "SQLite + local_rules；演示基线", "learning-effect.json"],
        ["并发与恢复", "8并发成功率100%；P50 106.86ms；P95 162.03ms；幂等率100%", "本机隔离环境，不代表生产性能", "performance-recovery.json"],
        ["安全专项", "8类提示注入、越权、非法资源与伪装上传检查通过", "本地规则与自动化测试", "security-validation.json"],
        ["知识图谱", "100节点、256唯一关系、10类关系；无孤立/重复/非法引用", "本地注册表与校验脚本", "2026-08-28 审计"],
        ["智能体", "9学习Agent、8评分Agent；含trace/steps/retry字段", "工程结构验证；真实模型后端待验", "agent-orchestration报告"],
        ["复习与路径", "错题→复习→画像→图谱→路径回归通过", "本地规则与测试数据", "path-replanning报告"],
    ]
    story.append(make_table(tests, [3.1 * cm, 5.2 * cm, 4.3 * cm, 3.8 * cm], st))
    story.append(Spacer(1, 10))
    story.append(P("未完成或待外部验证", st["h2"]))
    pending = [
        ["事项", "当前状态", "提交口径"],
        ["真实外部大模型 100 条核验", "缺完整真实运行证据", "不得写成已达标"],
        ["ASR/TTS/数字人 30 轮实测", "部分适配，缺全链路报告", "仅说明后续规划"],
        ["真实课程 ≥100 人次实验", "有实验方案和模板，缺真实签字与数据", "不得用模拟数据替代"],
        ["生产 MySQL 8 洁净环境", "有配置与验证脚本，外部环境结果待补", "仅陈述工程准备"],
    ]
    story.append(make_table(pending, [4.3 * cm, 6.2 * cm, 5.9 * cm], st))
    story.append(Spacer(1, 10))
    story.append(P("知识图谱完整界面截图已收录于“其他证明材料”ZIP，以避免大图在开发日志中形成空白分页。", st["small"]))

    story.append(PageBreak())
    story.append(P("6. 问题排查与解决记录", st["h1"]))
    issues = [
        ["问题", "影响", "处理方式", "结果"],
        ["正式前端栈可能混用", "维护成本与交互不一致", "统一 Vue 3 + Vite，并在项目约定中固化", "正式功能集中在 frontend/"],
        ["静态数据与真实接口混杂", "教师与学生看到的数据可能不一致", "引入 API 服务层和统一后端事实源", "核心统计与档案逐步完成联调"],
        ["生成任务重复/卡死", "资源重复或状态长期 running", "幂等键、并发验证、过期任务恢复", "本地并发与恢复报告通过"],
        ["错题不影响后续学习", "路径无法反映真实薄弱点", "SM-2 队列 + due bonus + 回归测试", "形成复习驱动路径闭环"],
        ["AI 能力宣传边界模糊", "评审难以判断证据真实性", "建立证据分级与未完成清单", "本地结果不再冒充真实模型"],
        ["材料复现困难", "提交后难安装、难查证", "一键启动、检查脚本、提交包构建、SHA256", "交付物可追溯"],
    ]
    story.append(make_table(issues, [3.4 * cm, 3.5 * cm, 6.0 * cm, 3.5 * cm], st))
    story.append(Spacer(1, 10))
    add_image(story, ROOT / "picture" / "中央调控.png", caption="图 5  管理端中央调控与系统治理界面", st=st)

    story.append(PageBreak())
    story.append(P("7. 团队协作与分工", st["h1"]))
    team = [
        ["成员/角色", "主要职责", "可追溯依据"],
        ["邬（wuyeni0806）", "项目负责人；系统、后端、接口、数据、安全、部署与材料冻结", "当前 Git 记录 27 次提交；部门分工表"],
        ["高梦琴（高梦琴 / gaomengqin97-ui）", "前端 UI、教师端与学生端体验、页面联调；参与实验与运营协调", "同邮箱合计 4 次提交；阶段文档与分工表"],
        ["王（完整姓名待补）", "预算、采购、外部服务授权、发票和投入产出材料", "部门分工表"],
        ["指导教师/领导层（待补）", "命题口径、学校资源协调、外部合作与最终真实性签字", "部门分工表；提交前补签"],
    ]
    story.append(make_table(team, [4.2 * cm, 7.6 * cm, 4.6 * cm], st))
    story.append(Spacer(1, 8))
    story.append(P("说明：Git 提交数量仅用于证明版本可追溯性，不代表工作量占比。团队完整姓名、学校、学院、指导教师和联系方式应在正式提交前由负责人补齐。", st["small"]))
    story.append(P("8. 版本迭代与证据管理", st["h1"]))
    version_rows = [
        ["版本节点", "核心变化", "对应证据"],
        ["MVP 基线", "认证、权限、用户、班级、学生/教师页面", "Git 05-11—05-29；阶段总结"],
        ["个性化基线", "画像、资源、审核、路径、前后测与安全", "Git 06-09；a3-next-stage 报告"],
        ["多智能体基线", "学习与评分智能体、编排、复习与路径", "Git 06-26—07-20；专项报告"],
        ["冻结候选版", "100节点/256关系、三端体验与提交材料", "Git 08-26；08-28 完成度审计"],
    ]
    story.append(make_table(version_rows, [3.4 * cm, 7.2 * cm, 5.8 * cm], st))

    story.append(PageBreak())
    story.append(P("9. 产品界面与证明材料索引", st["h1"]))
    add_image(story, ROOT / "picture" / "星轨.png", caption="图 6  学生端知识星轨与个性化学习路径", st=st)
    add_image(story, ROOT / "picture" / "试炼中枢.png", caption="图 7  教师端试炼中枢与教学任务发布", st=st)
    evidence = [
        ["类别", "文件/目录", "用途"],
        ["会议纪要", "request/0415-A3-第一次会议记录.pdf", "立项与早期讨论证明"],
        ["Git 记录", "其他证明材料 ZIP / 02-版本记录", "版本时间线与贡献者记录"],
        ["阶段文档", "docs/2026-05—08 系列总结", "方案、问题与迭代过程"],
        ["测试报告", "backend/reports/a3-next-stage 与 iflytek-990 本地报告", "学习效果、安全、性能、图谱与路径证据"],
        ["界面截图", "picture/ 与其他证明材料 ZIP", "学生、教师、管理端产品形态"],
        ["AI 使用报告", "docs/AI使用报告-开源项目与API调用.pdf", "工具、开源组件与 API 使用说明"],
        ["知识产权", "软著初稿.zip", "软件著作权申请材料初稿；非授权证书"],
    ]
    story.append(make_table(evidence, [3.0 * cm, 8.3 * cm, 5.1 * cm], st))

    story.append(PageBreak())
    story.append(P("10. 当前状态、后续计划与真实性说明", st["h1"]))
    story.append(P("当前已形成学生、教师、管理员三端可运行原型，具备画像、知识图谱、资源任务、审核、试炼、错题复习、路径重规划和基础评估能力，并留存阶段文档、自动化报告、Git 记录与产品截图。", st["body"]))
    next_steps = [
        ["优先级", "提交前行动", "完成标准"],
        ["P0", "重剪或重录演示视频", "MP4、≤3分钟、≤200MB、画面与声音清晰"],
        ["P0", "补全团队/学校/指导教师信息", "与报名系统和 PPT 完全一致"],
        ["P0", "人工核对 PPT 赛道名、团队名和事实口径", "无旧赛事名称、无未验证指标"],
        ["P1", "补真实课堂证据（如具备条件）", "教师签字、脱敏名单/记录、可配对前后测与授权"],
        ["P1", "补真实外部服务报告（如获权限）", "保留请求编号、模型版本、失败样本和延迟统计"],
    ]
    story.append(make_table(next_steps, [2.2 * cm, 7.1 * cm, 7.1 * cm], st))
    story.append(Spacer(1, 12))
    story.append(P("真实性声明", st["h2"]))
    story.append(P("本开发日志依据当前仓库、Git 历史、会议纪要、测试报告与截图整理。文中明确区分本地工程验证与真实外部环境验收；未取得真实凭证、真实课堂数据或授权证书的事项不表述为已完成。软著文件为申请材料初稿，不代表已经获得软件著作权登记证书。", st["body"]))
    story.append(Spacer(1, 1.0 * cm))
    sign = Table([
        [P("项目负责人签字：________________", st["body"]), P("指导教师签字：________________", st["body"])],
        [P("日期：________年____月____日", st["body"]), P("日期：________年____月____日", st["body"])],
    ], colWidths=[8.2 * cm, 8.2 * cm])
    sign.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 10)]))
    story.append(sign)

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)


def git_log_text() -> str:
    cmd = [
        "git", "log", "--date=short",
        "--pretty=format:%ad\t%h\t%an\t%s", "--reverse", "--all",
    ]
    return subprocess.check_output(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace") + "\n"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_evidence_zip():
    evidence_files = {
        "01-立项与会议/0415-A3-第一次会议记录.pdf": ROOT / "request" / "0415-A3-第一次会议记录.pdf",
        "03-阶段与验收/2026-05-26-教师工作台阶段总结.md": ROOT / "docs" / "2026-05-26-teacher-workbench-summary.md",
        "03-阶段与验收/2026-05-27-学生探索链路总结.md": ROOT / "docs" / "2026-05-27-student-exploration-summary.md",
        "03-阶段与验收/2026-06-12-证据索引.md": ROOT / "docs" / "2026-06-12-A3-evidence-index.md",
        "03-阶段与验收/2026-07-29-日终总结.md": ROOT / "docs" / "2026-07-29-end-of-day-summary.md",
        "03-阶段与验收/2026-08-28-完成度审计.md": ROOT / "docs" / "2026-08-28-iflytek-990-completion-audit.md",
        "03-阶段与验收/2026-08-28-教师看板验收.md": ROOT / "docs" / "2026-08-28-iflytek-990-teacher-dashboard-acceptance.md",
        "04-测试报告/learning-effect.json": ROOT / "backend" / "reports" / "a3-next-stage" / "learning-effect.json",
        "04-测试报告/security-validation.json": ROOT / "backend" / "reports" / "a3-next-stage" / "security-validation.json",
        "04-测试报告/performance-recovery.json": ROOT / "backend" / "reports" / "a3-next-stage" / "performance-recovery.json",
        "04-测试报告/clean-environment.json": ROOT / "backend" / "reports" / "a3-next-stage" / "clean-environment.json",
        "04-测试报告/agent-orchestration-local.json": ROOT / "backend" / "reports" / "iflytek-990-agent-orchestration-20260828.json",
        "04-测试报告/path-replanning-local.json": ROOT / "backend" / "reports" / "iflytek-990-path-replanning-20260828.json",
        "04-测试报告/risk-explainability-local.json": ROOT / "backend" / "reports" / "iflytek-990-risk-explainability-20260828.json",
        "05-产品截图/01-登录.png": ROOT / "picture" / "登录.png",
        "05-产品截图/02-学生探索舱.png": ROOT / "picture" / "探索舱.png",
        "05-产品截图/03-学生知识星轨.png": ROOT / "picture" / "星轨.png",
        "05-产品截图/04-教师领航总览.png": ROOT / "picture" / "教师端领航总览.png",
        "05-产品截图/05-教师试炼中枢.png": ROOT / "picture" / "试炼中枢.png",
        "05-产品截图/06-知识图谱.png": ROOT / "picture" / "知识图谱.png",
        "05-产品截图/07-智能体编排.png": ROOT / "picture" / "智能体编排.png",
        "05-产品截图/08-管理端中央调控.png": ROOT / "picture" / "中央调控.png",
        "06-合规与AI使用/AI使用报告-开源项目与API调用.pdf": ROOT / "docs" / "AI使用报告-开源项目与API调用.pdf",
        "06-合规与AI使用/AI-coding-tools-statement.md": ROOT / "docs" / "submission" / "AI-coding-tools-statement.md",
        "07-知识产权/软件著作权申请材料初稿-非证书.zip": ROOT / "软著初稿.zip",
    }
    readme = """# PLEX Universe 其他证明材料索引

本压缩包用于 ICAN 创新赛道“其他证明材料”上传，内容均来自项目仓库现有材料。

## 目录

1. 立项与会议：第一次会议记录。
2. 版本记录：Git 完整可见提交记录与贡献者统计。
3. 阶段与验收：阶段总结、证据索引和完成度审计。
4. 测试报告：学习效果、安全、并发恢复、智能体和路径重规划等机器可读报告。
5. 产品截图：学生、教师、管理端和知识图谱界面。
6. 合规与 AI 使用：开源项目、API 调用与 AI Coding 工具说明。
7. 知识产权：软件著作权申请材料初稿，仅证明已准备申请材料，不是授权证书。
8. 团队分工：按现有仓库记录整理的 ICAN 版本说明，正式提交前应补齐完整姓名。

## 真实性边界

- `local`、`local_rules`、SQLite 报告只证明本地工程验证，不代表真实外部模型或生产环境结果。
- 软著材料为初稿，不得宣传为“已获软件著作权”。
- 真实课程人数、教师签字、外部模型请求编号和语音链路等材料，如未取得，不应以模拟数据替代。
"""
    team_note = """# PLEX Universe 团队分工说明（ICAN 版）

- 邬（Git 主账号 `wuyeni0806`）：项目负责人；系统、后端、接口、数据、安全、部署与材料冻结。
- 高梦琴（Git 账号 `高梦琴` / `gaomengqin97-ui`）：前端 UI、教师端与学生端体验、页面联调，并参与实验与运营协调。
- 王（完整姓名待补）：预算、采购、外部服务授权、发票与投入产出材料。
- 指导教师/领导层（姓名待补）：命题口径、学校资源协调、外部合作与最终真实性签字。

说明：Git 提交数量仅用于说明版本可追溯性，不代表工作量占比。正式提交前请补齐所有成员完整姓名、学校、学院、专业、联系方式和指导教师信息。
"""
    hashes = []
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("00-说明/README-证据索引.md", readme)
        zf.writestr("02-版本记录/git-提交记录.txt", git_log_text())
        zf.writestr("08-团队分工/ICAN-团队分工说明.md", team_note)
        for arcname, source in evidence_files.items():
            if not source.exists():
                raise FileNotFoundError(source)
            zf.write(source, arcname)
            hashes.append(f"{sha256(source)}  {arcname}")
        zf.writestr("00-说明/SHA256SUMS.txt", "\n".join(hashes) + "\n")


def write_text_files():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "PLEX-产品介绍-网页粘贴版.md").write_text(PRODUCT_INTRO, encoding="utf-8")
    (OUT / "PLEX-ICAN-上传清单.md").write_text(UPLOAD_CHECKLIST, encoding="utf-8")
    (OUT / "PLEX-ICAN-开发日志-可编辑源稿.md").write_text(DEV_LOG_MD, encoding="utf-8")
    shutil.copy2(ROOT / "picture" / "登录.png", OUT / "PLEX-产品封面图.png")


def main():
    write_text_files()
    build_pdf()
    build_evidence_zip()
    print(f"generated: {OUT}")
    for path in sorted(OUT.iterdir()):
        print(f"{path.name}\t{path.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
