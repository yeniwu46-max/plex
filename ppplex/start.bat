@echo off
cd /d "%~dp0"
if not exist "node_modules\" (
  echo [PPPLEX] 首次运行，正在安装依赖...
  call npm install
  if errorlevel 1 exit /b 1
)
echo [PPPLEX] 启动答辩导航站 http://localhost:5174
echo [PPPLEX] 请保持本窗口打开；关闭窗口即停止服务
call npm run dev
