# 开源软件、许可证与 AI 工具说明

项目直接依赖的名称、锁定版本、许可证、运行范围和安装状态由
`backend/scripts/generate_dependency_inventory.py` 自动生成到
`backend/reports/a3-submission/dependency-inventory.json`。前端正式栈包括 Vue、
Vite、Naive UI、Pinia、Axios、AntV G6、ECharts、Vue Flow、Monaco、Uppy、
Driver.js 和 Fuse.js；后端正式栈包括 Flask、SQLAlchemy、JWT、Alembic、
Marshmallow、PyMySQL、Requests 和 JSON Schema。

CrewAI 是独立的可选智能体运行时，不并入默认生产依赖。当前 Git 安装声明未固定到
不可变提交，验证器会将其列为警告；正式提交前应固定版本或提交哈希并复测。

开发过程中使用 AI Coding 工具辅助需求拆解、代码实现、测试设计和文档整理。所有
生成内容均由团队通过代码审查、自动化测试、运行验证和人工演示复核；最终代码、
数据、引用和答辩表述责任由参赛团队承担。不得向 AI 服务发送真实密钥或学生隐私。
