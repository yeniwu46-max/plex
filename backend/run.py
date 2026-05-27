"""应用主入口"""
from app import create_app
import os

# 获取环境变量
env = os.getenv('FLASK_ENV', 'development')

# 创建应用
app = create_app(env)

if __name__ == '__main__':
    port = int(os.getenv('SERVER_PORT', '5000'))
    # Windows 下 debug 重载器会在 5000 上留下无路由的父进程，导致 HTTP 404
    use_reloader = os.name != 'nt' and os.getenv('FLASK_USE_RELOADER', '1') == '1'
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=use_reloader)
