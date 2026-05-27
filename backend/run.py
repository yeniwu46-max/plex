"""应用主入口"""
from app import create_app
import os

# 获取环境变量
env = os.getenv('FLASK_ENV', 'development')

# 创建应用
app = create_app(env)

if __name__ == '__main__':
    port = int(os.getenv('SERVER_PORT', '5000'))
    app.run(debug=True, host='0.0.0.0', port=port)
