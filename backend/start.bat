@echo off
REM 启动学习系统后端
REM 确保在 backend 目录下执行

cd /d "%~dp0"

echo ========================================
echo 学习系统后端 - 启动脚本
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

echo [1/4] 检查依赖包...
pip list | find "Flask" >nul 2>&1
if errorlevel 1 (
    echo [需要安装依赖]
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 安装失败，请检查网络连接
        pause
        exit /b 1
    )
) else (
    echo [✓] 依赖已就绪
)

echo.
echo [2/4] 初始化数据库...
python init_db.py
if errorlevel 1 (
    echo 数据库初始化失败
    pause
    exit /b 1
)

echo.
echo [3/4] 等待 Flask 启动...
timeout /t 2 /nobreak

echo.
echo [4/4] 启动服务...
echo ========================================
echo 服务正在启动... 请访问: http://localhost:5000
echo.
echo 测试账户:
echo   用户名: admin
echo   密码: admin123
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

python run.py

pause
