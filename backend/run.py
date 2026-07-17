"""应用主入口"""
from app import create_app
import os

# 获取环境变量
env = os.getenv('FLASK_ENV', 'development')

# 创建应用
app = create_app(env)

if __name__ == '__main__':
    port = int(os.getenv('SERVER_PORT', '5100'))
    is_windows = os.name == 'nt'
    # Windows 下 debug/重载器容易在监听端口留下无路由的旧进程，导致新接口 404
    use_debug = os.getenv('FLASK_DEBUG', '0' if is_windows else '1') == '1'
    use_reloader = (not is_windows) and os.getenv('FLASK_USE_RELOADER', '1') == '1'
    app.run(debug=use_debug, host='0.0.0.0', port=port, use_reloader=use_reloader)
