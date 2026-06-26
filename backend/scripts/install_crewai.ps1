# 从 GitHub 安装 CrewAI 到 Python 3.12 虚拟环境（PLEX 多智能体）
$ErrorActionPreference = 'Stop'
$BackendRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $BackendRoot '.venv-crewai'
$Py312 = 'py -3.12'

Write-Host ">> 创建/使用虚拟环境: $VenvPath"
& $Py312 -m venv $VenvPath
$Python = Join-Path $VenvPath 'Scripts\python.exe'
$Pip = Join-Path $VenvPath 'Scripts\pip.exe'

& $Python -m pip install --upgrade pip
& $Pip install "git+https://github.com/crewAIInc/crewAI.git@5cdc420c50cf9cb9ca12b50fdba3125377743a53#subdirectory=lib/crewai"

Write-Host ">> 验证安装..."
& $Python -c "import crewai; from crewai import Agent, Crew; print('crewai', crewai.__version__, 'OK')"

Write-Host ""
Write-Host "完成。启用方式："
Write-Host "  set AGENT_BACKEND=auto   # 或 crewai"
Write-Host "  set OPENAI_API_KEY=sk-...  # 真实 LLM 推理时需要"
Write-Host "Flask 仍可用 Python 3.14 启动，CrewAI 会从 .venv-crewai 自动加载。"
