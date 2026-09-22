from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "submission" / "PLEX-国创赛项目状态与部门分工-2026-09-07.xlsx"

NAVY = "17365D"
BLUE = "D9EAF7"
LIGHT_BLUE = "EAF3F8"
GREEN = "E2F0D9"
YELLOW = "FFF2CC"
RED = "FCE4D6"
GRAY = "F2F2F2"
WHITE = "FFFFFF"
THIN = Side(style="thin", color="B7C9D6")


def style_sheet(ws, widths):
    ws.freeze_panes = "A3"
    ws.sheet_view.showGridLines = False
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    for row in ws.iter_rows():
        for cell in row:
            cell.font = Font(name="Arial", size=10, color="000000")
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=THIN)


def title(ws, text, end_col):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    c = ws.cell(1, 1, text)
    c.font = Font(name="Arial", size=15, bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 28


def header(ws, row, values):
    for col, value in enumerate(values, 1):
        c = ws.cell(row, col, value)
        c.font = Font(name="Arial", size=10, bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor="2F75B5")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = Border(top=THIN, bottom=THIN)
    ws.row_dimensions[row].height = 30


def fill_status(ws, column, start, end):
    rng = f"{column}{start}:{column}{end}"
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"已验证"'], fill=PatternFill("solid", fgColor=GREEN)))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"进行中"'], fill=PatternFill("solid", fgColor=YELLOW)))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"待外部证据"'], fill=PatternFill("solid", fgColor=RED)))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"未开始"'], fill=PatternFill("solid", fgColor=GRAY)))


def build():
    wb = Workbook()
    overview = wb.active
    overview.title = "总览"
    title(overview, "PLEX × 科大讯飞新工科990｜项目状态与部门分工（DDL 2026-09-07）", 6)
    overview.append([])
    overview.append(["项目", "命题", "审计日期", "本次DDL", "最终DDL", "当前结论"])
    overview.append(["PLEX个性化学习平台", "大模型与多智能体技术在智慧教育个性化学习中的应用创新", date(2026, 8, 29), date(2026, 9, 7), date(2026, 10, 1), "本地工程证据通过；外部证据未闭环"])
    overview.append([])
    overview.append(["关键指标", "原版基线", "当前版本", "目标", "证据/文件", "状态"])
    metrics = [
        ["学习者画像维度", 8, 8, ">=6", "student_profile.py；本地评测报告", "已验证"],
        ["知识图谱节点", 26, 100, ">=100", "knowledge_node_registry.py；kg-validation报告", "已验证"],
        ["知识图谱关系", 35, 256, ">=200", "kg_topology.py；kg-validation报告", "已验证"],
        ["学习/评分Agent", "9/8", "9/8", ">=4专业Agent", "agent_registry.py；orchestration报告", "已验证"],
        ["资源类型", 6, 6, ">=5", "pedagogical_resource.py；RAG本地报告", "已验证"],
        ["SM-2复习闭环", "无标准化队列", "错题→到期队列→复习回写", "四联动", "mistake.py；测试7项", "已验证"],
        ["Spark真实调用", "未接入证据", "Pro配置模板/脚本已就绪", "100条真实调用", "evaluate_iflytek_live.py", "待外部证据"],
        ["ASR/TTS/数字人", "仅局部适配器", "TTS适配器与埋点", "30轮全链路/P95", "evaluate_voice_pipeline.py", "待外部证据"],
        ["真实教学实验", "无", "空白脱敏事件模板", ">=100人次", "data/experiments；analyze脚本", "待外部证据"],
        ["MySQL 8洁净环境", "未验证", "compose与验证脚本", "MySQL 8迁移/登录/闭环", "docker-compose.mysql8.yml", "待外部证据"],
        ["路演材料", "Markdown稿", "PPTX已生成；正式MP4缺失", "PPTX+MP4", "artifacts/PLEX-iflytek-990-defense.pptx", "进行中"],
    ]
    for row in metrics:
        overview.append(row)
    overview.append([])
    overview.append(["审计口径", "只有当前代码、自动化测试、运行记录或真实实验材料可直接证明的内容计为已完成；Mock、合成学生和静态截图不能关闭外部指标。"])
    overview.merge_cells(start_row=overview.max_row, start_column=2, end_row=overview.max_row, end_column=6)
    style_sheet(overview, [24, 24, 26, 22, 48, 18])
    overview["A3"].font = overview["A8"].font = Font(name="Arial", size=10, bold=True, color=WHITE)
    for row in (3, 5):
        for cell in overview[row]:
            cell.fill = PatternFill("solid", fgColor="2F75B5")
            cell.font = Font(name="Arial", size=10, bold=True, color=WHITE)
    for r in range(6, 6 + len(metrics)):
        overview.cell(r, 2).number_format = "0"
    fill_status(overview, "F", 6, 5 + len(metrics))

    changes = wb.create_sheet("原版-当前版改动")
    title(changes, "原版到当前版：已完成改动与可验证证据", 7)
    header(changes, 2, ["领域", "原版状态", "当前版改动", "带来的能力", "验证证据", "当前状态", "备注"])
    rows = [
        ["知识图谱", "8领域/26节点/35关系", "扩充注册表与拓扑至100节点、256唯一边，增加完整性校验", "满足节点/关系硬指标并支持路径重规划", "validate_knowledge_graph.py；iflytek-990-kg-validation-20260828.json", "已验证", "仍需教师人工审核语义"],
        ["多智能体", "9学习Agent、8评分Agent，但缺统一审计材料", "补充编排trace、依赖、重试和任务步骤报告", "可展示4+专业Agent协作过程", "evaluate_agent_orchestration.py；orchestration报告", "已验证", "跨进程队列压测仍可增强"],
        ["个性化路径", "静态/基础路径逻辑", "加入画像、错题、掌握度与SM-2到期奖励的动态重规划", "错题复习会影响后续学习路径", "evaluate_path_replanning.py；path-replanning报告", "已验证", "需浏览器端到端录像"],
        ["错题复习", "有错题记录，缺标准化复习调度", "新增质量分、复习间隔、到期队列和复习回写API", "形成考试—错题—复习闭环骨架", "mistake.py；test_mistakes.py（7项）", "已验证", "真实课程数据尚缺"],
        ["资源/RAG", "资源类型与规则管线基础能力", "固化6类资源、知识图谱约束和本地幻觉检测报告", "可审计多模态资源生成与引用约束", "pedagogical_resource.py；hallucination-local报告", "已验证", "100条真实输出核验未完成"],
        ["教师侧", "基础教师数据接口", "增加风险摘要、可解释因子和工单读写接口", "支持教师发现风险并安排干预", "TeacherHomeView.vue；risk报告", "进行中", "前端指派/复核/关闭全流程待验收"],
        ["讯飞接入", "凭证/模型口径不统一", "统一Spark Pro generalv3配置、APIPassword调用脚本和脱敏模板", "具备真实调用验收入口", "evaluate_iflytek_live.py；16-external-evidence-handoff.md", "待外部证据", "真实凭证必须旋转后本机注入"],
        ["发布工程", "无MySQL8洁净验证和冻结闸门", "新增MySQL8 compose、验证脚本、发布清单与就绪检查", "可复核部署、依赖和冻结状态", "docker-compose.mysql8.yml；verify_mysql8_environment.py", "待外部证据", "当前Docker引擎不可用"],
    ]
    for r in rows: changes.append(r)
    style_sheet(changes, [16, 28, 46, 38, 46, 18, 30])
    fill_status(changes, "F", 3, 2 + len(rows))

    todo = wb.create_sheet("待修改清单")
    title(todo, "DDL 2026-09-07 前必须关闭的修改与证据", 9)
    header(todo, 2, ["优先级", "待修改/待补证据", "具体动作", "验收标准", "责任部门", "输入依赖", "交付物", "DDL", "状态"])
    rows = [
        ["P0", "Spark Pro真实调用", "旋转泄露凭证；本机注入新APIPassword；执行100条并保存脱敏日志", "成功/解析/引用约束统计完整，模型与请求ID可追溯", "技术部", "企业/指导老师提供额度", "iflytek-990-live-final.json", date(2026,9,3), "待外部证据"],
        ["P0", "ASR+情感TTS+数字人", "取得ASR、情感TTS、数字人权限；跑30轮并记录首Token/P50/P95", "ASR识别、情感TTS、唇音同步可演示；P95≤1.5s或给出差距说明", "技术部/产品部", "讯飞接口权限、测试设备", "iflytek-990-voice-final.json；录屏", date(2026,9,4), "待外部证据"],
        ["P0", "真实教学实验", "锁定课程与教师；脱敏participant_id；采集前测/干预/后测≥100人次", "配对规则、退出/缺失处理、效果对比和教师证明齐全", "运营部/财务部", "学校授权、课程排期", "iflytek-990-experiment-final.json；教师证明", date(2026,9,5), "待外部证据"],
        ["P0", "MySQL8洁净环境", "修复Docker Desktop；启动compose；迁移、种子、登录、资源与反馈闭环", "verify_mysql8_environment.py通过且报告mysql8=true", "技术部", "Docker引擎可用", "mysql-clean-environment.json", date(2026,9,2), "待外部证据"],
        ["P1", "教师工单前端闭环", "完成指派→处理中→复核→关闭；录制教师浏览器验收", "工单状态与风险原因、干预完成率可追溯", "产品部/技术部", "教师验收账号", "teacher-dashboard-acceptance.mp4", date(2026,9,5), "进行中"],
        ["P1", "真实输出幻觉率", "构建100条统一事实集；对真实Spark输出做RAG/图谱引用核验", "幻觉率≤5%，报告保留失败样例和修正策略", "技术部/产品部", "Spark真实调用报告", "iflytek-990-hallucination-final.json", date(2026,9,5), "待外部证据"],
        ["P1", "正式路演MP4", "按脚本录制7分钟；去除浏览器个人信息弹窗；三轮彩排", "文件名/时长/分辨率符合提交要求，演示链路可复现", "运营部/产品部", "稳定部署、教师验收", "PLEX-A3-demo.mp4", date(2026,9,6), "进行中"],
        ["P1", "冻结发布包", "完成上述证据后重新生成manifest，清理临时文件并打包", "submission_ready=true；工作树干净；SHA一致", "领导层/技术部", "全部P0/P1证据", "最终提交ZIP+SHA256", date(2026,9,7), "未开始"],
    ]
    for r in rows: todo.append(r)
    style_sheet(todo, [10, 24, 46, 42, 18, 30, 38, 14, 18])
    for r in range(3, 3 + len(rows)):
        todo.cell(r, 8).number_format = "yyyy-mm-dd"
    fill_status(todo, "I", 3, 2 + len(rows))

    depts = wb.create_sheet("部门分工")
    title(depts, "按部门拆解：每个部门在9月7日前要交付什么", 7)
    header(depts, 2, ["部门", "核心职责", "本周具体任务", "必须交付", "量化验收", "协作对象", "负责人建议"])
    rows = [
        ["技术部", "系统、接口、数据、安全与发布", "修复Docker并完成MySQL8；旋转并注入讯飞凭证；跑Spark/ASR/TTS/数字人；补教师工单前端；执行全量测试与冻结", "5类真实报告、洁净环境报告、最终发布包", "Spark 100条；语音30轮；MySQL8通过；P95≤1.5s（或差距说明）", "产品部/运营部/领导层", "后端负责人+部署负责人"],
        ["财务部", "预算、采购、合规与投入产出", "确认讯飞额度/服务采购；记录API、设备、录制与实验成本；核对发票和授权；形成单项目成本表", "预算执行表、采购/授权凭证、ROI摘要", "费用有合同/发票；每项外部服务有用途与有效期", "技术部/运营部", "财务接口人"],
        ["运营部", "学校、教师、学生与实验组织", "锁定真实课程和教师；安排≥100人次；发放知情说明；组织前后测、满意度和教师证明；统筹录屏彩排", "脱敏实验CSV、教师证明、签到/排期、MP4", "participant_count≥100；前后测可配对；录屏无个人隐私", "产品部/技术部/领导层", "实验运营负责人"],
        ["产品部", "命题对齐、体验、验收与材料", "把指标转成验收脚本；验收画像/路径/复习/工单；维护事实核验集；编排7分钟故事线和PPT/MP4", "验收清单、事实集、最终PPT/脚本/MP4", "8项核心指标逐项有证据；演示不超过7分钟", "技术部/运营部", "产品经理+答辩主讲"],
        ["领导层", "资源协调、风险决策与最终签字", "确认命题口径和学校合作；协调讯飞企业联系人；审批预算；每48小时检查P0；在冻结前签署证据真实性声明", "资源确认单、风险决策记录、最终签字版材料", "P0按期关闭；无未授权数据/密钥；提交包可追溯", "全体部门", "项目负责人/指导老师"],
    ]
    for r in rows: depts.append(r)
    style_sheet(depts, [14, 28, 54, 38, 36, 24, 22])

    plan = wb.create_sheet("倒排计划")
    title(plan, "倒排计划：2026-08-29 至 2026-09-07", 6)
    header(plan, 2, ["日期", "当天目标", "关键动作", "验收证据", "主责", "风险/应对"])
    rows = [
        [date(2026,8,29), "冻结缺口与责任", "确认部门负责人、权限、课程和凭证轮换窗口", "本Excel+外部证据清单", "领导层", "无人负责→当天明确单一责任人"],
        [date(2026,8,30), "环境与接口就绪", "修复Docker；确认Spark/ASR/TTS/数字人权限；准备测试设备", "docker info、权限截图（不含密钥）", "技术部", "Docker仍失败→领导层升级IT支持"],
        [date(2026,8,31), "MySQL8闭环", "启动compose、迁移、种子、登录、资源/反馈/教师流程", "mysql-clean-environment.json", "技术部", "迁移失败→固定镜像与回滚日志"],
        [date(2026,9,1), "Spark真实基准", "执行100条Pro调用，保存脱敏请求/响应摘要", "iflytek-990-live-final.json", "技术部", "限流→分批并记录重试"],
        [date(2026,9,2), "语音链路", "ASR→LLM→情感TTS→数字人30轮；采集延迟", "voice-final.json+原始日志", "技术部/产品部", "设备不兼容→备用浏览器/设备"],
        [date(2026,9,3), "课程实验启动", "完成知情说明与前测，开始干预并采集脱敏事件", "实验登记与首批CSV", "运营部", "参与不足→扩展平行班级"],
        [date(2026,9,4), "教师验收", "跑风险看板、工单全流程；录浏览器验收", "teacher-dashboard-acceptance.mp4", "产品部/技术部", "隐私弹窗→全新浏览器用户档案"],
        [date(2026,9,5), "实验与事实核验收口", "达到100人次；真实输出100条事实核验；整理效果统计", "experiment-final、hallucination-final", "运营部/技术部", "缺失数据→按预设排除规则记录"],
        [date(2026,9,6), "路演彩排", "录制7分钟MP4，三轮彩排，财务核对成本与授权", "正式MP4、彩排记录、成本表", "运营部/产品部/财务部", "时长超标→按脚本删减"],
        [date(2026,9,7), "冻结提交包", "重新生成manifest、清理临时文件、SHA256、领导签字", "submission_ready=true；最终ZIP", "领导层/技术部", "任何P0未关闭→不上线宣称达标"],
    ]
    for r in rows: plan.append(r)
    style_sheet(plan, [14, 22, 52, 40, 22, 34])
    for r in range(3, 3 + len(rows)):
        plan.cell(r, 1).number_format = "yyyy-mm-dd"

    # Consistent row heights and metadata.
    for ws in wb.worksheets:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.oddFooter.center.text = "PLEX｜内部项目管理资料｜请勿写入真实密钥或学生身份信息"
        for row in range(3, ws.max_row + 1):
            ws.row_dimensions[row].height = 42
    overview.sheet_properties.tabColor = NAVY
    changes.sheet_properties.tabColor = "5B9BD5"
    todo.sheet_properties.tabColor = "ED7D31"
    depts.sheet_properties.tabColor = "70AD47"
    plan.sheet_properties.tabColor = "A5A5A5"
    wb.save(OUTPUT)

    # Reopen to ensure the workbook is structurally readable and formula cells exist.
    check = load_workbook(OUTPUT, data_only=False)
    assert check.sheetnames == ["总览", "原版-当前版改动", "待修改清单", "部门分工", "倒排计划"]
    check.close()
    print(OUTPUT)


if __name__ == "__main__":
    build()
