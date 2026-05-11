#!/bin/bash
# 启动学习系统后端

cd "$(dirname "$0")"

echo "========================================"
echo "学习系统后端 - 启动脚本"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python，请先安装 Python"
    exit 1
fi

echo "[1/4] 检查依赖包..."
pip list | grep -q Flask
if [ $? -ne 0 ]; then
    echo "[需要安装依赖]"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "安装失败，请检查网络连接"
        exit 1
    fi
else
    echo "[✓] 依赖已就绪"
fi

echo ""
echo "[2/4] 初始化数据库..."
python3 init_db.py
if [ $? -ne 0 ]; then
    echo "数据库初始化失败"
    exit 1
fi

echo ""
echo "[3/4] 等待 Flask 启动..."
sleep 2

echo ""
echo "[4/4] 启动服务..."
echo "========================================"
echo "服务正在启动... 请访问: http://localhost:5000"
echo ""
echo "测试账户:"
echo "  用户名: admin"
echo "  密码: admin123"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"
echo ""

python3 run.py
